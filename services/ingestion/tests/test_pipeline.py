"""Unit tests for the ingestion → normalization contract.

Runtime Kafka/PostgreSQL E2E is intentionally kept in scripts/smoke-test.sh;
this pytest module must remain deterministic and dependency-light.
"""
import json
import uuid
from datetime import datetime, timezone

from services.ingestion.adapters.citizen import normalize_citizen_report
from services.ingestion.normaliser.canonical_event import build_canonical_event


def test_citizen_normalization_produces_canonical_event():
    event = normalize_citizen_report(
        city="Mumbai", district="Mumbai Suburban", state="Maharashtra",
        latitude=19.076, longitude=72.878, category="flood", severity="high",
        description="Waterlogging on road", timestamp="2026-09-08T01:00:00.000Z",
        photo_urls=["/media/photos/a.jpg"], video_urls=[],
    )
    assert uuid.UUID(event["event_id"]).version == 4
    assert event["source_type"] == "citizen"
    assert event["location"]["city"] == "Mumbai"
    assert event["event"]["category"] == "flood"
    assert event["media"]["photos"] == ["/media/photos/a.jpg"]
    assert event["verification"]["status"] == "pending"


def test_canonical_event_is_json_serializable():
    event = build_canonical_event(
        source_type="weather_api", source_name="Open-Meteo", source_id="mumbai-1",
        description="Heavy rainfall flooded roads", category="heavy_rainfall",
        location={"latitude": 19.076, "longitude": 72.878, "city": "Mumbai", "country": "India"},
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), severity="high",
    )
    payload = json.dumps(event)
    assert json.loads(payload)["event_id"] == event["event_id"]
