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


hex_id = st.uuids().map(lambda u: u.hex)


@st.composite
def olist(draw: st.DrawFn) -> dict[str, list[dict[str, Any]]]:
    """Orders, plus the rows whose visibility hangs off them or off their own timestamp."""
    os = draw(orders)
    reviews = draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    "review_id": st.sampled_from("abc"),  # review ids repeat across orders
                    "order_id": st.sampled_from([o["order_id"] for o in os] or ["none"]),
                    "review_creation_date": purchase,
                    "review_answer_timestamp": st.none() | purchase,
                }
            ),
            max_size=20,
            unique_by=lambda r: (r["review_id"], r["order_id"]),
        )
    )
    # customer_id is per order; a person (customer_unique_id) may have several.
    customers = [
        {"customer_id": o["customer_id"], "customer_unique_id": draw(st.sampled_from("pq"))}
        for o in os
    ]
    sellers = draw(st.lists(hex_id, max_size=8, unique=True))
    # Some sellers sell (an order item), some closed a deal, some both, some neither.
    items = [
        {"order_id": o["order_id"], "order_item_id": 1, "seller_id": draw(st.sampled_from(sellers))}
        for o in os
        if sellers and draw(st.booleans())
    ]
    # Leads with and without a closed deal; deals with and without an order (via items above).
    leads = draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    "mql_id": hex_id,
                    "first_contact_date": purchase,
                    "origin": st.sampled_from(["organic_search", "paid_search", None]),
                }
            ),
            max_size=10,
            unique_by=lambda lead: lead["mql_id"],
        )
    )
    mql_ids = iter([lead["mql_id"] for lead in leads])
    deals = [
        {"mql_id": next(mql_ids, None) or draw(hex_id), "seller_id": s, "won_date": won}
        for s in sellers
        if (won := draw(st.none() | purchase))
    ]
    return {
        "orders": os,
        "order_reviews": reviews,
        "customers": customers,
        "sellers": [{"seller_id": s} for s in sellers],
        "order_items": items,
        "leads_qualified": leads,
        "leads_closed": deals,
        # Static tables. Geolocation has many rows per zip prefix.
        "products": [{"product_id": p} for p in draw(st.lists(hex_id, max_size=5))],
        "geolocation": [
            {"geolocation_zip_code_prefix": z} for z in draw(st.lists(st.sampled_from("12")))
        ],
        "product_category_name_translation": [
            {"product_category_name": c} for c in draw(st.lists(hex_id, max_size=3))
        ],
    }


STATIC = ["products", "geolocation", "product_category_name_translation"]
TIMED = ["order_reviews", "customers", "sellers", "leads_qualified", "leads_closed"]


def seller_first_activity(data: dict[str, list[dict[str, Any]]]) -> dict[str, datetime]:
    """The earlier of a seller's first order's purchase and their closed deal's won_date."""
    purchases = {o["order_id"]: o[PURCHASE] for o in data["orders"]}
    times = [(i["seller_id"], purchases[i["order_id"]]) for i in data["order_items"]]
    times += [(d["seller_id"], d["won_date"]) for d in data["leads_closed"]]
    first: dict[str, datetime] = {}
    for s, t in times:
        first[s] = min(t, first.get(s, t))
    return first


def as_text(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Timestamps written the way the source has them."""
    return [{k: str(v) if isinstance(v, datetime) else v for k, v in r.items()} for r in rows]


def counts(conn: psycopg.Connection[Any], views: list[str]) -> dict[str, int]:
    return {v: conn.execute(f"select count(*) from sim.{v}").fetchone()[0] for v in views}


@settings(max_examples=25, deadline=None)
@given(data=olist(), clocks=st.lists(st.dates(FIRST_DAY, LAST_DAY), min_size=1, max_size=5))
def test_reviews_customers_sellers_leads_and_static_tables_at_the_clock(
    pg: Pg, load: Load, data: dict[str, list[dict[str, Any]]], clocks: list[date]
) -> None:
    load(**{t: as_text(rows) for t, rows in data.items()})
    first_activity = seller_first_activity(data)
    static = {t: len(data[t]) for t in STATIC}
    with psycopg.connect(pg.app, autocommit=True) as conn:
        # With no clock: nothing time-dimensioned, and every static row.
        assert counts(conn, TIMED) == dict.fromkeys(TIMED, 0)
        assert counts(conn, STATIC) == static
        for clock in clocks:
            end = datetime.combine(clock + timedelta(days=1), time())
            with conn.transaction():
                set_clock(conn, clock)
                rows = conn.execute(
                    "select review_id, order_id, review_answer_timestamp from sim.order_reviews"
                )
                reviews = {(r, o): a for r, o, a in rows}
                customers = {r[0] for r in conn.execute("select customer_id from sim.customers")}
                sellers = {r[0] for r in conn.execute("select seller_id from sim.sellers")}
                mqls = {r[0] for r in conn.execute("select mql_id from sim.leads_qualified")}
                won = {r[0] for r in conn.execute("select mql_id from sim.leads_closed")}
                assert counts(conn, STATIC) == static
            assert reviews == {
                (r["review_id"], r["order_id"]): (
                    a if (a := r["review_answer_timestamp"]) and a < end else None
                )
                for r in data["order_reviews"]
                if r["review_creation_date"] < end
            }
            assert customers == {o["customer_id"] for o in data["orders"] if o[PURCHASE] < end}
            assert sellers == {s for s, t in first_activity.items() if t < end}
            assert mqls == {
                m["mql_id"] for m in data["leads_qualified"] if m["first_contact_date"] < end
            }
            assert won == {d["mql_id"] for d in data["leads_closed"] if d["won_date"] < end}


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
