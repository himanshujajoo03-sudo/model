# 01 — System Architecture

**Project:** SIH26069 — National Weather Big Data Analytics Platform
**Document:** `01_ARCHITECTURE.md`
**Version:** 1.4
**Status:** APPROVED
**Derived from:** `00_MASTER_PROJECT_SPEC.md` v1.0 + Architect approval notes (2026-08-31)
**Last updated:** 2026-09-02 — v1.4 training architecture note (see §17 change log)

---

## 1. Overview

The platform is a **lightweight, open-source, near-real-time weather intelligence pipeline** that:

- Ingests weather-related information from multiple heterogeneous sources
- Normalises all inputs into a **Canonical Weather Event** (defined in `02_DATA_SCHEMA.md §2`)
- Streams events through Apache Kafka
- Processes, validates, cleans and enriches events via Apache Spark Structured Streaming, which invokes ML modules as a Python library within the same process
- Persists structured results to PostgreSQL + PostGIS via a decoupled writer consumer
- Exposes data through a FastAPI REST layer
- Visualises intelligence on a React-based dashboard and Admin Panel

The platform is **not** a weather forecasting system.
It is an **information aggregation, event intelligence, credibility assessment and geospatial visualisation platform**.

---

## 2. MVP Geographic Scope

| City | State | Primary Scenarios |
|------|-------|------------------|
| **Mumbai** | Maharashtra | Heavy rainfall, urban flooding, waterlogging, thunderstorms |
| **Nagpur** | Maharashtra | Heatwave, high temperature, thunderstorms, strong winds |
| **Nashik** | Maharashtra | Heavy rainfall, flooding, thunderstorms, hailstorms |

> The **data model and APIs** are designed for the full `India → State → District → City → Coordinates` hierarchy.
> Only the above three cities are used for the MVP demonstration.
> Additional cities can be added via configuration — **no code changes required**.

---

## 3. High-Level Architecture Diagram

