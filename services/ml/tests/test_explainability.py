from __future__ import annotations

"""
Explainability Unit Tests (§25.1).
"""

import sys
from pathlib import Path
import pytest

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from explainability.reason_generator import generate_reasons


def test_reasons_match_actual_evidence():
    factors = {
        "source_trust": 0.95,
        "corroboration": 0.85,
        "weather_agreement": 0.90,
        "temporal_consistency": 1.0,
        "spatial_consistency": 1.0,
        "content_quality": 0.90,
    }
    event = {
        "corroboration_count": 3,
        "city": "Mumbai"
    }

    reasons = generate_reasons(factors=factors, event=event)
    assert len(reasons) >= 3
    assert any("high configured trust" in r for r in reasons)
    assert any("independent reports detected" in r for r in reasons)
    assert any("observations are consistent" in r for r in reasons)


def test_no_fabricated_evidence_when_absent():
    factors = {
        "source_trust": 0.40,
        "corroboration": 0.0,
        "weather_agreement": 0.30,
        "temporal_consistency": 0.30,
        "spatial_consistency": 0.30,
        "content_quality": 0.20,
    }
    event = {
        "corroboration_count": 0,
        "city": "Unknown"
    }

    reasons = generate_reasons(factors=factors, event=event)
    assert any("No independent corroborating reports" in r for r in reasons)
    assert any("No corroborating weather observation" in r for r in reasons)
    assert not any("Structured weather observations are consistent" in r for r in reasons)

