# How to Run the Project

> **See Also**: For the updated, complete guide covering every everyday command, PowerShell scripts, verification flow, and Windows troubleshooting, see [`HOW_TO_RUN_AND_COMMANDS.md`](HOW_TO_RUN_AND_COMMANDS.md).

- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- Git
- 4GB+ available RAM
- Ports 3000, 5173, 8000, 8080, 9092, 5432 available

## Quick Start (5 minutes)

### 1. Clone and Navigate
```bash
cd /d/ML/project2/model
```

### 2. Set Up Environment Variables
```bash
# Copy the example to create .env file (if not already done)
cp .env.example .env
```

Edit `.env` and set these required values:
```env
POSTGRES_PASSWORD=your_secure_password
JWT_SECRET_KEY=your_jwt_secret
ADMIN_PASSWORD=your_admin_password
```

### 3. Start All Services
```bash
docker compose up -d
```

This starts:
- **Kafka** (message broker) on port 9092
- **Zookeeper** (Kafka coordination) on port 2181
- **PostgreSQL** (database) on port 5432
- **Spark Master & Workers** (data processing)
- **Stream Processor** (real-time event processing)
- **API Backend** (FastAPI) on port 8000
- **Frontend** (React/Vite) on port 3000

### 4. Initialize Database & Topics

```bash
# Option A: Using PowerShell (Windows)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-test.ps1

# Option B: Using bash (Linux/Mac or WSL)
bash scripts/init-db.sh
bash scripts/init-kafka.sh
```

This creates:
- PostgreSQL tables (events, canonical_events, clusters, verification logs)
- Kafka topics (weather.raw, citizen.raw, weather.events, etc.)

### 5. Verify Everything Works

```bash
# PowerShell (Windows)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-test.ps1

# Bash (Linux/Mac)
bash scripts/smoke-test.sh
```

Expected output:
```
✅ All smoke tests passed.
```

---

## Access Points

Once running, access the application at:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | React dashboard |
| **API** | http://localhost:8000/api/v1 | REST API endpoints |
| **API Docs** | http://localhost:8000/docs | Swagger/OpenAPI documentation |
| **Kafka UI** | http://localhost:8080 | Kafka message browser |
| **PostgreSQL** | localhost:5432 | Database (psql client) |

---

## Common Commands

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f kafka
docker compose logs -f postgres
docker compose logs -f weather-api
docker compose logs -f weather-stream-processor
```

### Stop All Services
```bash
docker compose down
```

### Stop and Remove All Data (Clean Slate)
```bash
docker compose down -v
```

### Restart a Service
```bash
docker compose restart weather-api
```

### Check Running Containers
```bash
docker compose ps
```

### Execute Commands in Containers
```bash
# Connect to PostgreSQL
docker compose exec -T postgres psql -U weather -d weatherdb

# Check Kafka topics
docker run --rm --network model_weather-net confluentinc/cp-kafka:7.6.1 \
  kafka-topics --bootstrap-server kafka:9092 --list

# View Spark logs
docker compose logs weather-stream-processor
```

---

## Troubleshooting

### Services won't start
```bash
# Check logs
docker compose logs

# Rebuild images
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### "POSTGRES_PASSWORD is not set"
Create `.env` file with required variables:
```env
POSTGRES_PASSWORD=weather_dev_password
JWT_SECRET_KEY=dev_jwt_secret_key
ADMIN_PASSWORD=admin_dev_password
```

### Port already in use
Change port in `docker-compose.yml`:
```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change 8000 to 8001
```

### Database connection refused
```bash
# Check if postgres is healthy
docker compose ps postgres

# View postgres logs
docker compose logs postgres

# Recreate database
docker compose down postgres -v
docker compose up -d postgres
```

