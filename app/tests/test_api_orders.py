"""Seam 2: the order dashboard API. Every aggregate against hand-made orders at one clock."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from olist_agent import main
from tests.conftest import Load

CLOCK = "2017-03-31"  # 30-day window 2017-03-02..03-31, 90-day window 2017-01-01..03-31


def order(
    oid: str, person: str, state: str, bought: str, status: str = "delivered", **at: str
) -> dict[str, dict[str, Any]]:
    """at: the order's other timestamps by short name (approved, carrier, delivered, estimated)."""
    stages = {
        "approved": "order_approved_at",
        "carrier": "order_delivered_carrier_date",
        "delivered": "order_delivered_customer_date",
        "estimated": "order_estimated_delivery_date",
    }
    return {
        "orders": {
            "order_id": oid,
            "customer_id": f"c-{oid}",  # a new customer_id on every order, as in the source
            "order_status": status,
            "order_purchase_timestamp": bought,
            **{stages[k]: v for k, v in at.items()},
        },
        "customers": {
            "customer_id": f"c-{oid}",
            "customer_unique_id": person,
            "customer_state": state,
        },
    }


ORDERS = [
    # On time: the estimate is a day, so delivered later that same day is on time.
    order(
        "o1", "p1", "SP", "2017-03-10 09:00", delivered="2017-03-20 15:00", estimated="2017-03-20"
    ),
    # Late. The same person as o1.
    order(
        "o2", "p1", "SP", "2017-03-12 09:00", delivered="2017-03-25 10:00", estimated="2017-03-20"
    ),
    # Shipped at the clock; its late delivery on 04-01 isn't visible yet.
    order(
        "o3",
        "p2",
        "RJ",
        "2017-03-20 09:00",
        carrier="2017-03-22 10:00",
        delivered="2017-04-01 10:00",
        estimated="2017-03-28",
    ),
    # Bought before the 30 days, delivered late inside them.
    order(
        "o4", "p3", "RJ", "2017-02-01 09:00", delivered="2017-03-05 10:00", estimated="2017-03-01"
    ),
    # The day before the 90 days.
    order("o5", "p4", "MG", "2016-12-31 23:59:59", delivered="2017-01-10", estimated="2017-01-20"),
    # After the clock: invisible.
    order("o6", "p5", "SP", "2017-04-02 09:00"),
    # The day before the 30 days; canceled once its estimated date passes.
    order("o7", "p2", "RJ", "2017-03-01 23:59:59", "canceled", estimated="2017-03-15"),
    # The clock's last second.
    order("o8", "p6", "SP", "2017-03-31 23:59:59", "shipped"),
]
CATEGORIES = {"pa": "beleza_saude", "pb": "esporte_lazer", "pc": None} | {
    f"p{i:02}": f"cat{i:02}" for i in range(1, 12)
}
ITEMS = [("o1", "pa"), ("o1", "pa"), ("o2", "pa"), ("o2", "pb"), ("o3", "pb"), ("o4", "pc")]
ITEMS += [("o5", "pa"), ("o6", "pa"), ("o6", "pb")] + [("o5", f"p{i:02}") for i in range(1, 12)]
PAYMENTS = [("o1", 100), ("o2", 50), ("o2", 25), ("o3", 40), ("o4", 30), ("o5", 999), ("o8", 10)]
PAYMENTS += [("o6", 500), ("o7", 70)]
REVIEWS = [
    ("o1", 5, "2017-03-21 00:00:00"),
    ("o2", 2, "2017-03-26 00:00:00"),
    ("o3", 1, "2017-04-01 00:00:00"),  # created after the clock
    ("o5", 4, "2017-01-11 00:00:00"),  # before the 30 days
]


