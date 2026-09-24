"""
SIH26069 — Fast-Path Critical Event Consumer
Subscribes to 'weather.critical', enriches with RuleBasedClassifier,
and writes to PostgreSQL in milliseconds using ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

# Resolve ML path dynamically across Docker and local execution
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent.parent
for candidate in [
    CURRENT_DIR / "ml",
    REPO_ROOT / "services" / "ml",
    Path("/app/services/ml"),
    Path("/app/ml"),
]:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from classifier.rule_based_classifier import RuleBasedClassifier
except ImportError:
    from services.ml.classifier.rule_based_classifier import RuleBasedClassifier

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    from confluent_kafka import Consumer, KafkaError
except ImportError:
    Consumer = None
    KafkaError = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("critical_consumer")

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.environ.get("CRITICAL_TOPIC", "weather.critical")
GROUP_ID = os.environ.get("CRITICAL_CONSUMER_GROUP", "critical-fast-path-group")

PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
PG_DB = os.environ.get("POSTGRES_DB", "weatherdb")
PG_USER = os.environ.get("POSTGRES_USER", "weather")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "weather")
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_db_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed in the current environment")
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def ensure_priority_column(conn):
    """Defensive migration check: ensures priority column and indexes exist."""
    with conn.cursor() as cur:
        cur.execute("""
            ALTER TABLE IF EXISTS canonical_events
                ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal',
                ADD COLUMN IF NOT EXISTS spark_processed_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS db_written_at TIMESTAMPTZ;
            ALTER TABLE IF EXISTS events
                ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';
            CREATE INDEX IF NOT EXISTS idx_canonical_events_priority ON canonical_events(priority);
            CREATE INDEX IF NOT EXISTS idx_canonical_events_spark_processed_at ON canonical_events(spark_processed_at);
            CREATE INDEX IF NOT EXISTS idx_canonical_events_db_written_at ON canonical_events(db_written_at);
            CREATE INDEX IF NOT EXISTS idx_events_priority ON events(priority);
        """)
    conn.commit()


def process_message(event_data: dict, classifier: RuleBasedClassifier, conn) -> str:
    # Unpack envelope if present
    if "payload" in event_data:
        payload = event_data["payload"]
        event = json.loads(payload) if isinstance(payload, str) else payload
    else:
        event = event_data

    event_id = event.get("event_id") or str(uuid.uuid4())
    loc = event.get("location") or {}
    ev = event.get("event") or {}

    ALLOWED_CATEGORIES = {
        "rainfall", "heavy_rainfall", "flood", "thunderstorm", "lightning",
        "heatwave", "fog", "dust_storm", "strong_wind", "hailstorm", "cyclone", "other"
    }
    ALLOWED_SEVERITIES = {"low", "moderate", "high", "extreme"}
    ALLOWED_SOURCES = {
        "weather_api", "rss", "website", "social", "simulated_social",
        "government_dataset", "citizen_report", "sensor"
    }

    category = ev.get("category") or "other"
    if category not in ALLOWED_CATEGORIES:
        category = "other"

    raw_sev = (ev.get("severity") or "high").lower()
    if raw_sev in ("critical", "extreme"):
        severity = "extreme"
    elif raw_sev in ("high", "severe", "warning"):
        severity = "high"
    elif raw_sev in ("moderate", "medium"):
        severity = "moderate"
    else:
        severity = "low"

    raw_source_type = event.get("source_type") or "rss"
    source_type = raw_source_type if raw_source_type in ALLOWED_SOURCES else "rss"

    description = ev.get("description") or ""

    # Step 1: Rapid ML classification via existing RuleBasedClassifier (<2ms)
    clf_res = classifier.predict(description, category_hint=category)
    classified_cat = clf_res.get("classified_category") or category
    if classified_cat not in ALLOWED_CATEGORIES:
        classified_cat = category
    confidence = clf_res.get("classification_confidence") or 0.85

    event_ts = event.get("timestamp") or datetime.now(timezone.utc).isoformat()
    now_ts = datetime.now(timezone.utc)

    # Step 2: Direct upsert to PostgreSQL with ON CONFLICT DO NOTHING
    with conn.cursor() as cur:
        # Write to canonical_events (immediate API dashboard visibility)
        cur.execute("""
            INSERT INTO canonical_events (
                canonical_event_id, event_category, severity, description,
                latitude, longitude, city, district, state, country,
                first_seen, last_seen, source_count, report_count,
                contributing_sources, classified_category, classification_confidence,
                credibility_score, verification_status, priority, created_at, updated_at,
                spark_processed_at, db_written_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, 1, 1,
                ARRAY[%s], %s, %s,
                0.85, 'pending', 'critical', %s, %s,
                %s, %s
            )
            ON CONFLICT (canonical_event_id) DO NOTHING
        """, (
            event_id, category, severity, description,
            loc.get("latitude"), loc.get("longitude"),
            loc.get("city"), loc.get("district"), loc.get("state"), loc.get("country", "India"),
            event_ts, event_ts,
            event.get("source_name", "fast_path_triage"),
            classified_cat, confidence,
            now_ts, now_ts,
            event.get("spark_processed_at"), now_ts,
        ))

        # Write to events table
        cur.execute("""
            INSERT INTO events (
                event_id, source_id, source_type, source_name,
                event_timestamp, ingestion_timestamp,
                latitude, longitude, city, district, state, country,
                event_category, severity, description,
                classified_category, classification_confidence,
                canonical_event_id, verification_status, priority
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, 'pending', 'critical'
            )
            ON CONFLICT (event_id) DO NOTHING
        """, (
            event_id, event.get("source_id", event_id), source_type,
            event.get("source_name", "fast_path_triage"),
            event_ts, now_ts,
            loc.get("latitude"), loc.get("longitude"),
            loc.get("city"), loc.get("district"), loc.get("state"), loc.get("country", "India"),
            category, severity, description,
            classified_cat, confidence,
            event_id,
        ))
    conn.commit()
    return event_id



def main():
    logger.info("Starting Critical Fast-Path Consumer...")
    classifier = RuleBasedClassifier()

    # Connect to DB with retry
    conn = None
    for attempt in range(15):
        try:
            conn = get_db_connection()
            ensure_priority_column(conn)
            logger.info("Connected to PostgreSQL & verified schema.")
            break
        except Exception as e:
            logger.warning("Waiting for database (%s)... retry %d/15", e, attempt + 1)
            time.sleep(2)
    if not conn:
        logger.error("Could not connect to database. Exiting.")
        sys.exit(1)

    # Kafka Consumer config
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }
    consumer = Consumer(conf)
    consumer.subscribe([TOPIC])
    logger.info("Subscribed to topic: %s", TOPIC)

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Kafka error: %s", msg.error())
                continue

            t_start = time.perf_counter()
            try:
                val = json.loads(msg.value().decode("utf-8"))
                event_id = process_message(val, classifier, conn)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                # Console log for demo visibility
                print(f"CRITICAL event {event_id} processed in {elapsed_ms:.2f}ms", flush=True)
                logger.info("CRITICAL event %s processed in %.2fms", event_id, elapsed_ms)
            except Exception as e:
                logger.error("Failed processing critical event: %s", e, exc_info=True)
                try:
                    if conn and not conn.closed:
                        conn.rollback()
                except Exception:
                    pass
                if not conn or conn.closed:
                    conn = get_db_connection()
    except KeyboardInterrupt:
        logger.info("Consumer shutting down.")
    finally:
        consumer.close()
        if conn and not conn.closed:
            conn.close()


if __name__ == "__main__":
    main()
