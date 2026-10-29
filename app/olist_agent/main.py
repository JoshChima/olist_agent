import os
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, Query
from fastapi.staticfiles import StaticFiles
from psycopg import sql
from psycopg.rows import dict_row
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

from olist_agent import db

# Baked into the image at build time (see Dockerfile), so the CD smoke test can
# prove the revision serving traffic is the commit it just pushed.
VERSION = os.getenv("GIT_SHA", "dev")

# ADR-0006 picks the Azure Monitor exporter. Gating it on the env var keeps local
# runs Azure-free. Configured before the app is created so FastAPI gets instrumented.
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor()

app = FastAPI(title="olist_agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello from olist_agent"}


FIRST_DAY, LAST_DAY = date(2016, 9, 4), date(2018, 10, 17)
PAGE_SIZE = 50


def clock_param(clock: date) -> date:
    """Every data endpoint takes ?clock=YYYY-MM-DD, rejected rather than clamped (ADR-0009)."""
    if not FIRST_DAY <= clock <= LAST_DAY:
        raise HTTPException(422, f"clock must be from {FIRST_DAY} to {LAST_DAY}")
    return clock


Clock = Annotated[date, Depends(clock_param)]


@app.get("/api/data-status")
def data_status() -> dict[str, Any]:
    row = None
    if os.getenv("DATABASE_URL"):  # unset until the deployed app has a database
        with db.pool().connection() as conn:
            row = conn.execute("select source_sha256 from sim.data_status").fetchone()
    return {"loaded": row is not None, "source_sha256": row[0] if row else None}


def sim_views(conn: psycopg.Connection[Any]) -> list[str]:
    """The explorer's allowlist: the sim views, read from the database."""
    rows = conn.execute(
        "select table_name from information_schema.views"
        " where table_schema = 'sim' and table_name <> 'data_status' order by 1"
    )
    return [r[0] for r in rows]


@app.get("/api/explore")
def explore_views() -> dict[str, list[str]]:
    with db.pool().connection() as conn:
        return {"views": sim_views(conn)}


@app.get("/api/explore/{view}")
def explore_rows(
    view: str,
    clock: Clock,
    page: Annotated[int, Query(ge=1)] = 1,
    sort: str | None = None,
    desc: bool = False,
) -> dict[str, Any]:
    with db.at_clock(clock) as conn:
        if view not in sim_views(conn):
            raise HTTPException(404, f"unknown view {view!r}")
        columns: list[str] = [
            r[0]
            for r in conn.execute(
                "select column_name from information_schema.columns"
                " where table_schema = 'sim' and table_name = %s order by ordinal_position",
                [view],
            )
        ]
        sort = sort or columns[0]
        if sort not in columns:
            raise HTTPException(422, f"unknown sort column {sort!r}")
        v = sql.Identifier("sim", view)
        (total,) = conn.execute(sql.SQL("select count(*) from {}").format(v)).fetchone() or (0,)
        # Every column breaks ties, so pages don't overlap: first columns aren't always keys
        # (review ids repeat, geolocation has many rows per zip prefix).
        query = sql.SQL("select * from {} order by {} {} nulls last, {} limit %s offset %s")
        rows = conn.execute(
            query.format(
                v,
                sql.Identifier(sort),
                sql.SQL("desc" if desc else "asc"),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
            ),
            [PAGE_SIZE, (page - 1) * PAGE_SIZE],
        ).fetchall()
    return {"columns": columns, "rows": rows, "total": total, "page": page, "page_size": PAGE_SIZE}


# The order dashboard. Every query reads sim views only, which already hide anything later
# than the clock; the bounds below only narrow to the last 30 or 90 days.
ORDER_KPIS = """
select
    (select count(*) from sim.orders where order_purchase_timestamp >= %(d30)s) as orders,
    (select count(distinct c.customer_unique_id)
        from sim.orders o join sim.customers c using (customer_id)
        where o.order_purchase_timestamp >= %(d30)s) as customers,
    (select coalesce(sum(p.payment_value), 0)::float8
        from sim.order_payments p join sim.orders o using (order_id)
        where o.order_purchase_timestamp >= %(d30)s) as gmv,
    (select avg(review_score)::float8
        from sim.order_reviews where review_creation_date >= %(d30)s) as avg_review_score,
    -- Of the orders delivered in the 30 days. The estimate is a day, so late means a later day.
    (select 100 * avg((order_delivered_customer_date::date
                        > order_estimated_delivery_date::date)::int)::float8
        from sim.orders where order_delivered_customer_date >= %(d30)s) as late_pct
"""
DAILY_ORDERS = """
select d::date as day, count(o.order_id) as orders
from generate_series(%(d90)s::timestamp, %(clock)s::timestamp, interval '1 day') d
left join sim.orders o on o.order_purchase_timestamp::date = d::date
group by d order by d
"""
ORDERS_BY_STATUS = """
select order_status as status, count(*) as orders from sim.orders group by 1 order by 2 desc, 1
"""
TOP_CATEGORIES = """
select coalesce(t.product_category_name_english, p.product_category_name) as category,
    count(distinct i.order_id) as orders
from sim.order_items i
left join sim.products p using (product_id)
left join sim.product_category_name_translation t using (product_category_name)
group by 1 order by 2 desc, 1 nulls last limit 10
"""
ORDERS_BY_STATE = """
select c.customer_state as state, count(*) as orders,
    count(distinct c.customer_unique_id) as customers
from sim.orders o join sim.customers c using (customer_id)
group by 1 order by 2 desc, 1
"""


