"""Seam 1: what the sim views show at a clock. The future-leakage property test."""

from datetime import date, datetime, time, timedelta
from typing import Any

import psycopg
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from olist_agent.db import set_clock
from tests.conftest import Load, Pg

FIRST_DAY, LAST_DAY = date(2016, 9, 4), date(2018, 10, 17)
PURCHASE = "order_purchase_timestamp"

# Seconds resolution like the source, plus exact midnights to hit the day boundary.
purchase = st.one_of(
    st.datetimes(datetime(2016, 9, 1), datetime(2018, 10, 20)).map(
        lambda d: d.replace(microsecond=0)
    ),
    st.dates(FIRST_DAY, LAST_DAY).map(lambda d: datetime.combine(d, time())),
)
orders = st.lists(
    st.fixed_dictionaries(
        {
            "order_id": st.uuids().map(lambda u: u.hex),
            "customer_id": st.uuids().map(lambda u: u.hex),
            "order_status": st.sampled_from(["delivered", "shipped", "canceled", "unavailable"]),
            PURCHASE: purchase,
        }
    ),
    max_size=30,
    unique_by=lambda o: o["order_id"],
)


@settings(max_examples=25, deadline=None)
@given(orders=orders, clocks=st.lists(st.dates(FIRST_DAY, LAST_DAY), min_size=1, max_size=5))
def test_orders_never_leak_the_future(
    pg: Pg, load: Load, orders: list[dict[str, Any]], clocks: list[date]
) -> None:
    load(
        orders=[{**o, "order_purchase_timestamp": str(o[PURCHASE])} for o in orders],
        customers=[{"customer_id": o["customer_id"]} for o in orders],
    )
    with psycopg.connect(pg.app, autocommit=True) as conn:
        assert conn.execute("select count(*) from sim.orders").fetchone() == (0,)
        for clock in clocks:
            with conn.transaction():
                set_clock(conn, clock)
                rows = conn.execute("select order_id, order_purchase_timestamp from sim.orders")
                seen = dict(rows.fetchall())
            end = datetime.combine(clock + timedelta(days=1), time())
            assert all(ts < end for ts in seen.values())
            assert set(seen) == {o["order_id"] for o in orders if o[PURCHASE] < end}
        # Once the transaction ends, so does the clock.
        assert conn.execute("select count(*) from sim.orders").fetchone() == (0,)


def test_app_role_cannot_read_raw(pg: Pg, load: Load) -> None:
    load()
    with psycopg.connect(pg.app) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("select * from raw.orders")
