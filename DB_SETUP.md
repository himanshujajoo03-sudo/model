# SIH26069 — Quick Database Setup Guide

Complete guide for initializing the data pipeline with database and Kafka topics.

## Prerequisites

- ✅ Docker Desktop running
- ✅ `.env` file with required variables:
  ```bash
  POSTGRES_PASSWORD=weather_dev_password
  JWT_SECRET_KEY=<your-jwt-secret>
  ADMIN_PASSWORD=<your-admin-password>
  ```
- ✅ All services started: `docker compose up -d`

## One-Shot Setup (Recommended)

### Option 1: Using Python Script (Linux/Mac/WSL)

```bash
# Run complete setup (database + Kafka)
python scripts/db_setup.py

# Or specific setup
python scripts/db_setup.py --db-only
python scripts/db_setup.py --kafka-only
python scripts/db_setup.py --verify      # Check without changes
```

### Option 2: Using Bash Scripts (Linux/Mac/WSL)

```bash
# Run both
bash scripts/init-db.sh && bash scripts/init-kafka.sh

# Or individually
bash scripts/init-db.sh         # Database only
bash scripts/init-kafka.sh      # Kafka only
```

### Option 3: Using Complete Schema File (Any OS)

```bash
# Single SQL file with all migrations
docker exec -T weather-postgres psql -U weather -d weatherdb \
  -v ON_ERROR_STOP=1 \
  -f /dev/stdin < sql/00_complete_schema.sql
```

### Option 4: Manual Docker Compose Commands (Windows/PowerShell)

```powershell
# Copy schema into container
docker cp sql/00_complete_schema.sql weather-postgres:/tmp/schema.sql

# Execute schema
docker exec -T weather-postgres psql -U weather -d weatherdb `
  -v ON_ERROR_STOP=1 `
  -f /tmp/schema.sql

# Create Kafka topics (one at a time for Windows)
$topics = @("weather.raw", "citizen.raw", "social.raw", "government.raw", `
            "weather.processed", "weather.events", "weather.verified")
foreach ($topic in $topics) {
    docker exec weather-kafka kafka-topics `
        --bootstrap-server localhost:9092 `
        --create `
        --if-not-exists `
        --topic $topic `
        --partitions 1 `
        --replication-factor 1
}
```

## Verification

After setup, verify everything is working:

```bash
# Check database tables
docker exec -T weather-postgres psql -U weather -d weatherdb -c "\dt"

# Expected output:
#               List of relations
#  Schema |        Name        | Type  |  Owner
# --------+--------------------+-------+--------
#  public | canonical_events   | table | weather
#  public | event_clusters     | table | weather
#  public | event_cluster_members | table | weather
#  public | events             | table | weather
#  public | sources            | table | weather
#  public | verification_log   | table | weather
#  public | verification_outbox| table | weather

# Check Kafka topics
docker exec weather-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Expected output:
# citizen.raw
# government.raw
# social.raw
# weather.events
# weather.processed
# weather.raw
# weather.verified
```

## Full Integration Test

After initialization, run a complete smoke test:

```bash
# Windows (PowerShell)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-test.ps1

# Linux/Mac/WSL
bash scripts/smoke-test.sh
```

## Database Schema Overview

### Tables Created

| Table | Purpose | Records |
|-------|---------|---------|
| `events` | Individual source records | 0 (filled by ingestion) |
| `canonical_events` | Consolidated weather phenomena | 0 (filled by stream processor) |
| `sources` | Data source registry | 5 (sample data loaded) |
| `verification_log` | Admin verification audit trail | 0 (filled by API) |
| `event_clusters` | Event clustering data | 0 (filled by Spark) |
| `event_cluster_members` | Cluster membership mapping | 0 (filled by Spark) |
| `verification_outbox` | Transactional outbox for events | 0 (filled by API) |

### Key Features

✅ **PostGIS Integration**
- Automatic geometry sync from latitude/longitude
- Spatial indexing for geographic queries
- Distance-based event matching

✅ **Comprehensive Indexing**
- Temporal indexes (event_timestamp, created_at, updated_at)
- Categorical indexes (event_category, severity, verification_status)
- Foreign key indexes (canonical_event_id, cluster_id)
- Spatial indexes (geom column)

✅ **Triggers & Constraints**
- Auto-update of modified timestamps
- Geometry synchronization
- Data validation (lat/lon ranges, enum values, text length)

✅ **Kafka Topics** (7 total)
- `weather.raw` — Raw weather observations
- `citizen.raw` — Citizen-reported events  
- `social.raw` — Social media events
- `government.raw` — Government data
- `weather.processed` — Validated events
- `weather.events` — Final canonical events
- `weather.verified` — Verified subset

## Troubleshooting

### "PostgreSQL connection refused"

```bash
# Check if container is running
docker ps | grep postgres

