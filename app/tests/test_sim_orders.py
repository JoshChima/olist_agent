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
FINAL = ("canceled", "unavailable")
# Lifecycle stages drawn independently of each other, so they are often out of order.
stage = st.one_of(st.none(), purchase)
orders = st.lists(
    st.fixed_dictionaries(
        {
            "order_id": st.uuids().map(lambda u: u.hex),
            "customer_id": st.uuids().map(lambda u: u.hex),
            "order_status": st.sampled_from(["delivered", "shipped", *FINAL]),
            PURCHASE: purchase,
            "order_approved_at": stage,
            "order_delivered_carrier_date": stage,
            "order_delivered_customer_date": stage,
            "order_estimated_delivery_date": stage,
        }
    ),
    max_size=30,
    unique_by=lambda o: o["order_id"],
)
RANK = {"purchased": 0, "approved": 1, "shipped": 2, "delivered": 3, **dict.fromkeys(FINAL, 4)}


@settings(max_examples=25, deadline=None)
@given(orders=orders, clocks=st.lists(st.dates(FIRST_DAY, LAST_DAY), min_size=1, max_size=5))
def test_orders_never_leak_the_future(
    pg: Pg, load: Load, orders: list[dict[str, Any]], clocks: list[date]
) -> None:
    ids = [o["order_id"] for o in orders] + ["no-such-order"]
    load(
        orders=[{k: v and str(v) for k, v in o.items()} for o in orders],
        customers=[{"customer_id": o["customer_id"]} for o in orders],
        order_items=[{"order_id": i, "order_item_id": 1} for i in ids],
        order_payments=[{"order_id": i, "payment_sequential": 1} for i in ids],
    )
    rank: dict[str, int] = {}
    with psycopg.connect(pg.app, autocommit=True) as conn:
        assert conn.execute("select count(*) from sim.orders").fetchone() == (0,)
        for clock in sorted(clocks):
            with conn.transaction():
                set_clock(conn, clock)
                rows = conn.execute(
                    "select order_id, order_purchase_timestamp, order_approved_at,"
                    " order_delivered_carrier_date, order_delivered_customer_date,"
                    " order_status, order_estimated_delivery_date from sim.orders"
                ).fetchall()
                items = conn.execute("select order_id from sim.order_items").fetchall()
                payments = conn.execute("select order_id from sim.order_payments").fetchall()
            end = datetime.combine(clock + timedelta(days=1), time())
            seen = {r[0] for r in rows}
            assert seen == {o["order_id"] for o in orders if o[PURCHASE] < end}
            for order_id, *lifecycle, status, estimated in rows:
                assert all(ts is None or ts < end for ts in lifecycle)
                if status in FINAL:
                    assert estimated < end
                # Clocks ascend, so status never moves backwards.
                assert RANK[status] >= rank.get(order_id, 0)
                rank[order_id] = RANK[status]
            assert {i for (i,) in items} == {i for (i,) in payments} == seen
        # Once the transaction ends, so does the clock.
        assert conn.execute("select count(*) from sim.orders").fetchone() == (0,)


LIFECYCLE = (
    "order_status, order_approved_at, order_delivered_carrier_date,"
    " order_delivered_customer_date, order_estimated_delivery_date, repaired"
)


def at(pg: Pg, clock: date, query: str) -> list[tuple[Any, ...]]:
    with psycopg.connect(pg.app, autocommit=True) as conn, conn.transaction():
        set_clock(conn, clock)
        return conn.execute(query).fetchall()


def test_order_in_flight_shows_no_future_lifecycle(pg: Pg, load: Load) -> None:
    load(
        orders=[
            {
                "order_id": "o1",
                "order_status": "delivered",
                PURCHASE: "2017-03-01 10:00:00",
                "order_approved_at": "2017-03-01 11:00:00",
                "order_delivered_carrier_date": "2017-03-03 09:00:00",
                "order_delivered_customer_date": "2017-03-10 15:00:00",
                "order_estimated_delivery_date": "2017-03-20 00:00:00",
            }
        ]
    )
    rows = at(pg, date(2017, 3, 2), f"select {LIFECYCLE} from sim.orders")
    assert rows == [
        ("approved", datetime(2017, 3, 1, 11), None, None, datetime(2017, 3, 20), False)
    ]


def test_out_of_order_timestamps_are_repaired(pg: Pg, load: Load) -> None:
    # Delivered to the customer before the carrier picked it up.
    load(
        orders=[
            {
                "order_id": "o1",
                "order_status": "delivered",
                PURCHASE: "2017-03-01 10:00:00",
                "order_approved_at": "2017-03-02 11:00:00",
                "order_delivered_carrier_date": "2017-03-06 09:00:00",
                "order_delivered_customer_date": "2017-03-04 15:00:00",
                "order_estimated_delivery_date": "2017-03-20 00:00:00",
            }
        ]
    )
    query = "select order_status, order_delivered_customer_date, repaired from sim.orders"
    days = [at(pg, date(2017, 3, d), query)[0] for d in range(1, 8)]
    pickup = datetime(2017, 3, 6, 9)
    assert days == [
        ("purchased", None, True),
        ("approved", None, True),
        ("approved", None, True),
        ("approved", None, True),  # the source says delivered by now
        ("approved", None, True),
        ("delivered", pickup, True),
        ("delivered", pickup, True),
    ]
    with psycopg.connect(pg.admin) as conn:
        raw = conn.execute("select order_delivered_customer_date from raw.orders").fetchall()
    assert raw == [(datetime(2017, 3, 4, 15),)]


def test_canceled_shows_only_from_the_estimated_delivery_date(pg: Pg, load: Load) -> None:
    load(
        orders=[
            {
                "order_id": "o1",
                "order_status": "canceled",
                PURCHASE: "2017-03-01 10:00:00",
                "order_approved_at": "2017-03-01 11:00:00",
                "order_estimated_delivery_date": "2017-03-20 00:00:00",
            }
        ]
    )
    query = "select order_status from sim.orders"
    days = [at(pg, date(2017, 3, d), query)[0][0] for d in (1, 19, 20, 21)]
    assert days == ["approved", "approved", "canceled", "canceled"]


def test_items_and_payments_follow_their_order(pg: Pg, load: Load) -> None:
    load(
        orders=[
            {"order_id": "early", PURCHASE: "2017-03-01 10:00:00"},
            {"order_id": "late", PURCHASE: "2017-03-05 10:00:00"},
        ],
        order_items=[
            # The shipping limit is known at purchase, so it shows even when it's later.
            {"order_id": o, "order_item_id": 1, "shipping_limit_date": "2017-03-09 00:00:00"}
            for o in ("early", "late")
        ],
        order_payments=[{"order_id": o, "payment_sequential": 1} for o in ("early", "late")],
    )
    clock = date(2017, 3, 2)
    items = "select order_id, shipping_limit_date from sim.order_items"
    assert at(pg, clock, items) == [("early", datetime(2017, 3, 9))]
    assert at(pg, clock, "select order_id from sim.order_payments") == [("early",)]


def test_app_role_cannot_read_raw(pg: Pg, load: Load) -> None:
    load()
    with psycopg.connect(pg.app) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("select * from raw.orders")
