# 07 — Docker Deployment Specification

**Project:** SIH26069 — National Weather Big Data Analytics Platform
**Document:** `07_DOCKER_DEPLOYMENT_SPEC.md`
**Version:** 1.0
**Status:** AWAITING APPROVAL
**Derived from:** `01_ARCHITECTURE.md` v1.3 + `02_DATA_SCHEMA.md` v1.1 + `03_KAFKA_CONTRACT.md` v1.0 + `04_API_CONTRACT.md` v1.0 + `05_AI_ML_SPEC.md` v1.0 + `06_IMPLEMENTATION_PLAN.md` v1.0
**Last updated:** 2026-09-01

---

## Change Control

This document translates approved specifications into Docker deployment instructions.
It does NOT override, extend, or duplicate contract decisions. If a port, service,
topic, or configuration contradicts an approved document, this document must be updated.

---

## 1. Deployment Target

### 1.1 Supported Environment

| Property | Value |
|----------|-------|
| Target | Local developer machine |
| Orchestration | Docker Compose v2 |
| Deployment mode | Single-machine |
| Architecture | CPU-first, no GPU requirement |
| Container runtime | Docker Engine 24+ |
| OS support | Linux, macOS, Windows (Docker Desktop / WSL2) |
| Orchestration alternative | **None** — no Kubernetes, no Swarm |

### 1.2 Development vs Production

This document covers **development/demo deployment only.**

| Aspect | MVP (This Document) | Future Production |
|--------|--------------------|--------------------|
| Docker Compose | ✅ Primary orchestration | ❌ Not suitable |
| Single broker | ✅ Kafka broker.id=1 | Cluster with 3+ brokers |
| Single Spark worker | ✅ 1 worker | Multiple workers |
| No auth on reads | ✅ Public dashboard | Rate limiting + WAF |
| No TLS | ✅ Internal Docker network | TLS everywhere |
| No resource limits | ✅ Hackathon speed | CPU/memory limits |
| Filesystem dead-letter | ✅ MVP only | Kafka DLQ topic |

---

## 2. Service Inventory

### 2.1 Complete Service List

| # | Service | Image / Build Context | Port(s) | Role |
|---|---------|----------------------|---------|------|
| 1 | `zookeeper` | `confluentinc/cp-zookeeper:7.6` | `2181` | Kafka coordination |
| 2 | `kafka` | `confluentinc/cp-kafka:7.6` | `9092` (internal), `29092` (host) | Event bus |
| 3 | `kafka-ui` | `provectuslabs/kafka-ui:latest` | `8080` | Topic/message inspection |
| 4 | `postgres` | `postgis/postgis:15-3.4` | `5432` | Primary database + PostGIS |
| 5 | `spark-master` | `bitnami/spark:3.5` | `7077` (cluster), `8081` (UI) | Spark cluster master |
| 6 | `spark-worker` | `bitnami/spark:3.5` | `8082` | Spark executor |
| 7 | `ingestion` | `./services/ingestion` (build) | — (no HTTP) | Source adapters + Kafka producer |
| 8 | `api` | `./services/api` (build) | `8000` | FastAPI REST + Kafka producer |
| 9 | `frontend` | `./services/frontend` (build) | `5173` | React + Vite dev server |

> **`services/ml/` is NOT a Docker service.** It is a Python library
> `COPY`-ed into the Spark image at build time. Per `01_ARCHITECTURE.md §5`.

### 2.2 Service Details

#### `zookeeper`

| Property | Value |
|----------|-------|
| Image | `confluentinc/cp-zookeeper:7.6` |
| Ports | `2181:2181` |
| Environment | `ZOOKEEPER_CLIENT_PORT=2181`, `ZOOKEEPER_TICK_TIME=2000` |
| Volumes | None (ephemeral) |
| Dependencies | None |
| Healthcheck | `echo ruok \| nc localhost 2181` returns `imok` |
| Restart | `unless-stopped` |
| Network | `weather-net` |

#### `kafka`

| Property | Value |
|----------|-------|
| Image | `confluentinc/cp-kafka:7.6` |
| Ports | `9092:9092` (internal Docker), `29092:29092` (host access) |
| Environment | `KAFKA_BROKER_ID=1`, `KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181`, `KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092`, `KAFKA_AUTO_CREATE_TOPICS_ENABLE=false`, `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1`, `KAFKA_LOG_RETENTION_HOURS=168`, `KAFKA_MESSAGE_MAX_BYTES=1048576` |
| Volumes | `kafkadata:/var/lib/kafka/data` |
| Dependencies | `zookeeper` (healthy) |
| Healthcheck | `kafka-broker-api-versions --bootstrap-server localhost:9092` exits 0 |
| Restart | `unless-stopped` |
| Network | `weather-net` |

> **Critical:** `KAFKA_ADVERTISED_LISTENERS` MUST be `PLAINTEXT://kafka:9092`.
> Using `localhost` here breaks inter-container communication.

#### `kafka-ui`

| Property | Value |
|----------|-------|
| Image | `provectuslabs/kafka-ui:latest` |
| Ports | `8080:8080` |
| Environment | `KAFKA_CLUSTERS_0_NAME=weather-platform`, `KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS=kafka:9092`, `KAFKA_CLUSTERS_0_ZOOKEEPER=zookeeper:2181` |
| Volumes | None |
| Dependencies | `kafka` (healthy) |
| Healthcheck | HTTP GET `http://localhost:8080` returns 200 |
| Restart | `unless-stopped` |
| Network | `weather-net` |

#### `postgres`

| Property | Value |
|----------|-------|
| Image | `postgis/postgis:15-3.4` |
| Ports | `5432:5432` |
| Environment | `POSTGRES_DB=weatherdb`, `POSTGRES_USER=weather`, `POSTGRES_PASSWORD=${POSTGRES_PASSWORD}` |
| Volumes | `pgdata:/var/lib/postgresql/data`, `./sql/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro` |
| Dependencies | None |
| Healthcheck | `pg_isready -U weather -d weatherdb` exits 0 |
| Restart | `unless-stopped` |
| Network | `weather-net` |

> **Init SQL:** The `init.sql` file is mounted as a Docker entrypoint init script.
> PostgreSQL runs it automatically on first container start (when `pgdata` is empty).
> The `postgis/postgis:15-3.4` image includes `pgcrypto` and `postgis` extensions.

#### `spark-master`

| Property | Value |
|----------|-------|
| Image | `bitnami/spark:3.5` |
| Ports | `7077:7077` (cluster), `8081:8081` (Web UI) |
| Environment | `SPARK_MODE=master` |
| Volumes | None (checkpoints written to worker or shared volume) |
| Dependencies | None |
| Healthcheck | HTTP GET `http://localhost:8081` returns 200 |
| Restart | `unless-stopped` |
| Network | `weather-net` |

#### `spark-worker`

| Property | Value |
|----------|-------|
| Image | `bitnami/spark:3.5` |
| Ports | `8082:8082` |
| Environment | `SPARK_MODE=worker`, `SPARK_MASTER_URL=spark://spark-master:7077` |
| Volumes | `spark_checkpoints:/data/checkpoints`, `data_volume:/data` |
| Dependencies | `spark-master` |
| Healthcheck | HTTP GET `http://localhost:8082` returns 200 |
| Restart | `unless-stopped` |
| Network | `weather-net` |

