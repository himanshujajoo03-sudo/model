# 06 — Implementation Plan

**Project:** SIH26069 — National Weather Big Data Analytics Platform
**Document:** `06_IMPLEMENTATION_PLAN.md`
**Version:** 1.1
**Status:** AWAITING APPROVAL
**Derived from:** `01_ARCHITECTURE.md` v1.4 + `02_DATA_SCHEMA.md` v1.1 + `03_KAFKA_CONTRACT.md` v1.0 + `04_API_CONTRACT.md` v1.0 + `05_AI_ML_SPEC.md` v1.2
**Last updated:** 2026-09-02

---

## Change Control

This document translates approved specifications into implementation tasks.
It does NOT override or extend any contract. If a task contradicts a contract,
the contract wins and this document must be updated.

---

## 1. Repository Structure

```
weather-platform/
│
├── docker-compose.yml                    # All services
├── docker-compose.dev.yml                # Development overrides (optional)
├── .env.example                          # Template — committed without values
├── .gitignore
├── README.md
│
├── docs/
│   ├── 00_MASTER_PROJECT_SPEC.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_DATA_SCHEMA.md
│   ├── 03_KAFKA_CONTRACT.md
│   ├── 04_API_CONTRACT.md
│   ├── 05_AI_ML_SPEC.md
│   └── 06_IMPLEMENTATION_PLAN.md
│
├── scripts/
│   ├── init-db.sh                        # PostgreSQL init SQL runner
│   ├── init-kafka.sh                     # Topic creation script
│   └── smoke-test.sh                     # End-to-end verification
│
├── services/
│   │
│   ├── ingestion/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                       # Entry point — starts all adapters
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # Base adapter class
│   │   │   ├── weather_api.py            # Open-Meteo adapter
│   │   │   ├── rss.py                    # RSS feed adapter
│   │   │   ├── website.py                # Website scraper adapter
│   │   │   ├── social.py                 # Simulated social feed
│   │   │   └── government.py             # Government dataset adapter
│   │   ├── producer/
│   │   │   ├── __init__.py
│   │   │   └── kafka_producer.py         # Kafka producer wrapper
│   │   ├── normaliser/
│   │   │   ├── __init__.py
│   │   │   └── canonical_event.py        # Canonical Weather Event builder
│   │   └── config/
│   │       ├── sources.json              # Source adapter configurations
│   │       └── website_allowlist.json    # Allowlisted URLs
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── config/
│   │   │   ├── ml_config.yaml            # All thresholds and weights
│   │   │   ├── source_trust.yaml         # Source trust defaults
│   │   │   └── india_cities.json         # City bounding boxes
│   │   ├── classifier/
│   │   │   ├── __init__.py
│   │   │   ├── event_classifier.py       # classify_event()
│   │   │   └── rules.py                  # Keyword dictionaries
│   │   ├── credibility/
│   │   │   ├── __init__.py
│   │   │   ├── credibility_scorer.py     # score_credibility()
│   │   │   └── source_weights.py         # Source trust loading
│   │   ├── dedup/
│   │   │   ├── __init__.py
│   │   │   └── duplicate_detector.py     # compute_duplicate_score()
│   │   ├── clustering/
│   │   │   ├── __init__.py
│   │   │   └── event_clusterer.py        # assign_cluster()
│   │   ├── explainability/
│   │   │   ├── __init__.py
│   │   │   └── reason_generator.py       # generate_reasons()
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── text.py                   # normalize_text(), text_similarity()
│   │   │   ├── geo.py                    # haversine_km(), bounding box lookup
│   │   │   └── time_utils.py             # parse_timestamp(), time_diff_minutes()
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── fixtures/
│   │       │   ├── mumbai_flood_reports.json
│   │       │   ├── nagpur_heatwave_reports.json
│   │       │   ├── duplicate_reports.json
│   │       │   ├── low_credibility_reports.json
│   │       │   └── edge_cases.json
│   │       ├── test_classifier.py
│   │       ├── test_credibility.py
│   │       ├── test_dedup.py
│   │       ├── test_clustering.py
│   │       └── test_explainability.py
│   │
│   ├── spark/
│   │   ├── Dockerfile                    # Builds from bitnami/spark:3.5 + COPY ml/
│   │   ├── requirements.txt              # numpy, pyyaml, confluent-kafka, pyspark
│   │   ├── jobs/
│   │   │   ├── stream_processor.py       # Main Spark Structured Streaming job
│   │   │   └── pg_writer.py              # PostgreSQL writer consumer
│   │   └── config/
│   │       └── spark_config.yaml         # Kafka bootstrap, checkpoint paths, topics
│   │
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── requirements.txt              # fastapi, uvicorn, psycopg2, confluent-kafka, python-jose, pydantic
│   │   ├── main.py                       # FastAPI app entry point
│   │   ├── config.py                     # Settings from env vars
│   │   ├── dependencies.py               # DB session, Kafka producer, auth deps
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── events.py                 # GET /events, /events/{id}, /events/stats, /events/map
│   │   │   ├── citizen.py                # POST /citizen-reports
│   │   │   ├── verification.py           # POST /verification
│   │   │   ├── auth.py                   # POST /auth/login
│   │   │   └── health.py                 # GET /health
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py               # Pydantic request models
│   │   │   ├── responses.py              # Pydantic response models
│   │   │   └── events.py                 # Event-specific schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── event_service.py          # Business logic for events
│   │   │   ├── citizen_service.py        # Citizen report → Kafka
│   │   │   ├── verification_service.py   # Verification → DB + Kafka
│   │   │   └── kafka_service.py          # Kafka producer wrapper
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_events.py
│   │       ├── test_citizen.py
│   │       ├── test_verification.py
│   │       └── test_health.py
│   │
│   └── frontend/
│       ├── Dockerfile
│       ├── package.json
│       ├── vite.config.js
│       ├── tailwind.config.js
│       ├── index.html
│       ├── public/
│       └── src/
│           ├── main.jsx
│           ├── App.jsx
│           ├── api/
│           │   └── client.js             # Axios/fetch wrapper for API calls
│           ├── components/
│           │   ├── layout/
│           │   │   ├── Header.jsx
│           │   │   └── Sidebar.jsx
│           │   ├── dashboard/
│           │   │   ├── KpiCards.jsx
│           │   │   ├── EventTable.jsx
│           │   │   ├── EventFilters.jsx
│           │   │   └── Analytics.jsx
│           │   ├── map/
│           │   │   └── EventMap.jsx      # Leaflet map
│           │   ├── detail/
│           │   │   ├── EventDetail.jsx
│           │   │   └── AiBreakdown.jsx   # ML reasoning display
│           │   ├── citizen/
│           │   │   └── CitizenForm.jsx
│           │   └── admin/
│           │       ├── AdminPanel.jsx
│           │       ├── LoginForm.jsx
│           │       └── VerifyActions.jsx
│           ├── hooks/
│           │   ├── useEvents.js
│           │   └── useAuth.js
│           └── pages/
│               ├── Dashboard.jsx
│               ├── MapView.jsx
│               ├── EventDetailPage.jsx
│               ├── CitizenReportPage.jsx
│               └── AdminPage.jsx
│
├── training/                             # OFFLINE model training — never runs at runtime
│   ├── prepare_data.py                   # Load + clean labelled data for training
│   ├── train.py                          # Train sklearn Pipeline (TF-IDF + Logistic Regression)
│   ├── evaluate.py                       # Evaluate model (F1, confusion matrix, comparison)
│   └── data/
│       └── weather_events_labelled.csv   # Labelled training dataset
│
├── models/                               # Trained model artifacts
│   └── event_classifier/
│       ├── model.pkl                     # Trained sklearn Pipeline (joblib)
│       └── metadata.json                 # Model version, metrics, training date
│
├── data/
│   ├── raw/                              # Raw ingestion archive (one .jsonl per source per day)
│   │   └── government/                   # Government dataset files
│   ├── processed/
│   │   └── weather_events/               # Parquet partitioned year/month/day
│   ├── synthetic/                        # 1M+ load-test dataset
│   ├── media/
│   │   ├── photos/                       # Uploaded citizen photos
│   │   └── videos/                       # Uploaded citizen videos
│   └── logs/
│       ├── app/                          # Application logs
│       └── dead_letter/                  # Failed records (YYYY-MM-DD/<source>_failures.jsonl)
│
└── sql/
    └── init.sql                          # Complete PostgreSQL init script (02_DATA_SCHEMA.md §17)
```

---

## 2. Team Responsibilities

### M1 — Project Lead / Coordinator

| Aspect | Detail |
|--------|--------|
| **Files owned** | `README.md`, `.env.example`, `docker-compose.yml`, `scripts/` |
| **Components** | Project coordination, Docker orchestration, integration testing, demo preparation |
| **Dependencies** | All members; unblocks no one but integrates everyone |
| **Inputs required** | All members report blockers daily |
| **Outputs/contracts** | Working `docker-compose up` that starts all services; `smoke-test.sh` passes |
| **Definition of done** | All 8 services start in order; end-to-end event visible on dashboard |

### M2 — Ingestion Service

