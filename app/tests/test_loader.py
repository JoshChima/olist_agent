import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import IO

import psycopg
import pytest
from azure.core.exceptions import ResourceNotFoundError
from psycopg.conninfo import make_conninfo

from olist_agent import loader
from tests.conftest import Load, Pg


def test_unchanged_second_run_does_nothing(load: Load) -> None:
    orders = [{"order_id": uuid.uuid4().hex, "order_purchase_timestamp": "2017-01-01 10:00:00"}]
    assert load(orders=orders) == "loaded"
    assert load(orders=orders) == "unchanged"


def run_loader(pg: Pg, source: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": pg.admin, "OLIST_SQLITE": source}
    return subprocess.run(
        [sys.executable, "-m", "olist_agent.loader"], env=env, capture_output=True, text=True
    )


def test_missing_source_exits_0_with_no_source_data(pg: Pg) -> None:
    r = run_loader(pg, "no/such/olist.sqlite")
    assert (r.returncode, r.stdout.strip()) == (0, "no source data")


# Stands in for Azure's pg_catalog.pgaadauth_create_principal_with_oid, which maps a new
# login role to an Entra object. Here the mapping goes in the role's comment.
FAKE_PGAADAUTH = """
create function public.pgaadauth_create_principal_with_oid(
    role text, oid text, type text, admin boolean, mfa boolean) returns text
language plpgsql as $$
begin
    execute format('create role %I login password %L', role, 'entra-token');
    execute format('comment on role %I is %L', role, concat_ws(',', oid, type, admin, mfa));
    return 'Created role for ' || role;
end $$
"""


def test_in_azure_the_app_role_is_its_entra_identity_and_reads_only_sim(pg: Pg) -> None:
    with psycopg.connect(pg.admin, autocommit=True) as c:
        c.execute(FAKE_PGAADAUTH)
    try:
        for _ in range(2):  # the second run finds the role already there
            assert loader.load(pg.admin, None, "id-app", app_principal_id="app-oid") == (
                "no source data"
            )
        with psycopg.connect(pg.admin) as c:
            mapped = c.execute("select shobj_description('id-app'::regrole, 'pg_authid')")
            assert mapped.fetchone() == ("app-oid,service,f,f",)  # not an admin, no MFA

        app = make_conninfo(pg.admin, user="id-app", password="entra-token")
        with psycopg.connect(app) as c:
            assert c.execute("select count(*) from sim.data_status").fetchone() is not None
        with psycopg.connect(app) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("select count(*) from raw.orders")
    finally:
        with psycopg.connect(pg.admin, autocommit=True) as c:
            c.execute('drop role if exists "id-app"')
            c.execute("drop function public.pgaadauth_create_principal_with_oid")


class FakeBlob:
    """Stands in for azure.storage.blob.BlobClient: the container holds `content`, or nothing."""

    content: bytes | None = None
    opened: tuple[str, object] | None = None

    @classmethod
    def from_blob_url(cls, url: str, credential: object) -> "FakeBlob":
        FakeBlob.opened = (url, credential)
        return cls()

    def download_blob(self) -> "FakeBlob":
        if self.content is None:
            raise ResourceNotFoundError("The specified blob does not exist.")
        return self

    def readinto(self, stream: IO[bytes]) -> int:
        assert self.content is not None
        return stream.write(self.content)


BLOB_URL = "https://stolistdata.blob.core.windows.net/olist-data/olist.sqlite"


@pytest.fixture
def blob(monkeypatch: pytest.MonkeyPatch) -> type[FakeBlob]:
    monkeypatch.setattr(loader, "BlobClient", FakeBlob)
    monkeypatch.setattr(loader.db, "credential", lambda: "the loader identity")
    monkeypatch.setattr(FakeBlob, "content", None)
    return FakeBlob


def test_locally_the_source_is_the_olist_sqlite_path(
    blob: type[FakeBlob], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OLIST_BLOB_URL", raising=False)
    monkeypatch.setenv("OLIST_SQLITE", "/data/olist.sqlite")
    assert loader.source(tmp_path) == Path("/data/olist.sqlite")
    monkeypatch.delenv("OLIST_SQLITE")
    assert loader.source(tmp_path) is None


def test_in_azure_the_source_is_downloaded_from_blob_as_the_loader(
    blob: type[FakeBlob], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OLIST_BLOB_URL", BLOB_URL)
    monkeypatch.setenv("OLIST_SQLITE", "/ignored/in/azure.sqlite")
    monkeypatch.setattr(blob, "content", b"SQLite format 3\x00")
    path = loader.source(tmp_path)
    assert path is not None and path.read_bytes() == b"SQLite format 3\x00"
    assert blob.opened == (BLOB_URL, "the loader identity")


def test_in_azure_no_uploaded_blob_means_no_source(
    blob: type[FakeBlob], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OLIST_BLOB_URL", BLOB_URL)
    assert loader.source(tmp_path) is None


def test_loader_never_imports_the_web_app() -> None:
    code = "import sys, olist_agent.loader; print('olist_agent.main' in sys.modules)"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "False"
