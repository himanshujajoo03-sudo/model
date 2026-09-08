# SIH26069 — National Weather Big Data Analytics Platform

A lightweight, open-source, near-real-time weather intelligence pipeline that aggregates multi-source weather information, processes it in real time, detects and classifies weather events, assesses report credibility, removes duplicate noise, and delivers geospatial intelligence through a web dashboard and Admin Panel.

## Architecture

See [`docs/01_ARCHITECTURE.md`](docs/01_ARCHITECTURE.md) for the complete system design.

```text
Data Sources → Ingestion → Kafka → Spark + ML → PostgreSQL/PostGIS → FastAPI → React
```

## Quick Start

### Prerequisites

- Docker Engine 24+
- Docker Compose v2

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd weather-platform

# Create environment file
cp .env.example .env
# Edit .env — set at minimum:
#   POSTGRES_PASSWORD=<your-password>
#   JWT_SECRET_KEY=$(openssl rand -hex 32)

# Start infrastructure
docker compose up -d zookeeper kafka kafka-ui postgres
sleep 30

# Initialize database
bash scripts/init-db.sh

# Create Kafka topics
bash scripts/init-kafka.sh

# Start all services
docker compose up -d

# Run smoke test
bash scripts/smoke-test.sh
```

### Service Ports

| Service | Port | URL |
|---------|------|-----|
| Kafka UI | 8080 | http://localhost:8080 |
| Spark Master UI | 8081 | http://localhost:8081 |
| Spark Worker UI | 8082 | http://localhost:8082 |
| FastAPI | 8000 | http://localhost:8000 |
| FastAPI Docs | 8000 | http://localhost:8000/docs |
| React Frontend | 5173 | http://localhost:5173 |
| PostgreSQL | 5432 | localhost:5432 |
| Kafka | 9092/29092 | localhost:9092 |

## Documentation

| Document | Purpose |
|----------|---------|
| [`00_MASTER_PROJECT_SPEC.md`](docs/00_MASTER_PROJECT_SPEC.md) | Master project specification |
| [`01_ARCHITECTURE.md`](docs/01_ARCHITECTURE.md) | System architecture |
| [`02_DATA_SCHEMA.md`](docs/02_DATA_SCHEMA.md) | PostgreSQL/PostGIS schema |
| [`03_KAFKA_CONTRACT.md`](docs/03_KAFKA_CONTRACT.md) | Kafka topics and contracts |
| [`04_API_CONTRACT.md`](docs/04_API_CONTRACT.md) | FastAPI REST endpoints |
| [`05_AI_ML_SPEC.md`](docs/05_AI_ML_SPEC.md) | AI/ML processing pipeline |
| [`06_IMPLEMENTATION_PLAN.md`](docs/06_IMPLEMENTATION_PLAN.md) | 5-day implementation plan |
| [`07_DOCKER_DEPLOYMENT_SPEC.md`](docs/07_DOCKER_DEPLOYMENT_SPEC.md) | Docker deployment spec |
| [`08_TESTING_QA_SPEC.md`](docs/08_TESTING_QA_SPEC.md) | Testing and QA strategy |

## MVP Cities

- **Mumbai** — Heavy rainfall, urban flooding, waterlogging, thunderstorms
- **Nagpur** — Heatwave, high temperature, thunderstorms, strong winds
- **Nashik** — Heavy rainfall, flooding, thunderstorms, hailstorms

## Team

| Member | Responsibility |
|--------|---------------|
| M1 | Architecture / DevOps / Integration |
| M2 | Data Ingestion |
| M3 | Kafka / Spark |
| M4 | AI/ML |
| M5 | Database / Backend |
| M6 | Frontend |

## License

SIH26069 — National Weather Big Data Analytics Platform
