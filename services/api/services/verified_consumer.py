"""
Consumer for weather.verified Kafka topic.
Consumes verification action events and ensures all linked database states
(canonical_events and contributing events) are synchronized reliably.
"""
from __future__ import annotations

import json
import logging
import os
try:
    from confluent_kafka import Consumer, KafkaError
except ImportError:
    Consumer = None
    KafkaError = None

from dependencies import get_db

logger = logging.getLogger("api.verified_consumer")


class VerifiedEventConsumer:
    def __init__(self):
        bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.conf = {
            "bootstrap.servers": bootstrap,
            "group.id": "weather-verified-consumer-group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "session.timeout.ms": 30000,
        }
        self.topic = "weather.verified"
        self._running = True
        self.consumer = None

    def process_message(self, msg_val: bytes) -> bool:
        """Parse message envelope and synchronize database state."""
        try:
            envelope = json.loads(msg_val.decode("utf-8"))
            raw_payload = envelope.get("payload")
            if isinstance(raw_payload, str):
                payload = json.loads(raw_payload)
            elif isinstance(raw_payload, dict):
                payload = raw_payload
            else:
                logger.warning("Unrecognized payload format in verified message: %s", raw_payload)
                return True

            event_id = payload.get("event_id")
            new_status = payload.get("new_status")
            action = payload.get("action")
            performed_by = payload.get("performed_by")
            performed_at = payload.get("performed_at")

            if not event_id or not new_status:
                logger.warning("Missing event_id or new_status in payload: %s", payload)
                return True

            with get_db() as conn:
                with conn.cursor() as cur:
                    # 1. Synchronize canonical event status
                    cur.execute(
                        """UPDATE canonical_events
                           SET verification_status = %s,
                               verified_by = COALESCE(%s, verified_by),
                               verification_timestamp = COALESCE(%s::timestamptz, verification_timestamp),
                               updated_at = NOW()
                           WHERE canonical_event_id = %s""",
                        (new_status, performed_by, performed_at, str(event_id)),
                    )

                    # 2. Synchronize all contributing raw events
                    cur.execute(
                        """UPDATE events
                           SET verification_status = %s,
                               verified_by = COALESCE(%s, verified_by),
                               verification_timestamp = COALESCE(%s::timestamptz, verification_timestamp),
                               updated_at = NOW()
                           WHERE canonical_event_id = %s""",
                        (new_status, performed_by, performed_at, str(event_id)),
                    )
                conn.commit()

            logger.info(
                "Consumer synchronized event %s -> verification_status=%s",
                event_id,
                new_status,
            )
            return True
        except Exception as exc:
            logger.error("Failed to process verified event message: %s", exc, exc_info=True)
            return False

    def run_loop(self):
        """Persistent long-running consumer poll loop."""
        if Consumer is None:
            logger.warning("confluent_kafka not installed; VerifiedEventConsumer disabled")
            return
        try:
            self.consumer = Consumer(self.conf)
            self.consumer.subscribe([self.topic])
            logger.info("VerifiedEventConsumer started and subscribed to topic: %s", self.topic)

            while self._running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.warning("Kafka verified consumer error: %s", msg.error())
                        continue

                success = self.process_message(msg.value())
                if success:
                    try:
                        self.consumer.commit(msg, asynchronous=False)
                    except Exception as e:
                        logger.warning("Failed to commit offset: %s", e)
        except Exception as exc:
            logger.warning("Verified consumer loop exited: %s", exc)
        finally:
            if self.consumer:
                try:
                    self.consumer.close()
                except Exception:
                    pass

    def stop(self):
        self._running = False