# Check logs
docker logs weather-postgres

# Restart PostgreSQL
docker compose restart weather-postgres
sleep 10
# Re-run setup
```

### "Kafka broker not found"

```bash
# Check Kafka status
docker logs weather-kafka

# Wait for Kafka to be healthy
docker compose logs kafka | tail -20

# Restart Kafka + Zookeeper
docker compose restart zookeeper kafka
sleep 30
# Re-run setup
```

### "FATAL: database 'weatherdb' does not exist"

```bash
# Ensure database exists
docker exec weather-postgres createdb -U weather weatherdb

# Re-run schema initialization
python scripts/db_setup.py --db-only
```

### "Table already exists" errors

This is **normal and expected**. The schema uses `CREATE TABLE IF NOT EXISTS`, so re-running is safe and idempotent.

### SQL file not found errors

Ensure you're running from the project root:

```bash
pwd
# Should output: .../sih26069 (or your project root)

ls sql/00_complete_schema.sql
# Should find the file
```

## Clean Reset (⚠️ DESTRUCTIVE)

To completely reset database and Kafka:

```bash
# Stop services
docker compose down

# Remove volumes (deletes all data)
docker volume rm sih26069_pgdata sih26069_kafkadata sih26069_spark_checkpoints

# Start fresh
docker compose up -d

# Run setup again
python scripts/db_setup.py
```

## Data Access

### Query Events via PostgreSQL

```bash
# Connect to database
docker exec -it weather-postgres psql -U weather -d weatherdb

# Query source records
SELECT event_id, event_category, severity, city FROM events LIMIT 5;

# Query canonical events
SELECT canonical_event_id, event_category, severity, report_count FROM canonical_events LIMIT 5;

# Query sources
SELECT source_name, source_type, total_reports, trust_score FROM sources;
```

### View Kafka Messages

```bash
# View messages in a topic
docker exec weather-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic weather.events \
  --from-beginning \
  --max-messages 5

# Monitor in real-time
docker exec weather-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic weather.events \
  --from-beginning
```

### REST API Access

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List canonical events
curl http://localhost:8000/api/v1/events?page=1&page_size=10

# Query specific event
curl http://localhost:8000/api/v1/events/{event_id}

# View API docs
# Browser: http://localhost:8000/docs
```

## File Structure

```
project-root/
├── sql/
│   ├── 00_complete_schema.sql      ← Complete unified schema
│   ├── init.sql                     ← Legacy (use 00_complete_schema.sql)
│   ├── 02_canonical_events.sql     ← Legacy
│   ├── 05_verification_reasons.sql ← Legacy
│   ├── 06_verification_log_needs_review.sql ← Legacy
│   └── 07_verification_outbox.sql  ← Legacy
├── scripts/
│   ├── db_setup.py                 ← Python setup orchestrator
│   ├── init-db.sh                  ← Bash database setup
│   ├── init-kafka.sh               ← Bash Kafka setup
│   └── smoke-test.ps1/sh           ← Verification tests
└── docker-compose.yml
```

## Next Steps

1. ✅ Run setup (database + Kafka)
2. ✅ Verify with smoke tests
3. ✅ Access Frontend: http://localhost:3000
4. ✅ Access API Docs: http://localhost:8000/docs
5. ✅ Monitor Kafka UI: http://localhost:8080
6. ✅ View sample events in database

---

**Questions?** Check logs with `docker compose logs -f <service>`
