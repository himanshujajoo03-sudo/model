# Database Files & Setup — Complete Reference

Quick reference for all database initialization files and setup options.

## 📁 Files Created

### SQL Schema Files

| File | Purpose | Use When |
|------|---------|----------|
| `sql/00_complete_schema.sql` | **Complete unified schema** (RECOMMENDED) | First-time setup or clean initialization |
| `sql/init.sql` | Base schema with extensions and tables | Legacy/reference |
| `sql/02_canonical_events.sql` | Canonical events migration | Legacy/reference |
| `sql/05_verification_reasons.sql` | Verification reasons column | Legacy/reference |
| `sql/06_verification_log_needs_review.sql` | Verification log actions update | Legacy/reference |
| `sql/07_verification_outbox.sql` | Outbox and cluster tables | Legacy/reference |

### Setup Scripts

| File | Language | Platform | Purpose |
|------|----------|----------|---------|
| `scripts/db_setup.ps1` | PowerShell | Windows | Full orchestrated setup with verification |
| `scripts/db_setup.py` | Python | Linux/Mac/WSL | Comprehensive setup with error handling |
| `scripts/init-db.sh` | Bash | Linux/Mac/WSL | Database initialization only |
| `scripts/init-kafka.sh` | Bash | Linux/Mac/WSL | Kafka topic creation only |
| `scripts/smoke-test.ps1` | PowerShell | Windows | Verification/testing |
| `scripts/smoke-test.sh` | Bash | Linux/Mac/WSL | Verification/testing |

### Documentation

| File | Purpose |
|------|---------|
| `DB_SETUP.md` | Complete setup guide with all options and troubleshooting |
| `RUN_PROJECT.md` | Project running guide |
| `SIH26069_SETUP.md` | Complete project setup documentation |

---

## 🚀 Quick Start Options

### Windows — PowerShell (Recommended for Windows)

```powershell
# Navigate to project root
cd path/to/sih26069

# Full setup (database + Kafka)
.\scripts\db_setup.ps1

# Database only
.\scripts\db_setup.ps1 -DbOnly

# Kafka only
.\scripts\db_setup.ps1 -KafkaOnly

# Verify without changes
.\scripts\db_setup.ps1 -VerifyOnly

# Show help
.\scripts\db_setup.ps1 -Help
```

### Linux/Mac/WSL — Python (Recommended for Linux/Mac)

```bash
cd /path/to/sih26069

# Full setup (database + Kafka)
python scripts/db_setup.py

# Database only
python scripts/db_setup.py --db-only

# Kafka only
python scripts/db_setup.py --kafka-only

# Verify without changes
python scripts/db_setup.py --verify

# Help
python scripts/db_setup.py --help
```

### Linux/Mac/WSL — Bash

```bash
cd /path/to/sih26069

# Full setup
bash scripts/init-db.sh && bash scripts/init-kafka.sh

# Database only
bash scripts/init-db.sh

# Kafka only
bash scripts/init-kafka.sh
```

### Any OS — Direct Docker (Manual)

```bash
# Copy and execute unified schema
docker cp sql/00_complete_schema.sql weather-postgres:/tmp/schema.sql
docker exec -T weather-postgres psql -U weather -d weatherdb \
  -v ON_ERROR_STOP=1 -f /tmp/schema.sql

# Create Kafka topics (one line per topic for Windows)
for topic in weather.raw citizen.raw social.raw government.raw weather.processed weather.events weather.verified; do
  docker exec weather-kafka kafka-topics --bootstrap-server localhost:9092 \
    --create --if-not-exists --topic $topic --partitions 1 --replication-factor 1
done
```

---

## 📋 Schema Contents

### Complete Schema (`00_complete_schema.sql`)

**9 Phases in single file:**

