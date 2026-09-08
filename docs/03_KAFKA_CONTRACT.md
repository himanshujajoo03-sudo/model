# 03 — Kafka Contract

**Project:** SIH26069 — National Weather Big Data Analytics Platform
**Document:** `03_KAFKA_CONTRACT.md`
**Version:** 1.0
**Status:** APPROVED
**Derived from:** `01_ARCHITECTURE.md` v1.3 + `02_DATA_SCHEMA.md` v1.1
**Last updated:** 2026-09-01 — v1.0 initial Kafka contract

---

## Change Control

No topic name, message schema, key strategy, or partition count may be changed
without updating this document first and obtaining architect sign-off.

---

## 1. Kafka Infrastructure

### 1.1 Versions and Images

| Component | Image | Version |
|-----------|-------|---------|
| Kafka Broker | `confluentinc/cp-kafka` | 7.6 |
| Zookeeper | `confluentinc/cp-zookeeper` | 7.6 |
| Kafka UI | `provectuslabs/kafka-ui` | latest |

### 1.2 Broker Configuration

| Property | Value | Rationale |
|----------|-------|-----------|
| `broker.id` | `1` | Single-broker MVP |
| `listeners` | `PLAINTEXT://0.0.0.0:9092` | Internal Docker network |
| `advertised.listeners` | `PLAINTEXT://kafka:9092` | Container-internal DNS |
| `zookeeper.connect` | `zookeeper:2181` | Docker service name |
| `log.retention.hours` | `168` (7 days) | Sufficient for 5-day MVP + buffer |
| `log.segment.bytes` | `1073741824` (1 GB) | Default |
| `num.partitions` | `1` | Default; overridden per topic |
| `auto.create.topics.enable` | `false` | All topics must be pre-created |
| `message.max.bytes` | `1048576` (1 MB) | Canonical event is ~2 KB; 1 MB ceiling |

### 1.3 Host vs Internal Ports

| Service | Internal Port | Host Port | Bootstrap Server |
|---------|--------------|-----------|-----------------|
| Kafka | 9092 | 29092 | `localhost:29092` (host), `kafka:9092` (Docker) |
| Zookeeper | 2181 | 2181 | `zookeeper:2181` |
| Kafka UI | 8080 | 8080 | `http://localhost:8080` |

> **Producer/Consumer configuration inside Docker containers** MUST use
> `kafka:9092` as the bootstrap server. Only host-machine tools (kafka-ui,
> CLI debugging) use `localhost:29092`.

### 1.4 Serialization Format

- **Wire format:** JSON (UTF-8 encoded, newline-delimited)
- **Content type:** `application/json`
- **No Avro/Schema Registry** for MVP — plain JSON with schema validation
  enforced by the producer (Pydantic v2) and consumer (Spark schema)
- **Compression:** None for MVP (messages are small; compression adds complexity)

---

## 2. Topic Registry

### 2.1 All Topics

| Topic | Producer | Consumer(s) | Payload | Purpose |
|-------|----------|------------|---------|---------|
| `weather.raw` | ingestion | spark | Canonical Weather Event | Weather API, RSS, website events |
| `citizen.raw` | api | spark | Canonical Weather Event | Citizen form submissions |
| `social.raw` | ingestion | spark | Canonical Weather Event | Social / simulated feed |
| `government.raw` | ingestion | spark | Canonical Weather Event | Government dataset records |
| `weather.processed` | spark (optional) | none (debug/audit) | Canonical Weather Event | Validated + cleaned; **not consumed downstream** |
| `weather.events` | spark | postgres-writer | Enriched Canonical Weather Event | **Final events — source of truth for storage** |
| `weather.verified` | api | audit consumer | Verification Action | Human verification audit trail |

### 2.2 Per-Topic Specification

#### `weather.raw`

| Property | Value |
|----------|-------|
| Topic name | `weather.raw` |
| Producer | ingestion service (adapters: `weather_api`, `rss`, `website`) |
| Consumer | Spark Structured Streaming |
| Purpose | Ingested weather events from API, RSS, and website sources |
| Message schema | Canonical Weather Event (`02_DATA_SCHEMA.md §2`), `ai.*` all `null` |
| Key | `event_id` (UUID v4 string) |
| Partitions | `1` (MVP) |
| Replication factor | `1` (single-broker MVP) |
| Retention | 7 days (`log.retention.hours=168`) |
| Ordering requirement | Per-source adapter order preserved via key |
| Delivery semantics | At-least-once (producer retries) |

#### `citizen.raw`

| Property | Value |
|----------|-------|
| Topic name | `citizen.raw` |
| Producer | FastAPI service (`POST /citizen-reports`) |
| Consumer | Spark Structured Streaming |
| Purpose | Citizen-submitted weather reports |
| Message schema | Canonical Weather Event (`02_DATA_SCHEMA.md §2`), `ai.*` all `null`, `source_type="citizen"` |
| Key | `event_id` (UUID v4 string) |
| Partitions | `1` (MVP) |
| Replication factor | `1` |
| Retention | 7 days |
| Ordering requirement | Per-citizen submission order preserved via key |
| Delivery semantics | At-least-once |

#### `social.raw`

| Property | Value |
|----------|-------|
| Topic name | `social.raw` |
| Producer | ingestion service (adapter: `social` or `simulated_social`) |
| Consumer | Spark Structured Streaming |
| Purpose | Social media and simulated social feed events |
| Message schema | Canonical Weather Event (`02_DATA_SCHEMA.md §2`), `ai.*` all `null` |
| Key | `event_id` (UUID v4 string) |
| Partitions | `1` (MVP) |
| Replication factor | `1` |
| Retention | 7 days |
| Ordering requirement | Per-source adapter order preserved via key |
| Delivery semantics | At-least-once |

#### `government.raw`

