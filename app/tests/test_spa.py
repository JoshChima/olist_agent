import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import olist_agent.main as main


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "app.js").write_text("console.log('hi')")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path))
    yield TestClient(importlib.reload(main).app)
    monkeypatch.delenv("STATIC_DIR")
    importlib.reload(main)


def test_deep_link_serves_index(client: TestClient) -> None:
    r = client.get("/some/route")
    assert r.status_code == 200
    assert r.text == "<div id=root></div>"


def test_static_asset_and_api_still_win(client: TestClient) -> None:
    assert client.get("/app.js").text == "console.log('hi')"
    assert client.get("/health").json()["status"] == "ok"


def test_unknown_api_path_is_404(client: TestClient) -> None:
    assert client.get("/api/nope").status_code == 404


def test_missing_asset_is_404_not_index(client: TestClient) -> None:
    # A stale hashed bundle must 404, or the browser parses index.html as JS.
    assert client.get("/assets/old-hash.js").status_code == 404