#### `ingestion`

| Property | Value |
|----------|-------|
| Build | `./services/ingestion` |
| Ports | None (background producer) |
| Environment | `KAFKA_BOOTSTRAP_SERVERS=kafka:9092` |
| Volumes | `data_volume:/data` (for raw logs, dead-letter) |
| Dependencies | `kafka` (healthy) |
| Healthcheck | None (no HTTP) — relies on container running state |
| Restart | `unless-stopped` |
| Network | `weather-net` |

#### `api`

| Property | Value |
|----------|-------|
| Build | `./services/api` |
| Ports | `8000:8000` |
| Environment | `KAFKA_BOOTSTRAP_SERVERS=kafka:9092`, `DATABASE_URL=postgresql://weather:${POSTGRES_PASSWORD}@postgres:5432/weatherdb`, `JWT_SECRET_KEY=${JWT_SECRET_KEY}`, `JWT_EXPIRATION_HOURS=${JWT_EXPIRATION_HOURS:-8}`, `ADMIN_USERNAME=${ADMIN_USERNAME:-admin}`, `ADMIN_PASSWORD=${ADMIN_PASSWORD}`, `CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:5173}`, `MEDIA_UPLOAD_PATH=/data/media` |
| Volumes | `data_volume:/data` (for media uploads) |
| Dependencies | `kafka` (healthy), `postgres` (healthy) |
| Healthcheck | HTTP GET `http://localhost:8000/api/v1/health` returns 200 |
| Restart | `unless-stopped` |
| Network | `weather-net` |

#### `frontend`

| Property | Value |
|----------|-------|
| Build | `./services/frontend` |
| Ports | `5173:5173` |
| Environment | `VITE_API_URL=http://localhost:8000/api/v1` |
| Volumes | None |
| Dependencies | `api` (healthy) |
| Healthcheck | HTTP GET `http://localhost:5173` returns 200 |
| Restart | `unless-stopped` |
| Network | `weather-net` |

---

## 3. Docker Compose Implementation

### 3.1 `docker-compose.yml`

```yaml
version: "3.8"

services:
  # ─────────────────────────────────────────────────────
  # ZOOKEEPER
  # ─────────────────────────────────────────────────────
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6
    container_name: weather-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    healthcheck:
      test: ["CMD-SHELL", "echo ruok | nc localhost 2181 | grep imok"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # KAFKA
  # ─────────────────────────────────────────────────────
  kafka:
    image: confluentinc/cp-kafka:7.6
    container_name: weather-kafka
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
    volumes:
      - kafkadata:/var/lib/kafka/data
    healthcheck:
      test: ["CMD-SHELL", "kafka-broker-api-versions --bootstrap-server localhost:9092"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 30s
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # KAFKA UI
  # ─────────────────────────────────────────────────────
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: weather-kafka-ui
    depends_on:
      kafka:
        condition: service_healthy
    environment:
      KAFKA_CLUSTERS_0_NAME: weather-platform
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8080"]
      interval: 15s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # POSTGRESQL + POSTGIS
  # ─────────────────────────────────────────────────────
  postgres:
    image: postgis/postgis:15-3.4
    container_name: weather-postgres
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
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # SPARK MASTER
  # ─────────────────────────────────────────────────────
  spark-master:
    image: bitnami/spark:3.5
    container_name: weather-spark-master
    environment:
      SPARK_MODE: master
    ports:
      - "7077:7077"
      - "8081:8081"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8081"]
      interval: 15s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # SPARK WORKER
  # ─────────────────────────────────────────────────────
  spark-worker:
    image: bitnami/spark:3.5
    container_name: weather-spark-worker
    depends_on:
      - spark-master
    environment:
      SPARK_MODE: worker
      SPARK_MASTER_URL: spark://spark-master:7077
    ports:
      - "8082:8082"
    volumes:
      - spark_checkpoints:/data/checkpoints
      - data_volume:/data
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8082"]
      interval: 15s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # INGESTION SERVICE
  # ─────────────────────────────────────────────────────
  ingestion:
    build:
      context: ./services/ingestion
      dockerfile: Dockerfile
    container_name: weather-ingestion
    depends_on:
      kafka:
        condition: service_healthy
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      OPENMETEO_POLL_INTERVAL_SECONDS: ${OPENMETEO_POLL_INTERVAL_SECONDS:-300}
      RSS_POLL_INTERVAL_SECONDS: ${RSS_POLL_INTERVAL_SECONDS:-300}
    volumes:
      - data_volume:/data
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # FASTAPI BACKEND
  # ─────────────────────────────────────────────────────
  api:
    build:
      context: ./services/api
      dockerfile: Dockerfile
    container_name: weather-api
    depends_on:
      kafka:
        condition: service_healthy
      postgres:
        condition: service_healthy
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      DATABASE_URL: postgresql://weather:${POSTGRES_PASSWORD}@postgres:5432/weatherdb
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      JWT_EXPIRATION_HOURS: ${JWT_EXPIRATION_HOURS:-8}
      ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:5173}
      MEDIA_UPLOAD_PATH: /data/media
    ports:
      - "8000:8000"
    volumes:
      - data_volume:/data
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - weather-net

  # ─────────────────────────────────────────────────────
  # REACT FRONTEND
  # ─────────────────────────────────────────────────────
  frontend:
    build:
      context: ./services/frontend
      dockerfile: Dockerfile
    container_name: weather-frontend
    depends_on:
      api:
        condition: service_healthy
    environment:
      VITE_API_URL: http://localhost:8000/api/v1
    ports:
      - "5173:5173"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:5173"]
      interval: 15s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - weather-net

# ─────────────────────────────────────────────────────
# NETWORKS
# ─────────────────────────────────────────────────────
networks:
  weather-net:
    driver: bridge

# ─────────────────────────────────────────────────────
# VOLUMES
# ─────────────────────────────────────────────────────
volumes:
  pgdata:
    driver: local
  kafkadata:
    driver: local
  spark_checkpoints:
    driver: local
  data_volume:
    driver: local
```

---

## 4. Startup Dependency Rules

### 4.1 Boot Order

```
Phase 1 (no dependencies):
  └── zookeeper

Phase 2 (depends on zookeeper healthy):
  └── kafka

Phase 3 (depends on kafka healthy):
  ├── kafka-ui
  ├── ingestion
  └── api (also depends on postgres healthy)

Phase 4 (no dependencies, can start in parallel with Phase 2-3):
  └── postgres

Phase 5 (depends on nothing, but needs Spark master):
  ├── spark-master
  └── spark-worker (depends on spark-master started)

Phase 6 (depends on api healthy):
  └── frontend
```

### 4.2 Health-Readiness Requirements

| Service | Must Wait For | Health Check | Timeout |
|---------|-------------|-------------|---------|
| `kafka` | `zookeeper` healthy | `kafka-broker-api-versions` | 30s start period |
| `kafka-ui` | `kafka` healthy | HTTP 200 on `:8080` | 15s interval |
| `ingestion` | `kafka` healthy | Container running (no HTTP) | — |
| `api` | `kafka` healthy AND `postgres` healthy | HTTP 200 on `:8000/api/v1/health` | 10s interval |
| `postgres` | None | `pg_isready` | 5s interval |
| `spark-worker` | `spark-master` started | HTTP 200 on `:8082` | 15s interval |
| `frontend` | `api` healthy | HTTP 200 on `:5173` | 15s interval |