| Property | Value |
|----------|-------|
| Topic name | `government.raw` |
| Producer | ingestion service (adapter: `government_dataset`) |
| Consumer | Spark Structured Streaming |
| Purpose | Batch-loaded government/public dataset records |
| Message schema | Canonical Weather Event (`02_DATA_SCHEMA.md §2`), `ai.*` all `null` |
| Key | `event_id` (UUID v4 string) |
| Partitions | `1` (MVP) |
| Replication factor | `1` |
| Retention | 7 days |
| Ordering requirement | No ordering requirement; batch load |
| Delivery semantics | At-least-once |

#### `weather.processed`

| Property | Value |
|----------|-------|
| Topic name | `weather.processed` |
| Producer | Spark Structured Streaming (**optional, behind `SPARK_WRITE_PROCESSED_TOPIC` flag**) |
| Consumer | None (debug/monitoring only) |
| Purpose | Intermediate validated + cleaned events for debugging and audit |
| Message schema | Canonical Weather Event (`02_DATA_SCHEMA.md §2`), `ai.*` all `null`, timestamps normalised to UTC |
| Key | `event_id` (UUID v4 string) |
| Partitions | `1` (MVP) |
| Replication factor | `1` |
| Retention | 24 hours (short-lived debug topic) |
| Ordering requirement | None |
| Delivery semantics | At-least-once |

> **IMPORTANT:** This topic is **not consumed by any downstream service**.
> The PostgreSQL writer MUST NOT read from `weather.processed`.
> Set `SPARK_WRITE_PROCESSED_TOPIC=false` to disable writing to this topic entirely.

#### `weather.events`

| Property | Value |
|----------|-------|
| Topic name | `weather.events` |
| Producer | Spark Structured Streaming (via `foreachBatch`) |
| Consumer | PostgreSQL writer (separate Spark/Python consumer) |
| Purpose | **Final enriched events — sole source of truth for database storage** |
| Message schema | Enriched Canonical Weather Event (`02_DATA_SCHEMA.md §2`), `ai.*` fully populated by ML modules |
| Key | `event_id` (UUID v4 string) |
| Partitions | `1` (MVP) |
| Replication factor | `1` |
| Retention | 7 days (supports replay-to-rebuild) |
| Ordering requirement | Per-event ordering preserved via key; batch-level ordering sufficient |
| Delivery semantics | At-least-once (PostgreSQL writer uses idempotent upsert) |

#### `weather.verified`

| Property | Value |
|----------|-------|
| Topic name | `weather.verified` |
| Producer | FastAPI service (`POST /verification` admin action) |
| Consumer | Audit consumer (future; optional for MVP) |
| Purpose | Human verification audit trail |
| Message schema | Verification Action (see §6 of this document) — **NOT a full Canonical Weather Event** |
| Key | `event_id` (UUID v4 string of the event being verified) |
| Partitions | `1` (MVP) |
| Replication factor | `1` |
| Retention | 30 days (audit trail) |
| Ordering requirement | Per-event verification order preserved via key |
| Delivery semantics | At-least-once |

### 2.3 Topic Creation Commands

Topics MUST be pre-created before any producer or consumer starts.

```bash
# Raw topics (all identical config)
kafka-topics --bootstrap-server kafka:9092 --create --topic weather.raw      --partitions 1 --replication-factor 1
kafka-topics --bootstrap-server kafka:9092 --create --topic citizen.raw      --partitions 1 --replication-factor 1
kafka-topics --bootstrap-server kafka:9092 --create --topic social.raw      --partitions 1 --replication-factor 1
kafka-topics --bootstrap-server kafka:9092 --create --topic government.raw  --partitions 1 --replication-factor 1

# Processed topic (optional, debug)
kafka-topics --bootstrap-server kafka:9092 --create --topic weather.processed --partitions 1 --replication-factor 1

# Final enriched topic
kafka-topics --bootstrap-server kafka:9092 --create --topic weather.events  --partitions 1 --replication-factor 1

# Verification audit topic
kafka-topics --bootstrap-server kafka:9092 --create --topic weather.verified --partitions 1 --replication-factor 1
```

Alternatively, topics can be auto-created via a Docker entrypoint script
that waits for Kafka to be ready and runs these commands. The `auto.create.topics.enable`
broker setting remains `false` to prevent accidental topic creation.

---

## 3. Message Envelope

All messages across all topics share a **consistent envelope** wrapping the payload.

### 3.1 Envelope Structure

```json
{
  "schema_version": "1.0",
  "message_id": "<uuid-v4>",
  "event_type": "<string>",
  "produced_at": "<ISO 8601 UTC>",
  "producer": "<string>",
  "payload": {}
}
```

### 3.2 Envelope Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | YES | Schema version of the payload. Format: `"major.minor"` |
| `message_id` | UUID v4 | YES | Unique identifier for this Kafka message (distinct from `event_id` inside the payload) |
| `event_type` | string enum | YES | Identifies the payload structure. See §3.3 |
| `produced_at` | ISO 8601 UTC | YES | Time the message was produced to Kafka |
| `producer` | string | YES | Identifier of the producing service |
| `payload` | object | YES | The actual data. Structure depends on `event_type` |

### 3.3 Event Types

| `event_type` value | Topic(s) | Payload Structure |
|--------------------|----------|--------------------|
| `weather_event` | `weather.raw`, `citizen.raw`, `social.raw`, `government.raw`, `weather.processed`, `weather.events` | **Canonical Weather Event** (`02_DATA_SCHEMA.md §2`) |
| `verification_action` | `weather.verified` | **Verification Action** (see §6) |

### 3.4 Envelope Rules

1. The envelope wraps **every** message on **every** topic.
2. `message_id` is generated by the producer using `uuid.uuid4()`. It is
   distinct from `event_id` (which identifies the weather event, not the message).
3. `schema_version` tracks payload evolution. See §13 for versioning rules.
4. `producer` values: `"ingestion"`, `"api"`, `"spark"`.
5. `produced_at` is set at the moment `KafkaProducer.send()` is called.
6. The `payload` field contains the **complete** Canonical Weather Event for
   event topics, or the Verification Action for `weather.verified`.