```
╔══════════════════════════════════════════════════════════╗
║                      DATA SOURCES                        ║
║                                                          ║
║  Weather API  RSS Feeds  Websites   Social    Datasets   ║
║  (Open-Meteo) (public)  (allowlist) (API/sim) (CSV/JSON) ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║              INGESTION SERVICE (Member 2)                ║
║                                                          ║
║   Source Adapters → Normaliser → Canonical Weather Event ║
║   Produces to: weather.raw, social.raw, government.raw   ║
╚══════════════════════════════════════════════════════════╝
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
     Kafka: weather.raw        Kafka: social.raw
     Kafka: government.raw     Kafka: citizen.raw (via FastAPI)
              │                        │
              └───────────┬────────────┘
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║   SPARK STRUCTURED STREAMING + ML LIBRARY (Members 3/4)  ║
║                                                          ║
║  Consumes: weather.raw, citizen.raw,                     ║
║            social.raw, government.raw                    ║
║                                                          ║
║  Spark responsibilities (per-record):                    ║
║    1. Schema validation & rejection of malformed records ║
║    2. Field cleaning (nulls, type coercion, trimming)    ║
║    3. Transformation & UTC timestamp normalisation       ║
║    4. Basic deterministic deduplication (hash-based)     ║
║    5. Windowing & aggregation                            ║
║                                                          ║
║  ML responsibilities (invoked within micro-batch):       ║
║    6. Event classification  — per-record Python call     ║
║    7. Credibility scoring   — per-record Python call     ║
║    8. Duplicate scoring     — per-micro-batch, with      ║
║                               window of recent events    ║
║    9. Event clustering      — per-micro-batch, with      ║
║                               window of recent clusters  ║
║   10. Explainability        — per-record Python call     ║
║                                                          ║
║  ML modules imported as local Python library:            ║
║    from ml.classifier import classify_event              ║
║    from ml.credibility import score_credibility          ║
║    from ml.dedup import compute_duplicate_score          ║
║    from ml.clustering import assign_cluster              ║
║    from ml.explainability import generate_reasons        ║
║                                                          ║
║  Publishes:                                              ║
║    weather.processed  (validated + cleaned only)         ║
║    weather.events     (fully ML-enriched, final form)    ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
              Kafka: weather.events
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║           POSTGRESQL / POSTGIS WRITER                    ║
║           (Separate Spark/Python consumer — Members 3/5) ║
║                                                          ║
║  Consumes: weather.events                                ║
║  Writes to: PostgreSQL + PostGIS (events table)          ║
║  Also writes: event_clusters (upsert), sources (upsert)  ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║          DATABASE LAYER (Member 5)                       ║
║          PostgreSQL 15 + PostGIS 3.4                     ║
║                                                          ║
║  Initialization order:                                   ║
║    1. pgcrypto extension (gen_random_uuid)               ║
║    2. postgis extension (GEOMETRY types)                 ║
║    3. Helper functions (sync_geom, set_updated_at)       ║
║    4. event_clusters table                               ║
║    5. events table (FK → event_clusters)                 ║
║    6. sources table                                      ║
║    7. verification_log table (FK → events)               ║
║    8. Indexes (11 indexes including source_type)         ║
║    9. Triggers (sync_geom, set_updated_at × 3 tables)   ║
║                                                          ║
║  Tables: events, event_clusters, sources,                ║
║          verification_log                                ║
║  Geography: PostGIS GEOMETRY(Point, 4326) on events      ║
║             and event_clusters                           ║
║  Schema defined in: 02_DATA_SCHEMA.md                    ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║              FASTAPI BACKEND (Member 5)                  ║
║              Port: 8000                                  ║
║                                                          ║
║  GET  /events           — list/filter events             ║
║  GET  /events/{id}      — event detail                   ║
║  GET  /events/stats     — KPI aggregates                 ║
║  GET  /events/map       — geospatial bbox/radius query   ║
║  POST /citizen-reports  — citizen submission → citizen.raw║
║  POST /verification     — admin verify/reject/flag       ║
║  GET  /health           — system health                  ║
║                                                          ║
║  Contracts defined in: 04_API_CONTRACT.md                ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║         REACT DASHBOARD + ADMIN PANEL (Member 6)         ║
║         Port: 5173 (Vite dev server)                     ║
║                                                          ║
║  Stack: React, Vite, Tailwind CSS, Leaflet, Chart.js     ║
║                                                          ║
║  Panels:                                                 ║
║    • Main Dashboard   — KPI cards, filters               ║
║    • Event Map        — Leaflet geospatial view          ║
║    • Event Table      — filterable paginated table       ║
║    • Analytics        — time / type / location charts    ║
║    • Event Details    — per-event detail + AI breakdown  ║
║    • Admin Panel      — verify / reject / flag actions   ║
╚══════════════════════════════════════════════════════════╝
```

---

## 4. Citizen Report Path

Citizen reports enter the pipeline via FastAPI (not the ingestion service):

```
Citizen
  ↓
React Form (frontend :5173)
  ↓
POST /citizen-reports  (api :8000)
  ↓
Pydantic validation + canonical event construction (FastAPI)
  Sets source_type = "citizen", source_name = "citizen_form"
  Sets verification.status = "pending"
  Sets all ai.* fields = null
  ↓
Kafka: citizen.raw  ← carries Canonical Weather Event (same schema as other raw topics)
  ↓
Spark Structured Streaming + ML library
  ↓
Kafka: weather.events  ← carries Enriched Canonical Weather Event (ai.* populated)
  ↓
PostgreSQL Writer
  ↓
PostgreSQL/PostGIS
  ↓
GET /events (FastAPI) → Dashboard
```

Target: near-real-time availability (~5 seconds under normal demo conditions).

---

## 5. Docker Services

