"""Seam 2: the HTTP API over the sim views."""

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from olist_agent import loader, main
from tests.conftest import APP_ROLE, Pg
from tests.olist_sqlite import write_olist

# 60 orders on 2017-01-02 (more than one page), one on 2017-01-01, one after the range.
ORDERS = [
    {"order_id": f"jan2-{i:02}", "order_purchase_timestamp": f"2017-01-02 10:{i:02}:00"}
    for i in range(60)
] + [
    {"order_id": "jan1", "order_purchase_timestamp": "2017-01-01 23:59:59"},
    {"order_id": "late", "order_purchase_timestamp": "2018-10-18 00:00:00"},
]


@pytest.fixture(scope="module")
def source(pg: Pg, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = write_olist(tmp_path_factory.mktemp("api") / "olist.sqlite", orders=ORDERS)
    loader.load(pg.admin, path, APP_ROLE, APP_ROLE)
    return path


@pytest.fixture
def client(source: Path) -> Iterator[TestClient]:
    yield TestClient(main.app)


@pytest.mark.parametrize("clock", [None, "2016-09-03", "2018-10-18", "not-a-date"])
def test_missing_or_out_of_range_clock_is_422(client: TestClient, clock: str | None) -> None:
    params = {"clock": clock} if clock else {}
    assert client.get("/api/explore/orders", params=params).status_code == 422


def test_range_ends_are_valid_clocks(client: TestClient) -> None:
    for clock in ["2016-09-04", "2018-10-17"]:
        assert client.get("/api/explore/orders", params={"clock": clock}).status_code == 200


def test_view_list_is_the_sim_views(client: TestClient) -> None:
    views = client.get("/api/explore").json()["views"]
    assert {"orders", "order_items", "order_payments"} <= set(views)


def test_rows_page_50_at_a_time_with_total(client: TestClient) -> None:
    first = client.get("/api/explore/orders", params={"clock": "2017-01-02"}).json()
    second = client.get("/api/explore/orders", params={"clock": "2017-01-02", "page": 2}).json()
    assert (first["total"], len(first["rows"]), len(second["rows"])) == (61, 50, 11)
    assert "order_id" in first["columns"]


def test_sort_by_column(client: TestClient) -> None:
    def first_id(desc: bool) -> str:
        params = {"clock": "2017-01-02", "sort": "order_purchase_timestamp", "desc": desc}
        r = client.get("/api/explore/orders", params=params).json()
        return r["rows"][0][r["columns"].index("order_id")]

    assert (first_id(False), first_id(True)) == ("jan1", "jan2-59")


def test_rewind_shrinks_the_row_count(client: TestClient) -> None:
    def total(clock: str) -> int:
        return client.get("/api/explore/orders", params={"clock": clock}).json()["total"]

    assert (total("2017-01-02"), total("2017-01-01"), total("2016-12-31")) == (61, 1, 0)


def test_unknown_view_is_404(client: TestClient) -> None:
    for view in ["nope", "data_status"]:
        assert client.get(f"/api/explore/{view}", params={"clock": "2017-01-02"}).status_code == 404


def test_unknown_sort_column_is_422(client: TestClient) -> None:
    params = {"clock": "2017-01-02", "sort": "order_id; drop table x"}
    assert client.get("/api/explore/orders", params=params).status_code == 422


def test_data_status_reports_the_source_hash(client: TestClient, source: Path) -> None:
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    assert client.get("/api/data-status").json() == {"loaded": True, "source_sha256": sha}


def test_data_status_without_a_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    r = TestClient(main.app).get("/api/data-status")
    assert r.json() == {"loaded": False, "source_sha256": None}
