"""
SIH26069 — Fast-Path Priority Processing Lane Tests
Validates triage latency, keyword matching, classifier integration,
and consumer processing independently without requiring Spark or live Kafka.
"""

from __future__ import annotations

import sys
import time
import uuid
import json
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "ingestion"))
sys.path.insert(0, str(REPO_ROOT / "services" / "ml"))

from priority_triage import is_critical
from classifier.rule_based_classifier import RuleBasedClassifier
import critical_consumer


def test_triage_severity():
    assert is_critical({"event": {"severity": "extreme"}}) is True
    assert is_critical({"event": {"severity": "high"}}) is True
    assert is_critical({"event": {"severity": "moderate"}}) is False
    assert is_critical({"event": {"severity": "low"}}) is False
    assert is_critical({"severity": "EXTREME"}) is True
    assert is_critical({}) is False
    assert is_critical(None) is False


def test_triage_keywords():
    keywords = ["flood", "cyclone", "collapse", "trapped", "drowning", "emergency", "sos"]
    for kw in keywords:
        event = {
            "event": {
                "severity": "low",
                "description": f"Urgent alert: reports of {kw} in district",
            }
        }
        assert is_critical(event) is True, f"Keyword '{kw}' failed to trigger is_critical"

    non_critical_event = {
        "event": {
            "severity": "moderate",
            "description": "Scattered rain and gentle breeze in the morning.",
        }
    }
    assert is_critical(non_critical_event) is False


def test_triage_latency_under_5ms():
    event = {
        "event": {
            "severity": "moderate",
            "description": "Heavy rainfall in the area, check water levels carefully.",
        }
    }
    iterations = 5000
    t0 = time.perf_counter()
    for _ in range(iterations):
        is_critical(event)
    total_time_ms = (time.perf_counter() - t0) * 1000.0
    avg_latency_ms = total_time_ms / iterations
    print(f"\n[LATENCY BENCHMARK] Average triage latency: {avg_latency_ms * 1000.0:.2f} microseconds per event")
    assert avg_latency_ms < 5.0, f"Latency {avg_latency_ms}ms exceeded 5ms limit"


def test_rule_based_classifier_integration():
    classifier = RuleBasedClassifier()
    desc = "Urgent emergency rescue needed, severe flood water rising rapidly across streets."
    res = classifier.predict(desc, category_hint="flood")
    assert res["classified_category"] == "flood"
    assert res["classification_confidence"] >= 0.80


def test_critical_consumer_process_message():
    classifier = RuleBasedClassifier()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    test_event_id = str(uuid.uuid4())
    event_payload = {
        "event_id": test_event_id,
        "location": {"city": "Mumbai", "district": "Mumbai", "state": "Maharashtra", "latitude": 19.07, "longitude": 72.87},
        "event": {
            "category": "flood",
            "severity": "extreme",
            "description": "Extreme flash flood in Kurla, multiple people trapped.",
        },
        "source_name": "test_source",
        "timestamp": "2026-09-10T12:00:00.000Z",
    }

    t_start = time.perf_counter()
    returned_id = critical_consumer.process_message(event_payload, classifier, mock_conn)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    assert returned_id == test_event_id
    assert mock_conn.commit.called

    # Verify executed queries have ON CONFLICT DO NOTHING
    executed_sqls = [call[0][0] for call in mock_cur.execute.call_args_list]
    assert any("ON CONFLICT (canonical_event_id) DO NOTHING" in sql for sql in executed_sqls)
    assert any("ON CONFLICT (event_id) DO NOTHING" in sql for sql in executed_sqls)
    assert any("'critical'" in sql for sql in executed_sqls)

    log_line = f"CRITICAL event {test_event_id} processed in {elapsed_ms:.2f}ms"
    print(f"\n[MOCK CONSUMER TEST] {log_line}")


def test_synthetic_events_triage():
    import importlib.util
    ingestion_path = REPO_ROOT / "services" / "ingestion" / "main.py"
    spec = importlib.util.spec_from_file_location("ingestion_main", ingestion_path)
    ingestion_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ingestion_main)
    SYNTHETIC_EVENTS = ingestion_main.SYNTHETIC_EVENTS
    build_canonical_event = ingestion_main.build_canonical_event

    critical_count = 0
    normal_count = 0
    for test_ev in SYNTHETIC_EVENTS:
        canonical = build_canonical_event(test_ev)
        if is_critical(canonical):
            critical_count += 1
        else:
            normal_count += 1

    # In SYNTHETIC_EVENTS:
    # 1. Mumbai: severity='high' -> critical
    # 2. Nagpur: severity='extreme' -> critical
    # 3. Nashik: severity='moderate' -> normal
    assert critical_count == 2
    assert normal_count == 1
    print(f"\n[SYNTHETIC TEST] Verified {critical_count} critical dual-write events and {normal_count} normal events")


if __name__ == "__main__":
    test_triage_severity()
    test_triage_keywords()
    test_triage_latency_under_5ms()
    test_rule_based_classifier_integration()
    test_critical_consumer_process_message()
    test_synthetic_events_triage()
    print("\nALL FAST-PATH PRIORITY TESTS PASSED SUCCESSFULLY!")
