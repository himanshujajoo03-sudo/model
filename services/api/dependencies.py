"""
FastAPI dependencies — database connection pool using psycopg2.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool


# ── Connection pool (singleton) ─────────────────────────────────────
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Get or create the thread-safe connection pool."""
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL", "")
        if not dsn:
            # Build from individual env vars
            host = os.environ.get("POSTGRES_HOST", "postgres")
            port = os.environ.get("POSTGRES_PORT", "5432")
            db = os.environ.get("POSTGRES_DB", "weatherdb")
            user = os.environ.get("POSTGRES_USER", "weather")
            password = os.environ.get("POSTGRES_PASSWORD", "")
            dsn = f"host={host} port={port} dbname={db} user={user} password={password}"

        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=dsn,
        )
    return _pool


@contextmanager
def get_db() -> Generator:
    """
    Yield a database connection from the pool.
    Auto-commits on success, rolls back on exception.
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
