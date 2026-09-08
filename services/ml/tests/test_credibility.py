from __future__ import annotations

"""
Credibility Scoring Unit Tests (§25.1).
"""

import sys
from pathlib import Path
import pytest

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from credibility.credibility_scorer import score_credibility


def test_high_trust_weather_api_source():
    event = {
        "source_type": "weather_api",
        "source_name": "Open-Meteo",
        "latitude": 19.076,
        "longitude": 72.878,
        "city": "Mumbai",
        "timestamp": "2026-09-01T10:00:00Z",
        "ingestion_timestamp": "2026-09-01T10:05:00Z",
        "description": "Continuous heavy rainfall recorded at Mumbai observation station.",
        "category": "heavy_rainfall"
    }
    result = score_credibility(event)
    assert result["credibility_score"] >= 0.70
    assert len(result["credibility_reasons"]) > 0
    assert any("high configured trust" in r for r in result["credibility_reasons"])


def test_low_trust_social_source():
    event = {
        "source_type": "simulated_social",
        "source_name": "simulated_social",
        "latitude": 19.076,
        "longitude": 72.878,
        "city": "Mumbai",
        "timestamp": "2026-09-01T10:00:00Z",
        "description": "flood",
        "category": "flood"
    }
    result = score_credibility(event)
    assert result["credibility_score"] <= 0.65
    assert any("low configured trust" in r for r in result["credibility_reasons"])


def test_corroborated_events_boost_score():
    current_event = {
        "source_id": "c_001",
        "source_type": "citizen",
        "latitude": 19.076,
        "longitude": 72.878,
        "city": "Mumbai",
        "timestamp": "2026-09-01T10:00:00Z",
        "description": "Flooded street near station with deep water.",
        "category": "flood"
    }

    recent_events = [
        {
            "source_id": "r_001",
            "source_type": "rss",
            "latitude": 19.078,
            "longitude": 72.880,
            "timestamp": "2026-09-01T10:05:00Z",
            "category": "flood",
            "description": "Flooding reported in Mumbai."
        },
        {
            "source_id": "w_001",
            "source_type": "weather_api",
            "latitude": 19.075,
            "longitude": 72.875,
            "timestamp": "2026-09-01T10:02:00Z",
            "category": "heavy_rainfall",
            "description": "Heavy rain."
        },
    ]

    single_result = score_credibility(current_event, recent_events=[])
    corroborated_result = score_credibility(current_event, recent_events=recent_events)

    assert corroborated_result["credibility_score"] > single_result["credibility_score"]
    assert any("corroborating" in r or "independent reports" in r for r in corroborated_result["credibility_reasons"])


def test_spatial_inconsistency_penalty():
    # Coordinates in Delhi, but stated city is Mumbai
    suspicious_event = {
        "source_type": "citizen",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "city": "Mumbai",
        "timestamp": "2026-09-01T10:00:00Z",
        "description": "Water logging in area",
        "category": "flood"
    }
    result = score_credibility(suspicious_event)
    assert result["factors"]["spatial_consistency"] <= 0.30
    assert any("do not align" in r for r in result["credibility_reasons"])