### 4.3 Why `depends_on` Alone Is Not Enough

Docker Compose `depends_on` only waits for a container to **start**, not to be
**ready**. The healthcheck-based dependency (`condition: service_healthy`) is
required for:

- `kafka` → must wait for `zookeeper` to be fully initialized
- `api` → must wait for both `kafka` and `postgres` to be accepting connections
- `frontend` → must wait for `api` to be serving

Without healthchecks, `api` might start before `postgres` is ready, causing
connection refused errors on first boot.

---

## 5. Docker Networks

### 5.1 Network Configuration

| Network | Driver | Purpose |
|---------|--------|---------|
| `weather-net` | bridge | All inter-service communication |

### 5.2 Service DNS Names

All services communicate via Docker Compose service names:

| From | To | DNS Name | Port |
|------|----|---------|------|
| Any container | Kafka | `kafka` | `9092` |
| Any container | PostgreSQL | `postgres` | `5432` |
| Any container | Zookeeper | `zookeeper` | `2181` |
| Spark worker | Spark master | `spark-master` | `7077` |
| Frontend (browser) | API | `localhost` | `8000` |
| Kafka-ui (browser) | Kafka | — | via `kafka:9092` |

### 5.3 Critical: `localhost` vs Docker DNS

| Scenario | Correct Address | Wrong Address |
|----------|----------------|---------------|
| Ingestion → Kafka | `kafka:9092` | `localhost:9092` ❌ |
| API → PostgreSQL | `postgres:5432` | `localhost:5432` ❌ |
| API → Kafka | `kafka:9092` | `localhost:9092` ❌ |
| Spark → Kafka | `kafka:9092` | `localhost:9092` ❌ |
| Browser → Kafka-ui | `localhost:8080` | `kafka-ui:8080` ❌ |
| Browser → API | `localhost:8000` | `api:8000` ❌ |
| Browser → Frontend | `localhost:5173` | `frontend:5173` ❌ |

> **Rule:** Inside a container, use Docker service names. From the host machine
> (browser, curl), use `localhost` with the mapped port.

---

## 6. Volumes and Persistence

### 6.1 Volume Definitions

| Volume | Mount Point | Purpose | Survives Restart? |
|--------|------------|---------|-------------------|
| `pgdata` | `/var/lib/postgresql/data` | PostgreSQL data files | ✅ Yes |
| `kafkadata` | `/var/lib/kafka/data` | Kafka log segments | ✅ Yes |
| `spark_checkpoints` | `/data/checkpoints` | Spark Structured Streaming checkpoints | ✅ Yes |
| `data_volume` | `/data` | Raw data, processed Parquet, media, logs, dead-letter | ✅ Yes |

> **Development note:** `data_volume` is a named Docker volume. For development,
> you may prefer bind mounts (`./data/raw:/data/raw`, `./data/logs:/data/logs`)
> for easier file inspection. Both approaches are compatible with the architecture.
> Named volumes are used in this spec for consistency with production-like
> deployment.

### 6.2 Bind-Mounted Host Paths

| Host Path | Container Mount | Service | Purpose |
|-----------|----------------|---------|---------|
| `./sql/init.sql` | `/docker-entrypoint-initdb.d/01-init.sql:ro` | postgres | Database initialization |
| `./services/ingestion` | Build context | ingestion | Source code |
| `./services/api` | Build context | api | Source code |
| `./services/frontend` | Build context | frontend | Source code |

### 6.3 Data Persistence Rules

| Data Type | Stored In | Survives `docker compose down`? | Survives `docker compose down -v`? |
|-----------|----------|-------------------------------|----------------------------------|
| PostgreSQL data | `pgdata` volume | ✅ Yes | ❌ No (volume deleted) |
| Kafka logs | `kafkadata` volume | ✅ Yes | ❌ No (volume deleted) |
| Spark checkpoints | `spark_checkpoints` volume | ✅ Yes | ❌ No (volume deleted) |
| Raw data archive | `data_volume` → `/data/raw/` | ✅ Yes | ❌ No (volume deleted) |
| Processed Parquet | `data_volume` → `/data/processed/` | ✅ Yes | ❌ No (volume deleted) |
| Media uploads | `data_volume` → `/data/media/` | ✅ Yes | ❌ No (volume deleted) |
| Dead-letter logs | `data_volume` → `/data/logs/` | ✅ Yes | ❌ No (volume deleted) |

> **Warning:** `docker compose down -v` destroys ALL persistent data.
> Use only for a complete fresh start.

---

## 7. Environment Variables

### 7.1 `.env.example` (Committed Without Values)

```bash
# ═══════════════════════════════════════════════════════
# PostgreSQL
# ═══════════════════════════════════════════════════════
POSTGRES_PASSWORD=                  # REQUIRED — no default
# POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER
# are derived from docker-compose service config — not needed in .env.
# DATABASE_URL is constructed from these in docker-compose.yml.

# ═══════════════════════════════════════════════════════
# Kafka (read by ingestion, api, spark)
# ═══════════════════════════════════════════════════════
# KAFKA_BOOTSTRAP_SERVERS is set in docker-compose.yml
# as kafka:9092 — no .env entry needed for Docker services.
# Host tools use localhost:29092.

# ═══════════════════════════════════════════════════════
# FastAPI
# ═══════════════════════════════════════════════════════
JWT_SECRET_KEY=                    # REQUIRED — app refuses to start without it
JWT_EXPIRATION_HOURS=8             # Optional — defaults to 8
ADMIN_USERNAME=admin               # Optional — defaults to "admin"
ADMIN_PASSWORD=                    # REQUIRED — bcrypt hash

# ═══════════════════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════════════════
CORS_ORIGINS=http://localhost:5173 # Comma-separated allowed origins

# ═══════════════════════════════════════════════════════
# Ingestion (optional overrides)
# ═══════════════════════════════════════════════════════
OPENMETEO_POLL_INTERVAL_SECONDS=300 # Open-Meteo polling interval
RSS_POLL_INTERVAL_SECONDS=300       # RSS feed polling interval

# ═══════════════════════════════════════════════════════
# Spark / ML (optional overrides)
# ═══════════════════════════════════════════════════════
SPARK_WRITE_PROCESSED_TOPIC=false  # Set to "true" to write to weather.processed
SPARK_CHECKPOINT_PATH=/data/checkpoints/spark_streaming
PG_WRITER_CHECKPOINT_PATH=/data/checkpoints/pg_writer
ML_CLUSTER_RADIUS_KM=3.0
ML_CLUSTER_TIME_WINDOW_MINUTES=30
CLASSIFIER_BACKEND=rule_based      # Options: rule_based | trained | hybrid
MODEL_PATH=/opt/models/event_classifier/model.pkl
```

### 7.2 Variable Reference Table

