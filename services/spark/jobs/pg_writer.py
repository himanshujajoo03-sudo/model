"""
SIH26069 — PostgreSQL Writer
Consumes weather.events from Kafka via Spark Structured Streaming
and upserts enriched canonical weather events to PostgreSQL/PostGIS.

Ref: 01_ARCHITECTURE.md §5.4, 02_DATA_SCHEMA.md §6, 03_KAFKA_CONTRACT.md §2.2
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import logging
from datetime import datetime, timezone

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType,
    ArrayType, BooleanType,
)

import psycopg2
import psycopg2.extras

# ── Architecture note (see 01_ARCHITECTURE.md) ─────────────────────
# Primary AI/ML — classification, first-pass credibility, and spatial
# clustering — runs upstream in stream_processor.py, BEFORE an event is
# published to Kafka's weather.events topic. That satisfies the pipeline
# diagram: Spark -> Validation/Dedup/Aggregation -> AI/ML -> weather.events.
#
# The functions imported below are NOT a second, redundant ML pass. They
# compute a narrower, DB-dependent VERIFICATION step: cross-source
# corroboration ("how many independent source types confirm this?") and
# weather-API agreement. That signal only exists in durable PostgreSQL
# state (what other sources have already been persisted for this area),
# which a Kafka micro-batch cannot see on its own. Computing it here,
# inside the same transaction as the write, also avoids a race condition
# where the corroboration count goes stale between computing it and
# persisting it. This writer's job is therefore "parse -> verify against
# durable state -> persist", not "parse -> persist" plus independent ML.
try:
    from ml.credibility.credibility_scorer import score_credibility
    from ml.dedup.duplicate_detector import compute_duplicate_score
    from ml.verification.verification_engine import decide_verification
    ML_AVAILABLE = True
except (ImportError, ValueError, Exception) as exc:
    ML_AVAILABLE = False
    logger_ml = logging.getLogger("spark.pg_writer.ml")
    logger_ml.warning("ML modules not available — credibility/verification using safe fallbacks: %s", exc)

    def decide_verification(*args, **kwargs):
        return "needs_review", ["ML verification module not available; queued for review"]

    def score_credibility(*args, **kwargs):
        return 0.5, ["Credibility scorer not available"]

    def compute_duplicate_score(*args, **kwargs):
        return 0.0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spark.pg_writer")

# ── Configuration ───────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
EVENTS_TOPIC = os.environ.get("PG_WRITER_TOPIC", "weather.events")
CHECKPOINT_PATH = os.environ.get("PG_WRITER_CHECKPOINT_PATH", "/data/checkpoints/pg_writer")

# ── Canonical Event Matching Thresholds ─────────────────────────────
# MVP: conservative spatial-temporal matching per 06_IMPLEMENTATION_PLAN.md
CANONICAL_MATCH_DISTANCE_KM = float(os.environ.get("CANONICAL_MATCH_DISTANCE_KM", "50"))
CANONICAL_MATCH_TIME_HOURS = float(os.environ.get("CANONICAL_MATCH_TIME_HOURS", "24"))

DATABASE_URL = os.environ.get("DATABASE_URL", "")
PG_HOST = os.environ.get("POSTGRES_HOST", "postgres")
PG_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
PG_DB = os.environ.get("POSTGRES_DB", "weatherdb")
PG_USER = os.environ.get("POSTGRES_USER", "weather")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "weather")

# ── Kafka envelope schema (03_KAFKA_CONTRACT.md §3) ────────────────
ENVELOPE_SCHEMA = StructType([
    StructField("schema_version", StringType(), False),
    StructField("message_id", StringType(), False),
    StructField("event_type", StringType(), False),
    StructField("produced_at", StringType(), False),
    StructField("producer", StringType(), False),
    StructField("payload", StringType(), False),  # JSON string of canonical event
])

# ── Canonical Weather Event Schema (02_DATA_SCHEMA.md §2) ──────────
LOCATION_SCHEMA = StructType([
    StructField("latitude", FloatType(), True),
    StructField("longitude", FloatType(), True),
    StructField("city", StringType(), True),
    StructField("district", StringType(), True),
    StructField("state", StringType(), True),
    StructField("country", StringType(), True),
])

EVENT_FIELDS_SCHEMA = StructType([
    StructField("category", StringType(), False),
    StructField("severity", StringType(), True),
    StructField("description", StringType(), True),
])

SOCIAL_METADATA_SCHEMA = StructType([
    StructField("hashtags", ArrayType(StringType()), True),
    StructField("author_id", StringType(), True),
    StructField("platform", StringType(), True),
])

MEDIA_SCHEMA = StructType([
    StructField("photos", ArrayType(StringType()), True),
    StructField("videos", ArrayType(StringType()), True),
])

AI_SCHEMA = StructType([
    StructField("classified_category", StringType(), True),
    StructField("classification_confidence", FloatType(), True),
    StructField("duplicate_score", FloatType(), True),
    StructField("credibility_score", FloatType(), True),
    StructField("credibility_reasons", ArrayType(StringType()), True),
    StructField("verification_reasons", ArrayType(StringType()), True),
    StructField("cluster_id", StringType(), True),
])

VERIFICATION_SCHEMA = StructType([
    StructField("status", StringType(), True),
    StructField("verified_by", StringType(), True),
    StructField("verification_timestamp", StringType(), True),
    StructField("verification_reasons", ArrayType(StringType()), True),
])

CANONICAL_SCHEMA = StructType([
    StructField("event_id", StringType(), False),
    StructField("source_id", StringType(), False),
    StructField("source_type", StringType(), False),
    StructField("source_name", StringType(), False),
    StructField("source_url", StringType(), True),
    StructField("source_trust_score", FloatType(), True),
    StructField("timestamp", StringType(), False),
    StructField("ingestion_timestamp", StringType(), False),
    StructField("location", LOCATION_SCHEMA, True),
    StructField("event", EVENT_FIELDS_SCHEMA, True),
    StructField("social_metadata", SOCIAL_METADATA_SCHEMA, True),
    StructField("media", MEDIA_SCHEMA, True),
    StructField("ai", AI_SCHEMA, True),
    StructField("verification", VERIFICATION_SCHEMA, True),
])


# ── Database helpers ────────────────────────────────────────────────

def _get_connection():
    """Create a new PostgreSQL connection."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB,
        user=PG_USER, password=PG_PASSWORD,
    )


