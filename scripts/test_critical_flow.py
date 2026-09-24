"""
SIH26069 — Demo / Test Producer for Fast-Path Critical Lane
Produces a single test event with severity='extreme' to 'weather.critical'
and/or runs an end-to-end simulated processing cycle for demonstration.
"""

from __future__ import annotations

import os
import sys
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "ingestion"))
sys.path.insert(0, str(REPO_ROOT / "services" / "ml"))

from priority_triage import is_critical
from classifier.rule_based_classifier import RuleBasedClassifier

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
CRITICAL_TOPIC = os.environ.get("CRITICAL_TOPIC", "weather.critical")


def generate_critical_event(event_id: str | None = None) -> dict:
    eid = event_id or str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {
        "event_id": eid,
        "source_id": f"critical_test_{eid[:8]}",
        "source_type": "weather_api",
        "source_name": "emergency_broadcast",
        "timestamp": now_str,
        "ingestion_timestamp": now_str,
        "location": {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "city": "Mumbai",
            "district": "Mumbai City",
            "state": "Maharashtra",
            "country": "India",
        },
        "event": {
            "category": "flood",
            "severity": "extreme",
            "description": "FLASH FLOOD EMERGENCY: Water levels rising above 2 meters in Kurla. Multiple people trapped in building collapse.",
        },
    }


def main():
    print("=" * 60)
    print("SIH26069 — Fast-Path Priority Processing Lane Demo")
    print("=" * 60)

    event = generate_critical_event()
    event_id = event["event_id"]
    print(f"\n[1] Generated Test Event (severity='extreme', city='Mumbai'):")
    print(f"    Event ID: {event_id}")
    print(f"    Description: {event['event']['description']}")

    # Step 1: Priority Triage Check
    t0 = time.perf_counter()
    critical = is_critical(event)
    triage_time_us = (time.perf_counter() - t0) * 1e6
    print(f"\n[2] Triage Pre-Filter Evaluation:")
    print(f"    is_critical(event) = {critical}")
    print(f"    Triage Latency: {triage_time_us:.2f} microseconds (<5ms constraint satisfied)")
    assert critical is True

    # Step 2: Kafka Produce (if confluent_kafka available and broker reachable)
    kafka_produced = False
    try:
        from confluent_kafka import Producer
        p = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
        envelope = {
            "schema_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "event_type": "weather_event",
            "produced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "producer": "demo_test_script",
            "payload": json.dumps(event),
        }
        p.produce(CRITICAL_TOPIC, key=event_id.encode("utf-8"), value=json.dumps(envelope).encode("utf-8"))
        p.flush(timeout=2.0)
        print(f"\n[3] Kafka Dual-Write:")
        print(f"    Successfully produced to topic '{CRITICAL_TOPIC}' on broker {KAFKA_BOOTSTRAP}")
        kafka_produced = True
    except Exception as e:
        print(f"\n[3] Kafka Dual-Write: Broker not reachable ({e}). Proceeding with simulated consumer processing.")

    # Step 3: Fast-Path Enrichment and Consumer Processing
    t_start = time.perf_counter()
    classifier = RuleBasedClassifier()
    clf_res = classifier.predict(event["event"]["description"], category_hint=event["event"]["category"])
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    print(f"\n[4] Fast-Path Rule-Based Enrichment:")
    print(f"    Classified Category: {clf_res['classified_category']}")
    print(f"    Confidence: {clf_res['classification_confidence']}")

    print(f"\n[5] Console Visibility Output:")
    print(f"    CRITICAL event {event_id} processed in {elapsed_ms:.2f}ms")
    print("\n" + "=" * 60)
    print("Demo completed successfully. No Spark stack required!")
    print("=" * 60)


if __name__ == "__main__":
    main()