| Variable | Used By | Required | Default | Source Document |
|----------|---------|----------|---------|----------------|
| `POSTGRES_PASSWORD` | postgres, api | Yes | — | `04_API_CONTRACT.md §3.3` |
| `JWT_SECRET_KEY` | api | Yes | — | `04_API_CONTRACT.md §3.3` |
| `JWT_EXPIRATION_HOURS` | api | No | `8` | `04_API_CONTRACT.md §3.3` |
| `ADMIN_USERNAME` | api | No | `admin` | `04_API_CONTRACT.md §3.3` |
| `ADMIN_PASSWORD` | api | Yes | — | `04_API_CONTRACT.md §3.3` |
| `CORS_ORIGINS` | api | No | `http://localhost:5173` | `04_API_CONTRACT.md §20` |
| `KAFKA_BOOTSTRAP_SERVERS` | ingestion, api | — | Set in compose: `kafka:9092` | `03_KAFKA_CONTRACT.md §1.3` |
| `OPENMETEO_POLL_INTERVAL_SECONDS` | ingestion | No | `300` | `06_IMPLEMENTATION_PLAN.md §6` |
| `RSS_POLL_INTERVAL_SECONDS` | ingestion | No | `300` | `06_IMPLEMENTATION_PLAN.md §6` |
| `SPARK_WRITE_PROCESSED_TOPIC` | spark job | No | `false` | `01_ARCHITECTURE.md §9` |
| `SPARK_CHECKPOINT_PATH` | spark job | No | `/data/checkpoints/spark_streaming` | `06_IMPLEMENTATION_PLAN.md §6` |
| `PG_WRITER_CHECKPOINT_PATH` | spark job | No | `/data/checkpoints/pg_writer` | `06_IMPLEMENTATION_PLAN.md §6` |
| `CLASSIFIER_BACKEND` | ml (via spark) | No | `rule_based` | `05_AI_ML_SPEC.md §22.2` |
| `MODEL_PATH` | ml (via spark) | No | `/opt/models/event_classifier/model.pkl` | `05_AI_ML_SPEC.md §19.5` |
| `ML_CLUSTER_RADIUS_KM` | ml (via spark) | No | `3.0` | `05_AI_ML_SPEC.md §22` |
| `ML_CLUSTER_TIME_WINDOW_MINUTES` | ml (via spark) | No | `30` | `05_AI_ML_SPEC.md §22` |
| `VITE_API_URL` | frontend | No | `http://localhost:8000/api/v1` | `06_IMPLEMENTATION_PLAN.md §6` |

### 7.3 Credential Generation

```bash
# Generate JWT secret key
openssl rand -hex 32

# Generate admin password hash (Python required)
python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password-here'))"
```

---

## 8. Database Initialization

### 8.1 Mechanism

PostgreSQL uses Docker entrypoint initialization:
- `./sql/init.sql` is mounted to `/docker-entrypoint-initdb.d/01-init.sql`
- This script runs **automatically** on first container start (empty `pgdata`)
- It does **NOT** re-run on subsequent starts (data already exists)

### 8.2 Init Script Content

The complete `sql/init.sql` is defined in `06_IMPLEMENTATION_PLAN.md §9`
and matches `02_DATA_SCHEMA.md §17` exactly.

Execution order:
1. `CREATE EXTENSION IF NOT EXISTS pgcrypto`
2. `CREATE EXTENSION IF NOT EXISTS postgis`
3. `CREATE FUNCTION sync_geom()`
4. `CREATE FUNCTION set_updated_at()`
5. `CREATE TABLE event_clusters` (no FK dependencies)
6. `CREATE TABLE events` (FK → event_clusters)
7. `CREATE TABLE sources`
8. `CREATE TABLE verification_log` (FK → events)
9. 11 `CREATE INDEX` statements
10. 4 `CREATE TRIGGER` statements
11. `INSERT INTO sources` seed data (Open-Meteo, citizen_form)

### 8.3 Verification

After first boot, verify with:

```bash
docker compose exec postgres psql -U weather -d weatherdb -c "\dt"
# Expected: events, event_clusters, sources, verification_log

docker compose exec postgres psql -U weather -d weatherdb -c "\di"
# Expected: 11 indexes

docker compose exec postgres psql -U weather -d weatherdb -c "SELECT count(*) FROM sources;"
# Expected: 2 (Open-Meteo, citizen_form)
```

### 8.4 Re-initialization

To re-run init SQL on an existing database:

```bash
# Option A: Destroy and recreate
docker compose down -v
docker compose up -d postgres

# Option B: Manual re-run (caution: may fail on existing objects)
docker compose exec -T postgres psql -U weather -d weatherdb < sql/init.sql
```

---

## 9. Kafka Initialization

### 9.1 Topic Creation

Topics are **NOT auto-created** (`KAFKA_AUTO_CREATE_TOPICS_ENABLE=false`).
They must be created before any producer or consumer starts.

### 9.2 Creation Script: `scripts/init-kafka.sh`

```bash
#!/bin/bash
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:29092}"

echo "Waiting for Kafka to be ready..."
until kafka-topics --bootstrap-server "$BOOTSTRAP" --list > /dev/null 2>&1; do
  sleep 2
done
echo "Kafka is ready."

# Create all 7 approved topics
TOPICS=(
  "weather.raw:1:1"
  "citizen.raw:1:1"
  "social.raw:1:1"
  "government.raw:1:1"
  "weather.processed:1:1"
  "weather.events:1:1"
  "weather.verified:1:1"
)

for config in "${TOPICS[@]}"; do
  IFS=':' read -r name parts repl <<< "$config"
  echo "Creating topic: $name (partitions=$parts, replication=$repl)"
  kafka-topics --bootstrap-server "$BOOTSTRAP" \
    --create --if-not-exists \
    --topic "$name" \
    --partitions "$parts" \
    --replication-factor "$repl" \
    2>/dev/null || echo "  Topic $name already exists"
done

echo ""
echo "All topics:"
kafka-topics --bootstrap-server "$BOOTSTRAP" --list
```

### 9.3 Topic Configuration

Per `03_KAFKA_CONTRACT.md §2.2`:

| Topic | Partitions | Replication | Retention | Key |
|-------|-----------|-------------|-----------|-----|
| `weather.raw` | 1 | 1 | 7 days | `event_id` |
| `citizen.raw` | 1 | 1 | 7 days | `event_id` |
| `social.raw` | 1 | 1 | 7 days | `event_id` |
| `government.raw` | 1 | 1 | 7 days | `event_id` |
| `weather.processed` | 1 | 1 | 24 hours | `event_id` |
| `weather.events` | 1 | 1 | 7 days | `event_id` |
| `weather.verified` | 1 | 1 | 30 days | `event_id` |

### 9.4 Verification