1. **Extensions** — pgcrypto, PostGIS
2. **Helper Functions** — sync_geom(), set_updated_at()
3. **Base Tables** — events, event_clusters, sources, verification_log
4. **Canonical Events Table** — canonical_events (main aggregation table)
5. **Constraints** — FK references, CHECK constraints
6. **Outbox Tables** — verification_outbox, event_cluster_members
7. **Indexes** — Spatial, temporal, categorical, FK indexes
8. **Triggers** — Auto-update timestamps, geometry sync
9. **Data Cleanup** — Remove orphaned FKs
10. **Sample Data** — 5 source records (optional)
11. **Verification** — Schema validation notice

**Key Tables:**

```
┌─────────────────────┐
│   event_clusters    │  Clustering data
└──────────┬──────────┘
           │ FK
     ┌─────▼─────────────┐
     │      events       │  Individual source records
     └─────┬─────────────┘
           │ FK
     ┌─────▼──────────────┐
     │ canonical_events   │  Consolidated phenomena
     └────────────────────┘
           
sources ──────────────────┘ (reference table)

verification_log ─────────→ (audit trail)
event_cluster_members ────→ (cluster mapping)
verification_outbox ──────→ (transactional outbox)
```

---

## ✅ Verification Checklist

After running setup, verify with:

```bash
# 1. Database tables
docker exec -T weather-postgres psql -U weather -d weatherdb -c "\dt"
# Should show: 7 tables (events, canonical_events, sources, verification_log, 
#                        event_clusters, verification_outbox, event_cluster_members)

# 2. Kafka topics
docker exec weather-kafka kafka-topics --bootstrap-server localhost:9092 --list
# Should show: 7 topics (weather.raw, citizen.raw, social.raw, government.raw, 
#                        weather.processed, weather.events, weather.verified)

# 3. PostGIS
docker exec -T weather-postgres psql -U weather -d weatherdb \
  -c "SELECT PostGIS_Version();"
# Should show: PostGIS version

# 4. Sample sources
docker exec -T weather-postgres psql -U weather -d weatherdb \
  -c "SELECT source_name, source_type, trust_score FROM sources;"
# Should show: 5 sources loaded

# 5. API health
docker exec weather-api python -c "import urllib.request; \
  print(urllib.request.urlopen('http://localhost:8000/api/v1/health').read().decode())"
# Should show: {"status":"healthy",...}

# 6. Run smoke tests
# Windows:  .\scripts\smoke-test.ps1
# Linux:    bash scripts/smoke-test.sh
```

---

## 🔧 Setup Features

### Database Setup (`db_setup.ps1` / `db_setup.py`)

✅ **Automatic Service Health Checks**
- Wait for PostgreSQL to be ready (retries configurable)
- Wait for Kafka to be ready (retries configurable)
- Timeout protection (60s default)

✅ **Comprehensive Error Handling**
- Detailed error messages
- Fallback options
- Verbose logging

✅ **Idempotent Operations**
- Safe to run multiple times
- All CREATE statements use `IF NOT EXISTS`
- No data loss on re-run

✅ **Verification & Validation**
- Automatic schema verification after setup
- Table enumeration and row counts
- Topic listing and validation

✅ **Progress Feedback**
- Color-coded output (green=success, red=error, cyan=info)
- Step-by-step progress reporting
- Summary at end

### PowerShell Script (`db_setup.ps1`)

**Parameters:**
```powershell
-DbOnly      # Database only, skip Kafka
-KafkaOnly   # Kafka only, skip database
-VerifyOnly  # Verify without changes
-Verbose     # Show detailed output
-Help        # Show help
```

**Features:**
- Native PowerShell (no external dependencies)
- Cross-platform compatible (Windows 7+)
- Full Unicode support (✓, ✗, ℹ icons)
- Configurable timeouts and retries
- Docker command execution

### Python Script (`db_setup.py`)

**Options:**
```bash
--db-only      # Database only
--kafka-only   # Kafka only
--verify       # Verify without changes
--reset        # Reset system (DESTRUCTIVE)
```

**Features:**
- Cross-platform (Linux/Mac/WSL)
- Comprehensive logging
- Structured error handling
- Docker integration
- JSON-parseable output

