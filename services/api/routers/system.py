"""
System router — GET /system/status
Real-time system health and status information.

Only reports what can be truthfully verified from the API process.
Does not fabricate metrics or service statuses.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from dependencies import get_db

router = APIRouter(tags=["system"])

# Track API start time
_start_time = time.time()


class ServiceStatus(BaseModel):
    name: str
    status: str  # healthy, degraded, unavailable, unknown
    message: Optional[str] = None
    last_checked: str


class DatabaseStatus(BaseModel):
    connected: bool
    host: str
    database: str
    events_count: int
    canonical_events_count: int
    verification_log_count: int
    latest_ingestion: Optional[str] = None
    earliest_ingestion: Optional[str] = None
    last_checked: str


class KafkaStatus(BaseModel):
    available_topics: list[str]
    topic_count: int
    last_checked: str


class DataStatistics(BaseModel):
    total_source_records: int
    total_canonical_events: int
    total_verification_actions: int
    records_by_source_type: dict[str, int]
    events_by_status: dict[str, int]
    latest_event_timestamp: Optional[str] = None


class SystemStatusResponse(BaseModel):
    api: ServiceStatus
    database: DatabaseStatus
    kafka: KafkaStatus
    data: DataStatistics
    uptime_seconds: float
    checked_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _dt_to_iso(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return str(dt)


def _get_db_info() -> tuple:
    """Single connection for all database checks. Returns (DatabaseStatus, DataStatistics)."""
    now = _now_iso()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Verify connectivity
                cur.execute("SELECT 1")
                cur.fetchone()

                # Get host info (without exposing credentials)
                cur.execute("SELECT inet_server_addr()")
                server_addr = cur.fetchone()[0]
                host_display = server_addr if server_addr else "localhost"
                host_display = str(server_addr) if server_addr else "localhost"

                # Get database name
                cur.execute("SELECT current_database()")
                db_name = cur.fetchone()[0]

                # Table counts
                cur.execute("SELECT COUNT(*) FROM events")
                events_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM canonical_events")
                canonical_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM verification_log")
                verification_count = cur.fetchone()[0]

                # Latest/earliest ingestion
                cur.execute("SELECT MAX(ingestion_timestamp), MIN(ingestion_timestamp) FROM events")
                latest_ing, earliest_ing = cur.fetchone()

                # Source records by type
                cur.execute(
                    "SELECT source_type, COUNT(*) FROM events GROUP BY source_type ORDER BY COUNT(*) DESC"
                )
                by_source = {row[0]: row[1] for row in cur.fetchall()}

                # Canonical events by verification status
                cur.execute(
                    "SELECT verification_status, COUNT(*) FROM canonical_events GROUP BY verification_status ORDER BY COUNT(*) DESC"
                )
                by_status = {row[0]: row[1] for row in cur.fetchall()}

                # Latest event timestamp
                cur.execute("SELECT MAX(last_seen) FROM canonical_events")
                latest_event = cur.fetchone()[0]

                db_status = DatabaseStatus(
                    connected=True,
                    host=host_display,
                    database=db_name,
                    events_count=events_count,
                    canonical_events_count=canonical_count,
                    verification_log_count=verification_count,
                    latest_ingestion=_dt_to_iso(latest_ing),
                    earliest_ingestion=_dt_to_iso(earliest_ing),
                    last_checked=now,
                )

                data_stats = DataStatistics(
                    total_source_records=events_count,
                    total_canonical_events=canonical_count,
                    total_verification_actions=verification_count,
                    records_by_source_type=by_source,
                    events_by_status=by_status,
                    latest_event_timestamp=_dt_to_iso(latest_event),
                )

                return db_status, data_stats
    except Exception as exc:
        import logging
        logging.warning("System status DB check failed: %s", exc)
        db_status = DatabaseStatus(
            connected=False, host="unknown", database="unknown",
            events_count=0, canonical_events_count=0, verification_log_count=0,
            last_checked=now,
        )
        data_stats = DataStatistics(
            total_source_records=0, total_canonical_events=0, total_verification_actions=0,
            records_by_source_type={}, events_by_status={}, latest_event_timestamp=None,
        )
        return db_status, data_stats


def _check_kafka() -> KafkaStatus:
    """Query broker metadata and report the topics actually visible to this API."""
    try:
        from confluent_kafka import Producer
        bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        producer = Producer({
            "bootstrap.servers": bootstrap,
            "socket.timeout.ms": 2000,
            "message.timeout.ms": 2000,
            "socket.timeout.ms": 1500,
            "message.timeout.ms": 1500,
        })
        metadata = producer.list_topics(timeout=1.5)
        topics = sorted(metadata.topics.keys()) if metadata and metadata.topics else []
        return KafkaStatus(available_topics=topics, topic_count=len(topics), last_checked=_now_iso())
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("System status Kafka check failed: %s", exc)
        return KafkaStatus(available_topics=[], topic_count=0, last_checked=_now_iso())


@router.get("/system/status", response_model=SystemStatusResponse)
def get_system_status():
    """Real-time system health status — only reports what can be truthfully verified."""
    now = _now_iso()

    # Check API health (if we're responding, the API is healthy)
    api_status = ServiceStatus(
        name="API Server",
        status="healthy",
        message="FastAPI responding normally",
        last_checked=now,
    )

    # Check database and data statistics (single connection)
    db_status, data_stats = _get_db_info()

    # Check Kafka (reported by Docker health checks, we list known topics)
    kafka_status = _check_kafka()

    return SystemStatusResponse(
        api=api_status,
        database=db_status,
        kafka=kafka_status,
        data=data_stats,
        uptime_seconds=round(time.time() - _start_time, 1),
        checked_at=now,
    )