### 3.5 Full Envelope Example (Raw Event)

```json
{
  "schema_version": "1.0",
  "message_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "event_type": "weather_event",
  "produced_at": "2026-08-31T08:16:03.441Z",
  "producer": "ingestion",
  "payload": {
    "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "source_id": "rss_ndtv_weather_20260831_item_0042",
    "source_type": "rss",
    "source_name": "NDTV Weather RSS",
    "source_url": "https://feeds.ndtv.com/ndtv/weather",
    "source_trust_score": null,
    "timestamp": "2026-08-31T08:15:00.000Z",
    "ingestion_timestamp": "2026-08-31T08:16:03.441Z",
    "location": {
      "latitude": 19.076,
      "longitude": 72.8777,
      "city": "Mumbai",
      "district": "Mumbai City",
      "state": "Maharashtra",
      "country": "India"
    },
    "event": {
      "category": "heavy_rainfall",
      "severity": "high",
      "description": "Heavy rainfall has caused waterlogging in several low-lying areas."
    },
    "social_metadata": {
      "hashtags": ["#HeavyRain", "#Mumbai"],
      "author_id": null,
      "platform": null
    },
    "media": { "photos": [], "videos": [] },
    "ai": {
      "classified_category": null,
      "classification_confidence": null,
      "duplicate_score": null,
      "credibility_score": null,
      "credibility_reasons": [],
      "cluster_id": null
    },
    "verification": {
      "status": "pending",
      "verified_by": null,
      "verification_timestamp": null
    }
  }
}
```

---

## 4. Canonical Event Contract (Raw Topics)

The payload for `weather.raw`, `citizen.raw`, `social.raw`, and `government.raw`
MUST be an **exact Canonical Weather Event** as defined in `02_DATA_SCHEMA.md §2`.

### 4.1 Required Fields at Ingestion

The producer MUST populate these fields before sending:

| Field | Source | Requirement |
|-------|--------|-------------|
| `event_id` | `uuid.uuid4()` | Generate fresh UUID v4 |
| `source_id` | Adapter-assigned | Per `02_DATA_SCHEMA.md §5` conventions |
| `source_type` | Adapter-fixed | Must match §1.1 enum exactly |
| `source_name` | Adapter-fixed | Human-readable source name |
| `timestamp` | Source data | ISO 8601 UTC; normalised from source timezone |
| `ingestion_timestamp` | `datetime.now(timezone.utc)` | Set at adapter execution time |
| `location.country` | Default `"India"` or extracted | Non-null |
| `event.category` | Extracted/inferred | Must match §1.2 enum |

### 4.2 AI Fields at Ingestion

All `ai.*` fields MUST be `null` (or empty array for `ai.credibility_reasons`).
AI enrichment happens exclusively in Spark/ML — never at the adapter level.

```json
"ai": {
  "classified_category": null,
  "classification_confidence": null,
  "duplicate_score": null,
  "credibility_score": null,
  "credibility_reasons": [],
  "cluster_id": null
}
```

### 4.3 Verification Fields at Ingestion

`verification.status` MUST be `"pending"`.
`verification.verified_by` and `verification.verification_timestamp` MUST be `null`.

### 4.4 Per-Topic Differences

| Aspect | `weather.raw` | `citizen.raw` | `social.raw` | `government.raw` |
|--------|--------------|---------------|-------------|-----------------|
| `source_type` | `weather_api`, `rss`, or `website` | `citizen` | `social` or `simulated_social` | `government_dataset` |
| `source_name` | Adapter-specific | `"citizen_form"` | Platform name | Dataset filename |
| `social_metadata` | Hashtags empty; platform null | Hashtags from form; platform null | Populated from social source | Hashtags empty; platform null |
| `media.photos` | Usually empty | May contain uploaded URLs | May contain media URLs | Empty |
| `source_url` | API endpoint / feed URL / page URL | React app URL | Post URL | File path |

### 4.5 Synthetic Data

Records with `source_type="synthetic"` follow the identical Canonical Weather Event
structure. The `source_name` field MUST contain the substring `"synthetic"`.
Synthetic records can be produced to `weather.raw` (tagged) or loaded directly
into the Parquet data lake.

---

## 5. Processed Event Contract

### 5.1 What Changes: Raw → Processed → Events

| Stage | Topic | Changes Applied |
|-------|-------|----------------|
| **Ingestion** | `weather.raw`, `citizen.raw`, `social.raw`, `government.raw` | Canonical event with `ai.*` all null |
| **Spark validation + cleaning** | `weather.processed` (optional) | Validation pass; timestamps normalised to UTC; nulls handled; description truncated; invalid enums nullified |
| **ML enrichment + publication** | `weather.events` | `ai.*` fully populated; `verification.status` unchanged; all other fields preserved |

### 5.2 Spark Validation Transformations

After Spark validation (per `02_DATA_SCHEMA.md §11`), the following transformations
are applied before the record is eligible for `weather.processed` or `weather.events`:

| Field | Transformation | Rationale |
|-------|---------------|-----------|
| `timestamp` | Normalised to UTC string format `YYYY-MM-DDTHH:MM:SS.sssZ` | Consistency across sources |
| `ingestion_timestamp` | Normalised to UTC string format | Consistency |
| `event.description` | Truncated to 2000 chars if exceeding limit | WARN rule |
| `source_trust_score` | Set to `null` if outside 0.0–1.0 | WARN rule |
| `event.severity` | Set to `null` if not in §1.3 enum | WARN rule |
| `verification.status` | Set to `"pending"` if absent | AUTO-FIX rule |
| `source_type = synthetic` | Warning logged if `source_name` does not contain `"synthetic"` | WARN rule |
| `source_type = simulated_social` | Warning logged if `platform ≠ "simulated"` | WARN rule |

### 5.3 What is NOT Changed

