from __future__ import annotations

"""
Regression tests for Production Hardening Pass 2.

Covers:
  - Rule 2:  mathematically safe train/val/test split feasibility validation
  - Rule 3:  expanded data leakage detection (near-duplicate, event_id, source)
  - Rule 5:  force_deploy cannot bypass production safety gates
  - Rule 13/14: score validation rejects malformed external input
  - Rule 20: strict config validation for split ratios / leakage policy
  - Rule 21: single-source-of-truth config bugfix (no duplicate YAML keys)
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from config.config_loader import load_ml_config, validate_config, ConfigurationError
from training.split_validator import (
    minimum_samples_per_class,
    validate_split_feasibility,
    SplitFeasibilityError,
)
from training.leakage import check_leakage_detailed, LeakageError
from training.train import train_classifier, ForceDeployNotPermittedError, FORCE_DEPLOY_ENV_FLAG
from credibility.credibility_scorer import score_credibility
from utils.validation import validate_score, clamp_score, InvalidScoreError


# =====================================================================
# Rule 2: Split Feasibility Validator
# =====================================================================

DEFAULT_RATIOS = {"train": 0.80, "val": 0.10, "test": 0.10}


def test_minimum_samples_default_ratios():
    """With 80/10/10 ratios, the smallest split (10%) needs >= 10 samples/class."""
    assert minimum_samples_per_class(DEFAULT_RATIOS) == 10


def test_minimum_samples_even_ratios():
    """With even 1/3 splits, each class needs >= 3 samples."""
    ratios = {"train": 1 / 3, "val": 1 / 3, "test": 1 / 3}
    assert minimum_samples_per_class(ratios) == 3


def test_split_feasibility_one_sample_per_class_fails():
    class_counts = {"flood": 1, "heatwave": 1}
    with pytest.raises(SplitFeasibilityError) as exc_info:
        validate_split_feasibility(class_counts, DEFAULT_RATIOS)
    report = exc_info.value.report
    assert report["feasible"] is False
    assert "flood" in report["problematic_classes"]
    assert report["min_required_per_class"] == 10


def test_split_feasibility_two_samples_per_class_fails():
    class_counts = {"flood": 2, "heatwave": 2}
    with pytest.raises(SplitFeasibilityError):
        validate_split_feasibility(class_counts, DEFAULT_RATIOS)


def test_split_feasibility_three_samples_per_class_still_fails_for_default_ratios():
    """The OLD hardcoded check ('>= 3') is not sufficient for 80/10/10 splits;
    the new validator correctly still rejects this."""
    class_counts = {"flood": 3, "heatwave": 3}
    with pytest.raises(SplitFeasibilityError) as exc_info:
        validate_split_feasibility(class_counts, DEFAULT_RATIOS)
    assert exc_info.value.report["min_required_per_class"] == 10


def test_split_feasibility_minimum_valid_dataset_passes():
    class_counts = {"flood": 10, "heatwave": 10}
    report = validate_split_feasibility(class_counts, DEFAULT_RATIOS)
    assert report["feasible"] is True


def test_split_feasibility_large_dataset_passes():
    class_counts = {c: 500 for c in ["flood", "heatwave", "fog", "cyclone"]}
    report = validate_split_feasibility(class_counts, DEFAULT_RATIOS)
    assert report["feasible"] is True


def test_split_feasibility_highly_imbalanced_dataset():
    """One well-represented class and one severely underrepresented class."""
    class_counts = {"flood": 1000, "cyclone": 4}
    with pytest.raises(SplitFeasibilityError) as exc_info:
        validate_split_feasibility(class_counts, DEFAULT_RATIOS)
    problems = exc_info.value.report["problematic_classes"]
    assert "cyclone" in problems
    assert "flood" not in problems


def test_split_feasibility_unusual_ratios():
    """A near-even 3-way split needs far fewer samples/class than 80/10/10."""
    ratios = {"train": 0.40, "val": 0.30, "test": 0.30}
    class_counts = {"flood": 4, "heatwave": 4}
    report = validate_split_feasibility(class_counts, ratios)
    assert report["feasible"] is True


def test_split_feasibility_error_message_is_actionable():
    class_counts = {"flood": 2}
    with pytest.raises(SplitFeasibilityError) as exc_info:
        validate_split_feasibility(class_counts, DEFAULT_RATIOS)
    msg = str(exc_info.value)
    assert "flood" in msg
    assert "needs" in msg
    assert "add" in msg.lower()


def test_train_classifier_uses_split_validator(tmp_path):
    """End-to-end: train_classifier() must reject a dataset that the split
    validator deems infeasible, even though each class technically has
    >= 3 samples (the old, insufficient threshold)."""
    from training.train import SmallDatasetError

    small_csv = tmp_path / "small.csv"
    small_csv.write_text(
        "text,category\n"
        "Water in street one,flood\n"
        "Water in street two,flood\n"
        "Water in street three,flood\n"
        "Sunny hot day one,heatwave\n"
        "Sunny hot day two,heatwave\n"
        "Sunny hot day three,heatwave\n",
        encoding="utf-8"
    )
    with pytest.raises(SmallDatasetError) as exc_info:
        train_classifier(data_path=small_csv)
    assert exc_info.value.report.get("min_required_per_class") == 10


# =====================================================================
# Rule 3: Expanded Data Leakage Detection
# =====================================================================

def test_leakage_near_duplicate_detected():
    train_df = pd.DataFrame({"text": ["heavy rain flooding mumbai streets today reported"]})
    val_df = pd.DataFrame({"text": ["heavy rain flooding mumbai streets today"]})  # near-identical
    test_df = pd.DataFrame({"text": ["completely unrelated sunny day report"]})

    report = check_leakage_detailed(train_df, val_df, test_df, policy="warning", near_duplicate_threshold=0.8)
    assert report["near_duplicate_overlap"]["train_val"] >= 1


def test_leakage_event_id_overlap_blocks_strict():
    train_df = pd.DataFrame({"text": ["report a"], "event_id": ["evt-1"]})
    val_df = pd.DataFrame({"text": ["report b"], "event_id": ["evt-1"]})  # same real event!
    test_df = pd.DataFrame({"text": ["report c"], "event_id": ["evt-2"]})

    with pytest.raises(LeakageError) as exc_info:
        check_leakage_detailed(train_df, val_df, test_df, policy="strict")
    assert exc_info.value.report["event_id_overlap"]["train_val"] == 1


def test_leakage_event_id_overlap_warns_only_under_warning_policy():
    train_df = pd.DataFrame({"text": ["report a"], "event_id": ["evt-1"]})
    val_df = pd.DataFrame({"text": ["report b"], "event_id": ["evt-1"]})
    test_df = pd.DataFrame({"text": ["report c"], "event_id": ["evt-2"]})

    report = check_leakage_detailed(train_df, val_df, test_df, policy="warning")
    assert report["passed"] is False
    assert report["blocking_leakage_found"] is True


def test_leakage_source_overlap_is_informational_not_blocking():
    """Sharing a source (e.g. the national weather API) across splits is
    expected and must NOT by itself block training."""
    train_df = pd.DataFrame({"text": ["report a"], "source_id": ["IMD"]})
    val_df = pd.DataFrame({"text": ["report b"], "source_id": ["IMD"]})
    test_df = pd.DataFrame({"text": ["report c"], "source_id": ["IMD"]})

    report = check_leakage_detailed(train_df, val_df, test_df, policy="strict")
    assert report["source_overlap"]["train_val"] == 1
    assert report["passed"] is True


def test_leakage_disabled_policy_skips_checks():
    train_df = pd.DataFrame({"text": ["report a"], "event_id": ["evt-1"]})
    val_df = pd.DataFrame({"text": ["report a"], "event_id": ["evt-1"]})
    test_df = pd.DataFrame({"text": ["report c"]})

    report = check_leakage_detailed(train_df, val_df, test_df, policy="disabled")
    assert report["checked"] is False
    assert report["passed"] is True


def test_leakage_no_overlap_passes_strict():
    train_df = pd.DataFrame({"text": ["alpha report"], "event_id": ["evt-1"]})
    val_df = pd.DataFrame({"text": ["beta report"], "event_id": ["evt-2"]})
    test_df = pd.DataFrame({"text": ["gamma report"], "event_id": ["evt-3"]})

    report = check_leakage_detailed(train_df, val_df, test_df, policy="strict")
    assert report["passed"] is True
    assert report["total_exact_leakage_cases"] == 0


def test_leakage_invalid_policy_rejected():
    train_df = pd.DataFrame({"text": ["a"]})
    val_df = pd.DataFrame({"text": ["b"]})
    test_df = pd.DataFrame({"text": ["c"]})
    with pytest.raises(ValueError):
        check_leakage_detailed(train_df, val_df, test_df, policy="not_a_real_policy")


# =====================================================================
# Rule 5: force_deploy Cannot Bypass Production Safety
# =====================================================================

def test_force_deploy_blocked_without_env_flag(tmp_path, monkeypatch):
    """force_deploy=True must be refused unless the development-only
    environment flag is explicitly set."""
    monkeypatch.delenv(FORCE_DEPLOY_ENV_FLAG, raising=False)
    with pytest.raises(ForceDeployNotPermittedError):
        train_classifier(force_deploy=True)


def test_force_deploy_allowed_with_explicit_dev_flag(tmp_path, monkeypatch):
    """When explicitly enabled for development, force_deploy is permitted
    and clearly marked in metadata for audit purposes. Redirects production
    paths to a temp directory so this test never touches the real repo's
    production model."""
    import training.train as train_module

    monkeypatch.setenv(FORCE_DEPLOY_ENV_FLAG, "1")
    monkeypatch.setattr(train_module, "PRODUCTION_MODEL_DIR", tmp_path / "production")
    monkeypatch.setattr(train_module, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(train_module, "ARCHIVE_DIR", tmp_path / "archive")
    monkeypatch.setattr(train_module, "LEGACY_MODEL_DIR", tmp_path / "legacy")

    metadata = train_classifier(force_deploy=True)
    assert metadata["deployment_forced"] is True


def test_watcher_never_passes_force_deploy():
    """Static guarantee: the automatic watcher's training invocation must
    never pass force_deploy=True."""
    watch_source = (ML_ROOT / "training" / "watch.py").read_text(encoding="utf-8")
    assert "force_deploy=True" not in watch_source
    assert "force_deploy = True" not in watch_source


# =====================================================================
# Rule 13 / 14: Score Validation
# =====================================================================

def test_validate_score_accepts_valid_range():
    assert validate_score(0.0, "x") == 0.0
    assert validate_score(1.0, "x") == 1.0
    assert validate_score(0.5, "x") == 0.5
    assert validate_score(None, "x", allow_none=True) is None


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf"), -0.5, 1.5, "abc", True])
def test_validate_score_rejects_malformed_input(bad_value):
    with pytest.raises(InvalidScoreError):
        validate_score(bad_value, "test_score", allow_none=False)


def test_validate_score_rejects_none_when_not_allowed():
    with pytest.raises(InvalidScoreError):
        validate_score(None, "test_score", allow_none=False)


def test_clamp_score_never_raises():
    assert clamp_score(float("nan")) == 0.0
    assert clamp_score(float("inf")) == 0.0
    assert clamp_score(-0.5) == 0.0
    assert clamp_score(1.5) == 1.0
    assert clamp_score(0.42) == 0.42
    assert clamp_score("not a number") == 0.0


@pytest.mark.parametrize("bad_kwarg", ["weather_confirmation", "timestamp_validity", "location_validity", "completeness", "cross_source_agreement"])
def test_credibility_scorer_rejects_malformed_kwarg_overrides(bad_kwarg):
    """A malformed external override (NaN/Infinity/out-of-range) must be
    rejected, not silently coerced into an invalid intermediate factor."""
    event = {"description": "Flood in Mumbai", "category": "flood"}
    with pytest.raises(InvalidScoreError):
        score_credibility(event, **{bad_kwarg: 1.5})
    with pytest.raises(InvalidScoreError):
        score_credibility(event, **{bad_kwarg: float("nan")})


def test_credibility_scorer_accepts_valid_kwarg_overrides():
    event = {"description": "Flood in Mumbai", "category": "flood"}
    result = score_credibility(event, weather_confirmation=0.9)
    assert 0.0 <= result["credibility_score"] <= 1.0


# =====================================================================
# Rule 20: Strict Config Validation
# =====================================================================

def test_config_split_ratios_missing_key_rejected():
    cfg = {"training": {"split_ratios": {"train": 0.9, "val": 0.1}}}  # missing 'test'
    with pytest.raises(ConfigurationError):
        validate_config(cfg)


def test_config_split_ratios_extra_key_rejected():
    cfg = {"training": {"split_ratios": {"train": 0.7, "val": 0.1, "test": 0.1, "holdout": 0.1}}}
    with pytest.raises(ConfigurationError):
        validate_config(cfg)


def test_config_split_ratios_must_sum_to_one():
    cfg = {"training": {"split_ratios": {"train": 0.5, "val": 0.3, "test": 0.3}}}  # sums to 1.1
    with pytest.raises(ConfigurationError):
        validate_config(cfg)


def test_config_split_ratio_must_be_positive():
    cfg = {"training": {"split_ratios": {"train": 1.0, "val": 0.0, "test": 0.0}}}
    with pytest.raises(ConfigurationError):
        validate_config(cfg)


def test_config_invalid_leakage_policy_rejected():
    cfg = {
        "training": {
            "split_ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
            "leakage_policy": "yolo",
        }
    }
    with pytest.raises(ConfigurationError):
        validate_config(cfg)


def test_config_min_samples_per_class_must_be_positive_int():
    cfg = {
        "training": {
            "split_ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
            "min_samples_per_class": -1,
        }
    }
    with pytest.raises(ConfigurationError):
        validate_config(cfg)


def test_current_ml_config_yaml_passes_strict_validation():
    """The actual shipped config must itself pass the strengthened validator."""
    cfg = load_ml_config(force_reload=True)
    assert cfg["training"]["leakage_policy"] in ("strict", "warning", "disabled")
    ratios = cfg["training"]["split_ratios"]
    assert set(ratios.keys()) == {"train", "val", "test"}
    assert abs(sum(ratios.values()) - 1.0) < 1e-6


# =====================================================================
# Rule 12: Missing vs. Malformed vs. Invalid Coordinate Validation
# =====================================================================

from utils.geo import classify_coordinate
from utils.event_schema import NormalizedEvent, EventValidationError


def test_classify_coordinate_missing():
    assert classify_coordinate(None, is_latitude=True) == ("missing", None)


def test_classify_coordinate_valid_including_zero():
    assert classify_coordinate(0.0, is_latitude=True) == ("valid", 0.0)
    assert classify_coordinate("19.07", is_latitude=True) == ("valid", 19.07)


def test_classify_coordinate_malformed():
    status, value = classify_coordinate("abc", is_latitude=True)
    assert status == "malformed"
    assert value is None


def test_classify_coordinate_out_of_range():
    status, value = classify_coordinate(999, is_latitude=True)
    assert status == "out_of_range"
    assert value == 999.0  # value preserved for inspection even though invalid


def test_classify_coordinate_nan_and_inf_are_malformed():
    assert classify_coordinate(float("nan"), is_latitude=True)[0] == "malformed"
    assert classify_coordinate(float("inf"), is_latitude=True)[0] == "malformed"


def test_normalized_event_lenient_mode_missing_latitude_is_acceptable():
    """Default (lenient) mode: a truly missing coordinate is fine, no issues recorded."""
    evt = NormalizedEvent.from_dict({"description": "test", "latitude": None, "longitude": 72.8})
    assert evt.latitude is None
    assert "latitude_missing" not in evt.validation_issues


def test_normalized_event_lenient_mode_malformed_latitude_recorded_but_not_raised():
    """Lenient mode preserves backward compatibility: malformed input becomes
    None (like missing), but the reason is now tracked in validation_issues."""
    evt = NormalizedEvent.from_dict({"description": "test", "latitude": "abc", "longitude": 72.8})
    assert evt.latitude is None
    assert "latitude_malformed" in evt.validation_issues


def test_normalized_event_lenient_mode_out_of_range_latitude_recorded_but_not_raised():
    evt = NormalizedEvent.from_dict({"description": "test", "latitude": 999, "longitude": 72.8})
    assert evt.latitude is None
    assert "latitude_out_of_range" in evt.validation_issues


def test_normalized_event_strict_mode_rejects_malformed_latitude():
    with pytest.raises(EventValidationError) as exc_info:
        NormalizedEvent.from_dict({"description": "test", "latitude": "abc", "longitude": 72.8}, strict=True)
    assert "latitude_malformed" in exc_info.value.issues


def test_normalized_event_strict_mode_rejects_out_of_range_latitude():
    with pytest.raises(EventValidationError) as exc_info:
        NormalizedEvent.from_dict({"description": "test", "latitude": 999, "longitude": 72.8}, strict=True)
    assert "latitude_out_of_range" in exc_info.value.issues


def test_normalized_event_strict_mode_accepts_missing_latitude():
    """Strict mode must still allow genuinely MISSING coordinates -- strictness
    targets malformed/invalid input, not incompleteness."""
    evt = NormalizedEvent.from_dict({"description": "test", "latitude": None, "longitude": 72.8}, strict=True)
    assert evt.latitude is None


def test_normalized_event_strict_mode_accepts_fully_valid_event():
    evt = NormalizedEvent.from_dict(
        {"description": "test", "latitude": 19.07, "longitude": 72.8}, strict=True
    )
    assert evt.latitude == 19.07
    assert evt.validation_issues == []


# =====================================================================
# Rules 15 / 16: Duplicate Detection Missing-Data Semantics & Evidence
# =====================================================================

from dedup.duplicate_detector import compute_duplicate_evidence, compute_pairwise_duplicate_score


def test_missing_timestamp_not_treated_as_very_different():
    """Two events with identical text/category but no timestamp on either side
    should NOT be penalized as if they were far apart in time; the time
    signal should simply be excluded (marked missing), not scored as 0."""
    a = {"description": "Heavy flooding reported in Mumbai suburb", "category": "flood"}
    b = {"description": "Heavy flooding reported in Mumbai suburb", "category": "flood"}
    evidence = compute_duplicate_evidence(a, b)
    assert evidence["signals"]["time"] is None
    assert "time" in evidence["missing_signals"]
    # With text+category both matching strongly and time/distance/source
    # excluded (not counted as evidence against), the renormalized score
    # should be high, not artificially suppressed by an absent timestamp.
    assert evidence["score"] >= 0.85


def test_missing_coordinates_not_treated_as_very_far():
    a = {"description": "Cyclone warning issued for coastal Odisha region", "category": "cyclone"}
    b = {"description": "Cyclone warning issued for coastal Odisha region", "category": "cyclone"}
    evidence = compute_duplicate_evidence(a, b)
    assert evidence["signals"]["distance"] is None
    assert "distance" in evidence["missing_signals"]
    assert evidence["score"] >= 0.85


def test_missing_source_url_not_treated_as_evidence_against_duplicate():
    a = {"description": "Hailstorm damages crops near Nagpur", "category": "hailstorm"}
    b = {"description": "Hailstorm damages crops near Nagpur", "category": "hailstorm"}
    evidence = compute_duplicate_evidence(a, b)
    assert evidence["signals"]["source_url"] is None
    assert "source_url" in evidence["missing_signals"]


def test_duplicate_evidence_structure_matches_documented_shape():
    a = {
        "description": "Flooding in low-lying areas of Chennai",
        "category": "flood",
        "source_id": "src-1",
        "source_url": "https://example.com/report/1",
        "latitude": 13.08, "longitude": 80.27,
        "timestamp": "2026-06-01T10:00:00Z",
    }
    b = {
        "description": "Flooding in low-lying areas of Chennai",
        "category": "flood",
        "source_id": "src-1",
        "source_url": "https://example.com/report/1",
        "latitude": 13.08, "longitude": 80.27,
        "timestamp": "2026-06-01T10:02:00Z",
    }
    evidence = compute_duplicate_evidence(a, b)
    assert set(evidence.keys()) == {"score", "decision", "signals", "missing_signals"}
    assert evidence["decision"] in ("probable_duplicate", "possible_duplicate", "not_duplicate")
    # All metadata signals (source_id, source_url, time, distance) are available here
    assert [s for s in evidence["missing_signals"] if s != "semantic"] == []


def test_compute_pairwise_duplicate_score_still_returns_a_float():
    """Backward compatibility: existing callers expect a plain float."""
    a = {"description": "Fog reduces visibility on highway", "category": "fog"}
    b = {"description": "Fog reduces visibility on highway", "category": "fog"}
    score = compute_pairwise_duplicate_score(a, b)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


# =====================================================================
# Rule 24: Cluster Representative Must Not Discard Legitimate Zero Values
# =====================================================================

from clustering.event_clusterer import select_cluster_representative


def test_representative_selection_preserves_explicit_zero_trust():
    """A source_trust_score of 0.0 is a legitimate (if unfortunate) value and
    must NOT be silently replaced by the 'source_trust' fallback field via a
    falsy `x or y` check, which would incorrectly discard the explicit zero."""
    events = [
        {
            "description": "Report A", "category": "flood",
            "credibility_score": 0.5, "source_trust_score": 0.0, "source_trust": 0.9,
            "event_id": "a",
        },
        {
            "description": "Report B", "category": "flood",
            "credibility_score": 0.5, "source_trust_score": 0.3, "source_trust": 0.1,
            "event_id": "b",
        },
    ]
    rep = select_cluster_representative(events)
    # Report B has a HIGHER real source_trust_score (0.3 > 0.0), so it must win
    # the tiebreak -- if the old `or` bug were present, Report A's 0.0 would be
    # replaced by its fallback 0.9, incorrectly making it win instead.
    assert rep["event_id"] == "b"


def test_representative_selection_credibility_zero_is_respected():
    events = [
        {"description": "A", "category": "flood", "credibility_score": 0.0, "event_id": "a"},
        {"description": "B", "category": "flood", "credibility_score": 0.2, "event_id": "b"},
    ]
    rep = select_cluster_representative(events)
    assert rep["event_id"] == "b"


def test_representative_selection_missing_event_id_does_not_crash():
    events = [
        {"description": "A", "category": "flood", "credibility_score": 0.5},
        {"description": "B", "category": "flood", "credibility_score": 0.5, "timestamp": "2026-01-01T00:00:00Z"},
    ]
    rep = select_cluster_representative(events)
    assert rep is not None


def test_representative_selection_missing_timestamp_does_not_crash():
    events = [
        {"description": "A", "category": "flood", "credibility_score": 0.5, "event_id": "a"},
        {"description": "B", "category": "flood", "credibility_score": 0.5, "event_id": "b",
         "timestamp": "2026-01-01T00:00:00Z"},
    ]
    rep = select_cluster_representative(events)
    # Missing timestamp sorts as +inf (last), so "b" (has an actual timestamp) wins.
    assert rep["event_id"] == "b"
