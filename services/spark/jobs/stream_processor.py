"""
SIH26069 — Spark Structured Streaming Processor
Consumes raw Kafka topics, validates, cleans, normalizes,
enriches with ML, and publishes to weather.events.

Ref: 01_ARCHITECTURE.md §5.3, 02_DATA_SCHEMA.md §11, 03_KAFKA_CONTRACT.md §5
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType,
    ArrayType, MapType, BooleanType, TimestampType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spark.stream_processor")

# ── Configuration ───────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
RAW_TOPICS = os.environ.get(
    "SPARK_RAW_TOPICS", "weather.raw,citizen.raw,social.raw,government.raw"
)
PROCESSED_TOPIC = "weather.processed"
EVENTS_TOPIC = "weather.events"
CHECKPOINT_PATH = os.environ.get("SPARK_CHECKPOINT_PATH", "/data/checkpoints/spark_streaming")
WRITE_PROCESSED = os.environ.get("SPARK_WRITE_PROCESSED_TOPIC", "true").lower() == "true"

# Source of truth enums (02_DATA_SCHEMA.md §1)
VALID_SOURCE_TYPES = frozenset([
    "weather_api", "rss", "website", "social", "simulated_social",
    "government_dataset", "citizen", "synthetic",
])
VALID_CATEGORIES = frozenset([
    "rainfall", "heavy_rainfall", "flood", "thunderstorm", "lightning",
    "heatwave", "fog", "dust_storm", "strong_wind", "hailstorm", "cyclone", "other",
])
VALID_SEVERITIES = frozenset(["low", "moderate", "high", "extreme"])

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

ENVELOPE_SCHEMA = StructType([
    StructField("schema_version", StringType(), False),
    StructField("message_id", StringType(), False),
    StructField("event_type", StringType(), False),
    StructField("produced_at", StringType(), False),
    StructField("producer", StringType(), False),
    StructField("payload", StringType(), False),
])


# ── UDFs for validation / cleaning ─────────────────────────────────

@F.udf(returnType=StringType())
def normalize_timestamp_to_utc(ts_str):
    """Normalize any ISO 8601 timestamp to UTC Z format."""
    if ts_str is None:
        return None
    try:
        ts_str = str(ts_str).strip()
        if ts_str.endswith("Z"):
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        elif "+" in ts_str[10:] or ts_str[10:].startswith("-"):
            dt = datetime.fromisoformat(ts_str)
        else:
            dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return ts_str


@F.udf(returnType=FloatType())
def validate_trust_score(score):
    """Return None if trust_score is outside 0.0–1.0 (WARN rule)."""
    if score is None:
        return None
    try:
        val = float(score)
        if 0.0 <= val <= 1.0:
            return val
        return None
    except (TypeError, ValueError):
        return None


@F.udf(returnType=StringType())
def truncate_description(desc):
    """Truncate description to 2000 chars (WARN rule)."""
    if desc is None:
        return None
    s = str(desc).strip()
    if len(s) > 2000:
        return s[:2000]
    return s if s else None


@F.udf(returnType=StringType())
def validate_event_for_processing(payload_str):
    """Validate a Canonical Weather Event payload. Returns 'valid' or rejection reasons."""
    if payload_str is None:
        return "payload_is_null"
    try:
        event = json.loads(payload_str)
    except (json.JSONDecodeError, TypeError):
        return "invalid_json"

    reasons = []

    event_id = event.get("event_id")
    if not event_id or not isinstance(event_id, str):
        reasons.append("missing_event_id")
    else:
        try:
            u = uuid.UUID(event_id)
            if u.version != 4:
                reasons.append("event_id_not_v4")
        except ValueError:
            reasons.append("invalid_event_id")

    source_type = event.get("source_type")
    if not source_type or source_type not in VALID_SOURCE_TYPES:
        reasons.append("invalid_source_type")

    source_name = event.get("source_name")
    if not source_name or not str(source_name).strip():
        reasons.append("empty_source_name")

    ev = event.get("event") or {}
    category = ev.get("category")
    if not category or category not in VALID_CATEGORIES:
        reasons.append("invalid_category")

    loc = event.get("location") or {}
    country = loc.get("country")
    if not country or not str(country).strip():
        reasons.append("missing_country")

    ts = event.get("timestamp")
    if not ts:
        reasons.append("missing_timestamp")
    else:
        try:
            parsed_ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if parsed_ts.tzinfo is None:
                reasons.append("timestamp_not_timezone_aware")
        except (TypeError, ValueError):
            reasons.append("invalid_timestamp")

    ingest_ts = event.get("ingestion_timestamp")
    if not ingest_ts:
        reasons.append("missing_ingestion_timestamp")
    else:
        try:
            parsed_ingest_ts = datetime.fromisoformat(str(ingest_ts).replace("Z", "+00:00"))
            if parsed_ingest_ts.tzinfo is None:
                reasons.append("ingestion_timestamp_not_timezone_aware")
        except (TypeError, ValueError):
            reasons.append("invalid_ingestion_timestamp")

    lat = loc.get("latitude")
    lon = loc.get("longitude")
    city = loc.get("city")
    has_lat = lat is not None
    has_lon = lon is not None
    if has_lat != has_lon:
        reasons.append("unpaired_coordinates")
    if has_lat and has_lon:
        try:
            lat_f, lon_f = float(lat), float(lon)
            if not (-90.0 <= lat_f <= 90.0):
                reasons.append("latitude_out_of_range")
            if not (-180.0 <= lon_f <= 180.0):
                reasons.append("longitude_out_of_range")
        except (TypeError, ValueError):
            reasons.append("coordinates_malformed")
    if not has_lat and not has_lon and not city:
        reasons.append("no_location")

    return "valid" if not reasons else ",".join(reasons)


# ── ML Enrichment ──────────────────────────────────────────────────

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


def _rebuild_canonical(event_dict: dict) -> dict:
    """
    Rebuild the nested canonical event structure from flattened Spark columns.
    The output to weather.events must match 02_DATA_SCHEMA.md §2.
    """
    result = {
        "event_id": event_dict.get("event_id"),
        "source_id": event_dict.get("source_id"),
        "source_type": event_dict.get("source_type"),
        "source_name": event_dict.get("source_name"),
        "source_url": event_dict.get("source_url"),
        "source_trust_score": event_dict.get("source_trust_score"),
        "timestamp": event_dict.get("timestamp"),
        "ingestion_timestamp": event_dict.get("ingestion_timestamp"),
        "location": event_dict.get("location"),
        "event": {
            "category": event_dict.get("event_category"),
            "severity": event_dict.get("severity"),
            "description": event_dict.get("description"),
        },
        "social_metadata": event_dict.get("social_metadata"),
        "media": event_dict.get("media"),
        "ai": event_dict.get("ai"),
        "verification": event_dict.get("verification"),
    }
    return result


def _normalize_for_ml(event_dict: dict) -> dict:
    """
    Normalize a flattened Spark Row dict into the nested Canonical Event format
    expected by the ML functions. The cleaned DataFrame has flattened columns
    (event_category, severity, description at root) while ML expects nested
    event {category, severity, description}.
    """
    # If already has nested 'event' key, return as-is
    if "event" in event_dict and isinstance(event_dict["event"], dict):
        return event_dict

    # Build nested event from flattened columns
    ev = {
        "category": event_dict.get("event_category"),
        "severity": event_dict.get("severity"),
        "description": event_dict.get("description"),
    }

    result = dict(event_dict)
    result["event"] = ev
    return result


def _enrich_event(event_dict: dict, recent_events: list[dict] | None = None) -> dict:
    """
    Apply the canonical ML enrichment stage after Spark validation,
    event-id deduplication, and aggregation.

    Spark owns streaming concerns; service/ml owns classification,
    duplicate evidence, credibility, clustering semantics, and explainability.
    The ML pipeline never mutates the Spark row/event passed to it.
    """
    from ml.pipeline import enrich_event

    # The Spark stage already assigns/persists cluster state. Pass the current
    # cluster_id through ML and prevent the ML helper from creating a second
    # independent cluster for the same event.
    incoming_ai = event_dict.get("ai")
    incoming_ai = dict(incoming_ai) if isinstance(incoming_ai, dict) else {}

    try:
        from ml.pipeline import enrich_event
        enriched = enrich_event(
            _normalize_for_ml(event_dict),
            recent_events=recent_events or [],
            active_clusters=None,
            strict_validation=False,
            auto_create_cluster=False,
        )
    except Exception as exc:
        # DELIBERATE MVP behavior, not an oversight: a single malformed
        # record must not crash the whole streaming job and stall every
        # other event in the batch. The event still reaches weather.events
        # with conservative/absent AI fields; pg_writer's downstream
        # verification step (see pg_writer.py) then treats it as
        # low-confidence (defaults toward "needs_review", never
        # "verified") rather than silently marking it trustworthy. If a
        # hard requirement is "AI/ML is mandatory, fail the batch on ML
        # error", replace this except-and-continue with a re-raise.
        logger.exception(
            "ML enrichment failed for %s; preserving event with safe AI defaults",
            str(event_dict.get("event_id", "?"))[:8],
        )
        enriched = dict(event_dict)
        enriched["ai"] = incoming_ai

    # Preserve Spark's authoritative cluster assignment. This avoids a second
    # cluster decision inside the per-event ML helper and keeps cluster state
    # owned by the Spark micro-batch stage.
    final_ai = enriched.get("ai")
    final_ai = dict(final_ai) if isinstance(final_ai, dict) else {}
    if incoming_ai.get("cluster_id") is not None:
        final_ai["cluster_id"] = incoming_ai["cluster_id"]
    if "aggregation_count" in incoming_ai:
        final_ai["aggregation_count"] = incoming_ai["aggregation_count"]

    enriched["ai"] = final_ai
    return enriched


CLUSTER_STATE_PATH = os.environ.get("SPARK_CLUSTER_STATE_PATH", "/data/checkpoints/spark_streaming/cluster_state.json")

def _load_cluster_state() -> list[dict]:
    try:
        with open(CLUSTER_STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        return state if isinstance(state, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []

def _save_cluster_state(clusters: list[dict]) -> None:
    os.makedirs(os.path.dirname(CLUSTER_STATE_PATH), exist_ok=True)
    tmp = CLUSTER_STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clusters, f)
    os.replace(tmp, CLUSTER_STATE_PATH)


def _cluster_batch_events(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Assign spatial-temporal clusters in Spark before weather.events emission."""
    try:
        from ml.clustering.event_clusterer import assign_cluster
        active = _load_cluster_state()
        # Keep only clusters that can still accept an event under the configured window.
        cfg = __import__("ml.clustering.event_clusterer", fromlist=["get_clustering_config"]).get_clustering_config()
        now = datetime.now(timezone.utc)
        pruned = []
        for c in active:
            try:
                last = datetime.fromisoformat(str(c.get("last_event_at")).replace("Z", "+00:00"))
                if last.tzinfo is None: last = last.replace(tzinfo=timezone.utc)
                if (now - last).total_seconds() <= float(cfg["time_window_minutes"]) * 60:
                    pruned.append(c)
            except Exception:
                continue
        active = pruned
        clusters = {str(c["cluster_id"]): c for c in active if c.get("cluster_id")}
        output = []
        for event in events:
            loc, ev = event.get("location") or {}, event.get("event") or {}
            if loc.get("latitude") is None or loc.get("longitude") is None or not ev.get("category"):
                output.append(event); continue
            cluster_id = assign_cluster(event, active_clusters=active, auto_generate_on_none=True) or str(uuid.uuid4())
            cluster_id = str(uuid.UUID(str(cluster_id)))
            event.setdefault("ai", {})["cluster_id"] = cluster_id
            output.append(event)
            lat, lon, cat = float(loc["latitude"]), float(loc["longitude"]), ev["category"]
            if cluster_id not in clusters:
                clusters[cluster_id] = {"cluster_id": cluster_id, "category": cat, "centroid_lat": lat, "centroid_lon": lon, "member_count": 1, "last_event_at": event.get("timestamp")}
                active.append(clusters[cluster_id])
            else:
                c=clusters[cluster_id]; n=int(c["member_count"]); c["centroid_lat"]=(c["centroid_lat"]*n+lat)/(n+1); c["centroid_lon"]=(c["centroid_lon"]*n+lon)/(n+1); c["member_count"]=n+1; c["last_event_at"]=max(c.get("last_event_at") or event.get("timestamp"), event.get("timestamp") or c.get("last_event_at"))
        # Do not persist state yet. The caller commits this proposed state only
        # after both Kafka and Parquet sinks succeed.
        logger.info("Spark AI clustering proposed %d events into %d clusters", len(output), len(clusters))
        return output, active
    except Exception as exc:
        logger.warning("Spark AI clustering failed: %s", exc)
        return events, _load_cluster_state()