---

## 🐛 Troubleshooting

### PostgreSQL Not Ready

```bash
# Check status
docker logs weather-postgres | tail -20

# Restart
docker compose restart weather-postgres
sleep 10

# Re-run setup
./scripts/db_setup.ps1 -DbOnly
```

### Kafka Not Ready

```bash
# Check Zookeeper first
docker logs weather-zookeeper

# Restart Kafka + Zookeeper
docker compose restart zookeeper kafka
sleep 30

# Re-run setup
./scripts/db_setup.ps1 -KafkaOnly
```

### Schema File Not Found

```bash
# Verify file exists
ls sql/00_complete_schema.sql

# Run from project root
cd /path/to/sih26069
```

### Permission Denied

```bash
# Windows: Run PowerShell as Administrator
# Linux/Mac: Ensure docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

### Connection Refused

```bash
# Ensure Docker Desktop is running
docker ps

# If empty, start Docker Desktop and try again
```

---

## 📊 Schema Statistics

### Table Definitions

| Table | Columns | Indexes | FKs |
|-------|---------|---------|-----|
| `events` | 38 | 9 | 2 |
| `canonical_events` | 28 | 8 | 1 |
| `sources` | 9 | 0 | 0 |
| `verification_log` | 5 | 1 | 1 |
| `event_clusters` | 10 | 1 | 0 |
| `verification_outbox` | 8 | 1 | 1 |
| `event_cluster_members` | 4 | 1 | 2 |

### Constraint Summary

- **8 CHECK constraints** (data validation)
- **7 PRIMARY KEYs** (identity)
- **6 FOREIGN KEYs** (referential integrity)
- **8 UNIQUE constraints** (via primary keys)
- **26 INDEXES** (performance optimization)
- **5 TRIGGERS** (automatic maintenance)
- **2 FUNCTIONS** (sync_geom, set_updated_at)

### Kafka Topics

```
Weather Data Pipeline:
  ┌─ weather.raw ─────────┐
  ├─ citizen.raw ─────────┤
  ├─ social.raw ──────────┼──> Stream Processor ──> weather.processed
  └─ government.raw ──────┘                            ↓
                                                  weather.events ──> pg-writer ──> canonical_events table
                                                  
                                              weather.verified ──> (future use)
```

---

## 🎯 Next Steps After Setup

1. **Verify Services** — Run smoke tests
2. **Access Frontend** — http://localhost:3000
3. **Check API** — http://localhost:8000/docs
4. **Monitor Data** — Kafka UI at http://localhost:8080
5. **Query Database** — Connect to PostgreSQL and inspect tables

---

## 📚 Related Documentation

- **DB_SETUP.md** — Complete setup guide with all options
- **RUN_PROJECT.md** — Project running and command reference
- **SIH26069_SETUP.md** — Full project documentation (53KB+)
- **docs/02_DATA_SCHEMA.md** — Detailed schema documentation
- **docs/03_KAFKA_CONTRACT.md** — Kafka message format spec

---

## 🔑 Key Features of Complete Schema

✅ **All-in-One** — Single file combines all 5 legacy migrations  
✅ **Idempotent** — Safe to run multiple times  
✅ **Validated** — Comprehensive CHECK constraints  
✅ **Performant** — Strategic indexes for all query patterns  
✅ **Spatial** — PostGIS integration with geometry sync  
✅ **Audited** — Timestamps and verification logs  
✅ **Documented** — Inline comments for all major sections  
✅ **Sample Data** — 5 source records for testing  
✅ **Self-Verifying** — Final notice on completion  

---

## 🆘 Emergency Reset

**⚠️ DESTRUCTIVE — Deletes all data:**

```bash
# Stop services
docker compose down

# Remove all volumes
docker volume rm sih26069_pgdata sih26069_kafkadata sih26069_spark_checkpoints

# Start fresh
docker compose up -d

# Re-run setup
./scripts/db_setup.ps1
```

---

Created: 2024 | Project: SIH26069
