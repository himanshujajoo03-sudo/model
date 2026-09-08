from datetime import datetime, timezone

from pipeline import enrich_event


def test_enrich_event_produces_full_ai_contract():
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "event_id": "e1",
        "description": "Heavy rain flooded the road in Pune",
        "category": "rainfall",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "city": "Pune",
        "timestamp": now,
        "ingestion_timestamp": now,
        "source_id": "citizen-1",
        "source_type": "citizen",
    }
    result = enrich_event(event)
    assert result["ai"]["classified_category"] == "heavy_rainfall"
    assert 0 <= result["ai"]["classification_confidence"] <= 1
    assert 0 <= result["ai"]["duplicate_score"] <= 1
    assert 0 <= result["ai"]["credibility_score"] <= 1
    assert isinstance(result["ai"]["credibility_reasons"], list)
    assert isinstance(result["ai"]["explanation"], list)


def test_enrich_event_does_not_mutate_input():
    event = {"event_id": "e2", "description": "flooded road", "category": "flood"}
    original = dict(event)
    enrich_event(event)
    assert event == original
