import os
import subprocess
import sys
import uuid

from tests.conftest import Load, Pg


def test_unchanged_second_run_does_nothing(load: Load) -> None:
    orders = [{"order_id": uuid.uuid4().hex, "order_purchase_timestamp": "2017-01-01 10:00:00"}]
    assert load(orders=orders) == "loaded"
    assert load(orders=orders) == "unchanged"


def loader(pg: Pg, source: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": pg.admin, "OLIST_SQLITE": source}
    return subprocess.run(
        [sys.executable, "-m", "olist_agent.loader"], env=env, capture_output=True, text=True
    )


def test_missing_source_exits_0_with_no_source_data(pg: Pg) -> None:
    r = loader(pg, "no/such/olist.sqlite")
    assert (r.returncode, r.stdout.strip()) == (0, "no source data")


def test_loader_never_imports_the_web_app() -> None:
    code = "import sys, olist_agent.loader; print('olist_agent.main' in sys.modules)"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "False"
