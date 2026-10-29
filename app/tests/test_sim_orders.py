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
    deals = [
        {"mql_id": draw(hex_id), "seller_id": s, "won_date": won}
        for s in sellers
        if (won := draw(st.none() | purchase))
    ]
    return {
        "orders": os,
        "order_reviews": reviews,
        "customers": customers,
        "sellers": [{"seller_id": s} for s in sellers],
        "order_items": items,
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
def test_reviews_customers_sellers_and_static_tables_at_the_clock(
    pg: Pg, load: Load, data: dict[str, list[dict[str, Any]]], clocks: list[date]
) -> None:
    load(**{t: as_text(rows) for t, rows in data.items()})
    first_activity = seller_first_activity(data)
    static = {t: len(data[t]) for t in STATIC}
    with psycopg.connect(pg.app, autocommit=True) as conn:
        # With no clock: nothing time-dimensioned, and every static row.
        assert counts(conn, ["order_reviews", "customers", "sellers"]) == dict.fromkeys(
            ["order_reviews", "customers", "sellers"], 0
        )
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


def test_app_role_cannot_read_raw(pg: Pg, load: Load) -> None:
    load()
    with psycopg.connect(pg.app) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("select * from raw.orders")