def _row_to_dict(row) -> dict:
    """Convert a Spark Row to a nested dict, handling nested Rows."""
    from pyspark.sql import Row
    d = {}
    for field in row.__fields__:
        val = row[field]
        if isinstance(val, Row):
            d[field] = _row_to_dict(val)
        elif isinstance(val, (list, tuple)):
            d[field] = [_row_to_dict(v) if isinstance(v, Row) else v for v in val]
        else:
            d[field] = val
    return d


def _parse_event(message_json: str):
    """Parse a Kafka envelope and return its canonical payload."""
    try:
        envelope = json.loads(message_json)
        if not isinstance(envelope, dict): return None
        required = ("schema_version", "message_id", "event_type", "produced_at", "producer", "payload")
        if any(not envelope.get(k) for k in required): return None
        if envelope.get("event_type") != "weather_event": return None
        event = json.loads(envelope["payload"]) if isinstance(envelope["payload"], str) else envelope["payload"]
        if not isinstance(event, dict) or not event.get("event_id"): return None
        return event
    except (json.JSONDecodeError, TypeError):
        return None


def _safe_float(val, min_val=0.0, max_val=1.0):
    """Convert to float within range, or return None."""
    if val is None:
        return None
    try:
        f = float(val)
        if min_val <= f <= max_val:
            return round(f, 3)
        return None
    except (TypeError, ValueError):
        return None


def _safe_uuid(val):
    """Validate UUID string, return None if invalid."""
    if not val:
        return None
    try:
        uuid.UUID(str(val))
        return str(val)
    except (ValueError, TypeError):
        return None


def _haversine_km(lat1, lon1, lat2, lon2):
    """Haversine distance in km between two lat/lon points."""
    import math
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def _find_matching_canonical_event(conn, event: dict):
    """
    Find an existing canonical event that matches this source record.

    Matching criteria (conservative MVP):
    - Same event_category
    - Geographic distance <= CANONICAL_MATCH_DISTANCE_KM
    - Temporal distance <= CANONICAL_MATCH_TIME_HOURS

    Returns (canonical_event_id, num_independent_sources) or (None, 0)
    when there is genuinely no match.

    IMPORTANT: a DB *failure* here must never be silently treated as
    "no match" — that would let the caller create a brand-new canonical
    event for a report that may already have one, duplicating state
    during a transient PostgreSQL failure. DB errors are re-raised so
    the whole batch aborts, rolls back, and Spark retries the batch.
    """
    loc = event.get("location") or {}
    ev = event.get("event") or {}
    category = ev.get("category")
    latitude = loc.get("latitude")
    longitude = loc.get("longitude")
    timestamp = event.get("timestamp")

    if not category or latitude is None or longitude is None or not timestamp:
        return None, 0

    event_ts = _parse_timestamp(timestamp)
    if not event_ts:
        return None, 0

    try:
        with conn.cursor() as cur:
            hours = int(CANONICAL_MATCH_TIME_HOURS)
            interval_str = f"{hours} hours"
            cur.execute(
                "SELECT canonical_event_id, latitude, longitude, last_seen "
                "FROM canonical_events "
                "WHERE event_category = %s "
                "AND last_seen >= %s - (%s)::interval "
                "AND last_seen <= %s + (%s)::interval",
                (category, event_ts, interval_str, event_ts, interval_str),
            )

            candidates = cur.fetchall()
            if not candidates:
                return None, 0

            for row in candidates:
                ce_id, ce_lat, ce_lon, ce_last_seen = row
                if ce_lat is None or ce_lon is None:
                    continue
                dist = _haversine_km(
                    float(latitude), float(longitude),
                    float(ce_lat), float(ce_lon)
                )
                if dist <= CANONICAL_MATCH_DISTANCE_KM:
                    # Count independent source types already contributing
                    independent = _count_independent_sources(conn, str(ce_id))
                    return str(ce_id), independent

            return None, 0

    except Exception as e:
        # Do NOT swallow this. Returning (None, 0) here would make the
        # caller believe "no matching canonical event exists" and create
        # a duplicate one. Fail loud so _write_batch_to_postgres rolls
        # back the entire batch and Spark retries it.
        logger.error("Canonical match query failed, aborting batch: %s", e)
        raise


