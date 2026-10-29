import os
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, Query
from fastapi.staticfiles import StaticFiles
from psycopg import sql
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


@app.get("/api/funnel")
def funnel(clock: Clock) -> dict[str, Any]:
    """MQL -> closed deal -> active seller (GLOSSARY.md "Funnel stage"), cumulative at the clock."""
    with db.at_clock(clock) as conn:
        counts = conn.execute(
            "select (select count(*) from sim.leads_qualified),"
            " (select count(*) from sim.leads_closed),"
            # An active seller has an order at the clock; only those from a closed deal count.
            " (select count(distinct seller_id) from sim.leads_closed"
            "   where seller_id in (select seller_id from sim.order_items))"
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