| Service | Image / Build | Port(s) | Notes |
|---------|--------------|---------|-------|
| `zookeeper` | confluentinc/cp-zookeeper:7.6 | 2181 | Kafka dependency |
| `kafka` | confluentinc/cp-kafka:7.6 | 9092 (internal), 29092 (host) | Central event bus |
| `kafka-ui` | provectuslabs/kafka-ui:latest | 8080 | Development visibility |
| `postgres` | postgis/postgis:15-3.4 | 5432 | Primary database; pgcrypto + PostGIS pre-installed in this image |
| `spark-master` | bitnami/spark:3.5 | 7077 (cluster), 8081 (UI) | Spark master |
| `spark-worker` | bitnami/spark:3.5 | 8082 | Spark worker (1 for MVP) |
| `ingestion` | ./services/ingestion | — | Background producer, no HTTP |
| `api` | ./services/api | 8000 | FastAPI REST + Kafka producer |
| `frontend` | ./services/frontend | 5173 | React + Vite |

> **`services/ml/` has no Docker service and no port.**
> The ML package is `COPY`-ed into the Spark image at build time and imported directly.
> The Spark image Dockerfile is responsible for installing ML dependencies.

> **Note on pgcrypto:** The `postgis/postgis:15-3.4` image ships with PostgreSQL 15
> and PostGIS 3.4. `pgcrypto` (required for `gen_random_uuid()`) and `postgis` are
> activated via `CREATE EXTENSION IF NOT EXISTS` in the init SQL, which is guaranteed
> to run before any table creation.

---

## 6. ML Integration Pattern

ML modules live at `services/ml/` and are packaged as a local Python library.
They are built into the Spark Docker image — no HTTP, no IPC, no separate process.

```
services/spark/jobs/stream_processor.py
  │
  ├── from ml.classifier.event_classifier    import classify_event
  ├── from ml.credibility.credibility_scorer import score_credibility
  ├── from ml.dedup.duplicate_detector       import compute_duplicate_score
  ├── from ml.clustering.event_clusterer     import assign_cluster
  └── from ml.explainability.reason_generator import generate_reasons
```

### 6.1 Execution Context per ML Function

| Function | Execution Context | Requires Window? | Spark Pattern | Notes |
|----------|-----------------|-----------------|--------------|-------|
| `classify_event(text, metadata)` | Per-record | No | Pandas UDF (scalar) | Safe as vectorised UDF; called on `event.description` + `event.category` hint |
| `score_credibility(event_dict)` | Per-record | No | Pandas UDF (scalar) | Safe as vectorised UDF; uses source trust score, location presence, etc. |
| `generate_reasons(event_dict, factors)` | Per-record | No | Pandas UDF (scalar) | Safe as vectorised UDF; returns JSON-serialised string list |
| `compute_duplicate_score(event_dict, recent_events_list)` | Per-micro-batch | **Yes** | `foreachBatch` handler | Needs list of recent events (last N minutes) from in-memory window; **cannot be a per-row UDF** |
| `assign_cluster(event_dict, active_clusters_list)` | Per-micro-batch | **Yes** | `foreachBatch` handler | Needs active cluster state from in-memory window; **cannot be a per-row UDF** |

### 6.2 Important — Window-Based Functions

`compute_duplicate_score` and `assign_cluster` require access to
recent/active records. These functions are called inside Spark's
`foreachBatch` handler, which receives the full micro-batch DataFrame.

Implementation pattern:
```python
def process_batch(batch_df, batch_id):
    # Per-record ML (run as Pandas UDFs before foreachBatch, or inline here)
    batch_df = batch_df.withColumn("classified_category",
                                   classify_event_udf(col("description"), col("event_category")))
    batch_df = batch_df.withColumn("credibility_score",
                                   score_credibility_udf(struct("*")))
    batch_df = batch_df.withColumn("credibility_reasons",
                                   generate_reasons_udf(struct("*")))

    # Window-based ML (requires full batch + external state)
    records = batch_df.collect()  # safe for MVP micro-batch sizes
    recent_events = load_recent_events_from_memory(window_minutes=30)
    active_clusters = load_active_clusters_from_memory()

    enriched = []
    for record in records:
        dup_score = compute_duplicate_score(record.asDict(), recent_events)
        cluster_id = assign_cluster(record.asDict(), active_clusters)
        enriched.append({**record.asDict(),
                         "duplicate_score": dup_score,
                         "cluster_id": cluster_id})

    # Write enriched batch to weather.events topic and Parquet
    write_to_kafka(enriched, topic="weather.events")
    write_to_parquet(enriched, path="/data/processed/weather_events/")

stream_df.writeStream.foreachBatch(process_batch).start()
```