### Kafka topics not found
```bash
# Create topics manually
powershell -NoProfile -ExecutionPolicy Bypass -Command {
  $topics = @("weather.raw", "citizen.raw", "social.raw", "government.raw", "weather.processed", "weather.events", "weather.verified")
  foreach ($topic in $topics) {
    docker run --rm --network model_weather-net confluentinc/cp-kafka:7.6.1 `
      kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists `
      --topic $topic --partitions 1 --replication-factor 1
  }
}
```

---

## Development Workflow

### Run Tests
```bash
# Smoke tests (verify all services)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-test.ps1

# Unit tests (if available)
docker compose exec weather-api pytest
```

### View Real-time Data
```bash
# Kafka messages
docker run --rm --network model_weather-net confluentinc/cp-kafka:7.6.1 \
  kafka-console-consumer --bootstrap-server kafka:9092 \
  --topic weather.raw --from-beginning

# Database
docker compose exec -T postgres psql -U weather -d weatherdb \
  -c "SELECT * FROM events ORDER BY created_at DESC LIMIT 10;"
```

### Backend Development (Hot Reload)
The backend supports file watching. Edit files in `services/api/` and changes reload automatically.

### Frontend Development
Access the Vite dev server on http://localhost:3000 with hot module replacement enabled.

---

## Project Structure

```
project2/model/
├── services/
│   ├── api/              # FastAPI backend
│   ├── frontend/         # React/Vite frontend
│   ├── ingestion/        # Data ingestion service
│   ├── spark/            # Spark jobs (streaming, clustering)
│   └── ml/               # ML utilities and models
├── models/
│   └── classifier/model/ # Pre-trained ML models
├── sql/                  # Database schema files
├── scripts/
│   ├── smoke-test.sh     # Verification script (bash)
│   ├── smoke-test.ps1    # Verification script (PowerShell)
│   ├── init-db.sh        # Database initialization
│   └── init-kafka.sh     # Kafka topic creation
├── docker-compose.yml    # Service definitions
├── .env                  # Environment variables (create from .env.example)
└── Dockerfile.stream     # Stream processor build
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│                    http://localhost:3000                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│              API Backend (FastAPI)                           │
│             http://localhost:8000                            │
└──────────────┬────────────────────────────────┬──────────────┘
               │                                │
    ┌──────────▼───────────┐      ┌────────────▼──────────┐
    │   PostgreSQL DB      │      │   Kafka Broker        │
    │  (events, clusters)  │      │  (message streaming)  │
    └──────────────────────┘      └──────────┬────────────┘
                                             │
                              ┌──────────────▼─────────────┐
                              │  Stream Processor (Spark)   │
                              │  (real-time processing)     │
                              └─────────────────────────────┘
```

---

## Performance Tips

1. **Allocate sufficient memory to Docker**: 4GB minimum, 8GB+ recommended
2. **Monitor resource usage**: `docker stats`
3. **Check disk space**: `docker system df`
4. **Clean up old images**: `docker image prune -a`
5. **Use build cache**: First build takes time, subsequent builds are faster

---

## Next Steps

1. Access the frontend at http://localhost:3000
2. Check API documentation at http://localhost:8000/docs
3. Monitor Kafka topics at http://localhost:8080
4. View database queries in PostgreSQL
5. Configure ingestion sources in the UI or API
6. Start streaming real-time weather/event data

---

## Support

For issues or questions:
- Check logs: `docker compose logs [service_name]`
- Run smoke tests: `scripts/smoke-test.ps1` (Windows) or `scripts/smoke-test.sh` (Linux/Mac)
- Review `.env` configuration
- Ensure all required ports are available


## Verification hardening tests

For real PostgreSQL/PostGIS integration tests, point `TEST_DATABASE_URL` at a disposable PostGIS database and run:

```bash
TEST_DATABASE_URL=postgresql://weather:...@localhost:5432/weatherdb pytest -q tests/integration/test_pg_writer_postgres.py
```

The integration suite covers canonical report/source counting, severity ordering, first/last event time, cluster persistence and replay idempotency, and transaction rollback.