- `event_id` is never modified
- `source_id`, `source_type`, `source_name` are preserved as-is
- `location.*` fields are preserved (not geocoded, not modified)
- `social_metadata.*`, `media.*` are preserved
- `verification.*` is preserved (status remains `"pending"`)
- `ai.*` remains `null` in `weather.processed`
- Nested JSON structure is preserved (flattening only happens at PostgreSQL write)

### 5.4 ML Enrichment (Weather Events)

After Spark validation, ML modules populate the `ai.*` block:

| `ai` Field | ML Function | Value |
|------------|------------|-------|
| `ai.classified_category` | `classify_event()` | ML-assigned category (may differ from adapter `event.category`) |
| `ai.classification_confidence` | `classify_event()` | Confidence 0.0–1.0 |
| `ai.duplicate_score` | `compute_duplicate_score()` | 0.0 (unique) to 1.0 (certain duplicate) |
| `ai.credibility_score` | `score_credibility()` | 0.0 (low) to 1.0 (high) |
| `ai.credibility_reasons` | `generate_reasons()` | Human-readable string list |
| `ai.cluster_id` | `assign_cluster()` | UUID of assigned cluster, or `null` |

All other fields remain unchanged from the validated input.

---

## 6. Verification Contract

### 6.1 Message Structure

The `weather.verified` topic carries a **Verification Action** — a small,
focused message, NOT a full Canonical Weather Event.

```json
{
  "schema_version": "1.0",
  "message_id": "<uuid-v4>",
  "event_type": "verification_action",
  "produced_at": "2026-08-31T14:30:00.000Z",
  "producer": "api",
  "payload": {
    "event_id": "<uuid-v4>",
    "action": "<string>",
    "performed_by": "<string>",
    "notes": "<string | null>",
    "previous_status": "<verification_status enum>",
    "new_status": "<verification_status enum>",
    "performed_at": "2026-08-31T14:30:00.000Z"
  }
}
```

### 6.2 Verification Action Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | UUID v4 | YES | The event being verified |
| `action` | enum | YES | See §6.3 |
| `performed_by` | string | YES | Admin username |
| `notes` | string | NO | Optional admin notes |
| `previous_status` | enum | YES | Verification status before this action |
| `new_status` | enum | YES | Verification status after this action |
| `performed_at` | ISO 8601 UTC | YES | Time of admin action |

### 6.3 Verification Actions

| `action` Value | `new_status` | Description |
|----------------|-------------|-------------|
| `"verified"` | `"verified"` | Admin confirms event is genuine |
| `"rejected"` | `"pending"` (or flagged) | Admin rejects event; event returned to pending or flagged |
| `"marked_suspicious"` | `"suspicious"` | Admin flags event as suspicious |
| `"marked_duplicate"` | `"duplicate"` | Admin identifies event as duplicate |

### 6.4 Relationship to PostgreSQL

When `POST /verification` is called:
1. FastAPI updates `events.verification_status`, `events.verified_by`,
   `events.verification_timestamp` in PostgreSQL
2. FastAPI inserts a row into `verification_log` (with `action`, `performed_by`,
   `notes`, `performed_at`)
3. FastAPI produces a `verification_action` message to `weather.verified`

The `weather.verified` message is an **audit trail** — it is NOT consumed by
the PostgreSQL writer. The database is updated directly by the API service
before the Kafka message is produced.

---

## 7. Kafka Keys

### 7.1 Key Strategy

| Topic | Key | Rationale |
|-------|-----|-----------|
| `weather.raw` | `event_id` | Ensures all messages for the same event land on the same partition. With 1 partition this is moot, but prepares for scaling. |
| `citizen.raw` | `event_id` | Same as above |
| `social.raw` | `event_id` | Same as above |
| `government.raw` | `event_id` | Same as above |
| `weather.processed` | `event_id` | Preserves key from input |
| `weather.events` | `event_id` | Ensures PostgreSQL writer processes the same event on the same consumer instance. Critical for idempotent upsert. |
| `weather.verified` | `event_id` | Ensures all verification actions for the same event are ordered correctly |

### 7.2 Key Implementation

```python
# Producer side
producer.send(
    topic="weather.raw",
    key=event["event_id"].encode("utf-8"),   # Kafka key is bytes
    value=json.dumps(envelope).encode("utf-8")
)
```

- Keys are UTF-8 encoded strings (UUID v4 format).
- With `1` partition, key-based routing has no effect but the practice is
  correct for future scaling to multiple partitions.
- The PostgreSQL writer can rely on all updates for a given `event_id` arriving
  at the same partition in order (when partitions are increased).

---

## 8. Partitioning

### 8.1 MVP Partition Counts

| Topic | Partitions | Rationale |
|-------|-----------|-----------|
| `weather.raw` | `1` | Single-machine; low volume; no parallelism needed |
| `citizen.raw` | `1` | Low volume |
| `social.raw` | `1` | Low volume |
| `government.raw` | `1` | Batch load; order doesn't matter |
| `weather.processed` | `1` | Debug only |
| `weather.events` | `1` | Single PostgreSQL writer consumer |
| `weather.verified` | `1` | Low volume; ordered per event |

### 8.2 Scaling Notes (Post-MVP)

If the MVP exceeds 10,000 events/day or requires parallel processing:
- Increase `weather.raw` to `3` partitions (match 3 MVP cities)
- Increase `weather.events` to `3` partitions
- Adjust consumer group parallelism accordingly

> For the 5-day hackathon MVP, `1` partition per topic is sufficient and
> simplifies debugging.

---

## 9. Consumer Groups

### 9.1 Consumer Group Definitions

| Consumer Group ID | Consumes Topic(s) | Service | Notes |
|-------------------|-------------------|---------|-------|
| `spark-processing` | `weather.raw`, `citizen.raw`, `social.raw`, `government.raw` | Spark Structured Streaming | Single streaming job consuming all raw topics via `selectExpr` or union |
| `postgres-writer` | `weather.events` | PostgreSQL writer (separate consumer) | Idempotent upsert to PostgreSQL |
| `monitoring-debug` | `weather.processed` | Manual debugging / log consumer | Optional; no automated consumer in MVP |
| `audit-consumer` | `weather.verified` | Future audit service | Optional for MVP; messages retained for 30 days |