A small in-memory lookup of recent events (last N minutes, configurable) is maintained
within the batch handler — no external state store required for the MVP.

### 6.3 Training Architecture (Separate from Runtime)

Model training is a **separate, offline process** — it NEVER runs inside Spark Structured Streaming.

```text
External experimentation (Jupyter/Colab)
         ↓
Project training scripts (training/)
         ↓
Model artifact (models/event_classifier/model.pkl)
         ↓
Spark loads artifact at startup → inference only
```

See `05_AI_ML_SPEC.md §19` for the definitive three-stage training architecture.
The runtime pipeline only loads the pre-trained model and performs predictions.

---

## 7. Separation of Processing from Persistence

Processing and persistence are decoupled via the `weather.events` Kafka topic:

```
Spark (processing + ML)
  ↓
Kafka: weather.events
  ↓
PostgreSQL Writer (separate consumer)
  ↓
PostgreSQL + PostGIS
```

Benefits:
- Spark job can be restarted without affecting the database
- PostgreSQL writer can be replaced or scaled independently
- Processing logic is not tangled with database transaction logic
- `weather.events` can be replayed to rebuild the database from scratch

---

## 8. Data Lake / Historical Storage

| Layer | Technology | Location | Purpose |
|-------|-----------|----------|---------| 
| Raw data | Newline-delimited JSON (`.jsonl`) | `/data/raw/` on 1 TB HDD | Full raw ingestion archive, one file per source per day |
| Processed data | Parquet (partitioned `year/month/day`) | `/data/processed/` on 1 TB HDD | Analytical queries via Spark/DuckDB |
| Synthetic data | Parquet | `/data/synthetic/` on 1 TB HDD | 1M+ load-test dataset |
| Media | Binary | `/data/media/` on 1 TB HDD | Photos/videos from citizen reports |
| Dead-letter | Newline-delimited JSON (`.jsonl`) | `/data/logs/dead_letter/YYYY-MM-DD/<source_type>_failures.jsonl` | Rejected records with failure reasons |
| App logs | Text / JSON | `/data/logs/app/` on 1 TB HDD | Application and pipeline logs |
| Cloud (optional) | Cloudflare R2 | External | Selected demo Parquet files only |
| Analytics (optional) | DuckDB | Local binary | Ad-hoc Parquet query — **not a runtime dep** |

---

## 9. Kafka Topics Summary

| Topic | Producer | Consumer | Payload Type | Purpose |
|-------|----------|----------|-------------|---------|
| `weather.raw` | ingestion | spark | **Canonical Weather Event** (JSON, `ai.*` all null) | API, RSS, website events |
| `citizen.raw` | api | spark | **Canonical Weather Event** (JSON, `ai.*` all null) | Citizen form submissions |
| `social.raw` | ingestion | spark | **Canonical Weather Event** (JSON, `ai.*` all null) | Social / simulated feed |
| `government.raw` | ingestion | spark | **Canonical Weather Event** (JSON, `ai.*` all null) | Government dataset records |
| `weather.processed` | spark (optional, behind config flag) | monitoring only | **Canonical Weather Event** (JSON, validated + cleaned, `ai.*` still null or partial) | Debugging / audit; **not consumed by any downstream service** |
| `weather.events` | spark | postgres-writer | **Enriched Canonical Weather Event** (JSON, `ai.*` fully populated) | **Final enriched events — source of truth for storage** |
| `weather.verified` | api (admin action) | audit consumer | Verification action payload (JSON — see `03_KAFKA_CONTRACT.md`) | Human verification audit trail |

