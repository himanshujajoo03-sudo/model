from __future__ import annotations

import pandas as pd
import pytest

from training.leakage import LeakageError, check_leakage_detailed


def test_strict_leakage_check_blocks_near_duplicate_overlap():
    train = pd.DataFrame({"text": ["heavy rain caused flooding in pune"], "event_id": ["a"]})
    val = pd.DataFrame({"text": ["heavy rain caused flooding in pune today"], "event_id": ["b"]})
    test = pd.DataFrame({"text": ["clear weather in delhi"], "event_id": ["c"]})

    with pytest.raises(LeakageError):
        check_leakage_detailed(train, val, test, policy="strict", near_duplicate_threshold=0.80)


def test_strict_leakage_check_fails_closed_when_near_duplicate_check_skipped(monkeypatch):
    import training.leakage as leakage
    monkeypatch.setattr(leakage, "MAX_PAIRWISE_COMPARISONS", 0)
    frames = [
        pd.DataFrame({"text": ["heavy rain in pune"], "event_id": ["a"]}),
        pd.DataFrame({"text": ["clear weather in delhi"], "event_id": ["b"]}),
        pd.DataFrame({"text": ["heat wave in nagpur"], "event_id": ["c"]}),
    ]
    with pytest.raises(LeakageError, match="could not be completed"):
        check_leakage_detailed(*frames, policy="strict")


def test_negation_scope_does_not_hide_unrelated_later_event():
    from classifier.rule_based_classifier import RuleBasedClassifier
    c = RuleBasedClassifier()
    cases = {
        "No injuries were reported after heavy rain in Pune.": "heavy_rainfall",
        "No thunderstorm occurred, but heavy rain continued.": "heavy_rainfall",
        "Rain was not observed; fog covered the road.": "fog",
        "Not a cyclone, just strong winds were observed.": "strong_wind",
        "Without flooding, heavy rain affected the district.": "heavy_rainfall",
    }
    for text, expected in cases.items():
        assert c.predict(text)["classified_category"] == expected


def test_trained_classifier_does_not_erase_valid_event_after_unrelated_negation():
    from classifier.trained_classifier import TrainedModelClassifier
    clf = TrainedModelClassifier()
    assert clf.predict("No evidence of heavy rain but flooding occurred.")["classified_category"] == "flood"
    assert clf.predict("Without any cyclone, strong winds hit the coast")["classified_category"] == "strong_wind"


def test_weather_agreement_requires_temporal_alignment():
    from credibility.credibility_scorer import compute_weather_agreement
    from utils.event_schema import NormalizedEvent
    event = NormalizedEvent.from_dict({
        "description": "rain",
        "category": "rainfall",
        "latitude": 20.0,
        "longitude": 73.0,
        "timestamp": "2026-01-01T00:00:00Z",
    })
    api = NormalizedEvent.from_dict({
        "description": "rain",
        "category": "rainfall",
        "source_type": "weather_api",
        "latitude": 20.0,
        "longitude": 73.0,
        "timestamp": "2020-01-01T00:00:00Z",
    })
    assert compute_weather_agreement(event, [api]) == 0.20


def test_training_leakage_audit_uses_configured_near_duplicate_threshold(monkeypatch):
    import training.train as train_mod
    captured = {}
    def fake_check(*args, **kwargs):
        captured.update(kwargs)
        return {"passed": True}
    monkeypatch.setattr(train_mod, "check_leakage_detailed", fake_check)
    # This regression is checked statically because train_classifier is expensive;
    # ensure the source passes the configured threshold instead of relying on the default.
    source = open(train_mod.__file__, encoding="utf-8").read()
    assert 'near_duplicate_threshold=float(train_cfg.get("near_duplicate_threshold", 0.85))' in source
