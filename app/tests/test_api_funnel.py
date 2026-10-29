"""Seam 2: the funnel API. MQL -> closed deal -> active seller, as of the clock."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from olist_agent import loader, main
from tests.conftest import APP_ROLE, Pg
from tests.olist_sqlite import write_olist

LEADS = [
    {"mql_id": "m1", "first_contact_date": "2017-06-14 00:00:00", "origin": "organic_search"},
    {"mql_id": "m2", "first_contact_date": "2017-06-20 00:00:00", "origin": "paid_search"},
    {"mql_id": "m3", "first_contact_date": "2017-07-01 00:00:00", "origin": "organic_search"},
    {"mql_id": "m4", "first_contact_date": "2017-07-02 23:59:59", "origin": None},
    {"mql_id": "m5", "first_contact_date": "2017-08-01 00:00:00", "origin": "social"},
]
DEALS = [
    {"mql_id": "m1", "seller_id": "s1", "won_date": "2017-06-30 00:00:00"},
    {"mql_id": "m2", "seller_id": "s2", "won_date": "2017-07-01 00:00:00"},
    {"mql_id": "m3", "seller_id": "s3", "won_date": "2017-08-05 00:00:00"},
]
# s1 sells before 2017-07-02; s2 only after it; s9 sells but never closed a deal.
ORDERS = [
    {"order_id": "o1", "order_purchase_timestamp": "2017-07-01 10:00:00"},
    {"order_id": "o2", "order_purchase_timestamp": "2017-08-02 10:00:00"},
    {"order_id": "o3", "order_purchase_timestamp": "2017-06-01 10:00:00"},
]
ITEMS = [
    {"order_id": "o1", "order_item_id": 1, "seller_id": "s1"},
    {"order_id": "o2", "order_item_id": 1, "seller_id": "s2"},
    {"order_id": "o3", "order_item_id": 1, "seller_id": "s9"},
]


@pytest.fixture(scope="module")
def client(pg: Pg, tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    path = write_olist(
        tmp_path_factory.mktemp("funnel") / "olist.sqlite",
        leads_qualified=LEADS,
        leads_closed=DEALS,
        orders=ORDERS,
        order_items=ITEMS,
    )
    loader.load(pg.admin, path, APP_ROLE, APP_ROLE)
    yield TestClient(main.app)


def funnel(client: TestClient, clock: str) -> dict:
    r = client.get("/api/funnel", params={"clock": clock})
    assert r.status_code == 200
    return r.json()


def test_stages_and_conversion_at_the_clock(client: TestClient) -> None:
    # s2's deal is closed but its first order comes later, so it isn't an active seller yet.
    assert funnel(client, "2017-07-02")["stages"] == [
        {"stage": "mql", "count": 4, "conversion": None},
        {"stage": "closed_deal", "count": 2, "conversion": 0.5},
        {"stage": "active_seller", "count": 1, "conversion": 0.5},
    ]


def test_closed_deal_becomes_active_seller_with_its_first_order(client: TestClient) -> None:
    counts = [s["count"] for s in funnel(client, "2017-08-05")["stages"]]
    assert counts == [5, 3, 2]


def test_monthly_mqls_by_origin_stop_at_the_clock(client: TestClient) -> None:
    assert funnel(client, "2017-07-02")["monthly_mqls"] == [
        {"month": "2017-06", "origin": "organic_search", "mqls": 1},
        {"month": "2017-06", "origin": "paid_search", "mqls": 1},
        {"month": "2017-07", "origin": "organic_search", "mqls": 1},
        {"month": "2017-07", "origin": "unknown", "mqls": 1},
    ]


def test_before_any_lead_everything_is_zero(client: TestClient) -> None:
    assert funnel(client, "2016-12-31") == {
        "stages": [
            {"stage": "mql", "count": 0, "conversion": None},
            {"stage": "closed_deal", "count": 0, "conversion": None},
            {"stage": "active_seller", "count": 0, "conversion": None},
        ],
        "monthly_mqls": [],
    }


def test_out_of_range_clock_is_422(client: TestClient) -> None:
    assert client.get("/api/funnel", params={"clock": "2018-10-18"}).status_code == 422


def test_lead_views_are_in_the_explorer(client: TestClient) -> None:
    views = client.get("/api/explore").json()["views"]
    assert {"leads_qualified", "leads_closed"} <= set(views)