> **Topic payload rules:**
>
> - `weather.raw`, `citizen.raw`, `social.raw`, `government.raw` — all carry the **identical Canonical Weather Event** structure defined in `02_DATA_SCHEMA.md §2`. The `ai.*` block is present but all fields are `null`. The `verification.status` is `"pending"`.
>
> - `weather.processed` — **optional, behind a config flag** (`SPARK_WRITE_PROCESSED_TOPIC=true/false`). Same structure, but records have passed Spark validation. Fields may be normalised (e.g. timestamps converted to UTC string). `ai.*` fields remain null. This topic is **not** consumed by any downstream service — it is for debugging and audit only.
>
> - `weather.events` — same structure with `ai.*` fully populated by ML modules. This is the **only** topic the PostgreSQL writer consumes. Do not use `weather.processed` as input to the database.
>
> - `weather.verified` — **different, smaller payload** (verification action only, not a full event). Defined in `03_KAFKA_CONTRACT.md`.

Full message schemas, envelope format (key, headers, value wrapper), and Avro/JSON schema definitions are in: `03_KAFKA_CONTRACT.md`

---

## 10. Dead-Letter Handling

Records that fail Spark validation (REJECT-level rules) are **never silently discarded**.

### MVP Dead-Letter Mechanism: Filesystem Log Only

**Decision (MVP):** Dead-letter records are written exclusively to the filesystem.
A Kafka DLQ topic is **not** used in the MVP. This decision is final for the 5-day sprint.

Failed records are written to:
```
/data/logs/dead_letter/YYYY-MM-DD/<source_type>_failures.jsonl
```

Each line is a JSON object containing:
```json
{
  "failed_at": "<ISO 8601 UTC>",
  "source_adapter": "<string>",
  "failure_reasons": ["<string>"],
  "original_record": { "...": "..." }
}
```

File rotation: one file per `source_type` per calendar day (UTC).

> A Kafka DLQ topic (`weather.dead_letter`) **may be added in a future version**
> if operational replay of failed records becomes a requirement.
> For the 5-day MVP, the filesystem log is the sole dead-letter mechanism.

---

## 11. Data Source Constraints

### Weather API
- Provider: Open-Meteo (free, no API key required for basic endpoints)
- Kafka topic produced to: `weather.raw`
- `source_type` value: `"weather_api"`
- Poll interval: every 5 minutes
- Fields: temperature, precipitation, wind speed, humidity, weather code, timestamp, coordinates

### RSS Feeds
- Any publicly accessible RSS feed
- Kafka topic produced to: `weather.raw`
- `source_type` value: `"rss"`
- Parser: `feedparser` Python library
- Location extracted from content when absent from feed metadata

### Websites
- **Allowlist only — no general-purpose crawler**
- Kafka topic produced to: `weather.raw`
- `source_type` value: `"website"`
- Allowlist file: `services/ingestion/config/website_allowlist.json`
- HTTP client: `httpx`; parser: `BeautifulSoup4`
- Candidate allowlist entries: IMD news page, state disaster-management portal news sections

### Social Media
- **API-compliant or clearly labelled simulated feed — no unrestricted scraping**
- Kafka topic produced to: `social.raw`
- `source_type` value: `"social"` (genuine API) or `"simulated_social"` (hackathon simulation)
- For simulated data: `platform` field MUST be `"simulated"`
- Hackathon implementation: controlled simulated JSON feed

### Government Datasets
- Batch ingestion from CSV / JSON / Parquet files placed in `/data/raw/government/`
- Kafka topic produced to: `government.raw`
- `source_type` value: `"government_dataset"`

### Citizen Reports
- Submitted via React form → `POST /citizen-reports` → FastAPI constructs canonical event → `citizen.raw`
- Kafka topic produced to: `citizen.raw`
- `source_type` value: `"citizen"`

### Synthetic Data
- Generator produces 1M+ records for load testing
- `source_type` value: `"synthetic"`, `source_name` MUST contain `"synthetic"`
- **Never** presented as genuine reports in any dashboard view
- Can be produced to `weather.raw` (tagged) or loaded directly into the Parquet data lake

---

## 12. Security Principles

- All secrets via environment variables (`.env`) — never hardcoded
- Admin actions require authentication (mechanism defined in `04_API_CONTRACT.md`)
- Citizen PII minimised — no unnecessary personal data retained
- Uploaded media validated for type and size before storage
- API inputs validated via Pydantic v2 schemas
- `.env` is gitignored; `.env.example` committed without values
- `source_type = "synthetic"` and `source_type = "simulated_social"` are clearly
  labelled in all API responses and dashboard views