@pytest.fixture(scope="module")
def client(load: Load) -> Iterator[TestClient]:
    load(
        orders=[o["orders"] for o in ORDERS],
        customers=[o["customers"] for o in ORDERS],
        products=[{"product_id": p, "product_category_name": c} for p, c in CATEGORIES.items()],
        product_category_name_translation=[
            {"product_category_name": pt, "product_category_name_english": en}
            for pt, en in [("beleza_saude", "health_beauty"), ("esporte_lazer", "sports_leisure")]
        ],
        order_items=[
            {"order_id": o, "order_item_id": n, "product_id": p} for n, (o, p) in enumerate(ITEMS)
        ],
        order_payments=[
            {"order_id": o, "payment_sequential": n, "payment_value": v}
            for n, (o, v) in enumerate(PAYMENTS)
        ],
        order_reviews=[
            {"review_id": f"r-{o}", "order_id": o, "review_score": s, "review_creation_date": d}
            for o, s, d in REVIEWS
        ],
    )
    yield TestClient(main.app)


def dashboard(client: TestClient, clock: str = CLOCK) -> dict[str, Any]:
    r = client.get("/api/orders", params={"clock": clock})
    assert r.status_code == 200
    return r.json()


def test_kpis_cover_the_30_days_ending_at_the_clock(client: TestClient) -> None:
    kpis = dashboard(client)["kpis"]
    # o1, o2, o3, o8 were bought in the 30 days; o1 and o2 are one person.
    assert (kpis["orders"], kpis["people"]) == (4, 3)
    assert kpis["gmv"] == pytest.approx(100 + 50 + 25 + 40 + 10)


def test_a_review_created_after_the_clock_does_not_count(client: TestClient) -> None:
    assert dashboard(client)["kpis"]["avg_review_score"] == pytest.approx((5 + 2) / 2)
    assert dashboard(client, "2017-04-01")["kpis"]["avg_review_score"] == pytest.approx(8 / 3)


def test_a_late_delivery_not_yet_visible_does_not_count_as_late(client: TestClient) -> None:
    # Delivered in the 30 days: o1 on time, o2 and o4 late. o3 is still shipped.
    assert dashboard(client)["kpis"]["late_pct"] == pytest.approx(200 / 3)
    assert dashboard(client, "2017-04-01")["kpis"]["late_pct"] == pytest.approx(75)


def test_daily_orders_cover_the_90_days_ending_at_the_clock(client: TestClient) -> None:
    daily = dashboard(client)["daily_orders"]
    assert len(daily) == 90
    assert (daily[0]["day"], daily[-1]["day"]) == ("2017-01-01", CLOCK)
    assert {d["day"]: d["orders"] for d in daily if d["orders"]} == {
        "2017-02-01": 1,
        "2017-03-01": 1,
        "2017-03-10": 1,
        "2017-03-12": 1,
        "2017-03-20": 1,
        "2017-03-31": 1,
    }


def test_orders_by_derived_status_at_the_clock(client: TestClient) -> None:
    assert dashboard(client)["by_status"] == [
        {"status": "delivered", "orders": 4},
        {"status": "canceled", "orders": 1},
        {"status": "purchased", "orders": 1},
        {"status": "shipped", "orders": 1},
    ]


def test_top_10_categories_by_orders_in_english(client: TestClient) -> None:
    # Two items of one category in an order count once. Untranslated names stay as they are.
    assert dashboard(client)["top_categories"] == [
        {"category": "health_beauty", "orders": 3},
        {"category": "sports_leisure", "orders": 2},
    ] + [{"category": f"cat{i:02}", "orders": 1} for i in range(1, 9)]


def test_orders_and_people_by_customer_state(client: TestClient) -> None:
    assert dashboard(client)["by_state"] == [
        {"state": "RJ", "orders": 3, "people": 2},
        {"state": "SP", "orders": 3, "people": 2},
        {"state": "MG", "orders": 1, "people": 1},
    ]


def test_before_any_order_there_is_nothing_to_average(client: TestClient) -> None:
    d = dashboard(client, "2016-09-04")
    assert d["kpis"] == {
        "orders": 0,
        "people": 0,
        "gmv": 0,
        "avg_review_score": None,
        "late_pct": None,
    }
    assert len(d["daily_orders"]) == 90 and not any(x["orders"] for x in d["daily_orders"])
    assert (d["by_status"], d["top_categories"], d["by_state"]) == ([], [], [])


def test_out_of_range_clock_is_422(client: TestClient) -> None:
    assert client.get("/api/orders", params={"clock": "2018-10-18"}).status_code == 422
