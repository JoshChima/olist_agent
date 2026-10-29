from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from testcontainers.community.postgres import PostgresContainer

from olist_agent import db, loader
from tests.olist_sqlite import write_olist

APP_ROLE = "olist_app"


@dataclass
class Pg:
    admin: str  # the loader's DSN
    app: str  # the web app's DSN: a role that may only read sim


@pytest.fixture(scope="session")
def pg() -> Iterator[Pg]:
    """One Postgres per test session; each test loads its own data with the real loader."""
    with PostgresContainer("pgvector/pgvector:pg17", driver=None) as c:
        host, port = c.get_container_host_ip(), c.get_exposed_port(5432)
        app = f"postgresql://{APP_ROLE}:{APP_ROLE}@{host}:{port}/{c.dbname}"
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("DATABASE_URL", app)
            yield Pg(c.get_connection_url(), app)
        # The API's pool, if a test opened it, would keep reconnecting to a stopped container.
        if db.pool.cache_info().currsize:
            db.pool().close()
            db.pool.cache_clear()


Load = Callable[..., str]


@pytest.fixture(scope="session")
def load(pg: Pg, tmp_path_factory: pytest.TempPathFactory) -> Load:
    """Writes the given rows (table=[{column: value}]) to SQLite and runs the loader on it."""
    path = tmp_path_factory.mktemp("olist") / "olist.sqlite"

    def run(**rows: list[dict[str, Any]]) -> str:
        return loader.load(pg.admin, write_olist(path, **rows), APP_ROLE, APP_ROLE)

    return run