---

## 13. Observability

| Signal | Source | Access |
|--------|--------|--------|
| Ingestion record counts | ingestion service stdout | Docker logs / `/data/logs/app/` |
| Kafka topic lag / message counts | kafka-ui (port 8080) | Browser |
| Spark job status & throughput | Spark UI (port 8081) | Browser |
| Spark streaming metrics | Spark UI → Structured Streaming tab | Browser |
| Dead-letter record count | `/data/logs/dead_letter/` | File / log tail |
| API health | `GET /health` | curl / frontend |
| PostgreSQL | pg logs | Docker logs |

Key metrics produced by the pipeline:
```
records_ingested        (per source_type)
records_validated
records_rejected        (dead-letter count)
records_processed
duplicates_detected     (basic dedup hash hits)
events_classified       (ML classifier ran)
events_clustered        (cluster_id assigned)
events_verified         (admin actions)
```

---

## 14. Day-1 Success Criterion

A working end-to-end path demonstrating all five layers:

```
One canonical event
  → ingestion adapter (weather_api or synthetic)
  → Kafka: weather.raw
  → Spark: validate + clean + classify_event + score_credibility + generate_reasons
           + compute_duplicate_score + assign_cluster
  → Kafka: weather.events  (ai.* fully populated)
  → PostgreSQL Writer → PostgreSQL/PostGIS
  → GET /events (FastAPI :8000)
  → Dashboard event list (React :5173)
```

This path must work before any advanced features are implemented.

### Day-1 Checklist (Deployment Order)

1. `docker compose up zookeeper kafka kafka-ui` — verify kafka-ui at :8080
2. `docker compose up postgres` — run init SQL; verify tables exist
3. `docker compose up spark-master spark-worker` — verify Spark UI at :8081
4. `docker compose up ingestion` — produces one test event to `weather.raw`
5. Start Spark streaming job — verify event consumed, ML applied, published to `weather.events`
6. Start PostgreSQL writer — verify event written to `events` table
7. `docker compose up api` — verify `GET /health` returns 200
8. `docker compose up frontend` — verify event appears in dashboard

---

## 15. API → Database Field Mapping

Each API endpoint and the database fields it requires:

| Endpoint | DB Fields Required | Notes |
|----------|-------------------|-------|
| `GET /events` | `event_id`, `event_timestamp`, `event_category`, `severity`, `description`, `city`, `state`, `source_type`, `source_name`, `verification_status`, `credibility_score`, `credibility_reasons`, `classified_category`, `classification_confidence`, `duplicate_score`, `cluster_id`, `created_at` | Filterable; paginated; AI fields displayed on dashboard |
| `GET /events/{id}` | All `events` columns | Full event detail |
| `GET /events/stats` | `event_category`, `severity`, `verification_status`, `event_timestamp`, `source_type` | Aggregate counts; uses `COUNT`, `GROUP BY` |
| `GET /events/map` | `event_id`, `latitude`, `longitude`, `geom`, `event_category`, `severity`, `city`, `credibility_score` | Geospatial bbox/radius via PostGIS `ST_Within` / `ST_DWithin` |
| `POST /citizen-reports` | Constructs canonical event; no DB read required at submission | Writes to `citizen.raw` Kafka topic |
| `POST /verification` | `events.verification_status`, `events.verified_by`, `events.verification_timestamp`, `verification_log.*` | Updates event + inserts log row; also produces to `weather.verified` |
| `GET /health` | Connection check only | Ping DB + Kafka; no table query |

All required fields exist in `02_DATA_SCHEMA.md §6`. The JSON→PostgreSQL field mapping
(nested JSON paths to flat DB columns) is defined in `02_DATA_SCHEMA.md §6 preamble`.

---

## 16. Out of Scope