### 9.2 Consumer Group Rules

1. **`spark-processing`** — One consumer per topic-partition. With 1 partition per
   topic, there is exactly 1 Spark executor reading each topic. The Spark
   structured streaming checkpoint ensures exactly-once processing semantics
   at the Spark level (with at-least-once Kafka delivery).

2. **`postgres-writer`** — Single consumer reading `weather.events`. Uses
   idempotent PostgreSQL `INSERT ... ON CONFLICT (event_id) DO UPDATE` to
   handle duplicate messages.

3. **Independent consumption** — `spark-processing` and `postgres-writer` are
   in different consumer groups, so they can independently consume the same
   topic if needed. However, `postgres-writer` only reads `weather.events`,
   and `spark-processing` only reads raw topics.

4. **No shared consumer groups** — Each service has a unique consumer group ID.
   Two instances of the same service (e.g., during scaling) automatically
   rebalance within their group.

---

## 10. Delivery Semantics

### 10.1 Overall Guarantee: At-Least-Once

The system provides **at-least-once delivery** at the Kafka level, with
**idempotent processing** at the consumer level to prevent duplicate persistence.

### 10.2 Duplicate Message Handling

| Scenario | Behavior |
|----------|----------|
| **Kafka retries message** | PostgreSQL writer uses `INSERT ... ON CONFLICT (event_id) DO UPDATE`; duplicate is harmless |
| **Spark reprocesses micro-batch** | Spark checkpoint tracks consumed offsets; duplicate processing prevented by checkpoint recovery |
| **Producer retries** | Producer uses `acks=all`; Kafka deduplicates at partition level via producer ID (Confluent 7.x) |

### 10.3 Consumer Restart

| Component | Recovery Mechanism |
|-----------|-------------------|
| Spark Structured Streaming | Checkpoint stored at `/data/checkpoints/spark_streaming/`. On restart, resumes from last committed offset. |
| PostgreSQL writer | Checkpoint stored at `/data/checkpoints/pg_writer/`. On restart, resumes from last committed offset. Idempotent writes prevent duplicates. |

### 10.4 Producer Retry

| Scenario | Behavior |
|----------|----------|
| Kafka broker temporarily unavailable | Producer retries with exponential backoff (configured in Kafka producer: `retry.backoff.ms=1000`, `retries=Integer.MAX_VALUE`) |
| Message too large | Reject and log error (Canonical event is ~2 KB; limit is 1 MB) |
| Serialization failure | Reject and log error; record sent to dead-letter filesystem |

### 10.5 Spark Checkpoint Recovery

Spark Structured Streaming maintains checkpoints that track:
- Kafka topic offsets consumed
- Micro-batch IDs processed
- State for window-based operations

On failure:
1. Spark driver restarts
2. Reads checkpoint to determine last committed offset per topic
3. Resumes consuming from that offset
4. Re-processes any micro-batches that were in-flight at failure time
5. `foreachBatch` writes are idempotent (PostgreSQL upsert)

Checkpoint path: `/data/checkpoints/spark_streaming/`

### 10.6 PostgreSQL Writer Failure

If the PostgreSQL writer cannot write:
1. The consumer retries the message (Kafka consumer polls again)
2. If PostgreSQL is temporarily unavailable, the consumer's poll loop blocks
   until the connection is restored
3. No messages are lost; they remain in the Kafka topic
4. Once PostgreSQL recovers, the writer resumes from the last committed offset

### 10.7 Kafka Broker Restart

1. Kafka restarts and recovers partition data from disk
2. Producers reconnect and resume producing
3. Consumers reconnect and resume consuming from last committed offset
4. In-flight messages may be replayed (at-least-once); idempotent processing
   prevents duplicate effects

---

## 11. Dead-Letter Handling

### 11.1 Decision: Filesystem Only for MVP

Per `01_ARCHITECTURE.md §10`, dead-letter records are written **exclusively
to the filesystem**. A Kafka DLQ topic is NOT used in the MVP.

### 11.2 Failure Categories

| Failure Type | Where Detected | Behavior |
|-------------|---------------|----------|
| **Malformed JSON** (cannot parse envelope) | Spark consumer | REJECT → dead-letter filesystem |
| **Unknown `schema_version`** | Spark consumer | REJECT → dead-letter filesystem |
| **Unknown `event_type`** | Spark consumer | REJECT → dead-letter filesystem |
| **Validation failure** (REJECT-level rule per `02_DATA_SCHEMA.md §11`) | Spark validation | REJECT → dead-letter filesystem |
| **Processing failure** (ML exception) | Spark foreachBatch | REJECT → dead-letter filesystem; event skipped for this batch; may be retried on next micro-batch if Spark retries |
| **Serialization failure** (producer side) | Ingestion / API | REJECT → application log; message never sent to Kafka |

### 11.3 Dead-Letter File Format

**Path:**
```
/data/logs/dead_letter/YYYY-MM-DD/<source_type>_failures.jsonl
```

One file per `source_type` per calendar day (UTC). Each line is a JSON object:

```json
{
  "failed_at": "2026-08-31T08:16:05.123Z",
  "source_adapter": "ingestion",
  "failure_reasons": [
    "Invalid UUID v4 in event_id: 'not-a-uuid'",
    "source_type 'twitter_scrape' not in enum"
  ],
  "original_record": {
    "schema_version": "1.0",
    "message_id": "...",
    "event_type": "weather_event",
    "produced_at": "...",
    "producer": "ingestion",
    "payload": { "..." }
  }
}
```

### 11.4 Dead-Letter Rules

1. Every rejected record is logged with **all** failure reasons (not just the first).
2. `original_record` is the **complete envelope** (including envelope fields).
3. Dead-letter files are newline-delimited JSON (`.jsonl`).
4. Files are created on first write and appended to throughout the day.
5. No rotation beyond daily file boundaries.
6. Dead-letter files are **never deleted automatically** during the MVP.

