"""Loads the Olist SQLite file into Postgres: `python -m olist_agent.loader`.

Environment: DATABASE_URL (an admin DSN), OLIST_SQLITE (the source file), and optionally
APP_DB_ROLE / APP_DB_PASSWORD, the web app's login role, which may only read `sim`.

Must never import olist_agent.main: the loader job shouldn't pay for web or telemetry
imports. tests/test_loader.py enforces it.
"""

import hashlib
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import psycopg
from psycopg import sql

MIGRATIONS = sorted((Path(__file__).parent / "migrations").glob("*.sql"))
TABLES = [
    "customers",
    "geolocation",
    "order_items",
    "order_payments",
    "order_reviews",
    "orders",
    "products",
    "sellers",
    "product_category_name_translation",
    "leads_qualified",
    "leads_closed",
]

# Repaired timestamps: each stage no earlier than the stages before it. greatest() skips
# NULLs, so a missing stage is skipped over and a missing timestamp stays missing.
REPAIR_ORDERS = """
truncate raw.order_lifecycle;
insert into raw.order_lifecycle
select order_id, a.ts, c.ts, d.ts,
    (a.ts, c.ts, d.ts) is distinct from
    (order_approved_at, order_delivered_carrier_date, order_delivered_customer_date)
from raw.orders,
    lateral (select case when order_approved_at is not null
        then greatest(order_approved_at, order_purchase_timestamp) end) a(ts),
    lateral (select case when order_delivered_carrier_date is not null
        then greatest(order_delivered_carrier_date, a.ts, order_purchase_timestamp) end) c(ts),
    lateral (select case when order_delivered_customer_date is not null
        then greatest(order_delivered_customer_date, c.ts, a.ts, order_purchase_timestamp) end
    ) d(ts)
"""


def sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def migrations_sha256() -> str:
    h = hashlib.sha256()
    for m in MIGRATIONS:
        h.update(m.name.encode() + m.read_bytes())
    return h.hexdigest()


def load(
    dsn: str, source: Path | None, app_role: str | None = None, app_password: str | None = None
) -> str:
    """Brings the database up to date with the migrations and the source file.

    Returns what it did: "unchanged", "no source data" or "loaded".
    """
    migrations = migrations_sha256()
    source_sha = sha256(source) if source and source.is_file() else None
    with psycopg.connect(dsn, autocommit=True) as conn:
        state = None
        if conn.execute("select to_regclass('loader.state')").fetchone() != (None,):
            state = conn.execute("select source_sha256, migrations_sha256 from loader.state")
            state = state.fetchone()
        if source_sha and state == (source_sha, migrations):
            return "unchanged"

        # Its own transaction: CREATE OR REPLACE VIEW locks the view, and readers shouldn't
        # wait out the whole load below.
        with conn.transaction():
            for m in MIGRATIONS:
                conn.execute(m.read_bytes())
            if app_role:
                ensure_app_role(conn, app_role, app_password)
        if source is None or source_sha is None:
            return "no source data"

        # One transaction: readers see the old data until the commit, never a partial load.
        with conn.transaction():
            conn.execute("create schema staging")
            with closing(sqlite3.connect(source)) as src:
                for t in TABLES:
                    copy_table(conn, src, t)
            # ponytail: TRUNCATE locks raw tables while the copy below runs (seconds for the
            # full dataset). Swap tables by rename and re-create the views if that hurts.
            swap = sql.SQL("truncate raw.{t}; insert into raw.{t} select * from staging.{t}")
            for t in TABLES:
                conn.execute(swap.format(t=sql.Identifier(t)))
            conn.execute(REPAIR_ORDERS)
            conn.execute("refresh materialized view raw.seller_first_activity")
            conn.execute("drop schema staging cascade")
            conn.execute(
                "insert into loader.state (source_sha256, migrations_sha256) values (%s, %s)"
                " on conflict (id) do update set source_sha256 = excluded.source_sha256,"
                " migrations_sha256 = excluded.migrations_sha256, loaded_at = now()",
                [source_sha, migrations],
            )
    return "loaded"


def copy_table(conn: psycopg.Connection, src: sqlite3.Connection, table: str) -> None:
    """Copies one SQLite table into staging, shaped like its raw table."""
    t = sql.Identifier(table)
    conn.execute(sql.SQL("create table staging.{t} (like raw.{t})").format(t=t))
    cols = [
        r[0]
        for r in conn.execute(
            "select column_name from information_schema.columns"
            " where table_schema = 'raw' and table_name = %s order by ordinal_position",
            [table],
        )
    ]
    names = sql.SQL(", ").join(map(sql.Identifier, cols))
    query = f'select {", ".join(f'"{c}"' for c in cols)} from "{table}"'
    with conn.cursor().copy(sql.SQL("copy staging.{} ({}) from stdin").format(t, names)) as copy:
        for row in src.execute(query):
            # The source has some empty strings where it means "no value".
            copy.write_row([None if v == "" else v for v in row])


def ensure_app_role(conn: psycopg.Connection, role: str, password: str | None) -> None:
    """The web app's login role: a member of sim_reader, so it can read sim and nothing else."""
    r = sql.Identifier(role)
    if not conn.execute("select 1 from pg_roles where rolname = %s", [role]).fetchone():
        conn.execute(sql.SQL("create role {} login").format(r))
    if password:
        conn.execute(sql.SQL("alter role {} password {}").format(r, sql.Literal(password)))
    conn.execute(sql.SQL("grant sim_reader to {}").format(r))


def main() -> None:
    source = os.getenv("OLIST_SQLITE")
    print(
        load(
            os.environ["DATABASE_URL"],
            Path(source) if source else None,
            os.getenv("APP_DB_ROLE"),
            os.getenv("APP_DB_PASSWORD"),
        )
    )


if __name__ == "__main__":
    main()