```bash
# From host (using host-mapped port)
kafka-topics --bootstrap-server localhost:29092 --list
# Expected: 7 topic names

# From inside Docker network
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

---

## 10. Spark Deployment

### 10.1 Spark Infrastructure

| Component | Container | Image | Role |
|-----------|----------|-------|------|
| Master | `weather-spark-master` | `bitnami/spark:3.5` | Cluster coordinator; Web UI at `:8081` |
| Worker | `weather-spark-worker` | `bitnami/spark:3.5` | Executes tasks; Web UI at `:8082` |

### 10.2 ML Library Integration

The ML library at `services/ml/` is made available to Spark by:

1. **Build time:** The Spark Dockerfile (at `services/spark/Dockerfile`) copies
   the ML library into the image:
   ```dockerfile
   FROM bitnami/spark:3.5
   USER root
   COPY services/ml/ /opt/spark/ml/
   COPY services/spark/jobs/ /opt/spark/jobs/
   COPY services/spark/requirements.txt /opt/spark/requirements.txt
   RUN pip install --no-cache-dir -r /opt/spark/requirements.txt
   USER 1001
   ```

2. **Runtime:** The Spark job imports ML functions directly:
   ```python
   import sys
   sys.path.insert(0, "/opt/spark")
   from ml.classifier.event_classifier import classify_event
   ```

> **ML is a Python library, NOT a Docker service.** Per `01_ARCHITECTURE.md §5`.
>
> **Model artifact:** When `CLASSIFIER_BACKEND=trained` or `hybrid`, the trained model
> at `models/event_classifier/model.pkl` must be available inside the Spark worker.
> Mount it via docker-compose:
> ```yaml
> volumes:
>   - ./models:/opt/models    # Maps to MODEL_PATH=/opt/models/event_classifier/model.pkl
> ```
> For `CLASSIFIER_BACKEND=rule_based` (MVP default), no model artifact is needed.

### 10.3 Job Submission

The Spark streaming job and PostgreSQL writer are launched inside the Spark
worker container:

```bash
# Stream processor (main job)
docker compose exec spark-worker spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --conf spark.sql.shuffle.partitions=1 \
  /opt/spark/jobs/stream_processor.py

# PostgreSQL writer (separate process)
docker compose exec spark-worker spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  /opt/spark/jobs/pg_writer.py
```

### 10.4 Checkpoint Directories

| Job | Checkpoint Path | Volume |
|-----|----------------|--------|
| `stream_processor.py` | `/data/checkpoints/spark_streaming/` | `spark_checkpoints` |
| `pg_writer.py` | `/data/checkpoints/pg_writer/` | `spark_checkpoints` |

### 10.5 Restart and Recovery

Per `03_KAFKA_CONTRACT.md §10.3`:
- Spark checkpoints track consumed Kafka offsets
- On restart, Spark resumes from the last committed offset
- Idempotent processing prevents duplicate effects
- **Do NOT delete checkpoints** unless a full reprocess is desired

---

## 11. Application Dockerfiles

### 11.1 `services/ingestion/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

**Dependencies:** `confluent-kafka`, `httpx`, `feedparser`, `beautifulsoup4`, `pydantic`, `pyyaml`

### 11.2 `services/api/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dependencies:** `fastapi`, `uvicorn[standard]`, `psycopg2-binary`, `confluent-kafka`, `python-jose[cryptography]`, `passlib[bcrypt]`, `pydantic`, `python-multipart`

### 11.3 `services/frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Vite dev server for development (alternative to nginx):
# FROM node:20-alpine
# WORKDIR /app
# COPY package.json package-lock.json* ./
# RUN npm install
# COPY . .
# CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

EXPOSE 5173
CMD ["npx", "serve", "-s", "dist", "-l", "5173"]
```

> **Development note:** For live-reload during development, use the Vite dev
> server variant instead of the nginx build. Mount source code as a volume:
> `docker compose -f docker-compose.dev.yml up frontend`

### 11.4 `services/spark/Dockerfile`

```dockerfile
FROM bitnami/spark:3.5

USER root

# Copy ML library
COPY services/ml/ /opt/spark/ml/

# Copy Spark jobs
COPY services/spark/jobs/ /opt/spark/jobs/
COPY services/spark/requirements.txt /opt/spark/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /opt/spark/requirements.txt

USER 1001
```

**Dependencies:** `numpy`, `pyyaml`, `confluent-kafka`

> When `CLASSIFIER_BACKEND=trained` or `hybrid`, add `scikit-learn` and `joblib`
> to the Spark `requirements.txt`. See `05_AI_ML_SPEC.md §19.5`.

---

## 12. Frontend Configuration

### 12.1 API Communication

The React frontend communicates with the FastAPI backend via HTTP.

| Context | API Base URL | Protocol |
|---------|-------------|----------|
| Browser (development) | `http://localhost:8000/api/v1` | HTTP |
| Frontend container → API container | `http://localhost:8000/api/v1` | HTTP (via Docker port mapping) |

### 12.2 Vite Environment Variable

The API URL is configured via the `VITE_API_URL` environment variable:

```javascript
// services/frontend/src/api/client.js
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const apiClient = {
  async getEvents(params) {
    const response = await fetch(`${API_BASE_URL}/events?${new URLSearchParams(params)}`);
    return response.json();
  },
  // ... other methods
};
```

### 12.3 Browser → API Connection

The browser connects to the API at `localhost:8000` (host-mapped port).
The frontend container does NOT proxy API requests — the browser talks
directly to the API's host-mapped port.

```
Browser (host)
  ↓ HTTP to localhost:8000
API container (port 8000 mapped)
```

---

## 13. CORS

### 13.1 Configuration

Per `04_API_CONTRACT.md §20`:

```python
# services/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 13.2 Environment Override

```
CORS_ORIGINS=http://localhost:5173
```

> **No unrestricted `*` origin.** Only the configured frontend origin is allowed.
> This is a security requirement from `04_API_CONTRACT.md §20`.

---

## 14. Health Checks

### 14.1 Health Check Summary

| Service | Check Type | Command/URL | Interval | Timeout | Start Period | Retries |
|---------|-----------|-------------|----------|---------|-------------|---------|
| `zookeeper` | TCP | `echo ruok \| nc localhost 2181` | 10s | 5s | — | 5 |
| `kafka` | CLI | `kafka-broker-api-versions --bootstrap-server localhost:9092` | 10s | 10s | 30s | 10 |
| `kafka-ui` | HTTP | `GET http://localhost:8080` | 15s | 5s | — | 5 |
| `postgres` | CLI | `pg_isready -U weather -d weatherdb` | 5s | 5s | — | 10 |
| `spark-master` | HTTP | `GET http://localhost:8081` | 15s | 5s | — | 5 |
| `spark-worker` | HTTP | `GET http://localhost:8082` | 15s | 5s | — | 5 |
| `api` | HTTP | `GET http://localhost:8000/api/v1/health` | 10s | 5s | — | 5 |
| `frontend` | HTTP | `GET http://localhost:5173` | 15s | 5s | — | 5 |
| `ingestion` | None | Container running state | — | — | — | — |

### 14.2 Failure Behaviour

| Health Check Fails | Consequence |
|-------------------|-------------|
| `zookeeper` down | `kafka` won't start; all Kafka-dependent services block |
| `kafka` down | `ingestion`, `api` can't produce; Spark can't consume |
| `postgres` down | `api` health returns degraded/unhealthy; read endpoints fail |
| `api` down | `frontend` starts but shows connection errors |
| `spark-master` down | `spark-worker` disconnects; streaming stops |

---

## 15. Startup Commands

### 15.1 Fresh Setup

