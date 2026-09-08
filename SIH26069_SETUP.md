# SIH26069 — National Weather Big Data Analytics Platform

## Complete Developer Setup & Deployment Guide

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (START HERE)](#2-quick-start)
3. [Repository Structure](#3-repository-structure)
4. [Environment Configuration](#4-environment-configuration)
5. [Docker Architecture](#5-docker-architecture)
6. [Docker Commands](#6-docker-commands)
7. [Service Verification](#7-service-verification)
8. [Kafka Setup](#8-kafka-setup)
9. [Spark Pipeline](#9-spark-pipeline)
10. [Ingestion System](#10-ingestion-system)
11. [Database Schema](#11-database-schema)
12. [Backend API](#12-backend-api)
13. [Frontend](#13-frontend)
14. [ML / Intelligence Components](#14-ml-intelligence-components)
15. [Canonical Event Pipeline](#15-canonical-event-pipeline)
16. [Data & Storage](#16-data-storage)
17. [Troubleshooting](#17-troubleshooting)
18. [Reset / Clean Install](#18-reset-clean-install)
19. [Team Workflow](#19-team-workflow)
20. [Quick Reference](#20-quick-reference)

---

## 1. Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Docker Engine | 24+ | Container runtime |
| Docker Compose | v2 | Multi-container orchestration |
| Git | 2.30+ | Version control |
| Modern Browser | Chrome/Firefox/Edge | Frontend access |

### Recommended System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 12+ GB |
| Disk Space | 10 GB | 20+ GB |
| CPU | 4 cores | 6+ cores |

### Required Ports

Ensure these ports are available before starting:

| Port | Service |
|------|---------|
| 3000 | React Frontend |
| 5432 | PostgreSQL |
| 8000 | FastAPI Backend |
| 8080 | Kafka UI |
| 8081 | Spark Master UI |
| 8082 | Spark Worker UI |
| 9092 | Kafka Broker |
| 2181 | Zookeeper |
| 7077 | Spark Master |

### Operating System

- **Linux**: Ubuntu 20.04+, Debian 11+, or similar
- **macOS**: 12.0+ (Monterey or later)
- **Windows**: Windows 10/11 with WSL2 enabled

---

## 2. Quick Start (START HERE)

This section gets the complete platform running in under 10 minutes.

### Step 1 — Clone Repository

```bash
git clone <repository-url>
cd sih26069
```

### Step 2 — Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate JWT secret key
JWT_SECRET=$(openssl rand -hex 32)

# Edit .env file and set these required values:
# POSTGRES_PASSWORD=<your-secure-password>
# JWT_SECRET_KEY=<generated-key-from-above>
# ADMIN_PASSWORD=<your-admin-password>
```

**Required Environment Variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password | `secure_password_123` |
| `JWT_SECRET_KEY` | JWT signing key (64-char hex) | `openssl rand -hex 32` output |
| `ADMIN_PASSWORD` | Admin panel password | `admin_password` |

### Step 3 — Build and Start All Services

```bash
# Build all Docker images
docker compose build

# Start infrastructure services first
docker compose up -d zookeeper kafka kafka-ui postgres

# Wait for services to be healthy
sleep 30

# Initialize database schema
bash scripts/init-db.sh

# Create Kafka topics
bash scripts/init-kafka.sh

# Start all remaining services
docker compose up -d

# Wait for full startup
sleep 20
```

### Step 4 — Verify System

```bash
# Check all services are running
docker compose ps

# Run smoke test
bash scripts/smoke-test.sh
```

### Step 5 — Access Platform

Open your browser and navigate to:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **Kafka UI** | http://localhost:8080 |
| **Spark Master** | http://localhost:8081 |
| **Spark Worker** | http://localhost:8082 |

### Step 6 — Verify Data Flow

```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Check events (should return JSON with events)
curl http://localhost:8000/api/v1/events

# Check canonical events
curl http://localhost:8000/api/v1/events/stats
```

**Expected behavior:**
- Ingestion service starts producing synthetic events to Kafka
- Spark stream processor consumes and enriches events
- PostgreSQL writer stores canonical events in database
- Frontend displays events on dashboard

---

## 3. Repository Structure

```
sih26069/
├── docker-compose.yml          # Main Docker orchestration
├── .env.example                # Environment variable template
├── .env                        # Your local environment (not committed)
├── .gitignore                  # Git ignore rules
├── .dockerignore               # Docker build ignore rules
│
├── sql/                        # Database initialization
│   ├── init.sql                # Main schema (extensions, tables, indexes)
│   ├── 02_canonical_events.sql # Canonical events migration
│   ├── 05_verification_reasons.sql
│   ├── 06_verification_log_needs_review.sql
│   └── 03_backfill_canonical_events.py
│
├── scripts/                    # Utility scripts
│   ├── init-db.sh              # Database initialization
│   ├── init-kafka.sh           # Kafka topic creation
│   └── smoke-test.sh           # End-to-end smoke test
│
├── services/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py             # Application entry point
│   │   ├── config.py           # Configuration
│   │   ├── dependencies.py     # Database connection pool
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── routers/            # API route handlers
│   │   │   ├── events.py       # Canonical events endpoints
│   │   │   ├── reports.py      # Source records endpoints
│   │   │   ├── verification.py # Verification actions
│   │   │   ├── system.py       # System status
│   │   │   └── health.py       # Health check
│   │   ├── models/             # Pydantic models
│   │   ├── services/           # Business logic
│   │   └── tests/              # API tests
│   │
│   ├── frontend/               # React application
│   │   ├── src/
│   │   │   ├── App.jsx         # Main router
│   │   │   ├── pages/          # Page components
│   │   │   │   ├── CommandCenter.jsx
│   │   │   │   ├── LiveEvents.jsx
│   │   │   │   ├── EventIntelligence.jsx
│   │   │   │   ├── GeospatialIntelligence.jsx
│   │   │   │   ├── VerificationCenter.jsx
│   │   │   │   ├── EmergingEvents.jsx
│   │   │   │   ├── ReportReview.jsx
│   │   │   │   ├── SystemMonitoring.jsx
│   │   │   │   └── analytics/
│   │   │   │       ├── EventTrends.jsx
│   │   │   │       ├── GeographicAnalysis.jsx
│   │   │   │       └── SourceIntelligence.jsx
│   │   │   ├── components/     # Shared components
│   │   │   ├── stores/         # Zustand state management
│   │   │   └── api/            # API client
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── tailwind.config.js
│   │   └── Dockerfile
│   │
│   ├── ingestion/              # Data ingestion service
│   │   ├── main.py             # Entry point
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── adapters/           # Source adapters
│   │   │   ├── base.py         # Base adapter class
│   │   │   └── weather_api.py  # Open-Meteo adapter
│   │   ├── normaliser/         # Canonical event builder
│   │   ├── producer/           # Kafka producer
│   │   ├── config/             # Adapter configuration
│   │   └── tests/
│   │
│   ├── spark/                  # Spark processing jobs
│   │   ├── jobs/
│   │   │   ├── stream_processor.py  # Real-time stream processor
│   │   │   └── pg_writer.py        # PostgreSQL writer
│   │   ├── Dockerfile.master   # Spark master image
│   │   ├── Dockerfile.worker   # Spark worker image
│   │   ├── Dockerfile.stream   # Stream processor image
│   │   ├── Dockerfile.pg_writer # PG writer image
│   │   └── requirements.txt
│   │
│   └── ml/                     # Machine learning modules
│       ├── classifier/         # Event classification
│       │   ├── rule_based_classifier.py
│       │   ├── event_classifier.py
│       │   └── rules.py
│       ├── credibility/        # Credibility scoring
│       │   ├── credibility_scorer.py
│       │   └── source_weights.py
│       ├── dedup/              # Duplicate detection
│       │   └── duplicate_detector.py
│       ├── verification/       # Verification engine
│       │   └── verification_engine.py
│       ├── config/             # ML configuration
│       │   ├── source_trust.yaml
│       │   └── india_cities.json
│       └── utils/              # Utility functions
│
├── docs/                       # Documentation
│   ├── 00_MASTER_PROJECT_SPEC.md
│   ├── 01_ARCHITECTURE.md
│   ├── 02_DATA_SCHEMA.md
│   ├── 03_KAFKA_CONTRACT.md
│   ├── 04_API_CONTRACT.md
│   └── ...
│
├── data/                       # Runtime data (not committed)
│   ├── raw/
│   ├── processed/
│   ├── synthetic/
│   ├── media/
│   └── logs/
│
├── models/                     # ML model artifacts (not committed)
│   └── event_classifier/
│
├── training/                   # Training data (not committed)
│   └── data/
│
└── tests/                      # Integration tests
    └── test_pg_writer_fixes.py
```

---

## 4. Environment Configuration

### Environment Variables Reference

Create a `.env` file from the template:

```bash
cp .env.example .env
```

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL database password | `your_secure_password` |
| `JWT_SECRET_KEY` | JWT authentication secret (64-char hex) | `openssl rand -hex 32` |
| `ADMIN_PASSWORD` | Admin panel password | `admin_password` |

#### Optional Variables (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `postgres` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `weatherdb` | Database name |
| `POSTGRES_USER` | `weather` | Database user |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address |
| `API_PORT` | `8000` | FastAPI port |
| `JWT_EXPIRATION_HOURS` | `8` | JWT token expiration |
| `ADMIN_USERNAME` | `admin` | Admin username |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `SYNTHETIC_ENABLED` | `true` | Enable synthetic events |
| `OPENMETEO_POLL_INTERVAL_SECONDS` | `300` | Open-Meteo polling interval |
| `CLASSIFIER_BACKEND` | `rule_based` | Classification method |
| `MODEL_CONFIDENCE_THRESHOLD` | `0.75` | Classification confidence threshold |

#### Example .env File

```bash
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=weatherdb
POSTGRES_USER=weather
POSTGRES_PASSWORD=your_secure_password_here

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# FastAPI
API_PORT=8000
JWT_SECRET_KEY=your_generated_jwt_secret_key_here
JWT_EXPIRATION_HOURS=8
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_admin_password_here

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Ingestion
SYNTHETIC_ENABLED=true
OPENMETEO_POLL_INTERVAL_SECONDS=300

# ML Configuration
CLASSIFIER_BACKEND=rule_based
MODEL_CONFIDENCE_THRESHOLD=0.75
```

---

## 5. Docker Architecture

### Services Overview

The platform consists of 10 Docker services:

| Service | Purpose | Image | Port |
|---------|---------|-------|------|
| `zookeeper` | Kafka coordination | `confluentinc/cp-zookeeper:7.6.1` | 2181 |
| `kafka` | Message broker | `confluentinc/cp-kafka:7.6.1` | 9092, 29092 |
| `kafka-ui` | Kafka web interface | `provectuslabs/kafka-ui:latest` | 8080 |
| `postgres` | Database | `postgis/postgis:15-3.4` | 5432 |
| `spark-master` | Spark cluster manager | `spark:3.5.3` | 7077, 8081 |
| `spark-worker` | Spark compute node | `spark:3.5.3` | 8082 |
| `stream-processor` | Real-time event processing | `spark:3.5.3` | - |
| `pg-writer` | PostgreSQL writer | `spark:3.5.3` | - |
| `ingestion` | Data ingestion | `python:3.11-slim` | - |
| `api` | REST API | `python:3.11-slim` | 8000 |
| `frontend` | React UI | `node:20-slim` | 3000 |

### Service Dependencies

```
                    ┌─────────────────┐
                    │    Zookeeper    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │      Kafka      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
│   Ingestion   │    │   Streaming   │    │   pg-writer   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        │         ┌──────────┼──────────┐         │
        │         │          │          │         │
        │    ┌────▼────┐ ┌───▼───┐ ┌────▼────┐   │
        │    │ ML Lib  │ │Rules │ │Cred/Dedup│   │
        │    └────┬────┘ └───┬───┘ └────┬────┘   │
        │         │          │          │         │
        │         └──────────┼──────────┘         │
        │                    │                    │
        │            ┌───────▼───────┐            │
        │            │   PostgreSQL  │◄───────────┘
        │            └───────┬───────┘
        │                    │
        │            ┌───────▼───────┐
        │            │    FastAPI    │
        │            └───────┬───────┘
        │                    │
        │            ┌───────▼───────┐
        │            │ React Frontend│
        │            └───────────────┘
        │
   (Kafka topics)
```

### Startup Order

1. **Zookeeper** — starts first, required by Kafka
2. **Kafka** — depends on healthy Zookeeper
3. **PostgreSQL** — independent, starts in parallel
4. **Spark Master** — independent, starts in parallel
5. **Spark Worker** — depends on Spark Master
6. **Kafka UI** — depends on healthy Kafka
7. **Ingestion** — depends on healthy Kafka
8. **Stream Processor** — depends on healthy Kafka
9. **pg-writer** — depends on healthy Kafka and PostgreSQL
10. **FastAPI** — depends on healthy Kafka and PostgreSQL
11. **React Frontend** — depends on healthy FastAPI

### Volumes

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| `pgdata` | PostgreSQL data | Persistent |
| `kafkadata` | Kafka broker data | Persistent |
| `spark_checkpoints` | Spark streaming checkpoints | Persistent |
| `data_volume` | Shared data (logs, media, raw) | Persistent |

### Networks

All services communicate over a single bridge network: `weather-net`

---

## 6. Docker Commands

### Build Commands

```bash
# Build all images
docker compose build

# Build specific service
docker compose build api

# Build without cache (clean build)
docker compose build --no-cache
```

### Start Commands

```bash
# Start all services in background
docker compose up -d

# Start specific services
docker compose up -d zookeeper kafka postgres

# Start with build
docker compose up -d --build

# Start in foreground (see logs)
docker compose up
```

### Status Commands

```bash
# Check all services
docker compose ps

# Check specific service
docker compose ps api

# View service logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# Follow specific service logs
docker compose logs -f api

# View last 100 lines
docker compose logs --tail=100
```

### Stop Commands

```bash
# Stop all services (preserves data)
docker compose down

# Stop specific service
docker compose down api

# Stop and remove volumes (DESTRUCTIVE - removes database!)
docker compose down -v

# Stop and remove images
docker compose down --rmi all
```

### ⚠️ Destructive Commands Warning

```bash
# ⚠️ THIS DESTROYS ALL DATA
docker compose down -v

# This removes:
# - PostgreSQL database
# - Kafka topics and messages
# - Spark checkpoints
# - All uploaded files

# ONLY use when you need a completely fresh start
```

---

## 7. Service Verification

### Step-by-Step Verification

#### 1. Check Docker Services

```bash
docker compose ps
```

**Expected output:**
```
NAME                STATUS
weather-zookeeper   running (healthy)
weather-kafka       running (healthy)
weather-kafka-ui    running (healthy)
weather-postgres    running (healthy)
weather-spark-master running (healthy)
weather-spark-worker running (healthy)
weather-stream-processor running
weather-pg-writer   running
weather-ingestion   running
weather-api         running (healthy)
weather-frontend    running (healthy)
```

#### 2. Verify Zookeeper

```bash
docker compose exec zookeeper echo ruok | nc localhost 2181
```

**Expected:** `imok`

#### 3. Verify Kafka

```bash
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

**Expected:**
```
citizen.raw
government.raw
social.raw
weather.events
weather.processed
weather.raw
weather.verified
```

#### 4. Verify PostgreSQL

```bash
docker compose exec -T postgres psql -U weather -d weatherdb -c "\dt"
```

**Expected:** List of tables (events, canonical_events, sources, verification_log, event_clusters)

#### 5. Verify PostGIS Extension

```bash
docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT PostGIS_Version();"
```

**Expected:** PostGIS version string

#### 6. Verify Spark Master

```bash
curl -sf http://localhost:8081
```

**Expected:** Spark Master web UI HTML

#### 7. Verify FastAPI

```bash
curl -sf http://localhost:8000/api/v1/health
```

**Expected:** `{"status":"healthy"}`

#### 8. Verify Frontend

```bash
curl -sf http://localhost:3000 | grep -q '<div id="root"'
```

**Expected:** Exit code 0 (HTML contains React root div)

#### 9. Run Complete Smoke Test

```bash
bash scripts/smoke-test.sh
```

**Expected:** All checks pass with ✅

---

## 8. Kafka Setup

### Topics

The platform uses 7 Kafka topics:

| Topic | Purpose | Producer | Consumer |
|-------|---------|----------|----------|
| `weather.raw` | Raw weather events from adapters | Ingestion | Stream Processor |
| `citizen.raw` | Citizen-reported events | Ingestion | Stream Processor |
| `social.raw` | Social media events | Ingestion | Stream Processor |
| `government.raw` | Government data events | Ingestion | Stream Processor |
| `weather.processed` | Validated and enriched events | Stream Processor | Debug/Monitoring |
| `weather.events` | Final enriched canonical events | Stream Processor | pg-writer |
| `weather.verified` | Verified events | pg-writer | Future use |

### Topic Configuration

- **Partitions**: 1 (MVP)
- **Replication Factor**: 1 (single broker)
- **Retention**: 168 hours (7 days)
- **Max Message Size**: 1 MB

### Inspecting Kafka

```bash
# List all topics
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Describe a topic
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic weather.raw

# View messages (console consumer)
docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic weather.events --from-beginning --max-messages 5
```

### Kafka UI

Access the web interface at http://localhost:8080

Features:
- Topic browser
- Message viewer
- Consumer group monitoring
- Broker metrics

---

## 9. Spark Pipeline

### Spark Components

| Component | Image | Purpose |
|-----------|-------|---------|
| Spark Master | `spark:3.5.3` | Cluster resource manager |
| Spark Worker | `spark:3.5.3` | Compute executor |
| Stream Processor | `spark:3.5.3` | Real-time event processing |
| PG Writer | `spark:3.5.3` | PostgreSQL upsert operations |

### Stream Processor

**Location:** `services/spark/jobs/stream_processor.py`

**Function:**
1. Consumes raw events from `weather.raw`, `citizen.raw`, `social.raw`, `government.raw`
2. Validates event schema
3. Cleans and normalizes data
4. Applies ML enrichment (classification, credibility, duplicate detection)
5. Publishes enriched events to `weather.events`

**Configuration:**
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker address
- `SPARK_RAW_TOPICS`: Comma-separated list of input topics
- `SPARK_CHECKPOINT_PATH`: Checkpoint location for fault tolerance
- `CLASSIFIER_BACKEND`: Classification method (`rule_based` | `trained` | `hybrid`)

**Processing Flow:**
```
Raw Kafka Topics
    ↓
Schema Validation
    ↓
Data Cleaning & Normalization
    ↓
ML Enrichment (Classification, Credibility, Dedup)
    ↓
Write to weather.events Topic
```

### PostgreSQL Writer

**Location:** `services/spark/jobs/pg_writer.py`

**Function:**
1. Consumes enriched events from `weather.events`
2. Upserts source records to `events` table
3. Matches or creates canonical events
4. Applies ML enrichment with database context
5. Updates `canonical_events` table

**Key Features:**
- **Idempotent**: Safe to replay without data corruption
- **Canonical Matching**: Groups related events (same category, ≤50km, ≤24h)
- **Report Count**: Computed from actual linked source records (not inflated by replays)
- **Admin Verification**: Preserves admin-set verification status through replays

**Configuration:**
- `PG_WRITER_TOPIC`: Input topic (`weather.events`)
- `DATABASE_URL`: PostgreSQL connection string
- `CANONICAL_MATCH_DISTANCE_KM`: Spatial matching threshold (default: 50)
- `CANONICAL_MATCH_TIME_HOURS`: Temporal matching threshold (default: 24)

### Checkpoints

Spark uses checkpoints for fault tolerance:

```
/data/checkpoints/
├── spark_streaming/
│   ├── events/          # Stream processor checkpoint
│   ├── processed/       # weather.processed writer checkpoint
│   └── rejected/        # Dead-letter handler checkpoint
└── pg_writer/
    └── pg_writer/       # PostgreSQL writer checkpoint
```

**⚠️ Warning:** Deleting checkpoints may cause data reprocessing or loss.

---

## 10. Ingestion System

### Overview

The ingestion service collects weather data from multiple sources and publishes canonical weather events to Kafka.

**Location:** `services/ingestion/`

### Data Sources

#### Real Source: Open-Meteo API

- **Adapter:** `services/ingestion/adapters/weather_api.py`
- **Type:** `weather_api`
- **Source Name:** `Open-Meteo`
- **Polling Interval:** 300 seconds (5 minutes)
- **Supported Cities:**
  - Mumbai (19.076°N, 72.878°E)
  - Nagpur (21.146°N, 79.088°E)
  - Nashik (19.998°N, 73.790°E)

**Weather Conditions Detected:**
- WMO codes: Fog (45/48), Heavy Rainfall (65-67), Thunderstorm (95-99)
- Measurement-based: Heatwave (≥40°C), Strong Wind (≥50km/h), Heavy Rainfall (>7.5mm)

**Note:** Snow codes (71-86) are explicitly skipped (not relevant for Maharashtra).

#### Synthetic/Demo Source

- **Location:** `services/ingestion/main.py`
- **Type:** `synthetic`
- **Source Name:** `synthetic_gen`
- **Toggle:** `SYNTHETIC_ENABLED` (default: `true`)

**Synthetic Events (3 events):**

| City | Category | Severity | Coordinates |
|------|----------|----------|-------------|
| Mumbai | heavy_rainfall | high | 19.076°N, 72.878°E |
| Nagpur | heatwave | extreme | 21.146°N, 79.088°E |
| Nashik | thunderstorm | moderate | 19.998°N, 73.790°E |

### Event Categories Supported

```python
VALID_CATEGORIES = [
    'rainfall', 'heavy_rainfall', 'flood',
    'thunderstorm', 'lightning', 'heatwave',
    'fog', 'dust_storm', 'strong_wind',
    'hailstorm', 'cyclone', 'other'
]
```

### Deterministic Event Identity

Event IDs are generated deterministically using SHA256 hash:

```python
hash_input = f"{source_type}|{source_id}|{timestamp}|{lat}|{lon}"
event_id = uuid.UUID(hashlib.sha256(hash_input.encode()).hexdigest()[:32])
```

This ensures the same source observation always produces the same event_id, enabling idempotent processing.

### Kafka Message Format

Events are wrapped in a Kafka envelope:

```json
{
  "schema_version": "1.0",
  "message_id": "uuid",
  "event_type": "weather_event",
  "produced_at": "ISO8601",
  "producer": "ingestion",
  "payload": { /* Canonical Weather Event */ }
}
```

---

## 11. Database Schema

### Database Configuration

- **Engine:** PostgreSQL 15
- **Extensions:** PostGIS 3.4, pgcrypto
- **Database:** `weatherdb`
- **User:** `weather`

### Tables

#### `events` (Source Records)

Individual weather observations from all sources.

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | UUID (PK) | Deterministic event identifier |
| `source_id` | TEXT | Source-specific identifier |
| `source_type` | TEXT | Source type (weather_api, synthetic, etc.) |
| `source_name` | TEXT | Source name (Open-Meteo, etc.) |
| `source_url` | TEXT | Source URL if applicable |
| `source_trust_score` | NUMERIC(4,3) | Source trust level (0-1) |
| `event_timestamp` | TIMESTAMPTZ | When event occurred |
| `ingestion_timestamp` | TIMESTAMPTZ | When event was ingested |
| `latitude` | NUMERIC(9,6) | Event latitude |
| `longitude` | NUMERIC(10,6) | Event longitude |
| `city` | TEXT | City name |
| `district` | TEXT | District name |
| `state` | TEXT | State name |
| `country` | TEXT | Country (default: India) |
| `geom` | GEOMETRY(Point, 4326) | PostGIS geometry (auto-synced) |
| `event_category` | TEXT | Weather event category |
| `severity` | TEXT | Event severity |
| `description` | TEXT | Event description |
| `classified_category` | TEXT | ML-classified category |
| `classification_confidence` | NUMERIC(4,3) | Classification confidence (0-1) |
| `duplicate_score` | NUMERIC(4,3) | Duplicate probability (0-1) |
| `credibility_score` | NUMERIC(4,3) | Credibility score (0-1) |
| `credibility_reasons` | TEXT[] | Credibility explanation |
| `verification_status` | TEXT | Verification status |
| `verified_by` | TEXT | Who verified (admin/automated) |
| `verification_timestamp` | TIMESTAMPTZ | When verified |
| `canonical_event_id` | UUID (FK) | Linked canonical event |

#### `canonical_events` (Consolidated Events)

Aggregated weather phenomena from multiple source records.

| Column | Type | Description |
|--------|------|-------------|
| `canonical_event_id` | UUID (PK) | Canonical event identifier |
| `event_category` | TEXT | Event category |
| `severity` | TEXT | Most severe level |
| `description` | TEXT | Aggregated description |
| `latitude` | NUMERIC(9,6) | Most recent coordinates |
| `longitude` | NUMERIC(10,6) | Most recent coordinates |
| `city` | TEXT | City name |
| `first_seen` | TIMESTAMPTZ | Earliest observation |
| `last_seen` | TIMESTAMPTZ | Most recent observation |
| `source_count` | INTEGER | Distinct source names |
| `report_count` | INTEGER | Total linked source records |
| `contributing_sources` | TEXT[] | List of source names |
| `classified_category` | TEXT | ML-classified category |
| `classification_confidence` | NUMERIC(4,3) | Classification confidence |
| `credibility_score` | NUMERIC(4,3) | MAX credibility score |
| `credibility_reasons` | TEXT[] | Credibility explanation |
| `verification_status` | TEXT | Verification status |
| `verified_by` | TEXT | Who verified |
| `verification_timestamp` | TIMESTAMPTZ | When verified |
| `verification_reasons` | TEXT[] | Verification explanation |

#### `sources` (Source Registry)

Registered data sources.

| Column | Type | Description |
|--------|------|-------------|
| `source_name` | TEXT (PK) | Source identifier |
| `source_type` | TEXT | Source type |
| `base_url` | TEXT | Source URL |
| `trust_score` | NUMERIC(4,3) | Trust level (0-1) |
| `total_reports` | INTEGER | Total reports from source |
| `verified_reports` | INTEGER | Verified reports count |
| `rejected_reports` | INTEGER | Rejected reports count |
| `last_seen_at` | TIMESTAMPTZ | Last observation time |

#### `verification_log` (Audit Trail)

History of all verification actions.

| Column | Type | Description |
|--------|------|-------------|
| `log_id` | UUID (PK) | Log entry identifier |
| `event_id` | UUID (FK) | Source event ID |
| `action` | TEXT | Action performed |
| `performed_by` | TEXT | Who performed action |
| `notes` | TEXT | Optional notes |
| `performed_at` | TIMESTAMPTZ | When performed |

**Actions:** `verified`, `rejected`, `marked_suspicious`, `marked_duplicate`, `needs_review`

#### `event_clusters` (Clustering - Stub)

Reserved for future clustering implementation.

### Indexes

```sql
-- Spatial indexes
CREATE INDEX idx_events_geom ON events USING GIST (geom);
CREATE INDEX idx_ce_geom ON canonical_events USING GIST (geom);

-- Temporal indexes
CREATE INDEX idx_events_timestamp ON events (event_timestamp DESC);
CREATE INDEX idx_ce_timestamp ON canonical_events (last_seen DESC);
CREATE INDEX idx_ce_first_seen ON canonical_events (first_seen DESC);

-- Category indexes
CREATE INDEX idx_events_category ON events (event_category);
CREATE INDEX idx_ce_category ON canonical_events (event_category);

-- Verification indexes
CREATE INDEX idx_events_verification_status ON events (verification_status);
CREATE INDEX idx_ce_verification ON canonical_events (verification_status);

-- Relationship indexes
CREATE INDEX idx_events_canonical_event_id ON events (canonical_event_id);
CREATE INDEX idx_verification_log_event_id ON verification_log (event_id);
```

### Triggers

```sql
-- Auto-sync geometry from lat/lon
CREATE TRIGGER trg_sync_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude
    ON events
    FOR EACH ROW EXECUTE FUNCTION sync_geom();

-- Auto-update updated_at timestamp
CREATE TRIGGER trg_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### Database Initialization

```bash
# Initialize schema
bash scripts/init-db.sh

# Or manually
docker compose exec -T postgres psql -U weather -d weatherdb < sql/init.sql
```

---

## 12. Backend API

### FastAPI Application

**Location:** `services/api/`

**Entry Point:** `main.py`

**Base URL:** `http://localhost:8000`

**API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Endpoints

#### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | API health status |

**Response:**
```json
{"status": "healthy"}
```

#### Canonical Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/events` | List canonical events (paginated) |
| GET | `/api/v1/events/stats` | Event statistics aggregation |
| GET | `/api/v1/events/map` | Map data with bbox filtering |
| GET | `/api/v1/events/{event_id}` | Single event detail |

**Query Parameters (GET /events):**
- `page` (default: 1)
- `page_size` (default: 20, max: 100)
- `city`, `district`, `state` — Location filters
- `category` — Event category filter
- `severity` — Severity filter
- `verification_status` — Verification status filter
- `source_type` — Source type filter
- `start_time`, `end_time` — Time range filters
- `min_credibility` — Minimum credibility score
- `sort_by` — Sort field (default: last_seen)
- `sort_order` — Sort direction (asc/desc)

**Query Parameters (GET /events/map):**
- `min_lat`, `max_lat`, `min_lon`, `max_lon` — Bounding box (required)
- `category`, `severity`, `verification_status`, `city` — Filters
- `start_time`, `end_time` — Time range filters

#### Source Records (Reports)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/reports` | List source records (paginated) |
| GET | `/api/v1/reports/stats` | Source record statistics |
| GET | `/api/v1/reports/{report_id}` | Single source record detail |

**Query Parameters (GET /reports):**
- `page`, `page_size` — Pagination
- `source_type`, `source_name` — Source filters
- `category`, `severity` — Event filters
- `verification_status` — Verification status filter
- `city` — Location filter
- `has_canonical` — Filter by canonical linkage
- `search` — Text search

#### Verification

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/verification` | Perform verification action |

**Request Body:**
```json
{
  "event_id": "uuid",
  "action": "verified|rejected|marked_suspicious|marked_duplicate|needs_review",
  "performed_by": "admin",
  "notes": "Optional notes"
}
```

**Response:**
```json
{
  "event_id": "uuid",
  "old_status": "needs_review",
  "new_status": "verified",
  "action": "verified",
  "performed_by": "admin",
  "performed_at": "ISO8601",
  "log_id": "uuid"
}
```

#### System Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/system/status` | Real-time system health |

**Response includes:**
- API status
- Database connectivity and statistics
- Kafka topic information
- Data statistics (source records, canonical events, verification actions)
- API uptime

### Response Models

All responses use Pydantic models for validation and serialization. Error responses follow the format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "timestamp": "ISO8601"
  }
}
```

---

## 13. Frontend

### React Application

**Location:** `services/frontend/`

**Framework:** React 18 with Vite

**UI Library:** Tailwind CSS

**State Management:** Zustand

**Maps:** Leaflet with react-leaflet

**Charts:** Chart.js with react-chartjs-2

### Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Command Center | Main dashboard with KPIs, map, feed |
| `/events` | Live Events | Canonical events list with filters |
| `/events/:eventId` | Event Intelligence | Single event detail view |
| `/geospatial` | Geospatial Intelligence | Map-based analysis |
| `/analytics` | Analytics (landing) | Redirects to /analytics/events |
| `/analytics/events` | Event Trends | Temporal event analysis |
| `/analytics/geographic` | Geographic Analysis | City-based analysis |
| `/analytics/sources` | Source Intelligence | Source performance analysis |
| `/emerging` | Emerging Events | Newly observed situations |
| `/verification` | Verification Center | Canonical event verification |
| `/report-review` | Report Review | Source record inspection (read-only) |
| `/system-monitoring` | System Monitoring | System health dashboard |

### Development

```bash
# Install dependencies
cd services/frontend
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Docker

The frontend runs in Docker using:

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**Access:** http://localhost:3000 (mapped from container port 5173)

### API Connection

The frontend connects to the backend via environment variable:

```bash
VITE_API_URL=http://localhost:8000/api/v1
```

### Design System

- **Canvas:** #F3F5F7
- **Panels:** #FFFFFF
- **Borders:** #D9E0E6
- **Primary Text:** #18232D
- **Secondary Text:** #526170
- **Steel Blue:** #477D96
- **Amber (Warning):** #B98220
- **Success:** #31845D
- **Critical:** #B84848

---

## 14. ML / Intelligence Components

### ⚠️ Important: No Trained ML Model

**The SIH26069 project does NOT contain a trained production ML model.**

All classification and intelligence is currently **rule-based and heuristic**. The ML infrastructure is in place for future model integration, but the trained artifact is not ready.

### Components

#### 1. Rule-Based Classifier

**Location:** `services/ml/classifier/rule_based_classifier.py`

**Method:** Keyword-based classification using:
- English keywords
- Hindi keywords
- Marathi keywords
- Phrase matching (weighted 3x)
- Single keyword matching (weighted 1x)
- Category priority rules

**Output:** `classified_category` + `classification_confidence` (0-1)

#### 2. Credibility Scorer

**Location:** `services/ml/credibility/credibility_scorer.py`

**Factors:**
- Source trust (from configuration)
- Corroboration (independent sources)
- Weather agreement (API observations)
- Temporal consistency
- Spatial consistency
- Content quality

**Output:** `credibility_score` (0-1) + `credibility_reasons`

#### 3. Duplicate Detector

**Location:** `services/ml/dedup/duplicate_detector.py`

**Method:** Multi-factor similarity scoring:
- Text similarity (Jaccard)
- Source ID match
- Source URL match
- Category compatibility
- Time difference
- Geographic distance

**Output:** `duplicate_score` (0-1, where 1 = almost certainly duplicate)

#### 4. Verification Engine

**Location:** `services/ml/verification/verification_engine.py`

**Method:** Deterministic decision based on convergent evidence:
- Requires multiple positive signals
- Conservative: prefers `needs_review` over incorrect verification
- Explains every decision with human-readable reasons

**Statuses:**
- `pending` — No processing yet
- `verified` — Strong evidence (≥3 positive signals)
- `needs_review` — Ambiguous evidence
- `suspicious` — Multiple negative signals
- `duplicate` — High duplicate probability (≥85%)

### Configuration Files

| File | Purpose |
|------|---------|
| `services/ml/config/source_trust.yaml` | Source trust scores by type |
| `services/ml/config/india_cities.json` | City bounding boxes for spatial validation |
| `services/ml/config/ml_config.yaml` | ML thresholds and parameters |

### Model Artifacts

The `models/` directory is empty and not committed to Git. When a trained model is available:

1. Place model file at `models/event_classifier/model.pkl`
2. Set `CLASSIFIER_BACKEND=trained` in `.env`
3. Rebuild stream processor: `docker compose build stream-processor`
4. Restart: `docker compose up -d stream-processor`

---

## 15. Canonical Event Pipeline

### Flow Diagram

```
Source Records (Multiple Sources)
         ↓
    Normalization
         ↓
    Classification
         ↓
    Credibility Scoring
         ↓
    Duplicate Detection
         ↓
    Canonical Matching
         ↓
    Canonical Event Aggregation
         ↓
    Verification Decision
         ↓
    PostgreSQL Storage
         ↓
    FastAPI Exposure
         ↓
    React Frontend Display
```

### Key Concepts

#### Source Record vs Canonical Event

- **Source Record:** Individual observation from a single source
- **Canonical Event:** Consolidated weather phenomenon from multiple related source records

Example:
- Source Record 1: "Heavy rain in Mumbai" (Open-Meteo)
- Source Record 2: "Waterlogging in Mumbai" (Citizen report)
- Source Record 3: "Mumbai flooding" (Social media)

All three may be consolidated into one **canonical event**: "Heavy rainfall event in Mumbai"

### Deterministic Identity

Source record `event_id` is generated deterministically:

```python
hash_input = f"{source_type}|{source_id}|{timestamp}|{lat}|{lon}"
event_id = uuid.UUID(hashlib.sha256(hash_input.encode()).hexdigest()[:32])
```

**Benefits:**
- Same source observation always produces the same event_id
- Enables idempotent processing (safe to replay)
- Prevents duplicate source records

### Canonical Matching

Events are matched to existing canonical events using:

| Criterion | Threshold |
|-----------|-----------|
| Category | Exact match |
| Geographic Distance | ≤ 50 km |
| Temporal Distance | ≤ 24 hours |

**Matching Logic:**
1. Query candidate canonical events within time window
2. Filter by same category
3. Calculate haversine distance
4. Match if distance ≤ 50 km

### Aggregation Rules

When updating a canonical event:

| Field | Aggregation |
|-------|-------------|
| `first_seen` | MIN of contributing timestamps |
| `last_seen` | MAX of contributing timestamps |
| `source_count` | COUNT(DISTINCT source_name) |
| `report_count` | COUNT(*) of linked source records |
| `contributing_sources` | Array of distinct source names |
| `severity` | Maximum severity level |
| `credibility_score` | Maximum credibility score |
| `classification_confidence` | Maximum confidence |
| `latitude/longitude` | Most recent coordinates |
| `verification_status` | Priority-based (verified > needs_review > suspicious > pending) |

### Report Count (Idempotent)

**Current Implementation:**

```sql
UPDATE canonical_events SET report_count = 
  (SELECT COUNT(*) FROM events WHERE canonical_event_id = %s)
WHERE canonical_event_id = %s;
```

**Behavior:**
- Recomputed from actual linked source records after every upsert
- Safe to replay (does not inflate count)
- Represents true number of contributing source records

### Admin Verification Persistence

Admin-set verification status is preserved through pipeline replays:

```sql
UPDATE canonical_events SET verification_status = %s
WHERE canonical_event_id = %s
AND (verified_by IS NULL OR verified_by = 'automated');
```

**Behavior:**
- Pipeline can update status only if not manually verified
- Admin actions are durable across replays
- Audit trail maintained in verification_log

---

## 16. Data & Storage

### Docker Volumes

| Volume | Mount Point | Contents |
|--------|-------------|----------|
| `pgdata` | `/var/lib/postgresql/data` | PostgreSQL data files |
| `kafkadata` | `/var/lib/kafka/data` | Kafka broker data |
| `spark_checkpoints` | `/data/checkpoints` | Spark streaming checkpoints |
| `data_volume` | `/data` | Shared data directory |

### Data Directories

```
/data/
├── checkpoints/
│   ├── spark_streaming/    # Stream processor checkpoints
│   └── pg_writer/          # PostgreSQL writer checkpoints
├── logs/
│   ├── app/                # Application logs
│   └── dead_letter/        # Rejected events (JSONL)
├── media/
│   ├── photos/             # Uploaded photos
│   └── videos/             # Uploaded videos
├── raw/                    # Raw data files
├── processed/              # Processed data files
└── synthetic/              # Synthetic test data
```

### What Should NOT Be Committed to Git

From `.gitignore`:

```
# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Node
node_modules/
dist/

# Data (runtime)
data/raw/*
data/processed/*
data/synthetic/*
data/media/*
data/logs/*
data/checkpoints/

# Models (trained artifacts)
models/event_classifier/model.pkl
models/event_classifier/*.joblib

# Training data
training/data/*.csv
training/data/*.parquet
```

### What IS Committed

```
# Configuration templates
.env.example

# SQL migrations
sql/*.sql

# Scripts
scripts/*.sh

# Source code
services/**/*.{py,jsx,js,ts,css}

# Documentation
docs/*.md

# Dockerfiles
services/*/Dockerfile*

# Requirements
services/*/requirements.txt
services/frontend/package.json
```

---

## 17. Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:**
```
Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Solution:**
```bash
# Find process using the port
lsof -i :5432

# Stop the conflicting process or change port in docker-compose.yml
```

#### 2. Kafka Startup Issues

**Symptom:** Kafka fails to start or connect

**Solution:**
```bash
# Check Zookeeper health
docker compose logs zookeeper

# Restart in order
docker compose down
docker compose up -d zookeeper
sleep 10
docker compose up -d kafka
sleep 20
```

#### 3. PostgreSQL Connection Refused

**Symptom:** API or pg-writer cannot connect to database

**Solution:**
```bash
# Check PostgreSQL status
docker compose logs postgres

# Verify database exists
docker compose exec -T postgres psql -U weather -d weatherdb -c "\l"

# Check credentials match .env
docker compose exec -T postgres psql -U weather -d weatherdb
```

#### 4. Stale Checkpoints

**Symptom:** Stream processor not processing new events

**Solution:**
```bash
# ⚠️ WARNING: This may cause data reprocessing
docker compose down
docker volume rm sih26069_spark_checkpoints
docker compose up -d
```

#### 5. Ingestion Not Producing Events

**Symptom:** No new events appearing in Kafka

**Solution:**
```bash
# Check ingestion logs
docker compose logs ingestion

# Verify Kafka connectivity
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check if synthetic events are enabled
docker compose exec ingestion env | grep SYNTHETIC
```

#### 6. Frontend Cannot Connect to API

**Symptom:** Frontend shows API errors

**Solution:**
```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Check CORS configuration
docker compose exec api env | grep CORS

# Verify API URL in frontend
docker compose exec frontend env | grep VITE_API_URL
```

#### 7. ML Modules Not Available

**Symptom:** Logs show "ML modules not available"

**Solution:**
```bash
# This is expected if ML dependencies are not installed
# The system falls back to default values
# To enable ML, rebuild with ML dependencies
docker compose build stream-processor pg-writer
docker compose up -d stream-processor pg-writer
```

### Viewing Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs api

# Follow in real-time
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api

# Since specific time
docker compose logs --since 30m api
```

### Debugging

```bash
# Execute command in running container
docker compose exec api bash

# Check environment variables
docker compose exec api env

# Inspect container
docker inspect weather-api

# Check container resource usage
docker stats
```

---

## 18. Reset / Clean Install

### ⚠️ DANGEROUS: Full Reset

**This will delete ALL data including:**
- PostgreSQL database
- Kafka topics and messages
- Spark checkpoints
- All uploaded files
- All logs

```bash
# Stop all services and remove volumes
docker compose down -v

# Remove all images
docker compose down --rmi all

# Remove all data
rm -rf data/*
rm -rf models/*

# Rebuild from scratch
docker compose build
docker compose up -d

# Reinitialize
sleep 30
bash scripts/init-db.sh
bash scripts/init-kafka.sh
sleep 20
docker compose up -d
```

### Safe Reset (Preserve Data)

```bash
# Stop services
docker compose down

# Rebuild images
docker compose build

# Restart
docker compose up -d
```

### Database-Only Reset

```bash
# Stop API and pg-writer
docker compose stop api pg-writer

# Drop and recreate database
docker compose exec -T postgres psql -U weather -d postgres -c "DROP DATABASE IF EXISTS weatherdb;"
docker compose exec -T postgres psql -U weather -d postgres -c "CREATE DATABASE weatherdb;"

# Reinitialize schema
bash scripts/init-db.sh

# Restart services
docker compose up -d
```

---

## 19. Team Workflow

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes
# ...

# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new feature description"

# Push to remote
git push origin feature/your-feature-name

# Create pull request
# ...
```

### Development Workflow

```bash
# 1. Pull latest changes
git pull origin main

# 2. Build if dependencies changed
docker compose build

# 3. Restart affected services
docker compose up -d

# 4. Verify changes
bash scripts/smoke-test.sh

# 5. Run tests (if available)
cd services/api && python -m pytest tests/
cd services/ml && python -m pytest tests/

# 6. Check Docker health
docker compose ps
```

### After Dependency Changes

```bash
# Python dependencies
docker compose build api ingestion

# Node dependencies
docker compose build frontend

# Spark dependencies
docker compose build stream-processor pg-writer
```

### Files to NOT Commit

```bash
# Environment (secrets)
.env
.env.local

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Node
node_modules/
dist/

# Data
data/checkpoints/
data/logs/
data/media/

# Models
models/event_classifier/model.pkl

# IDE
.vscode/
.idea/
```

---

## 20. Quick Reference

### START

```bash
git clone <repo-url>
cd sih26069
cp .env.example .env
# Edit .env with required values
docker compose build
docker compose up -d zookeeper kafka kafka-ui postgres
sleep 30
bash scripts/init-db.sh
bash scripts/init-kafka.sh
docker compose up -d
sleep 20
bash scripts/smoke-test.sh
```

### STATUS

```bash
docker compose ps
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/events/stats
```

### LOGS

```bash
docker compose logs -f api
docker compose logs -f stream-processor
docker compose logs -f pg-writer
docker compose logs -f ingestion
```

### URLS

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **Kafka UI** | http://localhost:8080 |
| **Spark Master** | http://localhost:8081 |
| **Spark Worker** | http://localhost:8082 |

### STOP

```bash
docker compose down
```

### FULL RESET

```bash
# ⚠️ DESTROYS ALL DATA
docker compose down -v
docker compose down --rmi all
rm -rf data/*
docker compose build
docker compose up -d
sleep 30
bash scripts/init-db.sh
bash scripts/init-kafka.sh
docker compose up -d
```

### USEFUL COMMANDS

```bash
# Rebuild specific service
docker compose build api

# Restart specific service
docker compose restart api

# View container resources
docker stats

# Execute command in container
docker compose exec api bash

# Check Kafka topics
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Query database
docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT COUNT(*) FROM canonical_events;"
```

---

## Additional Resources

| Document | Location |
|----------|----------|
| Master Project Spec | `docs/00_MASTER_PROJECT_SPEC.md` |
| Architecture | `docs/01_ARCHITECTURE.md` |
| Data Schema | `docs/02_DATA_SCHEMA.md` |
| Kafka Contract | `docs/03_KAFKA_CONTRACT.md` |
| API Contract | `docs/04_API_CONTRACT.md` |
| AI/ML Spec | `docs/05_AI_ML_SPEC.md` |
| Implementation Plan | `docs/06_IMPLEMENTATION_PLAN.md` |
| Docker Deployment | `docs/07_DOCKER_DEPLOYMENT_SPEC.md` |
| Testing/QA | `docs/08_TESTING_QA_SPEC.md` |

---

**Last Updated:** September 2026

**Version:** 1.0 (MVP Complete)

**Status:** Demo-Ready