| Aspect | Detail |
|--------|--------|
| **Files owned** | `services/ingestion/` (all files) |
| **Components** | All source adapters (Open-Meteo, RSS, website, social, government), Kafka producer, canonical event builder |
| **Dependencies** | Kafka topics must exist (M1); schema defined in `02_DATA_SCHEMA.md` |
| **Inputs required** | `02_DATA_SCHEMA.md` §2 (Canonical Event), `03_KAFKA_CONTRACT.md` §3 (envelope), `01_ARCHITECTURE.md` §11 (source constraints) |
| **Outputs/contracts** | Produces valid Canonical Weather Events wrapped in Kafka envelopes to `weather.raw`, `social.raw`, `government.raw` |
| **Definition of done** | All 5 adapters running; producing to correct topics; events pass Spark validation; `docker compose up ingestion` works |

### M3 — Spark + PostgreSQL Writer

| Aspect | Detail |
|--------|--------|
| **Files owned** | `services/spark/` (all files), `docker-compose.yml` spark services, `sql/init.sql` |
| **Components** | Spark Structured Streaming job, PostgreSQL writer consumer, Spark Dockerfile, DB init SQL |
| **Dependencies** | Kafka topics (M1); ML library (M4); PostgreSQL schema (M5) |
| **Inputs required** | `02_DATA_SCHEMA.md` §11 (validation rules), `03_KAFKA_CONTRACT.md` §5 (processed event), `05_AI_ML_SPEC.md` §18 (Spark integration) |
| **Outputs/contracts** | Consumes raw topics → validates → calls ML → publishes to `weather.events`; writer upserts to PostgreSQL |
| **Definition of done** | Events flow from Kafka through Spark to PostgreSQL; dead-letter works; Parquet written |

### M4 — ML Modules

| Aspect | Detail |
|--------|--------|
| **Files owned** | `services/ml/` (all files), `training/` (all files), `models/` (artifacts) |
| **Components** | Classification (rule-based + trained model), credibility, dedup, clustering, explainability; offline training scripts |
| **Dependencies** | Spark integration pattern (M3); keyword dictionaries may need M2 input for Open-Meteo weather codes |
| **Inputs required** | `05_AI_ML_SPEC.md` (complete spec), `02_DATA_SCHEMA.md` §1.2 (categories), `01_ARCHITECTURE.md` §6.1 (function signatures) |
| **Outputs/contracts** | 5 functions matching architecture signatures: `classify_event`, `score_credibility`, `compute_duplicate_score`, `assign_cluster`, `generate_reasons`; offline training pipeline (`training/`); model artifact (`models/event_classifier/`) |
| **Definition of done** | All unit tests pass; functions match architecture signatures; ML library COPY-able into Spark image; training scripts produce valid model artifact |

### M5 — API + Database

| Aspect | Detail |
|--------|--------|
| **Files owned** | `services/api/` (all files), `sql/init.sql` (co-own with M3) |
| **Components** | FastAPI endpoints, Pydantic models, PostgreSQL queries, JWT auth, Kafka producer for citizen/verification |
| **Dependencies** | Database schema (M3/M5 co-own); Kafka topics (M1); API contract (`04_API_CONTRACT.md`) |
| **Inputs required** | `04_API_CONTRACT.md` (complete spec), `02_DATA_SCHEMA.md` §6 (DB schema), `03_KAFKA_CONTRACT.md` §6 (verification contract) |
| **Outputs/contracts** | All 8 API endpoints functional; JWT auth on `/verification`; citizen reports produce to `citizen.raw` |
| **Definition of done** | `GET /health` returns 200; all endpoints match API contract; Swagger UI at `/docs` |

### M6 — Frontend

| Aspect | Detail |
|--------|--------|
| **Files owned** | `services/frontend/` (all files) |
| **Components** | React dashboard, event map (Leaflet), event table, filters, analytics, citizen form, admin panel |
| **Dependencies** | API endpoints (M5); CORS configured in API |
| **Inputs required** | `04_API_CONTRACT.md` §8–§15 (endpoint schemas), `01_ARCHITECTURE.md` §3 (frontend stack: React, Vite, Tailwind, Leaflet, Chart.js) |
| **Outputs/contracts** | Dashboard shows events; map renders markers; filters work; citizen form submits; admin can verify |
| **Definition of done** | All dashboard panels render; map loads; citizen form produces event; admin login + verify works |

### Ownership Matrix (No Overlaps)

| Directory | Owner | Reviewer |
|-----------|-------|----------|
| `services/ingestion/` | M2 | M1 |
| `services/ml/` | M4 | M3 |
| `services/spark/` | M3 | M4 |
| `services/api/` | M5 | M1 |
| `services/frontend/` | M6 | M5 |
| `sql/` | M3 + M5 | M1 |
| `docker-compose.yml` | M1 | M3 |
| `scripts/` | M1 | M3 |
| `data/` | Runtime (no owner) | M1 |

---

## 3. Five-Day Execution Plan

### Day 1 — Infrastructure + Skeleton + End-to-End Vertical Slice

**Goal:** One canonical event traverses all five layers.

| Time Block | Task | Owner | Depends On | Acceptance Criterion |
|-----------|------|-------|------------|---------------------|
| Morning | Clone repo, set up `.env`, run `docker compose up zookeeper kafka kafka-ui` | M1 | — | kafka-ui accessible at `localhost:8080` |
| Morning | Run `init.sql` against PostgreSQL | M3/M5 | — | All 4 tables + 11 indexes + triggers exist |
| Morning | Create all 7 Kafka topics | M1 | Kafka running | `kafka-topics --list` shows all 7 topics |
| Morning | Spark master + worker up; verify Spark UI | M3 | — | Spark UI at `localhost:8081` |
| Morning | Build ML library; unit tests pass | M4 | — | `pytest services/ml/tests/` all green |
| Midday | M2: Open-Meteo adapter + Kafka producer → `weather.raw` | M2 | Kafka topics | One valid Canonical Event in `weather.raw` |
| Midday | M3: Spark stream_processor skeleton — consumes `weather.raw`, validates, calls ML stubs | M3 | M2 producing | Event consumed from `weather.raw` |
| Midday | M3: ML stubs (return defaults) integrated into Spark | M3/M4 | ML signatures agreed | `weather.events` receives enriched event |
| Afternoon | M3: PostgreSQL writer consumes `weather.events`, upserts to `events` table | M3 | Writer running | Event visible in `SELECT * FROM events` |
| Afternoon | M5: FastAPI skeleton — `GET /health` + `GET /events` | M5 | DB has data | `curl localhost:8000/api/v1/health` returns 200; `/events` returns the test event |
| Afternoon | M6: React skeleton — loads events from API | M6 | API running | Dashboard shows 1 event |
| **EOD** | **Demo checkpoint: full vertical slice** | **ALL** | — | **One event from ingestion → Kafka → Spark → PostgreSQL → API → Dashboard** |

**Day-1 Deliverables:**
- [ ] `docker compose up` starts all services
- [ ] Kafka topics created and healthy
- [ ] PostgreSQL tables exist with all constraints
- [ ] One test event traverses the full pipeline
- [ ] Dashboard shows the event
- [ ] `smoke-test.sh` passes basic checks

### Day 2 — Ingestion Adapters + Kafka + Canonical Validation

**Goal:** All source adapters running; events flow through Kafka correctly.

| Time Block | Task | Owner | Depends On | Acceptance Criterion |
|-----------|------|-------|------------|---------------------|
| Morning | M2: Open-Meteo adapter — poll every 5 min, produce to `weather.raw` | M2 | Day 1 vertical slice | Real weather data appearing in Kafka |
| Morning | M2: RSS adapter — parse feed, produce to `weather.raw` | M2 | — | RSS events in Kafka |
| Morning | M2: Website scraper — allowlist, httpx, BeautifulSoup | M2 | — | Website events in Kafka |
| Morning | M2: Simulated social feed — JSON feed, produce to `social.raw` | M2 | — | Social events in Kafka |
| Morning | M2: Government dataset adapter — read CSV/JSON from `/data/raw/government/` | M2 | — | Government events in Kafka |
| Midday | M2: Canonical event builder — all adapters use identical builder | M2 | — | All events match `02_DATA_SCHEMA.md §2` exactly |
| Midday | M3: Spark validation — implement all REJECT/WARN rules from `02_DATA_SCHEMA.md §11` | M3 | — | Invalid events rejected to dead-letter; valid events pass |
| Midday | M3: Dead-letter filesystem writer | M3 | — | `/data/logs/dead_letter/YYYY-MM-DD/<source>_failures.jsonl` written |
| Afternoon | M4: Classification rules — keyword dictionaries (English, Hindi, Marathi) | M4 | — | `pytest services/ml/tests/test_classifier.py` passes |
| Afternoon | M4: Credibility scoring — all 6 factors | M4 | — | `pytest services/ml/tests/test_credibility.py` passes |
| Afternoon | M4: Dedup + clustering + explainability | M4 | — | All ML tests pass |
| Afternoon | M6: Frontend filters + pagination wired | M6 | API stable | Filters update event list |
| **EOD** | **Demo checkpoint: multiple source types** | **ALL** | — | **Events from all 5 source types appear in Kafka; validation rejects bad events** |

### Day 3 — Spark Processing + ML Enrichment + PostgreSQL/PostGIS

**Goal:** Full ML enrichment pipeline; database fully populated.

