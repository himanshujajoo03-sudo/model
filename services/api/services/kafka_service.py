"""Kafka producer wrapper for API service."""

import json
import os
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer


def _publish(topic: str, event_type: str, payload: dict, key: str) -> None:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    producer = Producer({"bootstrap.servers": bootstrap, "client.id": "api", "acks": "all", "retries": 3})
    envelope = {
        "schema_version": "1.0", "message_id": str(uuid.uuid4()), "event_type": event_type,
        "produced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "producer": "api", "payload": json.dumps(payload),
    }
    producer.produce(topic=topic, key=key.encode("utf-8"), value=json.dumps(envelope).encode("utf-8"))
    producer.flush()


def publish_citizen_event(event: dict) -> None:
    """Publish normalized citizen event using the platform envelope."""
    _publish("citizen.raw", "weather_event", event, event["event_id"])


def publish_verification_action(action: dict) -> None:
    """Publish the authoritative admin verification action to weather.verified."""
    _publish("weather.verified", "verification_action", action, action["event_id"])