```bash
# 1. Clone and configure
git clone <repo-url>
cd weather-platform
cp .env.example .env

# 2. Generate secrets
# Edit .env and set:
#   POSTGRES_PASSWORD=<your-password>
#   JWT_SECRET_KEY=$(openssl rand -hex 32)
#   ADMIN_PASSWORD=$(python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('<password>'))")

# 3. Create data directories
mkdir -p data/{raw/government,processed,synthetic,media/{photos,videos},logs/{app,dead_letter}}

# 4. Start all services
docker compose up -d

# 5. Wait for health checks (~60 seconds)
docker compose ps  # All should show "healthy" or "running"

# 6. Create Kafka topics
bash scripts/init-kafka.sh

# 7. Verify
curl http://localhost:8000/api/v1/health
```

### 15.2 Normal Startup

```bash
docker compose up -d
# Services start in dependency order; healthchecks gate startup
```

### 15.3 Restart

```bash
docker compose restart
# Preserves volumes; services re-register with healthchecks
```

### 15.4 Stop

```bash
docker compose stop
# Stops containers; preserves volumes and data
```

### 15.5 Full Reset

```bash
docker compose down -v
# ⚠️ DESTROYS all volumes (PostgreSQL data, Kafka data, checkpoints, uploaded files)
# Use only for a complete fresh start
```

### 15.6 Rebuild After Code Changes

```bash
# Rebuild specific service
docker compose build api
docker compose up -d api

# Rebuild all custom images
docker compose build
docker compose up -d
```

### 15.7 View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f ingestion
docker compose logs -f spark-worker

# Last 100 lines
docker compose logs --tail 100 api
```

### 15.8 Check Service Status

```bash
docker compose ps
# Shows: name, image, status, health, ports
```

---

## 16. Smoke Test

### `scripts/smoke-test.sh`

```bash
#!/bin/bash
set -euo pipefail

PASS=0
FAIL=0

check() {
  local desc="$1"
  local cmd="$2"
  local expected="$3"

  result=$(eval "$cmd" 2>/dev/null)
  if echo "$result" | grep -q "$expected"; then
    echo "✅ $desc"
    PASS=$((PASS + 1))
  else
    echo "❌ $desc (expected: $expected, got: $result)"
    FAIL=$((FAIL + 1))
  fi
}

echo "═══════════════════════════════════════"
echo "  Weather Platform — Smoke Test"
echo "═══════════════════════════════════════"
echo ""

# Step 1: Kafka topics exist
check "Kafka topics exist" \
  "kafka-topics --bootstrap-server localhost:29092 --list 2>/dev/null | wc -l" \
  "7"

# Step 2: PostgreSQL tables exist
check "PostgreSQL tables exist" \
  "docker compose exec -T postgres psql -U weather -d weatherdb -t -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'\"" \
  "4"

# Step 3: PostGIS extension active
check "PostGIS extension active" \
  "docker compose exec -T postgres psql -U weather -d weatherdb -t -c \"SELECT count(*) FROM pg_extension WHERE extname='postgis'\"" \
  "1"

# Step 4: API health endpoint
check "API health endpoint returns 200" \
  "curl -sf http://localhost:8000/api/v1/health" \
  "healthy\|degraded"

# Step 5: Events endpoint returns data
check "GET /events returns data" \
  "curl -sf http://localhost:8000/api/v1/events" \
  "items"

# Step 6: Frontend serves HTML
check "Frontend serves HTML" \
  "curl -sf http://localhost:5173" \
  "root\|<!DOCTYPE"

# Step 7: Spark UI accessible
check "Spark UI accessible" \
  "curl -sf http://localhost:8081" \
  "Spark"

# Step 8: Kafka UI accessible
check "Kafka UI accessible" \
  "curl -sf http://localhost:8080" \
  ""

# Step 9: Swagger docs accessible
check "Swagger docs accessible" \
  "curl -sf http://localhost:8000/docs" \
  "swagger\|openapi"

echo ""
echo "═══════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
```

### Expected Results

| Step | Check | Expected |
|------|-------|---------|
| 1 | Kafka topics | 7 topics listed |
| 2 | PostgreSQL tables | 4 tables (events, event_clusters, sources, verification_log) |
| 3 | PostGIS extension | 1 (active) |
| 4 | API health | `"healthy"` or `"degraded"` |
| 5 | GET /events | JSON with `"items"` key |
| 6 | Frontend | HTML with `<div id="root">` |
| 7 | Spark UI | Spark master Web UI page |
| 8 | Kafka UI | Kafka UI page loads |
| 9 | Swagger docs | OpenAPI/Swagger UI page |

---

## 17. Failure Recovery

Per `03_KAFKA_CONTRACT.md §10`:

| Failure | Container | Recovery | Data Loss? |
|---------|----------|---------|-----------|
| Kafka restart | `kafka` | Automatic; producers/consumers reconnect | No (data in `kafkadata` volume) |
| PostgreSQL restart | `postgres` | Automatic; connections re-establish | No (data in `pgdata` volume) |
| Spark restart | `spark-master` + `spark-worker` | Automatic; resumes from checkpoint | No (checkpoints in `spark_checkpoints` volume) |
| Ingestion restart | `ingestion` | Automatic; resumes producing from source | Possibly 1 poll interval of events |
| API restart | `api` | Automatic; reconnects to DB + Kafka | No |
| Frontend restart | `frontend` | Automatic; served from static files | No |
| Container killed mid-processing | Any | `restart: unless-stopped` restarts it | No (at-least-once + idempotent) |

### Key Recovery Mechanisms

| Mechanism | Implementation | Contract Reference |
|-----------|---------------|-------------------|
| At-least-once Kafka delivery | Producer retries + consumer offset tracking | `03_KAFKA_CONTRACT.md §10.1` |
| Idempotent DB writes | `INSERT ... ON CONFLICT (event_id) DO UPDATE` | `03_KAFKA_CONTRACT.md §10.2` |
| Spark checkpoint recovery | Checkpoints at `/data/checkpoints/spark_streaming/` | `03_KAFKA_CONTRACT.md §10.5` |
| Dead-letter for invalid events | Filesystem log at `/data/logs/dead_letter/` | `01_ARCHITECTURE.md §10` |

---

## 18. Resource Requirements

### 18.1 Minimum Requirements

| Resource | Minimum | Notes |
|----------|---------|-------|
| RAM | 8 GB | Kafka (1GB) + Spark (2GB) + PostgreSQL (512MB) + API/Ingestion (512MB each) + OS overhead |
| CPU | 4 cores | Spark worker benefits from multiple cores |
| Disk | 20 GB free | Docker images (~8GB) + volumes + data |
| Docker | 24+ | Docker Engine with Compose v2 |

### 18.2 Recommended

| Resource | Recommended | Notes |
|----------|------------|-------|
| RAM | 16 GB | Allows comfortable multi-service operation |
| CPU | 8 cores | Spark processing + Kafka I/O + API |
| Disk | 50 GB free | Room for synthetic data + Parquet output |

### 18.3 Resource Consumers (Ranked)

| Rank | Service | RAM Usage | CPU Usage | Disk I/O |
|------|---------|----------|----------|----------|
| 1 | Spark (master + worker) | ~2 GB | High during processing | Medium (Parquet writes) |
| 2 | Kafka | ~1 GB | Medium | High (log segments) |
| 3 | PostgreSQL | ~512 MB | Medium | Medium (writes + spatial queries) |
| 4 | Ingestion | ~256 MB | Low | Low |
| 5 | API | ~256 MB | Low | Low |
| 6 | Frontend | ~128 MB | Negligible | None |

> **No performance benchmarks are claimed.** These are rough estimates based on
> typical Docker Compose deployments. Actual usage depends on event volume.

---

## 19. Security

### 19.1 Confirmed Security Properties

| Property | Implementation | Contract Reference |
|----------|---------------|-------------------|
| Secrets via env vars | `.env` file loaded by Docker Compose | `01_ARCHITECTURE.md §12` |
| `.env` gitignored | Listed in `.gitignore` | `01_ARCHITECTURE.md §12` |
| `.env.example` has placeholders | Committed without real values | `06_IMPLEMENTATION_PLAN.md §6` |
| No credentials in Dockerfiles | Dockerfiles only install packages | This document §11 |
| No credentials in Kafka messages | Canonical Event contains no secrets | `03_KAFKA_CONTRACT.md §13.2` |
| No unnecessary PII | No names, emails, phone numbers | `03_KAFKA_CONTRACT.md §13.3` |
| Media validation | File type + size checked before storage | `04_API_CONTRACT.md §13` |
| CORS restricted | Only `http://localhost:5173` allowed | `04_API_CONTRACT.md §20` |
| JWT for admin | `POST /verification` requires Bearer token | `04_API_CONTRACT.md §3` |
| SQL injection protection | Parameterised queries via ORM | `04_API_CONTRACT.md §22` |