def _count_independent_sources(conn, canonical_event_id: str) -> int:
    """
    Count distinct source_types already contributing to a canonical event.
    Used for corroboration scoring.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(DISTINCT source_type) FROM events "
                "WHERE canonical_event_id = %s",
                (canonical_event_id,),
            )
            result = cur.fetchone()
            return result[0] if result else 0
    except Exception:
        return 0


def _compute_corroboration_score(
    num_independent_sources: int,
    current_source_type: str,
    canonical_event_id: str | None,
    conn,
) -> float:
    """
    Compute corroboration score based on independent source types.

    Rules:
    - Only distinct source_types count (not repeated records from same source)
    - Repetitions from the SAME source type do NOT increase corroboration
    - 0 truly independent sources (first report or same source repeated) → 0.10
    - 1 independent source (different source type) → 0.40
    - 2 independent sources → 0.70
    - 3+ independent sources → 0.90

    Args:
        num_independent_sources: Count of DISTINCT source_types already
            contributing to this canonical event (from DB query).
        current_source_type: The source_type of the event currently being
            processed. Used to determine if this source is truly new.
        canonical_event_id: If matched to an existing canonical event.
        conn: Database connection.
    """
    if canonical_event_id:
        # num_independent_sources = COUNT(DISTINCT source_type) already in DB
        # The current event has NOT been inserted yet, so it's not counted.
        # If current_source_type is already in the set, adding it doesn't
        # increase the independent count.
        #
        # We need to check whether the current source_type is already present
        # among the contributing sources.
        already_present = _is_source_type_present(conn, canonical_event_id, current_source_type)
        effective_independent = num_independent_sources + (0 if already_present else 1)

        if effective_independent <= 1:
            return 0.10
        elif effective_independent == 2:
            return 0.40
        elif effective_independent == 3:
            return 0.70
        else:
            return 0.90

    # No canonical event match — first report for this area
    return 0.10


def _is_source_type_present(conn, canonical_event_id: str, source_type: str) -> bool:
    """
    Check if a source_type is already among the contributing records
    for a canonical event.
    """
    if not source_type or not canonical_event_id:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM events WHERE canonical_event_id = %s AND source_type = %s LIMIT 1",
                (canonical_event_id, source_type),
            )
            return cur.fetchone() is not None
    except Exception:
        return False


def _compute_weather_agreement_from_db(
    conn,
    latitude: float | None,
    longitude: float | None,
    category: str,
    event_ts,
) -> float:
    """
    Check if recent weather_api observations in the area agree with this report.

    Queries the events table for recent weather_api records near the location
    and checks if their event_category is compatible.

    Returns 0.0–1.0 agreement score.
    """
    if latitude is None or longitude is None or not category or not event_ts:
        return 0.30  # Cannot evaluate

    try:
        with conn.cursor() as cur:
            # Find recent weather_api observations within ~50km in last 2 hours
            cur.execute("""
                SELECT event_category, latitude, longitude
                FROM events
                WHERE source_type = 'weather_api'
                AND event_timestamp >= %s - interval '2 hours'
                AND event_timestamp <= %s + interval '2 hours'
                AND latitude IS NOT NULL AND longitude IS NOT NULL
            """, (event_ts, event_ts))

            rows = cur.fetchall()
            if not rows:
                return 0.30  # No weather observations nearby

            # Check if any nearby weather_api observation has compatible category
            from ml.classifier.rules import CATEGORY_COMPATIBILITY
            compatible = CATEGORY_COMPATIBILITY.get(category, set())

            for row in rows:
                api_cat, api_lat, api_lon = row
                if api_lat is None or api_lon is None:
                    continue
                dist = _haversine_km(
                    float(latitude), float(longitude),
                    float(api_lat), float(api_lon),
                )
                if dist <= 100.0:  # Within 100km
                    if api_cat == category:
                        return 1.0  # Exact category match from weather API
                    if api_cat in compatible:
                        return 0.70  # Compatible category

            return 0.20  # Weather API exists but disagrees

    except Exception as e:
        logger.debug("Weather agreement query failed: %s", e)
        return 0.30


def _upsert_canonical_event(conn, event: dict, canonical_event_id, verification_status="pending", verification_reasons=None, increment_report_count=True):
    """
    Upsert a canonical event. If canonical_event_id is provided, update existing;
    otherwise create new. Returns the canonical_event_id.

    Aggregation rules:
    - first_seen = MIN of contributing observation timestamps
    - last_seen = MAX of contributing observation timestamps
    - source_count = COUNT(DISTINCT source_name) from contributing records
    - report_count = COUNT(*) from contributing records
    - coordinates = most recent contributing record's coordinates
    - severity = most severe among contributing records
    - credibility_score = MAX among contributing records
    - classification_confidence = MAX among contributing records
    - verification_status = most severe status (suspicious > needs_review > pending > verified)
    """
    loc = event.get("location") or {}
    ev = event.get("event") or {}
    ai = event.get("ai") or {}
    verification = event.get("verification") or {}
    event_ts = _parse_timestamp(event.get("timestamp"))

    category = ev.get("category")
    if not category:
        return None

    latitude = _safe_float(loc.get("latitude"), -90, 90)
    longitude = _safe_float(loc.get("longitude"), -180, 180)
    severity = ev.get("severity") if ev.get("severity") in {"low", "moderate", "high", "extreme"} else None
    credibility = _safe_float(ai.get("credibility_score"), 0, 1)
    confidence = _safe_float(ai.get("classification_confidence"), 0, 1)
    source_name = event.get("source_name")

    # Severity ordering for conservative aggregation
    sev_order = {"low": 0, "moderate": 1, "high": 2, "extreme": 3}

    # Pre-compute values to avoid complex expressions in SQL params
    description = ev.get('description') or ''
    description = description[:2000] if description else None
    city = loc.get('city')
    district = loc.get('district')
    state = loc.get('state')
    country = loc.get('country') or 'India'
    classified_cat = ai.get('classified_category')
    cred_reasons = ai.get('credibility_reasons') or []
    ver_status = verification.get('status') or 'pending'

    try:
        with conn.cursor() as cur:
            if canonical_event_id:
                # Verification status aggregation for canonical events.
                # IMPORTANT: 'duplicate' is a SOURCE-RECORD concept, not a
                # canonical-event concept. A canonical event with some duplicate
                # source reports is still a real weather event.
                # Priority: verified > needs_review > suspicious > pending.
                # 'duplicate' from a source record does NOT override the
                # canonical event status -- it only affects the source record.
                ver_priority = {"verified": 4, "needs_review": 3, "suspicious": 2, "pending": 1, "duplicate": 0}
                # Skip 'duplicate' source records for canonical event status
                effective_ver_status = verification_status if verification_status != 'duplicate' else None
                # When status is 'duplicate', keep existing verification_reasons
                # to avoid psycopg2 polymorphic type error from empty array []
                effective_ver_reasons = verification_reasons if (verification_status != 'duplicate' and verification_reasons) else None
                cur.execute("""
                    UPDATE canonical_events SET
                        first_seen = LEAST(first_seen, %s),
                        last_seen = GREATEST(last_seen, %s),
                        report_count = report_count + CASE WHEN %s THEN 1 ELSE 0 END,
                        contributing_sources = (
                            CASE WHEN %s::text = ANY(contributing_sources)
                                 THEN contributing_sources
                                 ELSE array_append(contributing_sources, %s::text)
                            END
                        ),
                        source_count = array_length(
                            CASE WHEN %s::text = ANY(contributing_sources)
                                 THEN contributing_sources
                                 ELSE array_append(contributing_sources, %s::text)
                            END, 1
                        ),
                        severity = CASE
                            WHEN %s IS NULL THEN severity
                            WHEN severity IS NULL THEN %s
                            WHEN CASE %s::text
                                WHEN 'low' THEN 0 WHEN 'moderate' THEN 1
                                WHEN 'high' THEN 2 WHEN 'extreme' THEN 3 ELSE -1 END
                                > CASE severity
                                WHEN 'low' THEN 0 WHEN 'moderate' THEN 1
                                WHEN 'high' THEN 2 WHEN 'extreme' THEN 3 ELSE -1 END
                            THEN %s
                            ELSE severity
                        END,
                        credibility_score = CASE
                            WHEN %s IS NULL THEN credibility_score
                            WHEN credibility_score IS NULL THEN %s
                            WHEN %s > credibility_score THEN %s
                            ELSE credibility_score
                        END,
                        classification_confidence = CASE
                            WHEN %s IS NULL THEN classification_confidence
                            WHEN classification_confidence IS NULL THEN %s
                            WHEN %s > classification_confidence THEN %s
                            ELSE classification_confidence
                        END,
                        description = COALESCE(%s, description),
                        latitude = COALESCE(%s, latitude),
                        longitude = COALESCE(%s, longitude),
                        cluster_id = COALESCE(%s, cluster_id),
                        verification_status = CASE
                            WHEN %s IS NOT NULL AND (
                                verification_status IS NULL
                                OR verification_status = 'pending'
                                OR %s > CASE verification_status
                                    WHEN 'pending' THEN 1
                                    WHEN 'needs_review' THEN 3
                                    WHEN 'verified' THEN 4
                                    WHEN 'suspicious' THEN 2
                                    WHEN 'duplicate' THEN 0
                                    ELSE 1
                                END
                            ) THEN %s
                            ELSE verification_status
                        END,
                        verification_reasons = CASE
                            WHEN %s::text[] IS NOT NULL AND array_length(%s::text[], 1) > 0
                            THEN %s::text[]
                            ELSE verification_reasons
                        END
                    WHERE canonical_event_id = %s
                    RETURNING canonical_event_id
                """, (
                    event_ts, event_ts, increment_report_count,
                    source_name, source_name,
                    source_name, source_name,
                    severity, severity, severity, severity,
                    credibility, credibility, credibility, credibility,
                    confidence, confidence, confidence, confidence,
                    description, latitude, longitude, _safe_uuid(ai.get("cluster_id")),
                    effective_ver_status or 'pending', ver_priority.get(effective_ver_status, 1) if effective_ver_status else 0,
                    effective_ver_status or 'pending',
                    effective_ver_reasons, effective_ver_reasons, effective_ver_reasons,
                    canonical_event_id,
                ))
                result = cur.fetchone()
                if result:
                    logger.info("Updated canonical event %s (report_count incremented)", canonical_event_id[:8])
                    return canonical_event_id
                else:
                    logger.warning("Canonical event %s not found during update", canonical_event_id[:8])
                    return None

            else:
                # Create new canonical event
                ce_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO canonical_events (
                        canonical_event_id, event_category, severity, description,
                        latitude, longitude, city, district, state, country,
                        first_seen, last_seen, source_count, report_count,
                        contributing_sources,
                        classified_category, classification_confidence,
                        credibility_score, credibility_reasons, cluster_id,
                        verification_status, verification_reasons
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, 1, 1,
                        ARRAY[%s],
                        %s, %s, %s,
                        %s, %s,
                        %s, %s
                    )
                """, (
                    ce_id, category, severity, description,
                    latitude, longitude,
                    city, district, state, country,
                    event_ts, event_ts,
                    source_name,
                    classified_cat, confidence, credibility,
                    cred_reasons, _safe_uuid(ai.get("cluster_id")),
                    verification_status, verification_reasons or [],
                ))
                logger.info("Created new canonical event %s for %s/%s",
                            ce_id[:8], loc.get('city', '?'), category)
                return ce_id

    except Exception as e:
        # A silent None here would let the batch "succeed" while a
        # canonical event write actually failed — data loss without
        # error. Re-raise so the whole batch rolls back atomically.
        logger.error("Canonical event upsert failed, aborting batch: %s", e)
        raise


