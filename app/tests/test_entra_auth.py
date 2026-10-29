"""In Azure, Postgres connections sign in with a managed identity's Entra token (ADR-0010).

Postgres here can't check an Entra token, so a role's password stands in for it.
"""

import psycopg
import pytest
from azure.core.credentials import AccessToken
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from olist_agent import db
from tests.conftest import Pg


def test_each_new_connection_signs_in_with_the_current_token(
    pg: Pg, monkeypatch: pytest.MonkeyPatch
) -> None:
    with psycopg.connect(pg.admin, autocommit=True) as c:
        c.execute("drop role if exists entra_probe")
        c.execute("create role entra_probe login password 'token-1'")
    params = {**conninfo_to_dict(pg.app), "user": "entra_probe"}
    del params["password"]  # in Azure the DSN has none
    monkeypatch.setenv("DATABASE_URL", make_conninfo(**params))
    monkeypatch.setenv("AZURE_CLIENT_ID", "the-app-identity")

    token = "token-1"

    class Credential:
        def get_token(self, *scopes: str) -> AccessToken:
            assert scopes == ("https://ossrdbms-aad.database.windows.net/.default",)
            return AccessToken(token, 0)

    monkeypatch.setattr(db, "credential", Credential)
    with db.pool.__wrapped__() as pool:
        with pool.connection() as c:
            assert c.execute("select current_user").fetchone() == ("entra_probe",)

        # The token expired and Entra issued a new one; old tokens no longer sign in.
        with psycopg.connect(pg.admin, autocommit=True) as c:
            c.execute("alter role entra_probe password 'token-2'")
        token = "token-2"
        pool.drain()  # replaces every connection, as max_lifetime eventually does
        with pool.connection() as c:
            assert c.execute("select current_user").fetchone() == ("entra_probe",)
