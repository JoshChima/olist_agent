"""Seam 2: the delta event API. What appeared or changed in the days after `from` up to `to`."""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from olist_agent import main
from tests.conftest import Load

# The window (2017-03-01, 2017-03-10]: timestamps from 03-02 00:00 up to 03-10 23:59:59.
FROM, TO = "2017-03-01", "2017-03-10"
ORDERS = [
    # Bought and approved on the `from` day itself, so only its shipping and delivery count.
    {
        "order_id": "o1",
        "order_status": "delivered",
        "order_purchase_timestamp": "2017-03-01 10:00:00",
        "order_approved_at": "2017-03-01 11:00:00",
        "order_delivered_carrier_date": "2017-03-03 09:00:00",
        "order_delivered_customer_date": "2017-03-08 09:00:00",
        "order_estimated_delivery_date": "2017-03-20 00:00:00",
    },
    # Canceled, but its estimated date is after the window, so it isn't revealed yet.
    {
        "order_id": "o2",
        "order_status": "canceled",
        "order_purchase_timestamp": "2017-03-05 10:00:00",
        "order_approved_at": "2017-03-06 10:00:00",
        "order_estimated_delivery_date": "2017-03-25 00:00:00",
    },
    # Unavailable, revealed on the window's last day.
    {
        "order_id": "o3",
        "order_status": "unavailable",
        "order_purchase_timestamp": "2017-03-09 10:00:00",
        "order_approved_at": "2017-03-10 23:59:59",
        "order_estimated_delivery_date": "2017-03-10 00:00:00",
    },
    # Bought before the window, delivered on its first day.
    {
        "order_id": "o4",
        "order_status": "delivered",
        "order_purchase_timestamp": "2017-02-10 10:00:00",
        "order_approved_at": "2017-02-10 11:00:00",
        "order_delivered_carrier_date": "2017-02-12 09:00:00",
        "order_delivered_customer_date": "2017-03-02 00:00:00",
        "order_estimated_delivery_date": "2017-03-05 00:00:00",
    },
    # After the window.
    {"order_id": "o5", "order_status": "shipped", "order_purchase_timestamp": "2017-03-20 10:00"},
]
ITEMS = [("o1", "s1"), ("o2", "s3"), ("o4", "s2")]
REVIEWS = [("o1", "2017-03-09 00:00:00"), ("o4", "2017-03-01 00:00:00")]
LEADS = [
    ("m0", "2017-01-10 00:00:00"),
    ("m1", "2017-02-20 00:00:00"),
    ("m2", "2017-03-04 00:00:00"),
    ("m3", "2017-03-10 23:00:00"),
]
# An active seller counts from the later of its deal and its first order:
# s1 from 03-02 (deal), s3 from 03-05 (first order), s2 from 03-11 (deal).
DEALS = [("m0", "s3", "2017-02-01 00:00:00"), ("m1", "s1", "2017-03-02 00:00:00")]
DEALS += [("m2", "s2", "2017-03-11 00:00:00")]


@pytest.fixture(scope="module")
def client(load: Load) -> Iterator[TestClient]:
    load(
        orders=ORDERS,
        order_items=[{"order_id": o, "order_item_id": 1, "seller_id": s} for o, s in ITEMS],
        order_reviews=[
            {"review_id": f"r-{o}", "order_id": o, "review_creation_date": d} for o, d in REVIEWS
        ],
        leads_qualified=[{"mql_id": m, "first_contact_date": d} for m, d in LEADS],
        leads_closed=[{"mql_id": m, "seller_id": s, "won_date": d} for m, s, d in DEALS],
    )
    yield TestClient(main.app)


def delta(client: TestClient, from_: str, to: str) -> dict[str, int]:
    r = client.get("/api/delta", params={"from": from_, "to": to})
    assert r.status_code == 200, r.text
    return r.json()["counts"]


def test_every_count_for_a_forward_window(client: TestClient) -> None:
    assert delta(client, FROM, TO) == {
        "new_orders": 2,  # o2, o3
        "approved": 2,  # o2, o3
        "shipped": 1,  # o1
        "delivered": 2,  # o4, o1
        "canceled_or_unavailable": 1,  # o3
        "new_reviews": 1,  # o1's
        "new_mqls": 2,  # m2, m3
        "deals_closed": 1,  # m1
        "new_active_sellers": 2,  # s1, s3
    }


def test_a_window_over_the_whole_dataset_counts_everything(client: TestClient) -> None:
    assert delta(client, "2016-09-04", "2018-10-17") == {
        "new_orders": 5,
        "approved": 4,
        "shipped": 2,
        "delivered": 2,
        "canceled_or_unavailable": 2,
        "new_reviews": 2,
        "new_mqls": 4,
        "deals_closed": 3,
        "new_active_sellers": 3,
    }


def test_adjacent_windows_add_up_to_the_window_they_cover(client: TestClient) -> None:
    d0, d1 = date(2017, 2, 1), date(2017, 3, 31)
    whole = delta(client, d0.isoformat(), d1.isoformat())
    for n in range(1, (d1 - d0).days):
        dm = (d0 + timedelta(n)).isoformat()
        left, right = delta(client, d0.isoformat(), dm), delta(client, dm, d1.isoformat())
        assert {k: left[k] + right[k] for k in whole} == whole, dm


@pytest.mark.parametrize(
    ("from_", "to"),
    [
        (TO, FROM),  # backward
        (FROM, FROM),  # empty
        ("2016-09-03", TO),  # outside the dataset
        (FROM, "2018-10-18"),
    ],
)
def test_a_backward_empty_or_out_of_range_window_is_422(
    client: TestClient, from_: str, to: str
) -> None:
    assert client.get("/api/delta", params={"from": from_, "to": to}).status_code == 422
