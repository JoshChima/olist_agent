"""The web app's Postgres access: one pool, and a transaction with the clock set."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from functools import cache

import psycopg
from azure.core.credentials import TokenCredential
from psycopg_pool import ConnectionPool

PG_TOKEN_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


def set_clock(conn: psycopg.Connection, clock: date) -> None:
    """Sets the clock the sim views read (ADR-0008) until this transaction ends.

    set_config(..., true) is SET LOCAL in function form, which takes a bind parameter.
    """
    conn.execute("select set_config('sim.clock', %s, true)", [clock.isoformat()])


@cache
def credential() -> TokenCredential:
    """The managed identity named by AZURE_CLIENT_ID, which Container Apps sets in Azure."""
    from azure.identity import ManagedIdentityCredential

    return ManagedIdentityCredential(client_id=os.environ["AZURE_CLIENT_ID"])


def auth() -> dict[str, str]:
    """Connection settings to add to DATABASE_URL, asked for on every new connection.

    In Azure the password is an Entra token for the managed identity (ADR-0010). Tokens
    last about an hour; azure-identity caches one and fetches the next before it expires,
    so each new connection signs in with a valid token. An open connection stays signed in
    after its token expires. Locally DATABASE_URL carries a password, so nothing is added.
    """
    if not os.getenv("AZURE_CLIENT_ID"):
        return {}
    return {"password": credential().get_token(PG_TOKEN_SCOPE).token}


@cache
def pool() -> ConnectionPool:
    return ConnectionPool(os.environ["DATABASE_URL"], kwargs=auth, open=True)


@contextmanager
def at_clock(clock: date) -> Iterator[psycopg.Connection]:
    """A connection in a transaction, with the clock set. Commits or rolls back on exit."""
    with pool().connection() as conn:
        set_clock(conn, clock)
        yield conn
