"""
SIH26069 — Processing Latency Timestamps Unit & Integration Tests
Validates spark_processed_at and db_written_at across models, schema, and API response.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))
sys.path.insert(0, str(REPO_ROOT / "services" / "api" / "routers"))
sys.path.insert(0, str(REPO_ROOT / "services" / "spark" / "jobs"))

# Mock dependencies not installed in minimal test environments
for mod_name in ["fastapi", "fastapi.responses", "dependencies", "pyspark", "pyspark.sql", "pyspark.sql.functions", "pyspark.sql.types"]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from routers.events import (
    EventListItem,
    EventDetailResponse,
    EventDetailSource,
    EventDetailLocation,
    EventDetailEvent,
    EventDetailSocialMetadata,
    EventDetailMedia,
    EventDetailAI,
    EventDetailVerification,
)


def test_event_list_item_latency_fields():
    event_id = str(uuid.uuid4())
    item = EventListItem(
        event_id=event_id,
        event_category="flood",
        severity="extreme",
        city="Mumbai",
        state="Maharashtra",
        event_timestamp="2026-09-10T12:00:00.000Z",
        created_at="2026-09-10T12:00:05.000Z",
        spark_processed_at="2026-09-10T12:00:02.150Z",
        db_written_at="2026-09-10T12:00:02.300Z",
    )
    dumped = item.model_dump()
    assert dumped["spark_processed_at"] == "2026-09-10T12:00:02.150Z"
    assert dumped["db_written_at"] == "2026-09-10T12:00:02.300Z"
    print("\n[TEST PASSED] EventListItem successfully includes spark_processed_at and db_written_at")


def test_event_detail_response_latency_fields():
    event_id = str(uuid.uuid4())
    detail = EventDetailResponse(
        event_id=event_id,
        source=EventDetailSource(),
        event_timestamp="2026-09-10T12:00:00.000Z",
        ingestion_timestamp="2026-09-10T12:00:01.000Z",
        location=EventDetailLocation(city="Nagpur", state="Maharashtra"),
        event=EventDetailEvent(category="heatwave", severity="extreme"),
        social_metadata=EventDetailSocialMetadata(),
        media=EventDetailMedia(),
        ai=EventDetailAI(classified_category="heatwave", classification_confidence=0.92),
        verification=EventDetailVerification(status="verified"),
        created_at="2026-09-10T12:00:05.000Z",
        updated_at="2026-09-10T12:00:05.000Z",
        spark_processed_at="2026-09-10T12:00:03.450Z",
        db_written_at="2026-09-10T12:00:03.620Z",
    )
    dumped = detail.model_dump()
    assert dumped["spark_processed_at"] == "2026-09-10T12:00:03.450Z"
    assert dumped["db_written_at"] == "2026-09-10T12:00:03.620Z"
    print("[TEST PASSED] EventDetailResponse successfully includes spark_processed_at and db_written_at")


def test_stream_processor_canonical_rebuild():
    from stream_processor import _rebuild_canonical
    event = {
        "event_id": str(uuid.uuid4()),
        "event_category": "thunderstorm",
        "severity": "high",
        "description": "Lightning storm near Pune",
        "spark_processed_at": "2026-09-10T12:00:01.890Z",
    }
    rebuilt = _rebuild_canonical(event)
    assert rebuilt.get("spark_processed_at") == "2026-09-10T12:00:01.890Z"
    print("[TEST PASSED] stream_processor._rebuild_canonical preserves spark_processed_at")


def test_sql_migration_file():
    migration_file = REPO_ROOT / "sql" / "09_add_latency_timestamps.sql"
    assert migration_file.exists(), "Migration sql/09_add_latency_timestamps.sql missing"
    sql_text = migration_file.read_text(encoding="utf-8")
    assert "spark_processed_at TIMESTAMPTZ" in sql_text
    assert "db_written_at TIMESTAMPTZ" in sql_text
    assert "idx_canonical_events_spark_processed_at" in sql_text
    assert "idx_canonical_events_db_written_at" in sql_text
    print("[TEST PASSED] sql/09_add_latency_timestamps.sql contains required DDL statements")


def test_pg_writer_sql_contains_timestamps():
    pg_writer_path = REPO_ROOT / "services" / "spark" / "jobs" / "pg_writer.py"
    pg_writer_code = pg_writer_path.read_text(encoding="utf-8")
    assert "spark_processed_at, db_written_at" in pg_writer_code
    assert "db_written_at = %s" in pg_writer_code
    assert "spark_processed_at = COALESCE(%s, spark_processed_at)" in pg_writer_code
    print("[TEST PASSED] pg_writer.py upsert statements include spark_processed_at and db_written_at")


if __name__ == "__main__":
    test_event_list_item_latency_fields()
    test_event_detail_response_latency_fields()
    test_stream_processor_canonical_rebuild()
    test_sql_migration_file()
    test_pg_writer_sql_contains_timestamps()
    print("\nALL LATENCY TIMESTAMPS TESTS PASSED SUCCESSFULLY!")