### 19.2 `.gitignore` Entries

```gitignore
# Environment
.env

# Docker volumes (data)
data/

# Python
__pycache__/
*.pyc
.venv/

# Node
node_modules/
dist/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

---

## 20. Troubleshooting

### 20.1 Kafka Not Starting

**Symptom:** `weather-kafka` exits immediately or shows `Crloop` status.

**Cause:** Zookeeper not ready; port conflict; corrupted Kafka data.

**Fix:**
```bash
# Check Zookeeper health
docker compose ps zookeeper

# If Zookeeper is unhealthy, restart it first
docker compose restart zookeeper
sleep 10
docker compose restart kafka

# If port 9092 or 29092 is in use
lsof -i :9092  # Find process using the port
kill <PID>     # Stop conflicting process

# If Kafka data is corrupted
docker compose down -v
docker compose up -d zookeeper kafka
```

### 20.2 Zookeeper Unavailable

**Symptom:** Kafka logs show `zookeeper not available`.

**Fix:**
```bash
docker compose restart zookeeper
sleep 15
docker compose restart kafka
```

### 20.3 Port Already in Use

**Symptom:** `Bind for 0.0.0.0:5432 failed: port is already allocated`

**Fix:**
```bash
# Find what's using the port
lsof -i :5432

# Option 1: Stop the conflicting service
# Option 2: Change the host port in docker-compose.yml
#   ports: "5433:5432"  (use 5433 on host instead)
```

### 20.4 PostgreSQL Connection Refused

**Symptom:** API logs show `connection refused` to PostgreSQL.

**Fix:**
```bash
# Check PostgreSQL is running and healthy
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres

# Verify connectivity from API container
docker compose exec api python -c "import psycopg2; psycopg2.connect('postgresql://weather:${POSTGRES_PASSWORD}@postgres:5432/weatherdb')"

# If password mismatch, recreate
docker compose down -v
docker compose up -d postgres
```

### 20.5 PostGIS Missing

**Symptom:** `CREATE EXTENSION postgis` fails.

**Cause:** Wrong PostgreSQL image (missing PostGIS).

**Fix:** Ensure `docker-compose.yml` uses `postgis/postgis:15-3.4`, NOT `postgres:15`.

### 20.6 Spark Worker Not Connecting

**Symptom:** Spark UI shows 0 workers.

**Fix:**
```bash
# Check spark-master is running
docker compose ps spark-master

# Check spark-worker logs
docker compose logs spark-worker

# Verify network connectivity
docker compose exec spark-worker ping spark-master

# Restart in order
docker compose restart spark-master
sleep 5
docker compose restart spark-worker
```

### 20.7 ML Module Import Failure

**Symptom:** Spark job logs show `ModuleNotFoundError: No module named 'ml'`.

**Cause:** ML library not copied into Spark image.

**Fix:**
```bash
# Rebuild Spark image with ML library
docker compose build spark-worker
docker compose up -d spark-worker

# Verify ML is available
docker compose exec spark-worker python -c "import sys; sys.path.insert(0, '/opt/spark'); from ml.classifier.event_classifier import classify_event; print('OK')"
```

### 20.8 Kafka Topic Missing

**Symptom:** Ingestion logs show `TopicNotExistsError`.

**Fix:**
```bash
bash scripts/init-kafka.sh

# Verify
kafka-topics --bootstrap-server localhost:29092 --list
```

### 20.9 API Cannot Connect to Database

**Symptom:** `GET /health` returns `"database": "unavailable"`.

**Fix:**
```bash
# Check DATABASE_URL is correct
docker compose exec api env | grep DATABASE_URL

# Test connection directly
docker compose exec api python -c "
import psycopg2
conn = psycopg2.connect('postgresql://weather:${POSTGRES_PASSWORD}@postgres:5432/weatherdb')
print('Connected!')
conn.close()
"

# If password wrong, update .env and recreate api
docker compose up -d api
```

### 20.10 Frontend Cannot Reach API

**Symptom:** Dashboard shows "Failed to fetch" or CORS error.

**Fix:**
```bash
# Check CORS_ORIGINS in .env
cat .env | grep CORS

# Should be: CORS_ORIGINS=http://localhost:5173

# Check API is running
curl http://localhost:8000/api/v1/health

# Check browser console for exact error
# If CORS error, ensure API has CORS middleware configured
```

### 20.11 CORS Error

**Symptom:** Browser console shows `Access-Control-Allow-Origin` error.

**Fix:**
```bash
# Verify CORS_ORIGINS includes the frontend origin
docker compose exec api env | grep CORS

# Ensure API main.py has CORS middleware:
# app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], ...)

# Restart API after config change
docker compose restart api
```

### 20.12 Stale Docker Volumes

**Symptom:** Old data persists after code changes; unexpected behaviour.

**Fix:**
```bash
# Nuclear option: destroy everything and start fresh
docker compose down -v --remove-orphans
docker system prune -f
docker compose up -d

# Or selectively clear specific volume
docker volume rm weather-platform_pgdata
docker compose up -d postgres
```

---

## 21. Deployment Acceptance Checklist

A fresh developer can declare the deployment successful when ALL items pass:

| # | Step | Command | Expected Result |
|---|------|---------|----------------|
| 1 | Clone repository | `git clone <url> && cd weather-platform` | Source code available |
| 2 | Create `.env` | `cp .env.example .env` then edit | Secrets configured |
| 3 | Start infrastructure | `docker compose up -d zookeeper kafka postgres` | All 3 containers running |
| 4 | Wait for health | `docker compose ps` (wait ~30s) | All 3 show "healthy" |
| 5 | Create Kafka topics | `bash scripts/init-kafka.sh` | 7 topics listed |
| 6 | Start Spark | `docker compose up -d spark-master spark-worker` | Spark UI at :8081 |
| 7 | Start remaining | `docker compose up -d` | All 9 services running |
| 8 | Wait for health | `docker compose ps` (wait ~30s) | All services healthy |
| 9 | Verify API | `curl http://localhost:8000/api/v1/health` | `{"status":"healthy",...}` |
| 10 | Run smoke test | `bash scripts/smoke-test.sh` | All checks pass |