# ── Main processing pipeline ───────────────────────────────────────

def build_pipeline(spark: SparkSession) -> DataFrame:
    """Build the complete Spark Structured Streaming pipeline."""
    topics_csv = RAW_TOPICS
    raw_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", topics_csv)
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

    raw_strings = raw_df.select(
        F.col("key").cast("string").alias("key"),
        F.col("topic").alias("source_topic"),
        F.col("offset").alias("source_offset"),
        F.col("timestamp").alias("kafka_timestamp"),
        F.col("value").cast("string").alias("value"),
    )

    envelope_df = raw_strings.withColumn(
        "envelope", F.from_json("value", ENVELOPE_SCHEMA)
    )

    validated = (
        envelope_df
        .withColumn("event_type", F.col("envelope.event_type"))
        .withColumn("producer_id", F.col("envelope.producer"))
        .withColumn("payload_json", F.col("envelope.payload"))
        .withColumn(
            "validation_result",
            validate_event_for_processing(F.col("payload_json")),
        )
    )

    valid_df = validated.filter(F.col("validation_result") == "valid")
    rejected_df = validated.filter(F.col("validation_result") != "valid")

    # Dead-letter handler
    rejected_query = (
        rejected_df.writeStream
        .outputMode("append")
        .foreachBatch(_handle_rejected_batch)
        .option("checkpointLocation", CHECKPOINT_PATH + "/rejected")
        .trigger(processingTime="5 seconds")
        .start()
    )

    # Parse and clean valid events
    valid_events = (
        valid_df
        .withColumn("parsed_payload", F.from_json("payload_json", CANONICAL_SCHEMA))
    )

    cleaned = (
        valid_events
        .withColumn("event_id", F.col("parsed_payload.event_id"))
        .withColumn("source_id", F.col("parsed_payload.source_id"))
        .withColumn("source_type", F.col("parsed_payload.source_type"))
        .withColumn("source_name", F.col("parsed_payload.source_name"))
        .withColumn("source_url", F.col("parsed_payload.source_url"))
        .withColumn("source_trust_score", validate_trust_score(F.col("parsed_payload.source_trust_score")))
        .withColumn("timestamp", normalize_timestamp_to_utc(F.col("parsed_payload.timestamp")))
        .withColumn("ingestion_timestamp", normalize_timestamp_to_utc(F.col("parsed_payload.ingestion_timestamp")))
        .withColumn("location", F.col("parsed_payload.location"))
        .withColumn("event_category", F.col("parsed_payload.event.category"))
        .withColumn("severity", F.when(
            F.col("parsed_payload.event.severity").isin(list(VALID_SEVERITIES)),
            F.col("parsed_payload.event.severity"),
        ).otherwise(F.lit(None).cast("string")))
        .withColumn("description", truncate_description(F.col("parsed_payload.event.description")))
        .withColumn("social_metadata", F.col("parsed_payload.social_metadata"))
        .withColumn("media", F.col("parsed_payload.media"))
        .withColumn("ai", F.col("parsed_payload.ai"))
        .withColumn("verification", F.struct(
            F.when(
                F.col("parsed_payload.verification.status").isNull()
                | (F.length(F.trim(F.col("parsed_payload.verification.status"))) == 0),
                F.lit("pending"),
            ).otherwise(F.col("parsed_payload.verification.status")).alias("status"),
            F.col("parsed_payload.verification.verified_by").alias("verified_by"),
            F.col("parsed_payload.verification.verification_timestamp").alias("verification_timestamp"),
        ))
        .withColumn("schema_version", F.lit("1.0"))
        .withColumn("event_time", F.to_timestamp("timestamp"))
        .withWatermark("event_time", "30 minutes")
        .dropDuplicates(["event_id"])
    )

    # Build canonical event struct (shared by both outputs)
    canonical_struct = F.struct(
        "event_id", "source_id", "source_type", "source_name", "source_url",
        "source_trust_score", "timestamp", "ingestion_timestamp",
        "location",
        F.struct(
            F.col("event_category").alias("category"),
            "severity", "description",
        ).alias("event"),
        "social_metadata", "media", "ai", "verification",
    )

    # ── Write to weather.processed (optional debug topic) ──
    if WRITE_PROCESSED:
        processed_envelope = F.struct(
            F.lit("1.0").alias("schema_version"),
            F.expr("uuid()").alias("message_id"),
            F.lit("weather_event").alias("event_type"),
            F.date_format(F.current_timestamp(), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").alias("produced_at"),
            F.lit("spark").alias("producer"),
            F.to_json(canonical_struct).alias("payload"),
        )
        processed_query = (
            cleaned.select(F.col("event_id").alias("key"), F.to_json(processed_envelope).alias("value"))
            .writeStream
            .format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
            .option("topic", PROCESSED_TOPIC)
            .option("checkpointLocation", CHECKPOINT_PATH + "/processed")
            .outputMode("append")
            .trigger(processingTime="5 seconds")
            .start()
        )
        logger.info("Started weather.processed writer stream")
    else:
        processed_query = None
        logger.info("weather.processed writing is DISABLED")

    # ── ML Enrichment + Write to weather.events ──
    events_query = (
        cleaned
        .select(
            "event_id", "source_id", "source_type", "source_name", "source_url",
            "source_trust_score", "timestamp", "ingestion_timestamp",
            "location", "event_category", "severity", "description",
            "social_metadata", "media", "ai", "verification", "event_time",
        )
        .writeStream
        .outputMode("append")
        .foreachBatch(_enrich_and_write_events)
        .option("checkpointLocation", CHECKPOINT_PATH + "/events")
        .trigger(processingTime="5 seconds")
        .start()
    )
    logger.info("Started weather.events enrichment + writer stream")

    return rejected_query, processed_query, events_query


def _enrich_and_write_events(batch_df: DataFrame, batch_id: int) -> None:
    """
    foreachBatch handler: apply ML enrichment and write to weather.events.
    Per 03_KAFKA_CONTRACT.md §5.4 and 05_AI_ML_SPEC.md §2.1.
    """
    if batch_df.count() == 0:
        return

    logger.info("Enriching batch %d", batch_id)

    # Spark Structured Streaming aggregation occurs before AI/ML.
    try:
        # Use a deterministic 15-minute event-time bucket for the per-event
        # aggregation count. A sliding 15m/5m window would make one event join
        # to up to three windows and duplicate the event before Kafka output.
        bucketed = batch_df.withColumn(
            "_aggregation_bucket",
            F.window(F.col("event_time"), "15 minutes").alias("_aggregation_bucket"),
        )
        agg_df = (
            bucketed.filter(F.col("event_time").isNotNull())
            .groupBy(
                F.col("_aggregation_bucket"),
                F.col("event_category"),
                F.col("location.city").alias("city"),
            )
            .count()
        )
        batch_df = (
            bucketed.alias("e")
            .join(
                agg_df.alias("a"),
                (F.col("e._aggregation_bucket") == F.col("a._aggregation_bucket"))
                & (F.col("e.event_category") == F.col("a.event_category"))
                & (F.col("e.location.city") == F.col("a.city")),
                "left",
            )
            .select(
                "e.*",
                F.coalesce(F.col("a.count"), F.lit(1)).alias("aggregation_count"),
            )
            .drop("_aggregation_bucket")
        )
    except Exception as exc:
        logger.warning("Spark aggregation failed for batch %d: %s", batch_id, exc)
        batch_df = batch_df.withColumn("aggregation_count", F.lit(1))

    # Collect raw columns (avoids JSON double-serialization)
    rows = batch_df.select(
        "event_id", "source_id", "source_type", "source_name", "source_url",
        "source_trust_score", "timestamp", "ingestion_timestamp",
        "location", "event_category", "severity", "description",
        "social_metadata", "media", "ai", "verification", "aggregation_count",
    ).collect()

    batch_events, proposed_cluster_state = _cluster_batch_events([_row_to_dict(row) for row in rows])
    enriched_events = []
    recent_events = []

    for event_dict in batch_events:
        # Preserve the Spark aggregation result in the AI enrichment payload.
        ai_payload = event_dict.get("ai") if isinstance(event_dict.get("ai"), dict) else {}
        ai_payload["aggregation_count"] = int(event_dict.get("aggregation_count") or 1)
        event_dict["ai"] = ai_payload
        # Apply ML enrichment
        enriched = _enrich_event(event_dict, recent_events)
        # Keep the current micro-batch as duplicate-detection context for later rows.
        recent_events.append(enriched)

        # Rebuild nested canonical structure for output
        output_event = _rebuild_canonical(enriched)

        # Build Kafka envelope per 03_KAFKA_CONTRACT.md §3
        envelope = {
            "schema_version": "1.0",
            "message_id": output_event["event_id"],
            "event_type": "weather_event",
            "produced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "producer": "spark",
            "payload": json.dumps(output_event),
        }

        enriched_events.append({
            "key": output_event["event_id"],
            "value": json.dumps(envelope),
        })

    if not enriched_events:
        return

    # Write enriched events to Kafka weather.events topic
    try:
        spark_session = batch_df.sparkSession
        kafka_df = spark_session.createDataFrame(
            [(e["key"], e["value"]) for e in enriched_events],
            schema=["key", "value"],
        )

        kafka_df.write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
            .option("topic", EVENTS_TOPIC) \
            .save()

        logger.info(
            "Wrote %d enriched events to %s (batch %d)",
            len(enriched_events), EVENTS_TOPIC, batch_id,
        )

        # Historical data lake: final enriched canonical payloads partitioned by event date.
        try:
            parquet_rows = []
            for item in enriched_events:
                env = json.loads(item["value"])
                payload = json.loads(env["payload"])
                payload["_message_id"] = env["message_id"]
                parquet_rows.append(payload)

            # Clean and validate rows before creating DataFrame
            def _clean_parquet_rows(rows):
                cleaned = []
                for row in rows:
                    # Ensure required fields exist and have proper types
                    # Convert timestamps to ISO strings if they are not already
                    for ts_field in ["timestamp", "_event_ts"]:
                        if ts_field in row and not isinstance(row[ts_field], str):
                            try:
                                row[ts_field] = row[ts_field].isoformat()
                            except Exception:
                                row[ts_field] = None
                    # Cast numeric fields to float
                    for num_field in ["latitude", "longitude", "classification_confidence", "credibility_score"]:
                        if num_field in row:
                            try:
                                row[num_field] = float(row[num_field])
                            except Exception:
                                row[num_field] = None
                    cleaned.append(row)
                return cleaned

            flat_rows = []
            for item in parquet_rows:
                loc = item.get("location") if isinstance(item.get("location"), dict) else {}
                ev = item.get("event") if isinstance(item.get("event"), dict) else {}
                ai = item.get("ai") if isinstance(item.get("ai"), dict) else {}
                ver = item.get("verification") if isinstance(item.get("verification"), dict) else {}
                ts = str(item.get("timestamp") or item.get("ingestion_timestamp") or datetime.now(timezone.utc).isoformat())

                flat_rows.append({
                    "event_id": str(item.get("event_id") or ""),
                    "timestamp": ts,
                    "event_category": str(ev.get("category") or "other"),
                    "severity": str(ev.get("severity") or "moderate"),
                    "description": str(ev.get("description") or ""),
                    "latitude": float(loc["latitude"]) if loc.get("latitude") is not None else None,
                    "longitude": float(loc["longitude"]) if loc.get("longitude") is not None else None,
                    "city": str(loc.get("city") or "") if loc.get("city") else None,
                    "district": str(loc.get("district") or "") if loc.get("district") else None,
                    "state": str(loc.get("state") or "") if loc.get("state") else None,
                    "country": str(loc.get("country") or "") if loc.get("country") else None,
                    "classified_category": str(ai.get("classified_category") or ev.get("category") or "other"),
                    "classification_confidence": float(ai["classification_confidence"]) if ai.get("classification_confidence") is not None else None,
                    "credibility_score": float(ai["credibility_score"]) if ai.get("credibility_score") is not None else None,
                    "cluster_id": str(ai.get("cluster_id") or "") if ai.get("cluster_id") else None,
                    "verification_status": str(ver.get("status") or "pending"),
                })

            from pyspark.sql import types as T
            schema = T.StructType([
                T.StructField("event_id", T.StringType(), True),
                T.StructField("timestamp", T.StringType(), True),
                T.StructField("event_category", T.StringType(), True),
                T.StructField("severity", T.StringType(), True),
                T.StructField("description", T.StringType(), True),
                T.StructField("latitude", T.DoubleType(), True),
                T.StructField("longitude", T.DoubleType(), True),
                T.StructField("city", T.StringType(), True),
                T.StructField("district", T.StringType(), True),
                T.StructField("state", T.StringType(), True),
                T.StructField("country", T.StringType(), True),
                T.StructField("classified_category", T.StringType(), True),
                T.StructField("classification_confidence", T.FloatType(), True),
                T.StructField("credibility_score", T.FloatType(), True),
                T.StructField("cluster_id", T.StringType(), True),
                T.StructField("verification_status", T.StringType(), True),
            ])
            parquet_df = spark_session.createDataFrame(flat_rows, schema=schema)
            parquet_df = (parquet_df
                .withColumn("_event_ts", F.to_timestamp("timestamp"))
                .withColumn("year", F.coalesce(F.year("_event_ts"), F.lit(2026)))
                .withColumn("month", F.coalesce(F.month("_event_ts"), F.lit(9)))
                .withColumn("day", F.coalesce(F.dayofmonth("_event_ts"), F.lit(8)))
                .drop("_event_ts"))

            parquet_df.write.mode("append").partitionBy("year", "month", "day").parquet("/data/processed/weather_events")
            logger.info("Wrote %d historical events to /data/processed/weather_events (batch %d)", len(flat_rows), batch_id)
            _save_cluster_state(proposed_cluster_state)
            logger.info("Committed cluster state after Kafka + Parquet success for batch %d", batch_id)
        except Exception as exc:
            logger.error("Historical Parquet write failed for batch %d: %s", batch_id, exc)
    except Exception as e:
        logger.error("Failed to write enriched events to Kafka: %s", e, exc_info=True)
        # Do not swallow sink failures: foreachBatch must raise so Spark does
        # not commit the batch checkpoint and silently lose the events.
        raise


def _handle_rejected_batch(batch_df: DataFrame, batch_id: int) -> None:
    """Handle rejected events: write to dead-letter filesystem log."""
    if batch_df.count() == 0:
        return

    logger.warning("Processing batch %d with %d rejected events", batch_id, batch_df.count())

    rows = batch_df.select("source_topic", "validation_result", "payload_json").collect()

    dead_letter_path = "/data/logs/dead_letter"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_dir = os.path.join(dead_letter_path, today)
    os.makedirs(log_dir, exist_ok=True)

    for row in rows:
        source = row["source_topic"] or "unknown"
        reasons = row["validation_result"] or "unknown"
        original = row["payload_json"] or "{}"

        entry = {
            "failed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "source_adapter": source,
            "failure_reasons": reasons.split(","),
            "original_record": original,
        }

        filepath = os.path.join(log_dir, f"{source}_failures.jsonl")
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    logger.info("Wrote %d dead-letter entries to %s", len(rows), log_dir)


def main():
    logger.info("Spark stream processor starting")
    logger.info("Kafka bootstrap: %s", KAFKA_BOOTSTRAP)
    logger.info("Raw topics: %s", RAW_TOPICS)
    logger.info("weather.processed: %s", "ENABLED" if WRITE_PROCESSED else "DISABLED")
    logger.info("Checkpoint: %s", CHECKPOINT_PATH)

    master_url = os.environ.get("SPARK_MASTER_URL", "local[*]")
    spark = (
        SparkSession.builder
        .appName("SIH26069-StreamProcessor")
        .master(master_url)
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    logger.info("Spark session created — version %s", spark.version)

    rejected_query, processed_query, events_query = build_pipeline(spark)

    logger.info("Streaming pipeline started. Awaiting termination...")

    events_query.awaitTermination()
    if processed_query:
        processed_query.awaitTermination()
    rejected_query.awaitTermination()


if __name__ == "__main__":
    main()
