"""
FastAPI dependencies — database connection pool supporting psycopg2 and psycopg3.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

try:
    import psycopg2
    import psycopg2.pool
    _PSYCOPG_VER = 2
except ImportError:
    try:
        import psycopg
        from psycopg_pool import ConnectionPool
        _PSYCOPG_VER = 3
    except ImportError:
        _PSYCOPG_VER = 0


# ── Connection pool (singleton) ─────────────────────────────────────
_pool = None


def _get_pool():
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

        if _PSYCOPG_VER == 2:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=dsn,
            )
        elif _PSYCOPG_VER == 3:
            _pool = ConnectionPool(
                conninfo=dsn,
                min_size=2,
                max_size=10,
                open=True,
            )
        else:
            raise RuntimeError("Neither psycopg2 nor psycopg is installed")
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