### 11.5 Retry Policy for Processing Failures

| Scenario | Retry | Rationale |
|----------|-------|-----------|
| Validation REJECT | No retry | Data is invalid; cannot be fixed by retrying |
| ML function exception | No retry within batch; event may be reprocessed in next micro-batch if Spark retries the batch | ML exceptions indicate code/data bugs, not transient failures |
| Transient Spark failure | Spark checkpoint recovery replays the micro-batch | Automatic |

### 11.6 Future: Kafka DLQ Topic

If operational replay of failed records becomes a requirement post-MVP,
a `weather.dead_letter` topic will be added with:
- Same envelope structure
- `event_type: "dead_letter_event"`
- `payload` containing the original envelope + failure reasons
- Retention: 30 days

---

## 12. Schema Evolution

### 12.1 Schema Versioning

The `schema_version` field in the message envelope tracks payload evolution.

Format: `"major.minor"`

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| New optional field added | Minor bump | `1.0` → `1.1` |
| Field removed or renamed | Major bump | `1.1` → `2.0` |
| Enum value added | Minor bump | `1.0` → `1.1` |
| Enum value removed | Major bump | `1.1` → `2.0` |
| Structural change (object nesting) | Major bump | `1.x` → `2.0` |

### 12.2 Backward Compatibility Rules

1. **Minor version changes** (1.0 → 1.1): Consumers MUST tolerate missing
   optional fields (treat as `null`). Producers MUST NOT remove fields.
2. **Major version changes** (1.x → 2.0): Breaking. Both producers and
   consumers must be updated simultaneously. Requires architect approval.
3. **Consumers MUST check `schema_version`** before parsing `payload`.
   Unknown major versions cause REJECT → dead-letter.
4. **Unknown minor versions** within a known major are tolerated (forward-compatible).

### 12.3 Adding a Field

1. Add the field to `02_DATA_SCHEMA.md` with a default value (`null` for optional).
2. Bump `schema_version` minor.
3. Update producer to populate the field.
4. Existing consumers will see `null` until they update — this is safe.

### 12.4 Changing an Enum

1. Adding a new enum value (e.g., new `event_category`): minor bump. Consumers
   must tolerate unknown values (store as string or `other`).
2. Removing an enum value: major bump. All producers must stop emitting the
   value before consumers stop tolerating it.

### 12.5 Change Control

Per `02_DATA_SCHEMA.md Change Control`:
- No field, type, or enum may be changed without updating the schema document
  and obtaining architect sign-off.
- This Kafka contract must be updated simultaneously to reflect any
  payload schema changes.

---

## 13. Security

### 13.1 Credentials and Secrets

- Kafka bootstrap servers are configured via environment variables, NOT
  hardcoded in application code.
- No SASL/SSL for MVP (internal Docker network only).
- `.env` file contains:
  ```
  KAFKA_BOOTSTRAP_SERVERS=kafka:9092
  ```
- `.env` is gitignored; `.env.example` is committed without values.

### 13.2 Message-Level Security

- **No secrets inside Kafka messages.** The Canonical Weather Event contains
  no API keys, passwords, or tokens.
- `source_url` may contain public URLs only.
- `author_id` in `social_metadata` is an anonymised identifier, not PII.

### 13.3 PII Restrictions

- Citizen reports contain **no personal identifying information** beyond what
  is strictly necessary for the weather event (location coordinates, description).
- No names, email addresses, phone numbers, or IP addresses are stored in
  the Canonical Weather Event.
- `source_trust_score` is a numeric value derived from source-level reputation,
  not individual user tracking.

### 13.4 Media Handling

- `media.photos` and `media.videos` contain URLs to stored media files.
- Media files are validated for type and size before storage (FastAPI endpoint).
- No raw binary data flows through Kafka.

---

## 14. Docker Configuration

### 14.1 Service Environment Variables

#### `zookeeper`

```yaml
zookeeper:
  image: confluentinc/cp-zookeeper:7.6
  environment:
    ZOOKEEPER_CLIENT_PORT: 2181
    ZOOKEEPER_TICK_TIME: 2000
  ports:
    - "2181:2181"
```

> **Note:** The docker-compose snippets below are **illustrative excerpts**.
> The authoritative, complete `docker-compose.yml` is defined in
> `07_DOCKER_DEPLOYMENT_SPEC.md §3`.

#### `kafka`

```yaml
kafka:
  image: confluentinc/cp-kafka:7.6
  depends_on:
    - zookeeper
  environment:
    KAFKA_BROKER_ID: 1
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
    KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    KAFKA_MESSAGE_MAX_BYTES: 1048576
    KAFKA_LOG_RETENTION_HOURS: 168
  ports:
    - "9092:9092"
    - "29092:29092"
```

> **Note:** `KAFKA_ADVERTISED_LISTENERS` uses `kafka:9092` for inter-container
> communication. Host-machine access uses `localhost:29092` (mapped via ports).

#### `kafka-ui`

```yaml
kafka-ui:
  image: provectuslabs/kafka-ui:latest
  depends_on:
    - kafka
  environment:
    KAFKA_CLUSTERS_0_NAME: weather-platform
    KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
    KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
  ports:
    - "8080:8080"
```

#### `ingestion`

```yaml
ingestion:
  build: ./services/ingestion
  depends_on:
    - kafka
  environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:9092
  # No ports — background producer only
```

#### `api`

```yaml
api:
  build: ./services/api
  depends_on:
    - kafka
    - postgres
  environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    DATABASE_URL: postgresql://weather:${POSTGRES_PASSWORD}@postgres:5432/weatherdb
  ports:
    - "8000:8000"
```

#### `spark-master` and `spark-worker`

