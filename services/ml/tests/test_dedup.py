from __future__ import annotations

"""
Duplicate Detection Unit Tests (§25.1).
"""

import sys
from pathlib import Path
import pytest

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from dedup.duplicate_detector import (
    compute_duplicate_score,
    is_duplicate,
    is_review_candidate
)


def test_identical_reports():
    report1 = {
        "source_id": "src_1",
        "description": "Heavy rainfall in Mumbai causing traffic disruption",
        "latitude": 19.076,
        "longitude": 72.8777,
        "timestamp": "2026-09-01T10:00:00Z",
        "category": "heavy_rainfall"
    }

    report2 = {
        "source_id": "src_1",
        "description": "Heavy rainfall in Mumbai causing traffic disruption",
        "latitude": 19.076,
        "longitude": 72.8777,
        "timestamp": "2026-09-01T10:02:00Z",
        "category": "heavy_rainfall"
    }

    score = compute_duplicate_score(report1, report2)
    assert score >= 0.85
    assert is_duplicate(score) is True


def test_near_identical_text():
    report1 = {
        "source_id": "src_1",
        "description": "Severe flooding on Kurla highway with high water level",
        "latitude": 19.076,
        "longitude": 72.8777,
        "timestamp": "2026-09-01T10:00:00Z",
        "category": "flood"
    }

    report2 = {
        "source_id": "src_2",
        "description": "Severe flooding on Kurla highway road with high water",
        "latitude": 19.077,
        "longitude": 72.8780,
        "timestamp": "2026-09-01T10:05:00Z",
        "category": "flood"
    }

    score = compute_duplicate_score(report1, report2)
    assert score >= 0.58


def test_different_events_distinct_score():
    flood_event = {
        "source_id": "src_1",
        "description": "Severe flooding in Mumbai",
        "latitude": 19.076,
        "longitude": 72.8777,
        "timestamp": "2026-09-01T10:00:00Z",
        "category": "flood"
    }

    heat_event = {
        "source_id": "src_2",
        "description": "Scorching heat wave conditions in Nagpur",
        "latitude": 21.145,
        "longitude": 79.088,
        "timestamp": "2026-09-01T10:00:00Z",
        "category": "heatwave"
    }

    score = compute_duplicate_score(flood_event, heat_event)
    assert score < 0.30
    assert is_duplicate(score) is False


def test_empty_recent_events_returns_zero():
    event = {
        "description": "Rain in Mumbai",
        "latitude": 19.076,
        "longitude": 72.8777,
        "timestamp": "2026-09-01T10:00:00Z",
        "category": "rainfall"
    }
    score = compute_duplicate_score(event, recent_events=[])
    assert score == 0.0