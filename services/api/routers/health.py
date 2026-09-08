"""
Health router — GET /health
Per 04_API_CONTRACT.md §6.

Checks PostgreSQL connectivity (SELECT 1) and Kafka reachability
(list_topics with a short timeout) and reports a truthful status:
  - both connected        → 200  {"status": "healthy",   ...}
  - one dependency down   → 200  {"status": "degraded",  ...}
  - database down         → 503  {"status": "unhealthy", ...}
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Response

from dependencies import get_db

router = APIRouter(tags=["health"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _check_database() -> bool:
    """Return True if PostgreSQL is reachable."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False


def _check_kafka() -> bool:
    """Return True if a Kafka broker is reachable (short timeout, never hangs)."""
    try:
        from confluent_kafka import Producer

        bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        producer = Producer({
            "bootstrap.servers": bootstrap,
            "socket.timeout.ms": 2000,
            "message.timeout.ms": 2000,
        })
        metadata = producer.list_topics(timeout=2.0)
        return metadata is not None
    except Exception:
        return False


@router.get("/health")
def health_check(response: Response):
    """System health check — database and Kafka connectivity."""
    db_ok = _check_database()
    kafka_ok = _check_kafka()

    if db_ok and kafka_ok:
        status = "healthy"
        code = 200
    elif db_ok:
        status = "degraded"
        code = 200
    else:
        status = "unhealthy"
        code = 503

    response.status_code = code
    return {
        "status": status,
        "database": "connected" if db_ok else "unavailable",
        "kafka": "connected" if kafka_ok else "unavailable",
        "timestamp": _now_iso(),
    }