```yaml
spark-master:
  image: bitnami/spark:3.5
  environment:
    SPARK_MODE: master
  ports:
    - "7077:7077"
    - "8081:8081"

spark-worker:
  image: bitnami/spark:3.5
  depends_on:
    - spark-master
  environment:
    SPARK_MODE: worker
    SPARK_MASTER_URL: spark://spark-master:7077
  ports:
    - "8082:8082"
```

> Spark **infrastructure** config (master URL, worker memory) is set via Docker
> environment variables. Spark **application** config (Kafka bootstrap, checkpoint
> path, topic names, ML classifier backend) is passed via Spark submit parameters
> or application config file.

### 14.2 Kafka Connectivity Summary

| Service | Connects To | Bootstrap Server | Protocol |
|---------|------------|-----------------|----------|
| ingestion | Kafka | `kafka:9092` | PLAINTEXT |
| api | Kafka | `kafka:9092` | PLAINTEXT |
| spark (streaming) | Kafka | `kafka:9092` | PLAINTEXT |
| spark (pg-writer) | Kafka | `kafka:9092` | PLAINTEXT |
| kafka-ui | Kafka | `kafka:9092` | PLAINTEXT |

All internal Docker communication uses the `kafka` service hostname.
No service connects via `localhost`.

---

## 15. End-to-End Message Flow

### 15.1 Primary Flow: Ingestion → Storage

```
Source Adapter (weather_api / rss / website / social / government)
    │
    │  Constructs Canonical Weather Event (ai.* = null)
    │  Wraps in envelope (schema_version, message_id, event_type, produced_at, producer)
    │
    ▼
Kafka: weather.raw / social.raw / government.raw
    │
    │  Spark Structured Streaming consumes all raw topics
    │
    ▼
Spark: Validation + Cleaning (per 02_DATA_SCHEMA.md §11)
    │
    ├── Validation PASS ────────────────────────────────────────────┐
    │   • Timestamps normalised to UTC                              │
    │   • Description truncated if > 2000 chars                     │
    │   • Invalid enums nullified                                   │
    │   • WARN rules applied                                       │
    │                                                               │
    │  [Optional] ──► Kafka: weather.processed (debug/audit only)   │
    │                                                               │
    ▼                                                               │
ML Enrichment (within foreachBatch)                                 │
    │  • classify_event()     → ai.classified_category              │
    │  • score_credibility()  → ai.credibility_score + reasons      │
    │  • generate_reasons()   → ai.credibility_reasons              │
    │  • compute_duplicate_score() → ai.duplicate_score             │
    │  • assign_cluster()     → ai.cluster_id                       │
    │                                                               │
    ▼                                                               │
Kafka: weather.events (ai.* fully populated)                        │
    │                                                               │
    │  PostgreSQL writer consumes weather.events                    │
    ▼                                                               │
PostgreSQL Writer                                                   │
    │  • Flattens nested JSON → flat DB columns                     │
    │  • INSERT ... ON CONFLICT (event_id) DO UPDATE                │
    │  • Upserts to events, event_clusters, sources                 │
    │  • sync_geom trigger auto-populates geom                      │
    ▼                                                               │
PostgreSQL/PostGIS                                                  │
    │                                                               │
    ▼                                                               │
FastAPI: GET /events → React Dashboard                              │
```

### 15.2 Citizen Report Flow

```
Citizen
    │
    │  Fills React form (frontend :5173)
    ▼
React Form → POST /citizen-reports (api :8000)
    │
    │  FastAPI Pydantic validation
    │  Constructs Canonical Weather Event:
    │    source_type = "citizen"
    │    source_name = "citizen_form"
    │    verification.status = "pending"
    │    ai.* = all null
    │  Wraps in envelope
    ▼
Kafka: citizen.raw
    │
    ▼
Spark: Validation + ML Enrichment
    │  (same pipeline as §15.1)
    ▼
Kafka: weather.events
    │
    ▼
PostgreSQL Writer → PostgreSQL/PostGIS
    │
    ▼
GET /events (FastAPI) → Dashboard (target: ~5 seconds end-to-end)
```

### 15.3 Verification Flow

```
Admin (via React Admin Panel)
    │
    │  Selects action: verify / reject / flag / mark duplicate
    ▼
POST /verification (api :8000)
    │
    ├──► PostgreSQL: UPDATE events SET verification_status = ...
    │    PostgreSQL: INSERT INTO verification_log (...)
    │
    └──► Kafka: weather.verified (verification_action payload)
         │
         ▼
    Audit consumer (optional; retains trail for 30 days)
```

---

## 16. Failure Scenarios

| Failure | Affected Component | Expected Behavior | Recovery |
|---------|-------------------|-------------------|----------|
| **Kafka broker unavailable** | All producers | Producer retries with exponential backoff (`retry.backoff.ms=1000`). Messages buffered in producer. | Automatic when broker recovers. |
| **Kafka broker unavailable** | All consumers | Consumer poll loop blocks. No offset committed. | Automatic when broker recovers; resumes from last committed offset. |
| **Producer failure** (ingestion crash) | Ingestion | In-flight messages may be lost if not yet sent. Successfully sent messages are preserved in Kafka. | Restart ingestion; it resumes producing from source. |
| **Producer failure** (API crash) | API | Citizen report lost if POST not yet completed. Already-produced messages preserved. | Citizen re-submits form. |
| **Invalid event** (validation REJECT) | Spark | Record rejected and written to dead-letter filesystem. Processing continues for remaining records. | No retry; record is permanently rejected. |
| **Malformed JSON** (cannot parse envelope) | Spark | Record rejected and written to dead-letter filesystem with parse error reason. | No retry; record is permanently rejected. |
| **Unknown schema version** | Spark | Record rejected and written to dead-letter filesystem. | Upgrade consumer to support new version. |
| **Spark job failure** | Spark | Micro-batch in progress may be partially processed. Spark driver restarts. | Checkpoint recovery replays from last committed offset. |
| **ML exception** (classify/credibility/etc.) | Spark foreachBatch | Record skipped in this batch. May be retried if Spark retries the micro-batch. | Fix ML code/data bug. |
| **PostgreSQL unavailable** | PostgreSQL writer | Consumer poll loop blocks. Messages remain in Kafka topic. | Automatic when PostgreSQL recovers. |
| **PostgreSQL write conflict** | PostgreSQL writer | `ON CONFLICT (event_id) DO UPDATE` handles duplicate. No error. | N/A — idempotent. |
| **Duplicate event** (same `event_id` produced twice) | PostgreSQL writer | Upsert overwrites with latest data. No duplicate row. | N/A — idempotent. |
| **Consumer offset commit failure** | Any consumer | Kafka retries offset commit. On consumer restart, last committed offset is used (may reprocess some messages). | Automatic; idempotent processing prevents effects. |

