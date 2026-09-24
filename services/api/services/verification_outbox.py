"""Transactional outbox publisher for verification actions."""
from __future__ import annotations
import json, os
from datetime import datetime, timezone, timedelta
try:
    from confluent_kafka import Producer
except ImportError:
    Producer = None

from dependencies import get_db


def enqueue(conn, event_id: str, action: str, payload: dict) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO verification_outbox (event_id, action, payload)
               VALUES (%s, %s, %s::jsonb) RETURNING outbox_id""",
            (event_id, action, json.dumps(payload)),
        )
        return str(cur.fetchone()[0])


def _publish(outbox_id: str, payload: dict) -> None:
    if Producer is None:
        return
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    producer = Producer({
        "bootstrap.servers": bootstrap, "client.id": "api-verification-outbox",
        "acks": "all", "enable.idempotence": True, "retries": 5,
    })
    envelope = {
        "schema_version": "1.0", "message_id": outbox_id,
        "event_type": "verification_action",
        "produced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "producer": "api", "payload": json.dumps(payload),
    }
    producer.produce("weather.verified", key=payload["event_id"].encode(), value=json.dumps(envelope).encode())
    producer.flush(10)
    producer.flush(3)


def publish_pending(limit: int = 50) -> int:
    published = 0
    with get_db() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                """SELECT outbox_id, payload FROM verification_outbox
                   WHERE published_at IS NULL AND next_attempt_at <= NOW()
                   ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT %s""", (limit,)
            )
            rows = cur.fetchall()
            for outbox_id, payload in rows:
                try:
                    _publish(str(outbox_id), payload)
                    cur.execute(
                        "UPDATE verification_outbox SET published_at=NOW(), last_error=NULL WHERE outbox_id=%s",
                        (outbox_id,),
                    )
                    published += 1
                except Exception as exc:
                    cur.execute(
                        """UPDATE verification_outbox
                           SET attempts=attempts+1, last_error=%s,
                               next_attempt_at=NOW() + LEAST(interval '5 minutes', interval '5 seconds' * POWER(2, LEAST(attempts, 6)))
                           WHERE outbox_id=%s""", (str(exc)[:2000], outbox_id)
                    )
        conn.commit()
    return published