| Time Block | Task | Owner | Depends On | Acceptance Criterion |
|-----------|------|-------|------------|---------------------|
| Morning | M3: Spark `foreachBatch` with ML integration — per-record UDFs + batch dedup/clustering | M3/M4 | Day 2 ML complete | `ai.*` fields populated in `weather.events` |
| Morning | M3: Parquet writer — partitioned by year/month/day | M3 | — | `/data/processed/weather_events/year=.../month=.../day=.../part-*.parquet` exists |
| Morning | M3: In-memory recent events window for dedup/clustering | M3/M4 | — | Duplicate detection works across micro-batches |
| Midday | M5: PostgreSQL writer — complete field mapping, geometry trigger, upsert logic | M5 | DB schema ready | All `events` columns populated; `geom` auto-set by trigger |
| Midday | M5: Event clusters upsert + sources upsert in writer | M5 | — | `event_clusters` and `sources` tables populated |
| Midday | M5: PostgreSQL writer checkpoint at `/data/checkpoints/pg_writer/` | M5 | — | Writer survives restart without duplicates |
| Afternoon | M3: Spark checkpoint at `/data/checkpoints/spark_streaming/` | M3 | — | Spark survives restart; resumes from last offset |
| Afternoon | M5: `GET /events` — full filter/pagination/sort | M5 | DB has data | All query params work; response matches API contract |
| Afternoon | M5: `GET /events/{id}` — full detail with verification history | M5 | — | Nested response structure matches API contract |
| Afternoon | M5: `GET /events/stats` — aggregation queries | M5 | — | KPI counts match `SELECT COUNT(*)` checks |
| Afternoon | M5: `GET /events/map` — PostGIS bounding box query | M5 | — | `ST_MakeEnvelope` + GIST index returns correct markers |
| **EOD** | **Demo checkpoint: ML-enriched events in database** | **ALL** | — | **Classification, credibility, dedup, clustering all visible in DB and API** |

### Day 4 — FastAPI + Dashboard + Admin Verification

**Goal:** Complete API; complete frontend; citizen reports + admin verification working.

| Time Block | Task | Owner | Depends On | Acceptance Criterion |
|-----------|------|-------|------------|---------------------|
| Morning | M5: `POST /citizen-reports` — multipart form, media upload, Kafka produce | M5 | Kafka `citizen.raw` | Citizen event appears in pipeline within 5 sec |
| Morning | M5: `POST /verification` — JWT auth, DB update, `verification_log` insert, Kafka produce | M5 | JWT config | Admin can verify/reject; event status changes |
| Morning | M5: `POST /auth/login` — JWT token generation | M5 | — | Login returns access_token |
| Midday | M5: CORS middleware — allow `localhost:5173` | M5 | — | Frontend can call API |
| Midday | M5: Media upload — `/data/media/photos/`, `/data/media/videos/` | M5 | — | Files stored; URLs in Canonical Event |
| Midday | M6: KPI cards — total events, by category, by severity, by status | M6 | `/events/stats` | Cards show live data |
| Midday | M6: Event map — Leaflet with markers, bounding box | M6 | `/events/map` | Map renders events; markers clickable |
| Midday | M6: Event table — filterable, paginated, sortable | M6 | `/events` | Table shows events; filters work |
| Afternoon | M6: Event detail page — full event + AI breakdown | M6 | `/events/{id}` | Detail page shows all fields + credibility reasons |
| Afternoon | M6: Citizen form — submit report, upload photos | M6 | `/citizen-reports` | Form submits; event appears in pipeline |
| Afternoon | M6: Admin panel — login, verify/reject/flag actions | M6 | `/verification` | Admin can change event status |
| Afternoon | M6: Analytics charts — time series, category distribution | M6 | `/events/stats` | Charts render correctly |
| **EOD** | **Demo checkpoint: complete user journey** | **ALL** | — | **Citizen submits report → appears on dashboard → admin verifies** |

### Day 5 — Integration + Testing + Demo Prep

**Goal:** Production-ready MVP; all tests pass; demo rehearsed.

| Time Block | Task | Owner | Depends On | Acceptance Criterion |
|-----------|------|-------|------------|---------------------|
| Morning | ALL: Fix integration bugs from Day 4 | ALL | — | All services communicate correctly |
| Morning | M1: Synthetic data generator — 1M+ records to `/data/synthetic/` | M1 | — | Parquet file exists; `source_type: "synthetic"` |
| Morning | M4: Demo scenarios — verify all 5 scenarios from `05_AI_ML_SPEC.md §26` | M4 | ML + DB populated | All scenarios produce expected outputs |
| Morning | M4: Offline training pipeline — if labelled data available, run `training/train.py` to produce `models/event_classifier/model.pkl`; evaluate against rule-based baseline | M4 | Labelled data + `05_AI_ML_SPEC.md §19` | Model artifact exists; F1 exceeds rule-based baseline; `CLASSIFIER_BACKEND` can be switched to `trained` |
| Midday | M1: Load test — produce synthetic events; measure throughput | M1 | Synthetic data | Throughput documented; no crashes |
| Midday | M3: Spark failure recovery test — kill/restart Spark; verify checkpoint | M3 | — | Events not lost; no duplicates in DB |
| Midday | M5: API failure tests — malformed JSON, invalid UUID, missing auth | M5 | — | Correct error responses per API contract |
| Afternoon | M6: UI polish — loading states, error states, responsive layout | M6 | — | No blank screens; graceful error handling |
| Afternoon | ALL: Run `smoke-test.sh` — full end-to-end verification | M1 | All services | All checks pass |
| Afternoon | ALL: Rehearse demo — timing, talking points, fallback plan | M1 | — | Demo runs in < 5 minutes |
| **EOD** | **Demo checkpoint: MVP complete** | **ALL** | — | **All Day-1 through Day-5 criteria met** |

---

## 4. Dependency Graph

```
                        ┌─────────────────────┐
                        │  02_DATA_SCHEMA.md   │
                        │  01_ARCHITECTURE.md  │
                        │  03_KAFKA_CONTRACT.md│
                        └─────────┬───────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Docker +  │ │  Kafka   │ │PostgreSQL│
              │ Infrastructure│ Topics │ │ Schema   │
              └─────┬────┘ └────┬─────┘ └────┬─────┘
                    │           │            │
              ┌─────┘     ┌─────┘            │
              ▼           ▼                  │
        ┌──────────┐ ┌──────────┐            │
        │ ML Lib   │ │ Ingestion│            │
        │ (M4)     │ │ (M2)     │            │
        └────┬─────┘ └────┬─────┘            │
             │            │                  │
             ▼            ▼                  │
        ┌──────────────────────┐             │
        │  Spark Stream Proc   │             │
        │  (M3)                │             │
        └──────────┬───────────┘             │
                   │                         │
                   ▼                         │
        ┌──────────────────────┐             │
        │  weather.events      │             │
        │  (Kafka topic)       │             │
        └──────────┬───────────┘             │
                   │                         │
                   ▼                         │
        ┌──────────────────────┐             │
        │  PostgreSQL Writer   │◄────────────┘
        │  (M3/M5)             │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  PostgreSQL/PostGIS  │
        └──────────┬───────────┘
                   │
        ┌──────────┼───────────┐
        ▼          ▼           ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ FastAPI  │ │ Citizen  │ │ Admin    │
  │ (M5)     │ │ Reports  │ │ Verify   │
  └────┬─────┘ └──────────┘ └──────────┘
       │
       ▼
  ┌──────────┐
  │ React    │
  │ (M6)     │
  └──────────┘
```

### Parallelizable Work

| Track A (Sequential) | Track B (Parallel) | Track C (Parallel) |
|---------------------|--------------------|--------------------|
| Docker + Kafka setup | PostgreSQL schema + init SQL | ML library (all 5 modules) |
| Ingestion adapters | API skeleton + health endpoint | Frontend skeleton |
| Spark stream processor | API endpoints (full) | Frontend panels |
| PostgreSQL writer | API testing | Frontend integration |

**Key parallelism:** M2 (ingestion), M4 (ML), and M5 (API schema) can all work independently on Day 1 morning. M3 (Spark) needs both M2 (producing events) and M4 (ML functions) before full integration.

---

## 5. Day-1 Vertical Slice

### Minimum Implementation

Prove one event traverses all five layers:

```
Source Adapter (Open-Meteo or synthetic)
  → weather.raw (Kafka)
  → Spark: validate + clean + classify_event + score_credibility + generate_reasons
           + compute_duplicate_score + assign_cluster
  → weather.events (Kafka, ai.* fully populated)
  → PostgreSQL Writer
  → PostgreSQL/PostGIS (events table)
  → GET /events (FastAPI :8000)
  → Dashboard event list (React :5173)
```

### Step-by-Step Day-1 Build Order