---

## 17. Implementation Checklist

### M2 — Ingestion Service

- [ ] `weather_api` adapter: polls Open-Meteo every 5 min, constructs Canonical Weather Event, produces to `weather.raw`
- [ ] `rss` adapter: parses RSS feeds via `feedparser`, constructs Canonical Weather Event, produces to `weather.raw`
- [ ] `website` adapter: scrapes allowlist sites via `httpx` + `BeautifulSoup4`, produces to `weather.raw`
- [ ] `social` adapter: reads simulated JSON feed, produces to `social.raw`
- [ ] `government_dataset` adapter: reads CSV/JSON/Parquet from `/data/raw/government/`, produces to `government.raw`
- [ ] All adapters produce messages in the **envelope format** (§3.1)
- [ ] All adapters set `ai.*` fields to `null`
- [ ] All adapters set `verification.status` to `"pending"`
- [ ] All adapters generate `event_id` via `uuid.uuid4()`
- [ ] All adapters set `ingestion_timestamp` to `datetime.now(timezone.utc)`
- [ ] All adapters normalise timestamps to UTC
- [ ] All adapters use `KAFKA_BOOTSTRAP_SERVERS` environment variable
- [ ] All adapters use `event_id` as Kafka key
- [ ] Dead-letter: malformed source data logged to application log before Kafka production

### M3 — Spark Structured Streaming + PostgreSQL Writer

- [ ] Spark job consumes from `weather.raw`, `citizen.raw`, `social.raw`, `government.raw`
- [ ] Spark job validates against `02_DATA_SCHEMA.md §11` rules
- [ ] Spark job writes REJECT records to `/data/logs/dead_letter/YYYY-MM-DD/<source_type>_failures.jsonl`
- [ ] Spark job normalises timestamps to UTC
- [ ] Spark job optionally writes to `weather.processed` (behind `SPARK_WRITE_PROCESSED_TOPIC` flag)
- [ ] Spark job writes enriched events to `weather.events` with `event_id` as key
- [ ] Spark job writes Parquet to `/data/processed/weather_events/` partitioned by `year/month/day`
- [ ] Spark checkpoint path configured at `/data/checkpoints/spark_streaming/`
- [ ] PostgreSQL writer consumes from `weather.events`
- [ ] PostgreSQL writer flattens nested JSON → flat DB columns per `02_DATA_SCHEMA.md §6` mapping
- [ ] PostgreSQL writer uses `INSERT ... ON CONFLICT (event_id) DO UPDATE`
- [ ] PostgreSQL writer upserts to `events`, `event_clusters`, `sources` tables
- [ ] PostgreSQL writer checkpoint path configured at `/data/checkpoints/pg_writer/`

### M4 — ML Modules

- [ ] `classify_event()` — per-record Pandas UDF, returns `(category, confidence)`
- [ ] `score_credibility()` — per-record Pandas UDF, returns `(score, reasons_list)`
- [ ] `generate_reasons()` — per-record Pandas UDF, returns JSON string list
- [ ] `compute_duplicate_score()` — per-micro-batch, requires recent events window
- [ ] `assign_cluster()` — per-micro-batch, requires active clusters state
- [ ] All ML modules handle exceptions gracefully (log + return default values, don't crash Spark)
- [ ] ML modules packaged at `services/ml/` and copied into Spark Docker image

### M5 — API Service + PostgreSQL

- [ ] `POST /citizen-reports`: Pydantic validation → Canonical Event → produces to `citizen.raw`
- [ ] `POST /verification`: updates PostgreSQL + inserts `verification_log` + produces to `weather.verified`
- [ ] Verification message uses `verification_action` event type (§6)
- [ ] `GET /health`: pings PostgreSQL + Kafka; returns 200 if both healthy
- [ ] `GET /events`, `GET /events/{id}`, `GET /events/stats`, `GET /events/map`: reads from PostgreSQL
- [ ] API uses `KAFKA_BOOTSTRAP_SERVERS` environment variable
- [ ] API uses `DATABASE_URL` environment variable
- [ ] Admin actions require authentication (per `04_API_CONTRACT.md`)

### M6 — Frontend

- [ ] Kafka UI accessible at `localhost:8080` for monitoring
- [ ] Spark UI accessible at `localhost:8081` for monitoring
- [ ] Dashboard displays events from `GET /events`
- [ ] Admin Panel enables verification actions via `POST /verification`
- [ ] Dead-letter count visible via `/data/logs/dead_letter/` file monitoring

---

## 18. Open Questions

| # | Question | Owner |
|---|----------|-------|
| 1 | ~~Exact Kafka message envelope format~~ | ✅ Closed — see §3 |
| 2 | ~~Dead-letter: Kafka DLQ vs filesystem~~ | ✅ Closed — filesystem only for MVP (§11) |
| 3 | Micro-batch trigger interval (processing time vs. event time) | M3 |
| 4 | In-memory recent-event window size (minutes) for duplicate/cluster functions | M4 |
| 5 | Should `weather.processed` be completely disabled in production, or retained for audit? | M1 decision |

---

*This document is the Kafka-contract source of truth.
Any change to topics, message schemas, keys, or delivery semantics must be
reflected here before implementation begins.*
