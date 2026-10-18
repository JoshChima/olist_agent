from fastapi.testclient import TestClient

from olist_agent.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_hello() -> None:
    assert client.get("/api/hello").json() == {"message": "Hello from olist_agent"}
