"""The web app's Postgres access: one pool, and a transaction with the clock set."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from functools import cache

import psycopg
from psycopg_pool import ConnectionPool


def set_clock(conn: psycopg.Connection, clock: date) -> None:
    """Sets the clock the sim views read (ADR-0008) until this transaction ends.

    set_config(..., true) is SET LOCAL in function form, which takes a bind parameter.
    """
    conn.execute("select set_config('sim.clock', %s, true)", [clock.isoformat()])


@cache
def pool() -> ConnectionPool:
    return ConnectionPool(os.environ["DATABASE_URL"], open=True)


@contextmanager
def at_clock(clock: date) -> Iterator[psycopg.Connection]:
    """A connection in a transaction, with the clock set. Commits or rolls back on exit."""
    with pool().connection() as conn:
        set_clock(conn, clock)
        yield conn