@app.get("/api/orders")
def order_dashboard(clock: Clock) -> dict[str, Any]:
    bounds = {"clock": clock, "d30": clock - timedelta(29), "d90": clock - timedelta(89)}
    with db.at_clock(clock) as conn:
        cur = conn.cursor(row_factory=dict_row)
        return {
            "kpis": cur.execute(ORDER_KPIS, bounds).fetchone(),
            "daily_orders": cur.execute(DAILY_ORDERS, bounds).fetchall(),
            "by_status": cur.execute(ORDERS_BY_STATUS).fetchall(),
            "top_categories": cur.execute(TOP_CATEGORIES).fetchall(),
            "by_state": cur.execute(ORDERS_BY_STATE).fetchall(),
        }


# An active seller has an order at the clock; only those from a closed deal count.
ACTIVE_SELLERS = """
select count(distinct seller_id) from sim.leads_closed
where seller_id in (select seller_id from sim.order_items)
"""


@app.get("/api/funnel")
def funnel(clock: Clock) -> dict[str, Any]:
    """MQL -> closed deal -> active seller (GLOSSARY.md "Funnel stage"), cumulative at the clock."""
    with db.at_clock(clock) as conn:
        counts = conn.execute(
            "select (select count(*) from sim.leads_qualified),"
            " (select count(*) from sim.leads_closed),"
            f" ({ACTIVE_SELLERS})"
        ).fetchone() or (0, 0, 0)
        monthly = conn.execute(
            "select to_char(first_contact_date, 'YYYY-MM'), coalesce(origin, 'unknown'), count(*)"
            " from sim.leads_qualified group by 1, 2 order by 1, 2"
        ).fetchall()
    stages = [
        {"stage": name, "count": n, "conversion": n / prev if prev else None}
        for name, n, prev in zip(
            ["mql", "closed_deal", "active_seller"], counts, [0, *counts], strict=False
        )
    ]
    return {
        "stages": stages,
        "monthly_mqls": [{"month": m, "origin": o, "mqls": n} for m, o, n in monthly],
    }


# Everything the delta event counts, cumulative at the clock. Each count only grows as the
# clock moves forward, so the counts at `to` minus those at `from` are what happened in
# between, by the same definitions as the dashboards, and adjacent windows add up.
DELTA_COUNTS = f"""
select
    (select count(*) from sim.orders) as new_orders,
    -- Repaired timestamps, empty until they pass the clock.
    (select count(order_approved_at) from sim.orders) as approved,
    (select count(order_delivered_carrier_date) from sim.orders) as shipped,
    (select count(order_delivered_customer_date) from sim.orders) as delivered,
    -- Shown once the estimated delivery date passes (derived status).
    (select count(*) from sim.orders where order_status in ('canceled', 'unavailable'))
        as canceled_or_unavailable,
    (select count(*) from sim.order_reviews) as new_reviews,
    (select count(*) from sim.leads_qualified) as new_mqls,
    (select count(*) from sim.leads_closed) as deals_closed,
    ({ACTIVE_SELLERS}) as new_active_sellers
"""


@app.get("/api/delta")
def delta_event(from_: Annotated[date, Query(alias="from")], to: date) -> dict[str, Any]:
    """The delta event for the clock window [from+1 00:00, to+1 00:00) (GLOSSARY.md): the
    days after `from` up to and including `to`.

    `from` may be the day before the data, so a window can take in its first day. Computed
    on demand from the sim views at both clocks; nothing is stored.
    """
    if from_ != FIRST_DAY - timedelta(1):
        clock_param(from_)
    clock_param(to)
    if to <= from_:
        raise HTTPException(422, "to must be after from")
    counts = []
    with db.pool().connection() as conn:
        # One snapshot for both clocks, so a reload in between can't skew the difference.
        conn.execute("set transaction isolation level repeatable read")
        cur = conn.cursor(row_factory=dict_row)
        for clock in (from_, to):
            db.set_clock(conn, clock)
            counts.append(cur.execute(DELTA_COUNTS).fetchone() or {})
    before, after = counts
    return {"from": from_, "to": to, "counts": {k: after[k] - before[k] for k in after}}


class SPAStaticFiles(StaticFiles):
    """Serves index.html for unknown paths so client-side routes deep-link."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            # Unknown /api/* and missing files (/assets/old-hash.js) stay a 404
            # rather than returning the SPA shell. Only extensionless routes fall back.
            p = Path(path)
            if e.status_code != 404 or p.parts[:1] == ("api",) or p.suffix:
                raise
            return await super().get_response("index.html", scope)


# Mounted last so API routes win. Absent when running tests or API-only dev.
static_dir = Path(os.getenv("STATIC_DIR", "web/dist"))
if static_dir.is_dir():
    app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="spa")