def _upsert_event(conn, event: dict) -> tuple[bool, bool]:
    """
    Upsert a single source record into the events table.
    Uses ON CONFLICT (event_id) DO UPDATE for idempotency.
    PostGIS geometry is handled by the sync_geom() trigger.
    """
    loc = event.get("location") or {}
    ev = event.get("event") or {}
    social = event.get("social_metadata") or {}
    media = event.get("media") or {}
    ai = event.get("ai") or {}
    verification = event.get("verification") or {}

    event_id = _safe_uuid(event.get("event_id"))
    if not event_id:
        logger.warning("Invalid event_id, skipping")
        return False, False

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM events WHERE event_id = %s", (event_id,))
        event_already_exists = cur.fetchone() is not None

    # Parse timestamps
    event_ts = _parse_timestamp(event.get("timestamp"))
    ingestion_ts = _parse_timestamp(event.get("ingestion_timestamp"))
    verification_ts = _parse_timestamp(verification.get("verification_timestamp"))

    # Validate coordinates
    latitude = _safe_float(loc.get("latitude"), -90, 90)
    longitude = _safe_float(loc.get("longitude"), -180, 180)

    # Validate AI scores
    classification_confidence = _safe_float(ai.get("classification_confidence"), 0, 1)
    duplicate_score = _safe_float(ai.get("duplicate_score"), 0, 1)
    credibility_score = _safe_float(ai.get("credibility_score"), 0, 1)

    # Validate category enums
    valid_categories = {
        "rainfall", "heavy_rainfall", "flood", "thunderstorm", "lightning",
        "heatwave", "fog", "dust_storm", "strong_wind", "hailstorm", "cyclone", "other",
    }
    event_category = ev.get("category") if ev.get("category") in valid_categories else None
    classified_category = ai.get("classified_category") if ai.get("classified_category") in valid_categories else None
    severity = ev.get("severity") if ev.get("severity") in {"low", "moderate", "high", "extreme"} else None
    verification_status = verification.get("status") or "pending"
    if verification_status not in {"pending", "verified", "needs_review", "suspicious", "duplicate"}:
        verification_status = "pending"

    # Source type validation
    valid_source_types = {
        "weather_api", "rss", "website", "social", "simulated_social",
        "government_dataset", "citizen", "synthetic",
    }
    source_type = event.get("source_type") if event.get("source_type") in valid_source_types else None
    if not source_type:
        logger.warning("Invalid source_type for %s, skipping", event_id[:8])
        return False, False

    # Source trust score
    source_trust_score = _safe_float(event.get("source_trust_score"), 0, 1)

    # Arrays
    hashtags = social.get("hashtags") or []
    photo_urls = media.get("photos") or []
    video_urls = media.get("videos") or []
    credibility_reasons = ai.get("credibility_reasons") or []

    sql = """
        INSERT INTO events (
            event_id, source_id, source_type, source_name, source_url,
            source_trust_score, event_timestamp, ingestion_timestamp,
            latitude, longitude, city, district, state, country,
            event_category, severity, description,
            hashtags, author_id, platform,
            photo_urls, video_urls,
            classified_category, classification_confidence,
            duplicate_score, credibility_score, credibility_reasons,
            cluster_id, canonical_event_id,
            verification_status, verified_by, verification_timestamp
        ) VALUES (
            %(event_id)s, %(source_id)s, %(source_type)s, %(source_name)s, %(source_url)s,
            %(source_trust_score)s, %(event_timestamp)s, %(ingestion_timestamp)s,
            %(latitude)s, %(longitude)s, %(city)s, %(district)s, %(state)s, %(country)s,
            %(event_category)s, %(severity)s, %(description)s,
            %(hashtags)s, %(author_id)s, %(platform)s,
            %(photo_urls)s, %(video_urls)s,
            %(classified_category)s, %(classification_confidence)s,
            %(duplicate_score)s, %(credibility_score)s, %(credibility_reasons)s,
            %(cluster_id)s, %(canonical_event_id)s,
            %(verification_status)s, %(verified_by)s, %(verification_timestamp)s
        )
        ON CONFLICT (event_id) DO UPDATE SET
            source_id = EXCLUDED.source_id,
            source_type = EXCLUDED.source_type,
            source_name = EXCLUDED.source_name,
            source_url = EXCLUDED.source_url,
            source_trust_score = EXCLUDED.source_trust_score,
            event_timestamp = EXCLUDED.event_timestamp,
            ingestion_timestamp = EXCLUDED.ingestion_timestamp,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            city = EXCLUDED.city,
            district = EXCLUDED.district,
            state = EXCLUDED.state,
            country = EXCLUDED.country,
            event_category = EXCLUDED.event_category,
            severity = EXCLUDED.severity,
            description = EXCLUDED.description,
            hashtags = EXCLUDED.hashtags,
            author_id = EXCLUDED.author_id,
            platform = EXCLUDED.platform,
            photo_urls = EXCLUDED.photo_urls,
            video_urls = EXCLUDED.video_urls,
            classified_category = EXCLUDED.classified_category,
            classification_confidence = EXCLUDED.classification_confidence,
            duplicate_score = EXCLUDED.duplicate_score,
            credibility_score = EXCLUDED.credibility_score,
            credibility_reasons = EXCLUDED.credibility_reasons,
            cluster_id = EXCLUDED.cluster_id,
            canonical_event_id = EXCLUDED.canonical_event_id,
            verification_status = EXCLUDED.verification_status,
            verified_by = EXCLUDED.verified_by,
            verification_timestamp = EXCLUDED.verification_timestamp
    """

    params = {
        "event_id": event_id,
        "source_id": event.get("source_id"),
        "source_type": source_type,
        "source_name": event.get("source_name"),
        "source_url": event.get("source_url"),
        "source_trust_score": source_trust_score,
        "event_timestamp": event_ts,
        "ingestion_timestamp": ingestion_ts,
        "latitude": latitude,
        "longitude": longitude,
        "city": loc.get("city"),
        "district": loc.get("district"),
        "state": loc.get("state"),
        "country": loc.get("country") or "India",
        "event_category": event_category,
        "severity": severity,
        "description": (ev.get("description") or "")[:2000],
        "hashtags": hashtags,
        "author_id": social.get("author_id"),
        "platform": social.get("platform"),
        "photo_urls": photo_urls,
        "video_urls": video_urls,
        "classified_category": classified_category,
        "classification_confidence": classification_confidence,
        "duplicate_score": duplicate_score,
        "credibility_score": credibility_score,
        "credibility_reasons": credibility_reasons,
        "cluster_id": _safe_uuid(ai.get("cluster_id")),
        "canonical_event_id": _safe_uuid(event.get("canonical_event_id")),
        "verification_status": verification_status,
        "verified_by": verification.get("verified_by"),
        "verification_timestamp": verification_ts,
    }

    # NOTE: no per-row try/except here on purpose. A failed statement must
    # propagate to _write_batch_to_postgres, which rolls back the *whole*
    # batch transaction and raises so Spark retries it. Catching the error
    # here and calling conn.rollback() would roll back every earlier
    # statement in this transaction (including successfully-upserted
    # events earlier in the batch) while letting the loop continue and
    # commit later rows — an inconsistent, non-atomic batch.
    with conn.cursor() as cur:
        cur.execute(sql, params)
    return True, not event_already_exists