| Item | Reason |
|------|--------|
| Redis | Not required by master spec |
| Elasticsearch | Not required by master spec |
| Kubernetes | Explicitly excluded (spec §48) |
| Airflow | Explicitly excluded (spec §48) |
| Mobile application | Explicitly excluded (spec §48) |
| Satellite / deep-learning image ML | Explicitly excluded (spec §48) |
| Sub-second real-time guarantees | Near-real-time is the target |
| Cities beyond Mumbai / Nagpur / Nashik | MVP geographic scope |
| New event taxonomy categories | Requires change-control process |
| Standalone ML HTTP service | Removed per architect decision |
| Kafka DLQ topic (`weather.dead_letter`) | Deferred to future version; filesystem log is the MVP mechanism |
| `locations` table | Not defined in schema; location is stored inline on `events` |

---

## 17. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-08-31 | Initial approved architecture |
| 1.1 | 2026-08-31 | Removed `locations` table reference; clarified ML runs within Spark micro-batch; added ML execution-context table; separated dead-letter mechanism; clarified all Kafka topic payloads; corrected citizen path diagram; versioned Docker image tags; closed open question #1 |
| 1.2 | 2026-09-01 | **Consistency + correctness audit:** Added DB initialisation order to diagram (extensions → tables → indexes → triggers); fixed Kafka topic table to clearly distinguish `weather.processed` (intermediate, debug only) from `weather.events` (final, PostgreSQL writer input); resolved dead-letter ambiguity — filesystem-only for MVP, DLQ deferred; expanded ML execution pattern with concrete `foreachBatch` pseudocode; clarified Pandas UDF vs `foreachBatch` split; added §15 API↔DB field mapping table; added Day-1 deployment checklist; added per-source `source_type` and Kafka topic mapping to §11; clarified `citizen.raw` carries identical Canonical Event structure; added ingestion diagram annotation showing which service produces to which topic; noted `postgis/postgis:15-3.4` image includes pgcrypto |
| 1.3 | 2026-09-01 | **Schema consistency audit (paired with 02_DATA_SCHEMA.md v1.1):** Expanded §15 API→DB mapping to include AI fields (`classified_category`, `classification_confidence`, `credibility_reasons`, `description`, `created_at`) needed by dashboard; marked `weather.processed` as optional (behind config flag); added reference to JSON→DB field mapping in schema doc; updated change log |
| 1.4 | 2026-09-02 | **Training architecture:** Added §6.3 Training Architecture note — model training is a separate offline process; runtime only performs inference; updated open question #4 to reference three-stage model in `05_AI_ML_SPEC.md §19` |

---

## 18. Open Questions

| # | Question | Owner |
|---|----------|-------|
| 1 | ~~Exact Canonical Event JSON fields~~ | ✅ Closed — see `02_DATA_SCHEMA.md` |
| 2 | ~~Exact Kafka message envelope format~~ | ✅ Closed — see `03_KAFKA_CONTRACT.md §3` |
| 3 | ~~FastAPI auth mechanism for Admin Panel~~ | ✅ Closed — see `04_API_CONTRACT.md §3` (JWT Bearer tokens) |
| 4 | ~~ML model selection: rule-based vs. trained classifier~~ | ✅ Closed — see `05_AI_ML_SPEC.md §19` (three-stage: rule-based MVP, offline training, trained drop-in replacement) |
| 5 | Website allowlist — specific approved URLs | M2 → propose to M1 |
| 6 | Open-Meteo: which weather codes map to which event categories | M2 |
| 7 | Cloudflare R2 — use for demo or skip entirely for Day 1? | M1 decision |
| 8 | Micro-batch trigger interval (processing time vs. event time) | M3 |
| 9 | In-memory recent-event window size (minutes) for duplicate/cluster functions | M4 |
| 10 | ~~Dead-letter: Kafka DLQ vs filesystem~~ | ✅ Closed — filesystem only for MVP (§10) |
| 11 | ~~`weather.processed` vs `weather.events` ambiguity~~ | ✅ Closed — see §9 topic rules |

---

*This document is the architectural source of truth for the system design.
Any change to services, topics, ports, or integration patterns must be
reflected here before implementation begins.*
