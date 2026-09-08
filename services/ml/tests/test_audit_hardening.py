from __future__ import annotations

"""
Comprehensive Regression & Invariant Tests for AI/ML Hardening (§25–§29).
Verifies fixes across all 35 audit phases.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
import pandas as pd

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from classifier.rules import (
    VALID_CATEGORIES,
    categories_are_compatible,
    canonicalize_category,
    validate_category,
    InvalidCategoryError,
    CATEGORY_COMPATIBILITY
)
from classifier.event_classifier import classify_event
from classifier.rule_based_classifier import RuleBasedClassifier
from classifier.hybrid_classifier import HybridClassifier
from config.config_loader import load_ml_config, validate_weights, ConfigurationError
from credibility.credibility_scorer import score_credibility, get_credibility_weights
from dedup.duplicate_detector import (
    compute_duplicate_score,
    is_duplicate,
    is_review_candidate,
    get_duplicate_config
)
from clustering.event_clusterer import assign_cluster, select_cluster_representative
from explainability.reason_generator import generate_reasons
from utils.event_schema import NormalizedEvent
from utils.geo import (
    haversine_km,
    parse_and_validate_coord,
    is_valid_coordinate,
    check_city_bounding_box
)
from utils.time_utils import (
    parse_timestamp,
    time_diff_minutes,
    check_future_timestamp
)
from training.prepare_data import prepare_training_data, DatasetValidationError
from training.train import train_classifier, check_data_leakage, SmallDatasetError


# =====================================================================
# Phase 2: Category Compatibility Symmetry
# =====================================================================

def test_category_compatibility_symmetry():
    """Verify A <-> B is strictly symmetric to B <-> A across all valid categories."""
    for c1 in VALID_CATEGORIES:
        for c2 in VALID_CATEGORIES:
            assert categories_are_compatible(c1, c2) == categories_are_compatible(c2, c1), (
                f"Asymmetry detected for pair ({c1}, {c2})"
            )


def test_cyclone_flood_symmetric_regression():
    """Explicit regression test for cyclone <-> flood compatibility symmetry."""
    assert categories_are_compatible("cyclone", "flood") is True
    assert categories_are_compatible("flood", "cyclone") is True


def test_heavy_rainfall_cyclone_symmetric():
    """Explicit regression test for heavy_rainfall <-> cyclone compatibility."""
    assert categories_are_compatible("heavy_rainfall", "cyclone") is True
    assert categories_are_compatible("cyclone", "heavy_rainfall") is True


def test_hailstorm_thunderstorm_symmetric():
    """Explicit regression test for hailstorm <-> thunderstorm compatibility."""
    assert categories_are_compatible("hailstorm", "thunderstorm") is True
    assert categories_are_compatible("thunderstorm", "hailstorm") is True


def test_other_never_corroborates():
    """'other' must never corroborate any category, not even itself."""
    for c in VALID_CATEGORIES:
        assert categories_are_compatible("other", c) is False
        assert categories_are_compatible(c, "other") is False


# =====================================================================
# Phase 3: Category Validation & Canonicalization
# =====================================================================

def test_canonicalize_valid_categories():
    for cat in VALID_CATEGORIES:
        assert canonicalize_category(cat) == cat


def test_canonicalize_aliases():
    assert canonicalize_category("flooding") == "flood"
    assert canonicalize_category("waterlogging") == "flood"
    assert canonicalize_category("heavy rain") == "heavy_rainfall"
    assert canonicalize_category("rain") == "rainfall"
    assert canonicalize_category("high_winds") == "strong_wind"
    assert canonicalize_category("hail") == "hailstorm"


def test_canonicalize_casing_and_whitespace():
    assert canonicalize_category("  FLOOD  ") == "flood"
    assert canonicalize_category("Heavy-Rainfall") == "heavy_rainfall"


def test_invalid_category_rejection_strict():
    """Strict mode must raise InvalidCategoryError and never convert unknown labels to 'other'."""
    with pytest.raises(InvalidCategoryError) as exc_info:
        validate_category("banana", file_path="test.csv", row_index=42)
    err = exc_info.value
    assert "Invalid category 'banana'" in str(err)
    assert "test.csv" in str(err)
    assert err.invalid_value == "banana"


def test_invalid_category_non_strict():
    """Non-strict mode must return None for unknown category (never silently convert to 'other')."""
    assert canonicalize_category("banana", strict=False) is None
    assert canonicalize_category("invalid_storm_type", strict=False) is None


def test_explicit_other_accepted():
    assert canonicalize_category("other") == "other"
    assert validate_category("other") == "other"


# =====================================================================
# Phase 7: Rule-Based Confidence Calibration
# =====================================================================

def test_exact_single_keyword_confidence():
    """Direct canonical keyword 'rain' must score >= 0.80 confidence (fixing previous 0.595)."""
    classifier = RuleBasedClassifier()
    res = classifier.predict("rain")
    assert res["classified_category"] == "rainfall"
    assert res["classification_confidence"] >= 0.80, (
        f"Expected confidence >= 0.80 for exact keyword 'rain', got {res['classification_confidence']}"
    )


def test_multiple_keywords_higher_confidence():
    classifier = RuleBasedClassifier()
    res = classifier.predict("Heavy torrential rain downpour causing submerged roads and flood")
    assert res["classified_category"] in ("flood", "heavy_rainfall")
    assert res["classification_confidence"] >= 0.85


def test_ambiguous_conflicting_keywords_lower_confidence():
    """Conflicting category signals should produce a penalized / lower confidence."""
    classifier = RuleBasedClassifier()
    # High heatwave vs high flood in same sentence
    res = classifier.predict("Extreme heatwave scorching heat alongside flooded roads")
    assert res["classification_confidence"] <= 0.75


# =====================================================================
# Phase 11, 12, 13: Geographic Coordinates & Coordinate 0
# =====================================================================

def test_coordinate_zero_is_valid():
    """(0.0, 0.0) represents Prime Meridian / Equator and must be treated as valid numeric coords."""
    assert is_valid_coordinate(0.0, 0.0) is True
    assert parse_and_validate_coord(0.0, is_latitude=True) == 0.0
    assert parse_and_validate_coord(0.0, is_latitude=False) == 0.0

    # Distance between (0,0) and (0,0) must be exactly 0
    assert haversine_km(0.0, 0.0, 0.0, 0.0) == 0.0


def test_coordinate_bounds_validation():
    # Valid
    assert is_valid_coordinate(90.0, 180.0) is True
    assert is_valid_coordinate(-90.0, -180.0) is True

    # Invalid lat
    assert is_valid_coordinate(90.1, 0.0) is False
    assert is_valid_coordinate(-91.0, 0.0) is False

    # Invalid lon
    assert is_valid_coordinate(0.0, 180.1) is False
    assert is_valid_coordinate(0.0, -180.1) is False

    # NaN and inf
    assert is_valid_coordinate(float("nan"), 0.0) is False
    assert is_valid_coordinate(0.0, float("inf")) is False

    # Non-numeric strings
    assert is_valid_coordinate("invalid", 10.0) is False


def test_haversine_invalid_coords_returns_infinity():
    assert haversine_km(999.0, 0.0, 19.0, 72.0) == float("inf")
    assert haversine_km(None, 0.0, 19.0, 72.0) == float("inf")
    assert haversine_km(19.0, float("nan"), 19.0, 72.0) == float("inf")


def test_known_haversine_distance():
    # Mumbai (19.0760, 72.8777) to Pune (18.5204, 73.8567) is ~120 km
    dist = haversine_km(19.0760, 72.8777, 18.5204, 73.8567)
    assert 115.0 <= dist <= 125.0


# =====================================================================
# Phase 14, 15: Timezone & Future Timestamp Handling
# =====================================================================

def test_timezone_standardization_to_utc():
    naive_str = "2026-09-01T10:00:00"
    parsed = parse_timestamp(naive_str)
    assert parsed.tzinfo is not None
    assert parsed.tzinfo == timezone.utc

    # Timezone offset parsed and converted to UTC
    offset_str = "2026-09-01T15:30:00+05:30"
    parsed_offset = parse_timestamp(offset_str)
    assert parsed_offset.tzinfo == timezone.utc
    assert parsed_offset.hour == 10
    assert parsed_offset.minute == 0


def test_future_timestamp_penalized_in_credibility():
    """Significantly future timestamps (> 5 min) must receive heavy credibility penalty."""
    future_event = {
        "source_type": "citizen",
        "latitude": 19.076,
        "longitude": 72.878,
        "city": "Mumbai",
        "timestamp": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "description": "Flooding on roads",
        "category": "flood"
    }
    res = score_credibility(future_event)
    assert res["factors"]["temporal_consistency"] == 0.10
    assert any("future" in r.lower() for r in res["credibility_reasons"])


def test_clock_skew_tolerance():
    """Minor clock skew (<= 5 min) is tolerated."""
    ingestion = datetime.now(timezone.utc)
    event_ts = ingestion + timedelta(minutes=2)  # 2 min ahead due to clock skew
    is_future, skew = check_future_timestamp(event_ts, reference_ts=ingestion, allowed_skew_minutes=5.0)
    assert is_future is False


# =====================================================================
# Phase 16, 17: Centralized Configuration & Weight Validation
# =====================================================================

def test_config_weights_validation_success():
    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    validated = validate_weights(weights, "test", expected_sum=1.0)
    assert sum(validated.values()) == 1.0


def test_config_weights_validation_failure():
    invalid_weights = {"a": 0.5, "b": 0.3}  # sums to 0.8
    with pytest.raises(ConfigurationError):
        validate_weights(invalid_weights, "test", expected_sum=1.0)

    negative_weights = {"a": 1.2, "b": -0.2}
    with pytest.raises(ConfigurationError):
        validate_weights(negative_weights, "test", expected_sum=1.0)


def test_credibility_weights_from_config():
    weights = get_credibility_weights()
    assert abs(sum(weights.values()) - 1.0) < 1e-4
    assert weights["source_trust"] == 0.30
    assert weights["corroboration"] == 0.25


# =====================================================================
# Phase 18, 19, 20: Invariants (Credibility, Duplicate, Clustering)
# =====================================================================

def test_credibility_score_invariants():
    """Credibility score must always strictly be in [0.0, 1.0] without NaNs."""
    event = {
        "source_type": "unknown",
        "latitude": None,
        "longitude": None,
        "timestamp": None,
        "description": "",
    }
    res = score_credibility(event)
    assert 0.0 <= res["credibility_score"] <= 1.0
    for factor_name, score in res["factors"].items():
        assert 0.0 <= score <= 1.0


def test_duplicate_score_invariants():
    """Duplicate score must always strictly be in [0.0, 1.0]."""
    res = compute_duplicate_score(
        {"description": "Rain in Mumbai"},
        {"description": "Heavy rain in Mumbai"}
    )
    assert 0.0 <= res <= 1.0


def test_cluster_size_limit_enforced():
    """Clustering must not exceed max_cluster_size."""
    full_cluster = {
        "cluster_id": "c_full",
        "category": "flood",
        "centroid_lat": 19.076,
        "centroid_lon": 72.878,
        "last_event_at": "2026-09-01T10:00:00Z",
        "member_count": 50  # at max limit
    }
    new_event = {
        "category": "flood",
        "latitude": 19.076,
        "longitude": 72.878,
        "timestamp": "2026-09-01T10:05:00Z"
    }
    assigned = assign_cluster(new_event, active_clusters=[full_cluster], max_size=50)
    assert assigned is None


# =====================================================================
# Phase 4, 5, 6: Training Pipeline, Small Data & Leakage
# =====================================================================

def test_training_data_validation_policy_reject(tmp_path):
    """Training pipeline must reject invalid labels by default."""
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "text,category\n"
        "Water on roads,flood\n"
        "Tasty yellow fruit,banana\n",
        encoding="utf-8"
    )
    with pytest.raises(DatasetValidationError) as exc:
        prepare_training_data(input_path=bad_csv, validation_policy="reject")
    assert "Invalid category 'banana'" in str(exc.value)


def test_training_data_validation_policy_skip(tmp_path):
    """Training pipeline must skip bad records when configured with 'skip' policy."""
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "text,category\n"
        "Water on roads,flood\n"
        "Tasty yellow fruit,banana\n",
        encoding="utf-8"
    )
    df, summary = prepare_training_data(input_path=bad_csv, validation_policy="skip")
    assert len(df) == 1
    assert df.iloc[0]["category"] == "flood"
    assert summary["invalid_categories_dropped"] == 1


def test_small_dataset_split_protection(tmp_path):
    """Small dataset with < 3 samples per class must raise SmallDatasetError."""
    small_csv = tmp_path / "small.csv"
    small_csv.write_text(
        "text,category\n"
        "Water in street 1,flood\n"
        "Water in street 2,flood\n"
        "Sunny day in city,heatwave\n",  # heatwave has only 1 sample
        encoding="utf-8"
    )
    with pytest.raises(SmallDatasetError):
        train_classifier(data_path=small_csv)


def test_data_leakage_audit():
    train_texts = pd.Series(["rain in mumbai", "flood in kurla", "fog in delhi"])
    val_texts = pd.Series(["storm in pune", "flood in kurla"])  # flood in kurla is leaked!
    test_texts = pd.Series(["heat in nagpur"])

    leakage = check_data_leakage(train_texts, val_texts, test_texts)
    assert leakage["train_val_overlap"] == 1
    assert leakage["total_leakage_cases"] == 1


# =====================================================================
# Phase 26: NormalizedEvent
# =====================================================================

def test_normalized_event_field_extraction():
    raw_payload = {
        "event_id": "evt-999",
        "location": {
            "latitude": 0.0,
            "longitude": 72.8777,
            "city": "Mumbai"
        },
        "event": {
            "description": "Water logging in area",
            "category": "flooding"
        },
        "timestamp": "2026-09-01T10:00:00Z"
    }

    norm = NormalizedEvent.from_dict(raw_payload)
    assert norm.event_id == "evt-999"
    assert norm.latitude == 0.0
    assert norm.longitude == 72.8777
    assert norm.city == "Mumbai"
    assert norm.description == "Water logging in area"
    assert norm.category == "flooding"
    assert norm.timestamp is not None

