"""
SIH26069 — Ingestion Service
Source adapters → Canonical Weather Event → Kafka

MVP: produces synthetic test events, then enters Open-Meteo polling loop.
"""

import os
import sys
import json
import uuid
import hashlib
import time
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ingestion")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
RAW_TOPIC = "weather.raw"


def _parse_bool(value, default=True):
    """Parse a string environment variable as a boolean.

    Accepts: true/false/1/0/yes/no (case-insensitive).
    Returns default if the variable is absent or unparseable.
    """
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes")


SYNTHETIC_ENABLED = _parse_bool(os.environ.get("SYNTHETIC_ENABLED"), default=True)

# ── Synthetic test events ────────────────────────────────────────────
SYNTHETIC_EVENTS = [
    {
        "source_id": "synth_20260902_001",
        "source_name": "synthetic_gen",
        "city": "Mumbai",
        "district": "Mumbai City",
        "state": "Maharashtra",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "category": "heavy_rainfall",
        "severity": "high",
        "description": (
            "Heavy rainfall caused waterlogging in Sion, Kurla and Andheri. "
            "IMD has issued a red alert for Mumbai."
        ),
    },
    {
        "source_id": "synth_20260902_002",
        "source_name": "synthetic_gen",
        "city": "Nagpur",
        "district": "Nagpur",
        "state": "Maharashtra",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "category": "heatwave",
        "severity": "extreme",
        "description": (
            "Nagpur recorded 44.2°C, well above the normal maximum. "
            "Heatwave conditions expected to continue for 3 days."
        ),
    },
    {
        "source_id": "synth_20260902_003",
        "source_name": "synthetic_gen",
        "city": "Nashik",
        "district": "Nashik",
        "state": "Maharashtra",
        "latitude": 19.9975,
        "longitude": 73.7898,
        "category": "thunderstorm",
        "severity": "moderate",
        "description": (
            "Thunderstorm activity in Nashik district with lightning. "
            "Minor damage to crops reported in surrounding areas."
        ),
    },
]


def build_canonical_event(test):
    """Build a Canonical Weather Event matching 02_DATA_SCHEMA.md §2 exactly.

    event_id is deterministic: hash(source_type + source_id + timestamp + lat + lon).
    This ensures the same source observation always produces the same event_id.
    """
    now = datetime.now(timezone.utc)
    event_ts = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    ingest_ts = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Deterministic event_id from stable source fields
    source_type = "synthetic"
    source_id = test["source_id"]
    lat = test["latitude"]
    lon = test["longitude"]
    hash_input = f"{source_type}|{source_id}|{event_ts}|{lat}|{lon}"
    raw = bytearray(hashlib.sha256(hash_input.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    deterministic_id = str(uuid.UUID(bytes=bytes(raw)))

    return {
        "event_id": deterministic_id,
        "source_id": test["source_id"],
        "source_type": "synthetic",
        "source_name": test["source_name"],
        "source_url": None,
        "source_trust_score": None,
        "timestamp": event_ts,
        "ingestion_timestamp": ingest_ts,
        "location": {
            "latitude": test["latitude"],
            "longitude": test["longitude"],
            "city": test["city"],
            "district": test["district"],
            "state": test["state"],
            "country": "India",
        },
        "event": {
            "category": test["category"],
            "severity": test["severity"],
            "description": test["description"],
        },
        "social_metadata": {
            "hashtags": ["#SyntheticTest", "#SIH26069"],
            "author_id": None,
            "platform": "simulated",
        },
        "media": {"photos": [], "videos": []},
        "ai": {
            "classified_category": None,
            "classification_confidence": None,
            "duplicate_score": None,
            "credibility_score": None,
            "credibility_reasons": [],
            "cluster_id": None,
        },
        "verification": {
            "status": "pending",
            "verified_by": None,
            "verification_timestamp": None,
        },
    }


def wrap_kafka_envelope(payload, producer_id="ingestion"):
    """
    Wrap the Canonical Weather Event in the Kafka message envelope
    per 03_KAFKA_CONTRACT.md §3.
    """
    return {
        "schema_version": "1.0",
        "message_id": str(uuid.uuid4()),
        "event_type": "weather_event",
        "produced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "producer": producer_id,
        "payload": json.dumps(payload),
    }


def produce_event(producer, topic, event):
    """Produce a single wrapped event to the given Kafka topic."""
    envelope = wrap_kafka_envelope(event)
    key = event["event_id"]
    value = json.dumps(envelope)
    producer.produce(
        topic=topic,
        key=key.encode("utf-8"),
        value=value.encode("utf-8"),
    )
    producer.flush()
    logger.info(
        "Produced event %s to %s — category=%s city=%s",
        key[:8],
        topic,
        event["event"]["category"],
        event["location"].get("city", "N/A"),
    )


def _run_optional_adapters(producer):
    """Poll configured RSS, websites, social and government sources once."""
    from adapters.rss import RssAdapter
    from adapters.website import WebsiteAdapter
    from adapters.social import SocialAdapter
    from adapters.government import GovernmentAdapter

    adapters = [
        (RssAdapter(), "rss"),
        (WebsiteAdapter(), "website"),
        (SocialAdapter(), "simulated_social"),
        (GovernmentAdapter(), "government_dataset"),
    ]
    for adapter, topic in adapters:
        try:
            events = adapter.fetch_events()
            topic_map = {"rss": "weather.raw", "website": "weather.raw", "simulated_social": "social.raw", "government_dataset": "government.raw"}
            for event in events:
                produce_event(producer, topic_map[topic], event)
            if events:
                logger.info("%s adapter published %d events", adapter.source_name, len(events))
        except Exception as exc:
            logger.warning("%s adapter failed: %s", adapter.source_name, exc, exc_info=True)


def main():
    from confluent_kafka import Producer
    logger.info("Ingestion service starting — Kafka: %s", KAFKA_BOOTSTRAP)
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP, "client.id": "ingestion", "acks": "all", "retries": 3, "retry.backoff.ms": 500})

    if SYNTHETIC_ENABLED:
        for test_event in SYNTHETIC_EVENTS:
            canonical = build_canonical_event(test_event)
            produce_event(producer, RAW_TOPIC, canonical)
            time.sleep(0.5)

    from adapters.weather_api import OpenMeteoAdapter
    weather = OpenMeteoAdapter(produce_fn=lambda e: produce_event(producer, RAW_TOPIC, e))
    while True:
        try:
            weather.run_once()
            _run_optional_adapters(producer)
        except Exception as exc:
            logger.error("Ingestion cycle failed: %s", exc, exc_info=True)
        time.sleep(int(os.environ.get("INGESTION_POLL_INTERVAL_SECONDS", "300")))


if __name__ == "__main__":
    main()
