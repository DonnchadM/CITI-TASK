"""PostgreSQL connection management and schema bootstrap (psycopg 3).

The module-level connection is reused across warm Lambda invocations to avoid
reconnecting on every request. :func:`transaction` yields a cursor wrapped in a
transaction that commits on success and rolls back on any error, so writes never
leave the database in an inconsistent state.
"""

import logging
import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from .config import postgres_dsn

logger = logging.getLogger(__name__)

# Reused across invocations within the same warm Lambda container.
_conn: "psycopg.Connection | None" = None

# Guards the one-time idempotent schema bootstrap per container.
_schema_ready = False


def get_connection() -> "psycopg.Connection":
    """Return a live connection, (re)connecting if the cached one is closed."""
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(postgres_dsn(), row_factory=dict_row, autocommit=False)
    return _conn


@contextmanager
def transaction() -> Iterator["psycopg.Cursor"]:
    """Yield a cursor inside a transaction.

    Commits when the block exits normally; rolls back and re-raises on error.
    A broken connection is discarded so the next call reconnects cleanly.
    """
    global _conn
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:  # pragma: no cover - connection already dead
            logger.debug("Rollback failed; the connection is likely already dead.")
        if conn.closed:
            _conn = None
        raise


def ensure_schema() -> None:
    """Apply the idempotent schema (tables + analytics view) once per container.

    The DDL uses ``IF NOT EXISTS`` / ``CREATE OR REPLACE``, so it is safe to run on
    every cold start. A dedicated migration step is the documented scale-up path.
    """
    global _schema_ready
    if _schema_ready:
        return
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as handle:
        ddl = handle.read()
    with transaction() as cur:
        cur.execute(ddl)
    _schema_ready = True
    logger.info("Database schema ensured.")