### Post-Start Verification

| # | Check | Command | Expected |
|---|-------|---------|---------|
| 11 | Kafka-ui | Open `http://localhost:8080` | Kafka UI page loads |
| 12 | Spark UI | Open `http://localhost:8081` | Spark master page loads |
| 13 | API docs | Open `http://localhost:8000/docs` | Swagger UI loads |
| 14 | Frontend | Open `http://localhost:5173` | React app loads |
| 15 | DB tables | `docker compose exec postgres psql -U weather -d weatherdb -c "\dt"` | 4 tables listed |
| 16 | DB indexes | `docker compose exec postgres psql -U weather -d weatherdb -c "\di"` | 11 indexes listed |

---

## 22. Final Consistency Check

### Against `01_ARCHITECTURE.md`

| Check | Result | Evidence |
|-------|--------|----------|
| 9 Docker services match §5 | ✅ PASS | zookeeper, kafka, kafka-ui, postgres, spark-master, spark-worker, ingestion, api, frontend |
| Port mapping matches §5 | ✅ PASS | 2181, 9092/29092, 8080, 5432, 7077/8081, 8082, 8000, 5173 — all identical |
| ML NOT a Docker service | ✅ PASS | §2.1 explicitly states "services/ml/ is NOT a Docker service" |
| Kafka internal port 9092, host port 29092 | ✅ PASS | §3.1 compose file matches |
| Kafka UI at 8080 | ✅ PASS | §2.2 matches |
| PostgreSQL 15 + PostGIS 3.4 | ✅ PASS | Image `postgis/postgis:15-3.4` |
| pgcrypto included | ✅ PASS | `postgis/postgis:15-3.4` image includes pgcrypto |
| Data lake paths match §8 | ✅ PASS | `/data/raw/`, `/data/processed/`, `/data/synthetic/`, `/data/media/`, `/data/logs/` |

### Against `02_DATA_SCHEMA.md`

| Check | Result | Evidence |
|-------|--------|----------|
| `init.sql` matches §17 exactly | ✅ PASS | Same extensions, functions, tables, indexes, triggers |
| 4 tables created | ✅ PASS | events, event_clusters, sources, verification_log |
| 11 indexes created | ✅ PASS | All index names match §8 |
| 4 triggers created | ✅ PASS | sync_geom + 3 set_updated_at |
| Seed data for sources | ✅ PASS | Open-Meteo + citizen_form inserted |

### Against `03_KAFKA_CONTRACT.md`

| Check | Result | Evidence |
|-------|--------|----------|
| 7 topics created | ✅ PASS | §9.2 script creates all 7 |
| Topic configs match §2.2 | ✅ PASS | 1 partition, replication factor 1 for all |
| `KAFKA_AUTO_CREATE_TOPICS_ENABLE=false` | ✅ PASS | §3.1 compose file |
| `KAFKA_ADVERTISED_LISTENERS=kafka:9092` | ✅ PASS | §3.1 compose file |
| Bootstrap servers consistent | ✅ PASS | All services use `kafka:9092` internally |

### Against `04_API_CONTRACT.md`

| Check | Result | Evidence |
|-------|--------|----------|
| API port 8000 | ✅ PASS | §2.2 service detail |
| CORS for localhost:5173 | ✅ PASS | §13 CORS section |
| JWT secret required | ✅ PASS | `JWT_SECRET_KEY` marked REQUIRED |
| Health endpoint at `/api/v1/health` | ✅ PASS | Healthcheck uses this path |
| Swagger docs at `/docs` | ✅ PASS | Smoke test checks this |

### Against `05_AI_ML_SPEC.md`

| Check | Result | Evidence |
|-------|--------|----------|
| ML library COPY-ed into Spark image | ✅ PASS | §10.2 Spark Dockerfile copies `services/ml/` |
| ML dependencies (numpy, pyyaml) installed | ✅ PASS | §11.4 Spark Dockerfile RUN pip install |
| ML imported as Python library | ✅ PASS | §10.2 shows `from ml.classifier import classify_event` |
| No separate ML Docker service | ✅ PASS | §2.1 explicitly excludes it |

### Against `06_IMPLEMENTATION_PLAN.md`

| Check | Result | Evidence |
|-------|--------|----------|
| Directory structure matches §1 | ✅ PASS | All paths referenced in this document exist in the plan |
| `.env.example` matches §6 | ✅ PASS | §7 reconciles all variables |
| Startup sequence matches §8 | ✅ PASS | §15 commands match plan's step-by-step |
| DB init matches §9 | ✅ PASS | Same `init.sql` content |
| Kafka init matches §10 | ✅ PASS | Same topic list and config |
| Smoke test matches §16 plan | ✅ PASS | §16 implements the plan's smoke test |

### Summary

| Document | Contradictions | Assumptions | Decisions Changed |
|----------|---------------|-------------|-------------------|
| `01_ARCHITECTURE.md` | 0 | 0 | 0 |
| `02_DATA_SCHEMA.md` | 0 | 0 | 0 |
| `03_KAFKA_CONTRACT.md` | 0 | 0 | 0 |
| `04_API_CONTRACT.md` | 0 | 0 | 0 |
| `05_AI_ML_SPEC.md` | 0 | 0 | 0 |
| `06_IMPLEMENTATION_PLAN.md` | 0 | 0 | 0 |

**No contradictions found. No assumptions introduced. No decisions changed.**

All six contracts are internally consistent with this Docker deployment specification.

---

## Appendix A: Complete Port Map

| Port | Service | Protocol | Accessible From |
|------|---------|----------|-----------------|
| `2181` | Zookeeper | TCP | Host + Docker network |
| `9092` | Kafka | PLAINTEXT | Docker network only |
| `29092` | Kafka | PLAINTEXT | Host (mapped from 9092) |
| `8080` | Kafka UI | HTTP | Host |
| `5432` | PostgreSQL | TCP | Host + Docker network |
| `7077` | Spark Master | TCP | Docker network |
| `8081` | Spark Master UI | HTTP | Host |
| `8082` | Spark Worker UI | HTTP | Host |
| `8000` | FastAPI | HTTP | Host |
| `5173` | Frontend | HTTP | Host |

## Appendix B: Quick Reference Commands

```bash
# Start everything
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api

# Stop everything (preserve data)
docker compose stop

# Full reset (destroy data)
docker compose down -v

# Rebuild after code change
docker compose build api && docker compose up -d api

# Smoke test
bash scripts/smoke-test.sh

# Access services
open http://localhost:5173    # Frontend
open http://localhost:8000/docs  # API docs
open http://localhost:8080    # Kafka UI
open http://localhost:8081    # Spark UI
```

---

*This document is the Docker deployment source of truth.
Any change to ports, services, networks, volumes, or startup sequences
must be reflected here and cross-checked against all approved contracts.*