def _persist_cluster_assignment(conn, event: dict) -> str | None:
    """Persist Spark's cluster assignment with idempotent membership accounting."""
    loc = event.get("location") or {}
    ev = event.get("event") or {}
    ai = event.get("ai") or {}
    cluster_id = ai.get("cluster_id")
    event_id = _safe_uuid(event.get("event_id"))
    event_ts = _parse_timestamp(event.get("timestamp"))
    lat, lon, category = loc.get("latitude"), loc.get("longitude"), ev.get("category")
    if not cluster_id or not event_id or lat is None or lon is None or not category or not event_ts:
        return None
    cluster_id = str(uuid.UUID(str(cluster_id)))
    city, state = loc.get("city"), loc.get("state")
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO event_clusters
               (cluster_id, representative_id, event_category, city, state, centroid_geom,
                member_count, first_event_at, last_event_at)
               VALUES (%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326),0,%s,%s)
               ON CONFLICT (cluster_id) DO NOTHING""",
            (cluster_id, event_id, category, city, state, float(lon), float(lat), event_ts, event_ts),
        )
        # event_cluster_members is the idempotency authority. Replays do not
        # inflate member_count or alter centroid twice.
        cur.execute(
            """INSERT INTO event_cluster_members(event_id, cluster_id, event_timestamp)
               VALUES (%s,%s,%s) ON CONFLICT (event_id) DO NOTHING
               RETURNING event_id""",
            (event_id, cluster_id, event_ts),
        )
        inserted = cur.fetchone() is not None
        if inserted:
            cur.execute(
                """SELECT ST_Y(centroid_geom), ST_X(centroid_geom), member_count
                   FROM event_clusters WHERE cluster_id=%s FOR UPDATE""", (cluster_id,)
            )
            c_lat, c_lon, count = cur.fetchone()
            count = int(count or 0)
            if count == 0:
                new_lat, new_lon = float(lat), float(lon)
            else:
                new_lat = ((float(c_lat) * count) + float(lat)) / (count + 1)
                new_lon = ((float(c_lon) * count) + float(lon)) / (count + 1)
            cur.execute(
                """UPDATE event_clusters SET centroid_geom=ST_SetSRID(ST_MakePoint(%s,%s),4326),
                   member_count=member_count+1, first_event_at=LEAST(first_event_at,%s),
                   last_event_at=GREATEST(last_event_at,%s), updated_at=NOW()
                   WHERE cluster_id=%s""",
                (new_lon, new_lat, event_ts, event_ts, cluster_id),
            )
    return cluster_id

def _compute_ml_enrichment(conn, event: dict, existing_ce_id: str | None, independent_sources: int) -> dict:
    """
    Compute full ML enrichment with database context.

    This is the authoritative ML enrichment point. It queries the database
    for:
    - Recent events for duplicate detection
    - Contributing source types for corroboration
    - Recent weather_api observations for weather agreement

    Then computes:
    - credibility_score + credibility_reasons (with context)
    - duplicate_score (with recent events)
    - verification_status + verification_reasons

    Returns the enriched event dict with ai.* and verification.* fields updated.
    """
    if not ML_AVAILABLE:
        logger.debug("ML not available, skipping enrichment for %s", event.get("event_id", "?")[:8])
        return event

    ev = event.get("event") or {}
    ai = event.get("ai") or {}
    loc = event.get("location") or {}
    category = ev.get("category")
    latitude = loc.get("latitude")
    longitude = loc.get("longitude")
    source_type = event.get("source_type", "")
    event_ts = _parse_timestamp(event.get("timestamp"))

    # ── 1. Duplicate detection with recent events context ──
    dup_score = 0.0
    try:
        with conn.cursor() as sp_cur:
            sp_cur.execute("SAVEPOINT ml_dup")
        # Exclude current event_id to prevent self-matching
        current_event_id = event.get("event_id")
        recent_events = _query_recent_events(conn, category, latitude, longitude, event_ts, exclude_event_id=current_event_id)
        ml_event = _normalize_for_ml(event)
        dup_score = compute_duplicate_score(ml_event, recent_events)
        ai["duplicate_score"] = round(dup_score, 3)
        with conn.cursor() as sp_cur:
            sp_cur.execute("RELEASE SAVEPOINT ml_dup")
    except Exception as e:
        logger.warning("Duplicate detection failed: %s", e)
        ai["duplicate_score"] = 0.0
        try:
            with conn.cursor() as sp_cur:
                sp_cur.execute("ROLLBACK TO SAVEPOINT ml_dup")
        except Exception:
            pass

    # ── 2. Corroboration from independent sources ──
    corroboration = _compute_corroboration_score(
        independent_sources, source_type, existing_ce_id, conn
    )

    # ── 3. Weather agreement from DB ──
    try:
        with conn.cursor() as sp_cur:
            sp_cur.execute("SAVEPOINT ml_weather")
        weather_agreement = _compute_weather_agreement_from_db(
            conn, latitude, longitude, category, event_ts
        )
        with conn.cursor() as sp_cur:
            sp_cur.execute("RELEASE SAVEPOINT ml_weather")
    except Exception as e:
        logger.warning("Weather agreement query failed: %s", e)
        weather_agreement = 0.30
        try:
            with conn.cursor() as sp_cur:
                sp_cur.execute("ROLLBACK TO SAVEPOINT ml_weather")
        except Exception:
            pass

    # ── 0. Classification if missing or zero ──
    if not ai.get("classification_confidence") or float(ai.get("classification_confidence", 0.0)) <= 0.0:
        try:
            from ml.classifier.event_classifier import classify_event
            pred = classify_event(ev.get("description", ""), category)
            if pred and float(pred.get("classification_confidence", 0.0) or 0.0) > 0.0:
                ai["classified_category"] = pred.get("classified_category", category)
                ai["classification_confidence"] = float(pred.get("classification_confidence", 0.0))
        except Exception as e:
            logger.debug("Classification fallback in pg_writer: %s", e)

    # ── 4. Credibility scoring with full context ──
    try:
        ml_event = _normalize_for_ml(event)
        cred_result = score_credibility(
            ml_event,
            corroboration=corroboration,
            weather_agreement=weather_agreement,
            duplicate_score=dup_score,
        )
        if isinstance(cred_result, dict):
            cred_score = cred_result.get("credibility_score", 0.5)
            cred_reasons = cred_result.get("credibility_reasons") or cred_result.get("reasons", [])
        elif isinstance(cred_result, (list, tuple)) and len(cred_result) >= 2:
            cred_score, cred_reasons = cred_result[0], cred_result[1]
        else:
            cred_score, cred_reasons = float(cred_result), []
        ai["credibility_score"] = cred_score
        ai["credibility_reasons"] = cred_reasons
    except Exception as e:
        logger.warning("Credibility scoring failed: %s", e)
        ai["credibility_score"] = 0.5
        ai["credibility_reasons"] = ["Credibility scoring failed — using default"]

    event["ai"] = ai

    # ── 5. Verification decision ──
    try:
        ver_status, ver_reasons = decide_verification(
            credibility_score=ai.get("credibility_score"),
            duplicate_score=ai.get("duplicate_score"),
            corroboration=corroboration,
            source_trust=event.get("source_trust_score"),
            spatial_consistency=_compute_spatial_score(event),
            temporal_consistency=_compute_temporal_score(event),
            classification_confidence=ai.get("classification_confidence"),
            weather_agreement=weather_agreement,
            source_type=source_type,
        )
        event["verification"] = {
            "status": ver_status,
            "verified_by": "automated" if ver_status == "verified" else None,
            "verification_timestamp": (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                if ver_status != "pending" else None
            ),
            "verification_reasons": ver_reasons,
        }
    except Exception as e:
        logger.warning("Verification decision failed: %s", e)
        event["verification"] = {
            "status": "needs_review",
            "verified_by": None,
            "verification_timestamp": None,
            "verification_reasons": ["Verification engine failed"],
        }

    return event


def _query_recent_events(conn, category, latitude, longitude, event_ts, window_minutes=30, exclude_event_id=None):
    """
    Query recent events from the database for duplicate detection context.

    Returns a list of event dicts in the format expected by
    compute_duplicate_score().

    Args:
        exclude_event_id: If provided, exclude this event_id from results
            to prevent self-matching when reprocessing the same record.
    """
    if not category or not event_ts:
        return []

    try:
        with conn.cursor() as cur:
            interval_str = f"{window_minutes} minutes"
            # DISTINCT ON (source_id) ensures we return at most one record
            # per unique source, preventing repeated records from the same
            # source from inflating the duplicate score.
            if exclude_event_id:
                cur.execute("""
                    SELECT DISTINCT ON (source_id)
                           event_category, severity, description,
                           latitude, longitude, city,
                           event_timestamp, source_id, source_url
                    FROM events
                    WHERE event_timestamp >= %s - (%s)::interval
                    AND event_timestamp <= %s + (%s)::interval
                    AND event_id != %s
                    ORDER BY source_id, event_timestamp DESC
                    LIMIT 50
                """, (event_ts, interval_str, event_ts, interval_str, exclude_event_id))
            else:
                cur.execute("""
                    SELECT DISTINCT ON (source_id)
                           event_category, severity, description,
                           latitude, longitude, city,
                           event_timestamp, source_id, source_url
                    FROM events
                    WHERE event_timestamp >= %s - (%s)::interval
                    AND event_timestamp <= %s + (%s)::interval
                    ORDER BY source_id, event_timestamp DESC
                    LIMIT 50
                """, (event_ts, interval_str, event_ts, interval_str))

            rows = cur.fetchall()
            recent = []
            for r in rows:
                recent.append({
                    "event": {
                        "category": r[0],
                        "severity": r[1],
                        "description": r[2] or "",
                    },
                    "location": {
                        "latitude": float(r[3]) if r[3] is not None else None,
                        "longitude": float(r[4]) if r[4] is not None else None,
                        "city": r[5],
                    },
                    "timestamp": r[6].isoformat() if r[6] else None,
                    "source_id": r[7],
                    "source_url": r[8],
                })
            return recent
    except Exception as e:
        logger.debug("Recent events query failed: %s", e)
        return []


def _normalize_for_ml(event: dict) -> dict:
    """
    Normalize event dict into the nested format expected by ML functions.
    The event from Kafka has event.category, event.severity, event.description.
    ML functions expect a dict with 'event' key containing a dict.
    """
    if "event" in event and isinstance(event["event"], dict):
        return event
    # Build from flattened fields if needed
    result = dict(event)
    result["event"] = {
        "category": event.get("event_category"),
        "severity": event.get("severity"),
        "description": event.get("description"),
    }
    return result


def _compute_spatial_score(event: dict) -> float:
    """Compute spatial consistency score (reused from credibility scorer logic)."""
    loc = event.get("location") or {}
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    city = loc.get("city")
    if lat is None or lon is None:
        return 0.50
    if city is None:
        return 0.70
    # Simple check: coordinates are valid and city is provided
    return 0.80


def _compute_temporal_score(event: dict) -> float:
    """Compute temporal consistency score."""
    event_ts = _parse_timestamp(event.get("timestamp"))
    ingestion_ts = _parse_timestamp(event.get("ingestion_timestamp"))
    if not event_ts or not ingestion_ts:
        return 0.50
    lag_minutes = (ingestion_ts - event_ts).total_seconds() / 60.0
    if lag_minutes < 0:
        return 0.20
    elif lag_minutes < 30:
        return 1.0
    elif lag_minutes < 120:
        return 0.70
    elif lag_minutes < 360:
        return 0.50
    else:
        return 0.30


def _upsert_source(conn, event: dict) -> bool:
    """Upsert source record. Returns True on success."""
    source_name = event.get("source_name")
    source_type = event.get("source_type")
    source_url = event.get("source_url")

    if not source_name or not source_type:
        return False

    sql = """
        INSERT INTO sources (source_name, source_type, base_url, last_seen_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (source_name) DO UPDATE SET
            source_type = EXCLUDED.source_type,
            base_url = COALESCE(EXCLUDED.base_url, sources.base_url),
            last_seen_at = NOW()
    """
    # This is secondary/informational metadata (last-seen bookkeeping for a
    # source), not core event data. A failure here should not blow away
    # everything else already done in this transaction, so it's isolated
    # in its own SAVEPOINT rather than calling conn.rollback() (which would
    # roll back the whole in-flight batch transaction, including
    # already-upserted events, silently).
    try:
        with conn.cursor() as cur:
            cur.execute("SAVEPOINT sp_source_upsert")
            cur.execute(sql, (source_name, source_type, source_url))
            cur.execute("RELEASE SAVEPOINT sp_source_upsert")
        return True
    except Exception as e:
        logger.warning("Source upsert failed for %s: %s", source_name, e)
        try:
            with conn.cursor() as cur:
                cur.execute("ROLLBACK TO SAVEPOINT sp_source_upsert")
        except Exception:
            pass
        return False


def _parse_timestamp(ts_str: str):
    """Parse ISO 8601 timestamp string to Python datetime."""
    if not ts_str:
        return None
    try:
        ts_str = str(ts_str).strip()
        if ts_str.endswith("Z"):
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        elif "+" in ts_str[10:] or ts_str[10:].startswith("-"):
            return datetime.fromisoformat(ts_str)
        else:
            return datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


# ── Spark foreachBatch handler ──────────────────────────────────────

def _write_batch_to_postgres(batch_df: DataFrame, batch_id: int) -> None:
    """
    foreachBatch handler: consume enriched events from weather.events,
    parse, upsert source record, match/create canonical event.
    """
    if batch_df.count() == 0:
        return

    logger.info("PG Writer processing batch %d", batch_id)

    # Collect raw Kafka values; every weather.events message is the platform envelope.
    rows = batch_df.select("value").collect()

    conn = None
    success_count = 0
    fail_count = 0
    canonical_count = 0

    try:
        conn = _get_connection()
        conn.autocommit = False

        for row in rows:
            payload = row["value"]
            if not payload:
                fail_count += 1
                continue

            event = _parse_event(payload)
            if not event:
                logger.warning("Failed to parse event in batch %d, skipping", batch_id)
                fail_count += 1
                continue

            # 1. Find or create matching canonical event
            existing_ce_id, independent_sources = _find_matching_canonical_event(conn, event)

            # 2. Compute full ML enrichment with database context
            event = _compute_ml_enrichment(conn, event, existing_ce_id, independent_sources)

            # 3. Persist the cluster already assigned by Spark AI/ML.
            _persist_cluster_assignment(conn, event)

            # 4. Extract verification info
            verification = event.get("verification") or {}
            ver_status = verification.get("status", "pending")
            ver_reasons = verification.get("verification_reasons", [])

            # 5. Only a genuinely new source event increments canonical report_count.
            event_id = _safe_uuid(event.get("event_id"))
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM events WHERE event_id = %s", (event_id,))
                source_event_exists = cur.fetchone() is not None

            ce_id = _upsert_canonical_event(
                conn, event, existing_ce_id,
                verification_status=ver_status,
                verification_reasons=ver_reasons,
                increment_report_count=not source_event_exists,
            )

            if ce_id:
                canonical_count += 1
                event["canonical_event_id"] = ce_id

            # 6. Upsert source record (with computed credibility, verification)
            event_ok, inserted_new = _upsert_event(conn, event)
            if event_ok:
                success_count += 1
                _upsert_source(conn, event)
            else:
                fail_count += 1

        conn.commit()
        logger.info(
            "Batch %d committed: %d source records, %d canonical events, %d failed",
            batch_id, success_count, canonical_count, fail_count,
        )

    except Exception as e:
        logger.error("Batch %d database error: %s", batch_id, e)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ── Main pipeline ───────────────────────────────────────────────────

def build_pg_pipeline(spark: SparkSession) -> DataFrame:
    """Build the Spark Structured Streaming pipeline for PostgreSQL writes."""
    logger.info("PG Writer consuming from topic: %s", EVENTS_TOPIC)

    events_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", EVENTS_TOPIC)
        .option("startingOffsets", "earliest")
        .option(
            # MVP/demo default. For a strict national-event pipeline this
            # should be "true" plus explicit operational handling of
            # Kafka retention/offset loss, so silent data loss can never
            # happen unnoticed. Left as "false" here so a topic
            # retention hiccup pauses ingestion for that topic instead of
            # crash-looping the whole streaming job in a demo environment.
            "failOnDataLoss", "false"
        )
        .load()
    )

    # weather.events values are validated Kafka envelopes; _parse_event unwraps payload.

    pg_query = (
        events_df
        .select(F.col("value").cast("string").alias("value"))
        .writeStream
        .outputMode("append")
        .foreachBatch(_write_batch_to_postgres)
        .option("checkpointLocation", CHECKPOINT_PATH)
        .trigger(processingTime="5 seconds")
        .start()
    )

    logger.info("PG Writer streaming started with checkpoint: %s", CHECKPOINT_PATH)
    return pg_query


def main():
    logger.info("PG Writer starting")
    logger.info("Kafka bootstrap: %s", KAFKA_BOOTSTRAP)
    logger.info("Topic: %s", EVENTS_TOPIC)
    logger.info("Checkpoint: %s", CHECKPOINT_PATH)
    logger.info("Database: %s:%s/%s (user=%s)", PG_HOST, PG_PORT, PG_DB, PG_USER)

    # Wait for Kafka and PostgreSQL to be ready
    _wait_fordependencies()

    master_url = os.environ.get("SPARK_MASTER_URL", "local[*]")
    spark = (
        SparkSession.builder
        .appName("SIH26069-PGWriter")
        .master(master_url)
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    logger.info("Spark session created — version %s", spark.version)

    pg_query = build_pg_pipeline(spark)

    logger.info("PG Writer pipeline started. Awaiting termination...")
    pg_query.awaitTermination()


def _wait_fordependencies():
    """Wait for Kafka and PostgreSQL to become available."""
    import time
    import socket

    # Wait for Kafka
    logger.info("Waiting for Kafka at %s...", KAFKA_BOOTSTRAP)
    kafka_host = KAFKA_BOOTSTRAP.split(":")[0]
    kafka_port = int(KAFKA_BOOTSTRAP.split(":")[1]) if ":" in KAFKA_BOOTSTRAP else 9092
    for i in range(60):
        try:
            sock = socket.create_connection((kafka_host, kafka_port), timeout=2)
            sock.close()
            logger.info("Kafka is reachable")
            break
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(2)
    else:
        logger.warning("Kafka not ready after 120s, proceeding anyway")

    # Wait for PostgreSQL
    logger.info("Waiting for PostgreSQL at %s:%s...", PG_HOST, PG_PORT)
    for i in range(60):
        try:
            conn = _get_connection()
            conn.close()
            logger.info("PostgreSQL is ready")
            break
        except Exception:
            time.sleep(2)
    else:
        logger.warning("PostgreSQL not ready after 120s, proceeding anyway")


if __name__ == "__main__":
    main()