| Step | Service | Command | Verification |
|------|---------|---------|-------------|
| 1 | Kafka | `docker compose up zookeeper kafka kafka-ui` | kafka-ui at `localhost:8080` shows 0 topics |
| 2 | PostgreSQL | `docker compose up postgres` | Container healthy |
| 3 | Init DB | `docker exec -i postgres psql -U weather -d weatherdb < sql/init.sql` | `SELECT table_name FROM information_schema.tables` shows 4 tables |
| 4 | Kafka topics | `bash scripts/init-kafka.sh` | `kafka-topics --list` shows 7 topics |
| 5 | Spark | `docker compose up spark-master spark-worker` | Spark UI at `localhost:8081` |
| 6 | ML library | `docker build -t spark-ml services/spark/` | Image builds without errors |
| 7 | Ingestion | `docker compose up ingestion` | One event appears in `weather.raw` (check kafka-ui) |
| 8 | Spark job | Submit streaming job to Spark | Event consumed; published to `weather.events` |
| 9 | PG Writer | Start writer consumer | `SELECT * FROM events` returns 1 row |
| 10 | API | `docker compose up api` | `curl localhost:8000/api/v1/health` → 200 |
| 11 | Events | `curl localhost:8000/api/v1/events` | Returns the test event with `ai.*` fields populated |
| 12 | Frontend | `docker compose up frontend` | Dashboard at `localhost:5173` shows 1 event |

### Success Criteria

- [ ] One valid event exists in `events` table with all fields populated
- [ ] `ai.classified_category` is a valid enum value
- [ ] `ai.credibility_score` is between 0.0 and 1.0
- [ ] `ai.credibility_reasons` contains at least 1 string
- [ ] `geom` column is auto-populated by `sync_geom` trigger
- [ ] `GET /events` returns the event
- [ ] Dashboard renders the event in the table

---

## 6. Environment Configuration

### `.env.example` (Committed Without Values)

```bash
# ─── PostgreSQL ───────────────────────────────────────
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=weatherdb
POSTGRES_USER=weather
POSTGRES_PASSWORD=                  # REQUIRED — no default
DATABASE_URL=postgresql://weather:${POSTGRES_PASSWORD}@postgres:5432/weatherdb

# ─── Kafka ────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_AUTO_CREATE_TOPICS_ENABLE=false

# ─── FastAPI ──────────────────────────────────────────
API_PORT=8000
JWT_SECRET_KEY=                    # REQUIRED — app refuses to start without it
JWT_EXPIRATION_HOURS=8
ADMIN_USERNAME=admin
ADMIN_PASSWORD=                    # REQUIRED — bcrypt hash

# ─── CORS ─────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173

# ─── Ingestion ────────────────────────────────────────
OPENMETEO_POLL_INTERVAL_SECONDS=300
RSS_POLL_INTERVAL_SECONDS=300

# ─── Spark ────────────────────────────────────────────
SPARK_WRITE_PROCESSED_TOPIC=false
SPARK_CHECKPOINT_PATH=/data/checkpoints/spark_streaming
PG_WRITER_CHECKPOINT_PATH=/data/checkpoints/pg_writer

# ─── ML Configuration ─────────────────────────────────
ML_CLUSTER_RADIUS_KM=3.0
ML_CLUSTER_TIME_WINDOW_MINUTES=30
ML_RECENT_EVENTS_WINDOW_MINUTES=30

# ─── Media Upload ─────────────────────────────────────
MEDIA_MAX_IMAGE_SIZE_MB=5
MEDIA_MAX_VIDEO_SIZE_MB=20
MEDIA_UPLOAD_PATH=/data/media

# ─── Storage ──────────────────────────────────────────
DATA_RAW_PATH=/data/raw
DATA_PROCESSED_PATH=/data/processed
DATA_SYNTHETIC_PATH=/data/synthetic
DATA_LOGS_PATH=/data/logs
```

### Variable Consistency Check

| Variable | Docker Compose | Application Code | Consistent? |
|----------|---------------|-----------------|-------------|
| `POSTGRES_HOST` | `postgres` service name | `config.py` → `settings.postgres_host` | ✅ |
| `DATABASE_URL` | `api.environment` | `dependencies.py` → `get_db()` | ✅ |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` in all services | `kafka_producer.py` / `spark_config.yaml` | ✅ |
| `JWT_SECRET_KEY` | `api.environment` | `config.py` → `settings.jwt_secret_key` | ✅ |
| `CORS_ORIGINS` | N/A | `main.py` → CORS middleware | ✅ |

---

## 7. Docker Implementation

### `docker-compose.yml` Specification

```yaml
version: "3.8"

services:
  # ── Zookeeper ──────────────────────────────────────
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    healthcheck:
      test: ["CMD", "echo", "ruok", "|", "nc", "localhost", "2181"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── Kafka ──────────────────────────────────────────
  kafka:
    image: confluentinc/cp-kafka:7.6
    depends_on:
      zookeeper:
        condition: service_healthy
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
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 30s

  # ── Kafka UI ───────────────────────────────────────
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    depends_on:
      kafka:
        condition: service_healthy
    environment:
      KAFKA_CLUSTERS_0_NAME: weather-platform
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
    ports:
      - "8080:8080"

  # ── PostgreSQL + PostGIS ───────────────────────────
  postgres:
    image: postgis/postgis:15-3.4
    environment:
      POSTGRES_DB: weatherdb
      POSTGRES_USER: weather
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U weather -d weatherdb"]
      interval: 5s
      timeout: 5s
      retries: 10

  # ── Spark Master ───────────────────────────────────
  spark-master:
    image: bitnami/spark:3.5
    environment:
      SPARK_MODE: master
    ports:
      - "7077:7077"
      - "8081:8081"

  # ── Spark Worker ───────────────────────────────────
  spark-worker:
    image: bitnami/spark:3.5
    depends_on:
      - spark-master
    environment:
      SPARK_MODE: worker
      SPARK_MASTER_URL: spark://spark-master:7077
    ports:
      - "8082:8082"

  # ── Ingestion Service ──────────────────────────────
  ingestion:
    build: ./services/ingestion
    depends_on:
      kafka:
        condition: service_healthy
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      OPENMETEO_POLL_INTERVAL_SECONDS: ${OPENMETEO_POLL_INTERVAL_SECONDS:-300}
    volumes:
      - ./data/raw:/data/raw
      - ./data/logs:/data/logs
    restart: unless-stopped

  # ── FastAPI Backend ────────────────────────────────
  api:
    build: ./services/api
    depends_on:
      kafka:
        condition: service_healthy
      postgres:
        condition: service_healthy
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      JWT_EXPIRATION_HOURS: ${JWT_EXPIRATION_HOURS:-8}
      ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:5173}
      MEDIA_UPLOAD_PATH: ${MEDIA_UPLOAD_PATH:-/data/media}
    ports:
      - "8000:8000"
    volumes:
      - ./data/media:/data/media
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── React Frontend ─────────────────────────────────
  frontend:
    build: ./services/frontend
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000/api/v1

volumes:
  pgdata:
```

### Network

All services communicate on the default Docker Compose network.
Inter-service communication uses service names (e.g., `kafka:9092`, `postgres:5432`).

---

## 8. Local Startup Sequence

### Prerequisites

```bash
# Required software
docker --version          # Docker Engine 24+
docker compose version    # Docker Compose v2
git --version
```

### Step 1: Clone and Configure

```bash
git clone <repo-url>
cd weather-platform
cp .env.example .env
# Edit .env — set at minimum:
#   POSTGRES_PASSWORD=<your-password>
#   JWT_SECRET_KEY=$(openssl rand -hex 32)
#   ADMIN_PASSWORD=$(python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('<your-password>'))")
```

### Step 2: Start Infrastructure

```bash
# Start Kafka ecosystem
docker compose up -d zookeeper kafka kafka-ui
# Wait for Kafka to be healthy (~30 seconds)
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Start PostgreSQL
docker compose up -d postgres
# Wait for healthy (~10 seconds)
docker compose exec postgres pg_isready -U weather -d weatherdb
```

### Step 3: Initialize Database

```bash
# Tables, indexes, triggers — all created by init.sql mounted as entrypoint
# Verify:
docker compose exec postgres psql -U weather -d weatherdb -c "\dt"
# Should show: events, event_clusters, sources, verification_log
```

### Step 4: Create Kafka Topics

```bash
bash scripts/init-kafka.sh
# Or manually:
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic weather.raw --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic citizen.raw --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic social.raw --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic government.raw --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic weather.processed --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic weather.events --partitions 1 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic weather.verified --partitions 1 --replication-factor 1
```

### Step 5: Start Spark

```bash
docker compose up -d spark-master spark-worker
# Verify Spark UI at http://localhost:8081
```

### Step 6: Build and Start Ingestion

```bash
docker compose up -d ingestion
# Check logs for successful produce:
docker compose logs -f ingestion
# Check kafka-ui for events in weather.raw
```

### Step 7: Start Spark Streaming Job

```bash
# Submit the Spark job (details depend on Spark Dockerfile setup)
docker compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  /opt/spark/jobs/stream_processor.py
```

### Step 8: Start PostgreSQL Writer

```bash
# In separate terminal or as part of Spark job
docker compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  /opt/spark/jobs/pg_writer.py
```

### Step 9: Start API

```bash
docker compose up -d api
# Verify:
curl http://localhost:8000/api/v1/health
# Should return: {"status":"healthy","database":"connected","kafka":"connected",...}
```

### Step 10: Start Frontend

```bash
docker compose up -d frontend
# Open http://localhost:5173
```

### Step 11: Smoke Test

```bash
bash scripts/smoke-test.sh
# Checks:
#   - Kafka topics exist
#   - PostgreSQL tables exist
#   - API health endpoint returns 200
#   - At least 1 event in database
#   - Frontend returns HTML
```

---

## 9. Database Initialization

### `sql/init.sql` — Complete Script

Respects `02_DATA_SCHEMA.md §17` exactly.

```sql
-- ============================================================
-- STEP 1: Extensions (must come before any table or function)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- STEP 2: Helper functions
-- ============================================================
CREATE OR REPLACE FUNCTION sync_geom()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- STEP 3: Tables (in dependency order)
-- ============================================================
-- 3a. event_clusters (no FK dependencies)
CREATE TABLE IF NOT EXISTS event_clusters (
    cluster_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    representative_id   UUID,
    event_category      TEXT NOT NULL,
    city                TEXT,
    state               TEXT,
    centroid_geom       GEOMETRY(Point, 4326),
    member_count        INTEGER NOT NULL DEFAULT 1,
    first_event_at      TIMESTAMPTZ NOT NULL,
    last_event_at       TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3b. events (FK → event_clusters)
CREATE TABLE IF NOT EXISTS events (
    event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           TEXT NOT NULL,
    source_type         TEXT NOT NULL
                            CHECK (source_type IN (
                                'weather_api','rss','website','social',
                                'simulated_social','government_dataset',
                                'citizen','synthetic'
                            )),
    source_name         TEXT NOT NULL,
    source_url          TEXT,
    source_trust_score  NUMERIC(4,3) CHECK (source_trust_score BETWEEN 0 AND 1),
    event_timestamp     TIMESTAMPTZ NOT NULL,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latitude            NUMERIC(9,6) CHECK (latitude BETWEEN -90 AND 90),
    longitude           NUMERIC(10,6) CHECK (longitude BETWEEN -180 AND 180),
    city                TEXT,
    district            TEXT,
    state               TEXT,
    country             TEXT NOT NULL DEFAULT 'India',
    geom                GEOMETRY(Point, 4326),
    event_category      TEXT NOT NULL
                            CHECK (event_category IN (
                                'rainfall','heavy_rainfall','flood',
                                'thunderstorm','lightning','heatwave',
                                'fog','dust_storm','strong_wind',
                                'hailstorm','cyclone','other'
                            )),
    severity            TEXT CHECK (severity IN ('low','moderate','high','extreme')),
    description         TEXT CHECK (char_length(description) <= 2000),
    hashtags            TEXT[],
    author_id           TEXT,
    platform            TEXT,
    photo_urls          TEXT[],
    video_urls          TEXT[],
    classified_category       TEXT CHECK (classified_category IN (
                                'rainfall','heavy_rainfall','flood',
                                'thunderstorm','lightning','heatwave',
                                'fog','dust_storm','strong_wind',
                                'hailstorm','cyclone','other'
                              )),
    classification_confidence NUMERIC(4,3) CHECK (classification_confidence BETWEEN 0 AND 1),
    duplicate_score           NUMERIC(4,3) CHECK (duplicate_score BETWEEN 0 AND 1),
    credibility_score         NUMERIC(4,3) CHECK (credibility_score BETWEEN 0 AND 1),
    credibility_reasons       TEXT[],
    cluster_id                UUID REFERENCES event_clusters(cluster_id) ON DELETE SET NULL,
    verification_status     TEXT NOT NULL DEFAULT 'pending'
                                CHECK (verification_status IN (
                                    'pending','verified','needs_review',
                                    'suspicious','duplicate'
                                )),
    verified_by             TEXT,
    verification_timestamp  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3c. sources (no FK dependencies)
CREATE TABLE IF NOT EXISTS sources (
    source_name         TEXT PRIMARY KEY,
    source_type         TEXT NOT NULL,
    base_url            TEXT,
    trust_score         NUMERIC(4,3) NOT NULL DEFAULT 0.5
                            CHECK (trust_score BETWEEN 0 AND 1),
    total_reports       INTEGER NOT NULL DEFAULT 0,
    verified_reports    INTEGER NOT NULL DEFAULT 0,
    rejected_reports    INTEGER NOT NULL DEFAULT 0,
    last_seen_at        TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3d. verification_log (FK → events)
CREATE TABLE IF NOT EXISTS verification_log (
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    action          TEXT NOT NULL
                        CHECK (action IN (
                            'verified','rejected','marked_suspicious','marked_duplicate'
                        )),
    performed_by    TEXT NOT NULL,
    notes           TEXT,
    performed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- STEP 4: Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_events_geom ON events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_category ON events (event_category);
CREATE INDEX IF NOT EXISTS idx_events_verification_status ON events (verification_status);
CREATE INDEX IF NOT EXISTS idx_events_city ON events (city);
CREATE INDEX IF NOT EXISTS idx_events_cluster_id ON events (cluster_id);
CREATE INDEX IF NOT EXISTS idx_events_source_name ON events (source_name);
CREATE INDEX IF NOT EXISTS idx_events_source_id ON events (source_id);
CREATE INDEX IF NOT EXISTS idx_events_source_type ON events (source_type);
CREATE INDEX IF NOT EXISTS idx_clusters_centroid ON event_clusters USING GIST (centroid_geom);
CREATE INDEX IF NOT EXISTS idx_verification_log_event_id ON verification_log (event_id);

-- ============================================================
-- STEP 5: Triggers
-- ============================================================
CREATE TRIGGER trg_sync_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude
    ON events
    FOR EACH ROW EXECUTE FUNCTION sync_geom();

CREATE TRIGGER trg_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_event_clusters_updated_at
    BEFORE UPDATE ON event_clusters
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- STEP 6: Seed source records
-- ============================================================
INSERT INTO sources (source_name, source_type, base_url, trust_score, notes)
VALUES
    ('Open-Meteo', 'weather_api', 'https://api.open-meteo.com', 0.95, 'Primary weather data source'),
    ('citizen_form', 'citizen', NULL, 0.60, 'Citizen web form submissions')
ON CONFLICT (source_name) DO NOTHING;
```

---

## 10. Kafka Initialization

### `scripts/init-kafka.sh`

```bash
#!/bin/bash
set -e

BOOTSTRAP="kafka:9092"

TOPICS=(
  "weather.raw:1:1:168h"
  "citizen.raw:1:1:168h"
  "social.raw:1:1:168h"
  "government.raw:1:1:168h"
  "weather.processed:1:1:24h"
  "weather.events:1:1:168h"
  "weather.verified:1:1:720h"
)

for topic_config in "${TOPICS[@]}"; do
  IFS=':' read -r name partitions replication retention <<< "$topic_config"
  echo "Creating topic: $name (partitions=$partitions, replication=$replication, retention=$retention)"
  kafka-topics --bootstrap-server "$BOOTSTRAP" \
    --create --if-not-exists \
    --topic "$name" \
    --partitions "$partitions" \
    --replication-factor "$replication" \
    --config "retention.ms=$(echo "$retention" | sed 's/h/*3600000/' | bc)" \
    2>/dev/null || echo "  Topic $name already exists or creation deferred"
done

echo "All topics created. Listing:"
kafka-topics --bootstrap-server "$BOOTSTRAP" --list
```

### Topic Summary

| Topic | Partitions | Replication | Retention | Key | Consumer Group |
|-------|-----------|-------------|-----------|-----|---------------|
| `weather.raw` | 1 | 1 | 7 days | `event_id` | `spark-processing` |
| `citizen.raw` | 1 | 1 | 7 days | `event_id` | `spark-processing` |
| `social.raw` | 1 | 1 | 7 days | `event_id` | `spark-processing` |
| `government.raw` | 1 | 1 | 7 days | `event_id` | `spark-processing` |
| `weather.processed` | 1 | 1 | 24 hours | `event_id` | `monitoring-debug` |
| `weather.events` | 1 | 1 | 7 days | `event_id` | `postgres-writer` |
| `weather.verified` | 1 | 1 | 30 days | `event_id` | `audit-consumer` |

---

## 11. Ingestion Implementation

### Adapter Priority (Build Order)

| Priority | Adapter | Topic | Complexity | Day |
|----------|---------|-------|-----------|-----|
| 1 | Open-Meteo (`weather_api`) | `weather.raw` | Low | 1 |
| 2 | Simulated social feed | `social.raw` | Low | 2 |
| 3 | RSS feeds | `weather.raw` | Medium | 2 |
| 4 | Website allowlist | `weather.raw` | Medium | 2 |
| 5 | Government dataset | `government.raw` | Low | 2 |
| 6 | Citizen reports (via API) | `citizen.raw` | Medium | 4 |

### Per-Adapter Specification

#### Open-Meteo Adapter

| Aspect | Detail |
|--------|--------|
| **Input** | HTTP GET `https://api.open-meteo.com/v1/forecast?latitude=...&longitude=...&current_weather=true` |
| **Poll interval** | Every 5 minutes |
| **Cities** | Mumbai (19.076, 72.878), Nagpur (21.146, 79.088), Nashik (19.997, 73.789) |
| **Transformation** | Map Open-Meteo fields → Canonical Weather Event; infer `event.category` from weather codes |
| **Output** | Valid Canonical Weather Event to `weather.raw` |
| **Error handling** | HTTP timeout (10s) → log warning, skip cycle; malformed response → log, skip |
| **Retry** | Next poll cycle (5 min) |
| **Logging** | `INFO` each successful produce; `WARNING` each failure |
| **Test data** | Use live API; no mock needed |

#### Simulated Social Feed

| Aspect | Detail |
|--------|--------|
| **Input** | Local JSON file `services/ingestion/config/simulated_social_feed.json` |
| **Produce to** | `social.raw` |
| **source_type** | `"simulated_social"` |
| **platform** | `"simulated"` |
| **Transformation** | Map JSON fields → Canonical Weather Event |
| **Output** | Valid Canonical Weather Event to `social.raw` |
| **Error handling** | Parse failure → log, skip record |

#### RSS Feed Adapter

| Aspect | Detail |
|--------|--------|
| **Input** | Public RSS feeds (IMD, NDTV Weather, etc.) |
| **Parser** | `feedparser` Python library |
| **Produce to** | `weather.raw` |
| **source_type** | `"rss"` |
| **Transformation** | Extract title, description, pubDate → Canonical Weather Event; NLP keyword extraction for category |
| **Output** | Valid Canonical Weather Event to `weather.raw` |
| **Error handling** | Feed unreachable → log, retry next cycle; parse error → log, skip item |

#### Website Scraper

| Aspect | Detail |
|--------|--------|
| **Input** | URLs in `services/ingestion/config/website_allowlist.json` |
| **HTTP client** | `httpx` |
| **Parser** | `BeautifulSoup4` |
| **Produce to** | `weather.raw` |
| **source_type** | `"website"` |
| **Transformation** | Scrape page text → extract weather info → Canonical Weather Event |
| **Error handling** | HTTP error → log, skip; parse error → log, skip |
| **Respect** | `robots.txt`; rate-limit requests |

#### Government Dataset

| Aspect | Detail |
|--------|--------|
| **Input** | CSV/JSON/Parquet files in `/data/raw/government/` |
| **Produce to** | `government.raw` |
| **source_type** | `"government_dataset"` |
| **Transformation** | Read file → map columns → Canonical Weather Event |
| **Error handling** | File parse error → log, skip file; schema mismatch → log, skip record |

### Canonical Event Builder (Shared)

All adapters use `services/ingestion/normaliser/canonical_event.py`:

```python
def build_canonical_event(
    source_type: str,
    source_name: str,
    source_id: str,
    description: str,
    category: str,
    location: dict,
    timestamp: str,
    source_url: str = None,
    severity: str = None,
    hashtags: list = None,
) -> dict:
    """Build a Canonical Weather Event matching 02_DATA_SCHEMA.md §2."""
    return {
        "event_id": str(uuid.uuid4()),
        "source_id": source_id,
        "source_type": source_type,
        "source_name": source_name,
        "source_url": source_url,
        "source_trust_score": None,
        "timestamp": timestamp,
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "location": {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "city": location.get("city"),
            "district": location.get("district"),
            "state": location.get("state"),
            "country": location.get("country", "India"),
        },
        "event": {
            "category": category,
            "severity": severity,
            "description": description,
        },
        "social_metadata": {
            "hashtags": hashtags or [],
            "author_id": None,
            "platform": None,
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
```

---

## 12. Spark Implementation

### Processing Pipeline

```
Kafka (weather.raw / citizen.raw / social.raw / government.raw)
  ↓
Deserialise envelope (03_KAFKA_CONTRACT.md §3)
  ↓
Validate against 02_DATA_SCHEMA.md §11 rules
  ↓
  ├── FAIL → write to /data/logs/dead_letter/YYYY-MM-DD/<source>_failures.jsonl
  └── PASS ↓
Clean + normalise timestamps to UTC
  ↓
Hash-based deduplication (event_id check)
  ↓
ML enrichment (within foreachBatch):
  ├── classify_event()        → ai.classified_category, ai.classification_confidence
  ├── score_credibility()     → ai.credibility_score
  ├── generate_reasons()      → ai.credibility_reasons
  ├── compute_duplicate_score() → ai.duplicate_score
  └── assign_cluster()        → ai.cluster_id
  ↓
[Optional] Write to weather.processed (if SPARK_WRITE_PROCESSED_TOPIC=true)
  ↓
Write to weather.events (with event_id as Kafka key)
  ↓
Write Parquet to /data/processed/weather_events/year=YYYY/month=MM/day=DD/
  ↓
Update in-memory recent events window
```

### Dead-Letter Format

Per `01_ARCHITECTURE.md §10`:

```json
{
  "failed_at": "2026-08-31T08:16:05.123Z",
  "source_adapter": "ingestion",
  "failure_reasons": ["Invalid UUID v4 in event_id"],
  "original_record": { "...full envelope..." }
}
```

Path: `/data/logs/dead_letter/YYYY-MM-DD/<source_type>_failures.jsonl`

---

## 13. ML Implementation

Per `05_AI_ML_SPEC.md` exactly. No modifications.

### Module Files

| Module | File | Function | Spark Pattern |
|--------|------|----------|--------------|
| Classification | `services/ml/classifier/event_classifier.py` | `classify_event(description, category_hint)` | Pandas UDF |
| Credibility | `services/ml/credibility/credibility_scorer.py` | `score_credibility(event_dict)` | Pandas UDF |
| Dedup | `services/ml/dedup/duplicate_detector.py` | `compute_duplicate_score(event_dict, recent_events)` | foreachBatch |
| Clustering | `services/ml/clustering/event_clusterer.py` | `assign_cluster(event_dict, active_clusters)` | foreachBatch |
| Explainability | `services/ml/explainability/reason_generator.py` | `generate_reasons(event_dict, factors)` | Pandas UDF |

### Dependencies

```
numpy>=1.24
pyyaml>=6.0
```

No sklearn, no torch, no tensorflow, no LLM APIs.

### Test Files

| Test File | Tests |
|-----------|-------|
| `test_classifier.py` | 10+ tests (one per category + edge cases) |
| `test_credibility.py` | 6+ tests (high/low trust, corroboration, weather agreement) |
| `test_dedup.py` | 6+ tests (identical, near-identical, different) |
| `test_clustering.py` | 6+ tests (same location/time, outside radius) |
| `test_explainability.py` | 3+ tests (reasons match evidence) |

---

## 14. PostgreSQL Writer

### Implementation: `services/spark/jobs/pg_writer.py`

| Step | Operation | SQL/Logic |
|------|-----------|-----------|
| 1 | Consume from `weather.events` | Kafka consumer, group `postgres-writer` |
| 2 | Parse JSON envelope | Extract `payload` (Canonical Weather Event) |
| 3 | Flatten nested JSON → flat columns | Per `02_DATA_SCHEMA.md §6 preamble` mapping |
| 4 | Upsert to `events` | `INSERT ... ON CONFLICT (event_id) DO UPDATE SET ...` |
| 5 | Upsert to `event_clusters` | If `cluster_id` is not null; update `member_count`, `centroid_geom`, `last_event_at` |
| 6 | Upsert to `sources` | Increment `total_reports`; update `last_seen_at` |
| 7 | Geometry auto-set | `sync_geom` trigger handles `geom` column |
| 8 | Commit offset | Only after successful DB commit |

### Field Mapping (Nested → Flat)

| JSON Path | DB Column |
|-----------|-----------|
| `event_id` | `event_id` |
| `source_id` | `source_id` |
| `source_type` | `source_type` |
| `source_name` | `source_name` |
| `source_url` | `source_url` |
| `source_trust_score` | `source_trust_score` |
| `timestamp` | `event_timestamp` |
| `ingestion_timestamp` | `ingestion_timestamp` |
| `location.latitude` | `latitude` |
| `location.longitude` | `longitude` |
| `location.city` | `city` |
| `location.district` | `district` |
| `location.state` | `state` |
| `location.country` | `country` |
| `event.category` | `event_category` |
| `event.severity` | `severity` |
| `event.description` | `description` |
| `social_metadata.hashtags` | `hashtags` |
| `social_metadata.author_id` | `author_id` |
| `social_metadata.platform` | `platform` |
| `media.photos` | `photo_urls` |
| `media.videos` | `video_urls` |
| `ai.classified_category` | `classified_category` |
| `ai.classification_confidence` | `classification_confidence` |
| `ai.duplicate_score` | `duplicate_score` |
| `ai.credibility_score` | `credibility_score` |
| `ai.credibility_reasons` | `credibility_reasons` |
| `ai.cluster_id` | `cluster_id` |
| `verification.status` | `verification_status` |
| `verification.verified_by` | `verified_by` |
| `verification.verification_timestamp` | `verification_timestamp` |

### Idempotency

`INSERT ... ON CONFLICT (event_id) DO UPDATE` ensures:
- Duplicate Kafka messages → harmless overwrite
- Spark micro-batch retry → no duplicate rows
- Writer restart → no duplicate rows

### Failure Behaviour

| Failure | Behaviour |
|---------|-----------|
| DB connection lost | Consumer poll loop blocks; resumes on recovery |
| Individual record fails | Log error; skip record; continue batch |
| Transaction failure | Rollback; retry on next poll |
| Kafka offset commit fails | Kafka retries; may reprocess some records on restart |

---

## 15. FastAPI Implementation

### Endpoint → File Mapping

| Endpoint | Route File | Request Schema | Response Schema | Service | DB Query |
|----------|-----------|---------------|----------------|---------|----------|
| `GET /health` | `routers/health.py` | None | `HealthResponse` | Direct DB + Kafka ping | `SELECT 1` |
| `GET /events` | `routers/events.py` | Query params | `EventListResponse` | `event_service.list_events()` | Dynamic `SELECT` with filters |
| `GET /events/{id}` | `routers/events.py` | Path: `event_id` | `EventResponse` | `event_service.get_event()` | `SELECT` + `JOIN verification_log` |
| `GET /events/stats` | `routers/events.py` | Query params | `EventStatsResponse` | `event_service.get_stats()` | `GROUP BY` aggregations |
| `GET /events/map` | `routers/events.py` | Bounding box params | `MapEventResponse` | `event_service.get_map_events()` | PostGIS `ST_MakeEnvelope` |
| `POST /citizen-reports` | `routers/citizen.py` | `CitizenReportRequest` | `CitizenReportResponse` | `citizen_service.submit_report()` | No DB write (Kafka only) |
| `POST /auth/login` | `routers/auth.py` | `LoginRequest` | `TokenResponse` | `auth_service.login()` | None |
| `POST /verification` | `routers/verification.py` | `VerificationRequest` | `VerificationResponse` | `verification_service.verify()` | `UPDATE events` + `INSERT verification_log` |

### No Undocumented Endpoints

Every endpoint is listed above. No additional routes are added.

---

## 16. React Dashboard

### Implementation Priority (Demo-Critical First)

| Priority | Component | Day | Dependencies |
|----------|-----------|-----|-------------|
| 1 | API client (`src/api/client.js`) | 1 | CORS configured in API |
| 2 | Event table with pagination | 1 | `GET /events` |
| 3 | KPI cards | 4 | `GET /events/stats` |
| 4 | Event filters | 2 | `GET /events` query params |
| 5 | Event map (Leaflet) | 3 | `GET /events/map` |
| 6 | Event detail page | 3 | `GET /events/{id}` |
| 7 | AI breakdown display | 3 | `ai.*` fields in detail |
| 8 | Citizen report form | 4 | `POST /citizen-reports` |
| 9 | Admin login | 4 | `POST /auth/login` |
| 10 | Admin verification actions | 4 | `POST /verification` |
| 11 | Analytics charts | 4 | `GET /events/stats` time series |
| 12 | Loading/error states | 5 | All endpoints |
| 13 | Responsive layout polish | 5 | Tailwind CSS |

### Tech Stack (Per Architecture §3)

- React 18+
- Vite (dev server on port 5173)
- Tailwind CSS
- Leaflet (map)
- Chart.js (analytics)

---

## 17. Testing Strategy

### Unit Tests

| Component | Location | Framework | Minimum Count |
|-----------|----------|-----------|--------------|
| ML classifier | `services/ml/tests/test_classifier.py` | `pytest` | 10 (one per category + edges) |
| ML credibility | `services/ml/tests/test_credibility.py` | `pytest` | 6 |
| ML dedup | `services/ml/tests/test_dedup.py` | `pytest` | 6 |
| ML clustering | `services/ml/tests/test_clustering.py` | `pytest` | 6 |
| ML explainability | `services/ml/tests/test_explainability.py` | `pytest` | 3 |
| API schemas | `services/api/tests/` | `pytest` + `httpx` | 5 |
| Canonical event builder | `services/ingestion/tests/` | `pytest` | 3 |

### Integration Tests

| Test | What It Verifies | How |
|------|-----------------|-----|
| Kafka → Spark | Events consumed from raw topics | Produce test event; verify Spark processes it |
| Spark → Kafka | Events published to `weather.events` | Consume from `weather.events`; verify `ai.*` populated |
| Kafka → PostgreSQL | Writer upserts correctly | Query `events` table after produce |
| API → PostgreSQL | Read endpoints return correct data | `GET /events` matches DB contents |

### End-to-End Test

```bash
# scripts/smoke-test.sh
echo "1. Checking Kafka topics..."
kafka-topics --bootstrap-server localhost:29092 --list | wc -l  # Should be 7

echo "2. Checking PostgreSQL tables..."
docker exec postgres psql -U weather -d weatherdb -c "\dt" | grep -c "events"  # Should be 4

echo "3. Checking API health..."
curl -sf http://localhost:8000/api/v1/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] in ('healthy','degraded')"

echo "4. Checking events endpoint..."
curl -sf http://localhost:8000/api/v1/events | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['total'] >= 1"

echo "5. Checking frontend..."
curl -sf http://localhost:5173 | grep -q "<div id=\"root\">"

echo "All smoke tests passed!"
```

### Failure Tests

| Test | Expected Behaviour |
|------|-------------------|
| Malformed JSON to Kafka | Dead-letter file written; pipeline continues |
| Kafka unavailable | Producer retries; consumer blocks |
| PostgreSQL unavailable | Writer retries; events remain in Kafka |
| Invalid coordinates | REJECT rule; dead-letter |
| Duplicate event | Upsert overwrites; no duplicate row |
| Invalid source_type | REJECT rule; dead-letter |
| ML exception | Fields set to null; event preserved |
| API 404 for missing event | `EVENT_NOT_FOUND` error response |

---

## 18. Synthetic Load Test

### Generator: `scripts/generate_synthetic.py`

| Aspect | Detail |
|--------|--------|
| **Output** | Parquet file at `/data/synthetic/weather_events_1m.parquet` |
| **Record count** | 1,000,000+ |
| **source_type** | `"synthetic"` (always) |
| **source_name** | `"synthetic_gen"` (always contains "synthetic") |
| **Distribution** | 40% Mumbai, 35% Nagpur, 25% Nashik |
| **Categories** | Weighted: `heavy_rainfall` 25%, `flood` 15%, `heatwave` 15%, `thunderstorm` 15%, `fog` 10%, `other` 20% |
| **Timestamps** | Spread over 30 days; random within each day |
| **Coordinates** | Gaussian distribution around city centres |
| **Descriptions** | Template-based: "{severity} {category} reported in {city} area" |
| **ai.*** | All null (ML enriches when loaded into pipeline) |
| **Labelling** | `source_type: "synthetic"` — **never** presented as genuine |

### Loading Method

```bash
# Option A: Produce to weather.raw (tagged as synthetic)
python3 scripts/generate_synthetic.py --output kafka --topic weather.raw --count 1000000

# Option B: Write directly to Parquet (bypass pipeline)
python3 scripts/generate_synthetic.py --output parquet --path /data/synthetic/ --count 1000000
```

### Performance Measurement

- Document throughput (records/second) after actual measurement
- Do NOT claim performance numbers until measured
- Measure: ingestion rate, Spark processing rate, PostgreSQL write rate

---

## 19. Observability

### Metrics Production

| Metric | Producer | Where to Inspect |
|--------|----------|-----------------|
| `records_ingested` (per source_type) | Ingestion service | Docker logs + `/data/logs/app/` |
| `records_validated` | Spark stream_processor | Spark UI → Structured Streaming tab |
| `records_rejected` | Spark stream_processor | `/data/logs/dead_letter/` file count |
| `records_processed` | Spark stream_processor | Spark UI metrics |
| `duplicates_detected` | ML dedup module | Spark logs (WARNING level) |
| `events_classified` | ML classifier | Spark logs (INFO level) |
| `events_clustered` | ML clustering | Spark logs (INFO level) |
| `events_verified` | FastAPI verification endpoint | PostgreSQL `verification_log` count |

### Access Points

| Signal | Source | Access Method |
|--------|--------|--------------|
| Ingestion counts | Docker logs | `docker compose logs -f ingestion` |
| Kafka lag/messages | kafka-ui | `http://localhost:8080` |
| Spark job status | Spark UI | `http://localhost:8081` |
| Dead-letter count | Filesystem | `find /data/logs/dead_letter -name "*.jsonl" | wc -l` |
| API health | API | `curl http://localhost:8000/api/v1/health` |
| PostgreSQL | pg logs | `docker compose logs postgres` |

---

## 20. Demo Acceptance Checklist

| # | Criterion | Verified By | Status |
|---|-----------|-------------|--------|
| 1 | `docker compose up` starts all services without errors | M1 | ☐ |
| 2 | Kafka is healthy (7 topics exist) | M1 | ☐ |
| 3 | PostgreSQL/PostGIS is healthy (4 tables, 11 indexes, 4 triggers) | M3/M5 | ☐ |
| 4 | Spark processes events (Spark UI shows streaming activity) | M3 | ☐ |
| 5 | ML enrichment appears (`ai.*` fields populated) | M4 | ☐ |
| 6 | Events reach PostgreSQL (`SELECT count(*) FROM events` > 0) | M3/M5 | ☐ |
| 7 | API returns events (`GET /events` returns data) | M5 | ☐ |
| 8 | Map displays events (Leaflet markers at correct coordinates) | M6 | ☐ |
| 9 | Filters work (city, category, severity, time range) | M6 | ☐ |
| 10 | Event details show AI reasoning (credibility reasons, classification) | M6 | ☐ |
| 11 | Citizen report works (submit → appears in pipeline within 5 sec) | M5/M6 | ☐ |
| 12 | Admin verification works (login → verify → status changes) | M5/M6 | ☐ |
| 13 | Duplicate detection works (same event twice → high duplicate_score) | M4 | ☐ |
| 14 | Dead-letter handling works (malformed event → logged, pipeline continues) | M3 | ☐ |
| 15 | Synthetic data is clearly labelled (`source_type: "synthetic"` in all views) | M1/M6 | ☐ |
| 16 | No secrets committed (`.env` gitignored; `.env.example` has no values) | M1 | ☐ |
| 17 | Swagger docs accessible (`http://localhost:8000/docs`) | M5 | ☐ |
| 18 | All 5 demo scenarios from `05_AI_ML_SPEC.md §26` produce expected outputs | M4 | ☐ |

---

## 21. Definition of Done

The MVP is declared complete when ALL of the following are true:

1. **Infrastructure:** `docker compose up` starts all 9 services without errors.
2. **Kafka:** All 7 topics exist and accept messages.
3. **PostgreSQL:** All 4 tables created with constraints, indexes, and triggers.
4. **Ingestion:** At least 3 source adapters producing valid Canonical Weather Events.
5. **Spark:** Streaming job consumes raw topics, validates, and publishes to `weather.events`.
6. **ML:** All 5 ML functions operational; `ai.*` fields populated on events.
7. **PostgreSQL Writer:** Events upserted to database; `geom` auto-populated.
8. **API:** All 8 endpoints functional; match `04_API_CONTRACT.md` exactly.
9. **Frontend:** Dashboard shows events; map renders; filters work; citizen form submits; admin verifies.
10. **Dead-letter:** Malformed events logged to filesystem; pipeline continues.
11. **Testing:** All unit tests pass; smoke test passes.
12. **Demo:** One complete user journey rehearsed in < 5 minutes.
13. **Security:** No secrets committed; `.env` gitignored; JWT auth on admin endpoints.
14. **Documentation:** All 6 docs (`00`–`06`) committed and consistent.

---

## 22. Remaining Risks

| # | Risk | Impact | Mitigation | Owner |
|---|------|--------|-----------|-------|
| 1 | Open-Meteo API rate limiting or downtime during demo | No live weather data | Pre-record 1 hour of data to `weather.raw` as fallback | M2 |
| 2 | Spark Docker image build fails due to ML dependency conflicts | ML cannot run in Spark | Test build on Day 1 morning; pin numpy/pyyaml versions | M3/M4 |
| 3 | PostGIS `ST_MakeEnvelope` query slow without proper index | Map loads slowly | Ensure `idx_events_geom` GIST index exists; test with 1000+ events | M5 |
| 4 | Kafka topic not pre-created before producers start | Ingestion crashes | `init-kafka.sh` runs before any service; add `depends_on` healthcheck | M1 |
| 5 | JWT secret not set → API refuses to start | API unavailable | Document in README; fail fast with clear error message | M5 |
| 6 | Circular FK between `events.cluster_id` and `event_clusters.representative_id` | DB init failure | `representative_id` has NO FK (per `02_DATA_SCHEMA.md §6.2`); use application-level integrity | M3/M5 |
| 7 | In-memory recent events window lost on Spark restart | Dedup/clustering temporarily ineffective | Window rebuilds from scratch; events still processed (just no dedup for first few minutes) | M3/M4 |
| 8 | Micro-batch trigger interval too slow for demo responsiveness | Events appear slowly | Use processing time trigger with 5-second interval; tune on Day 3 | M3 |

---

## Consistency Check

### Against `01_ARCHITECTURE.md`

| Check | Result | Notes |
|-------|--------|-------|
| All 9 Docker services match §5 | ✅ PASS | zookeeper, kafka, kafka-ui, postgres, spark-master, spark-worker, ingestion, api, frontend |
| Ports match §5 | ✅ PASS | 2181, 9092/29092, 8080, 5432, 7077/8081, 8082, 8000, 5173 |
| ML as library (no Docker service) | ✅ PASS | ML COPY-ed into Spark image per §5 note |
| Dead-letter filesystem only | ✅ PASS | §10 followed exactly |
| Day-1 checklist matches §14 | ✅ PASS | Same 8-step deployment order |
| API endpoints match §3 diagram | ✅ PASS | All 7 endpoints implemented |
| Data lake paths match §8 | ✅ PASS | `/data/raw/`, `/data/processed/`, `/data/synthetic/`, `/data/media/`, `/data/logs/` |

### Against `02_DATA_SCHEMA.md`

| Check | Result | Notes |
|-------|--------|-------|
| `init.sql` matches §17 exactly | ✅ PASS | Same extensions, functions, tables, indexes, triggers |
| JSON→DB mapping matches §6 preamble | ✅ PASS | All 32 field mappings documented in §14 |
| CHECK constraints preserved | ✅ PASS | All enum CHECKs, range CHECKs present |
| Verification log actions match §6.5 | ✅ PASS | `verified`, `rejected`, `marked_suspicious`, `marked_duplicate` |

### Against `03_KAFKA_CONTRACT.md`

| Check | Result | Notes |
|-------|--------|-------|
| All 7 topics created with correct config | ✅ PASS | §10 matches §2.2 exactly |
| Envelope format used | ✅ PASS | §12 Spark pipeline deserialises envelope |
| `weather.events` is sole DB input topic | ✅ PASS | Writer consumes only `weather.events` |
| `weather.verified` carries verification action | ✅ PASS | API produces to this topic on admin action |
| Consumer groups match §9 | ✅ PASS | `spark-processing`, `postgres-writer` defined |

### Against `04_API_CONTRACT.md`

| Check | Result | Notes |
|-------|--------|-------|
| All 8 endpoints implemented | ✅ PASS | §15 maps every endpoint to files |
| Pydantic models match §16 | ✅ PASS | Request/response schemas defined |
| JWT auth on `/verification` | ✅ PASS | §7 public/protected split followed |
| CORS for `localhost:5173` | ✅ PASS | §20 CORS config in docker-compose |
| Error responses match §5 | ✅ PASS | Consistent error structure |

### Against `05_AI_ML_SPEC.md`

| Check | Result | Notes |
|-------|--------|-------|
| ML functions match §2.3 signatures | ✅ PASS | `classify_event`, `score_credibility`, `compute_duplicate_score`, `assign_cluster`, `generate_reasons` |
| Package structure matches §17 | ✅ PASS | Identical directory layout |
| All 5 module files created | ✅ PASS | classifier, credibility, dedup, clustering, explainability |
| Config files match §22 | ✅ PASS | `ml_config.yaml`, `source_trust.yaml`, `india_cities.json` |
| Tests match §25 | ✅ PASS | All test files and minimum counts specified |
| Dependencies = numpy + pyyaml only | ✅ PASS | No ML frameworks |

### Summary

| Document | Contradictions | Assumptions | Decisions Closed | Remaining Blockers |
|----------|---------------|-------------|-----------------|-------------------|
| `01_ARCHITECTURE.md` | 0 | 0 | 0 | Open Q #5 (website allowlist), #6 (weather codes), #7 (R2), #8 (micro-batch interval) |
| `02_DATA_SCHEMA.md` | 0 | 0 | 0 | None |
| `03_KAFKA_CONTRACT.md` | 0 | 0 | 0 | Open Q #3 (micro-batch interval), #4 (window size) |
| `04_API_CONTRACT.md` | 0 | 0 | 0 | None |
| `05_AI_ML_SPEC.md` | 0 | 0 | 0 | Open Q #3 (weather codes), #4 (Hindi/Marathi completeness), #5 (city bounding boxes) |

**No contradictions found.** All five contracts are internally consistent and align with this implementation plan.

### Decisions Made in This Document

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Build order: infra → ingestion → Spark → ML → DB → API → frontend | Matches architecture data flow; enables Day-1 vertical slice |
| 2 | ML library built on Day 1 morning (unit tests only) | Unblocks Spark integration on Day 1 afternoon |
| 3 | Synthetic data generator as script, not service | One-time generation; no runtime dependency |
| 4 | PostgreSQL init via Docker entrypoint mount | Zero manual steps; automatic on first `docker compose up` |
| 5 | In-memory recent events window default: 30 minutes | Matches `05_AI_ML_SPEC.md §22` default; tunable |

---

## Appendix: Open Items from Architecture

These remain open in `01_ARCHITECTURE.md` and are NOT resolved by this plan:

| # | Question | Owner | Impact on Implementation |
|---|----------|-------|------------------------|
| 5 | Website allowlist — specific approved URLs | M2 → M1 | M2 proposes 2-3 URLs; M1 approves before Day 2 |
| 6 | Open-Meteo weather codes → event categories | M2 | M2 implements mapping; default to "other" for unknown codes |
| 7 | Cloudflare R2 — use for demo? | M1 | M1 decides by Day 2; if no, skip entirely |
| 8 | Micro-batch trigger interval | M3 | M3 defaults to 5 seconds processing time; tune on Day 3 |
| 9 | In-memory recent-event window size | M4 | M4 defaults to 30 minutes per `05_AI_ML_SPEC.md §22` |

---

*This document is the implementation source of truth for the 5-day MVP.
Any change to tasks, ownership, timelines, or build order must be
reflected here and cross-checked against all five approved contracts.*
