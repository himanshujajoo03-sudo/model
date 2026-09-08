# SIH26069 Weather Intelligence Platform — Run & Commands Guide

This guide provides everything needed to run, manage, test, and develop the SIH26069 Extreme Weather Detection and Verification Platform.

---

## 1. Quick Access & Service Map

| Service | Access URL | Port | Credentials / Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend UI (React/Vite)** | [http://localhost:3000](http://localhost:3000) | `3000` | Real-time weather dashboard & verification center |
| **Backend REST API** | [http://localhost:8000/api/v1](http://localhost:8000/api/v1) | `8000` | FastAPI service endpoints |
| **Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | `8000` | Swagger UI for interactive API testing |
| **Kafka Web UI** | [http://localhost:8080](http://localhost:8080) | `8080` | Topic browser, consumer groups, message monitor |
| **Spark Master Web UI** | [http://localhost:8081](http://localhost:8081) | `8081` | Spark streaming cluster status & workers |
| **PostgreSQL / PostGIS** | `127.0.0.1:5432` | `5432` | User: `weather`, DB: `weatherdb` |
| **Kafka Broker** | `127.0.0.1:9092` | `9092` | Internal listener `kafka:9092` |

### Default Credentials
- **Admin Authentication**:
  - Username: `admin`
  - Password: `admin` *(configured via `ADMIN_PASSWORD` in `.env`)*
- **PostgreSQL Database**:
  - Host: `127.0.0.1` (or `postgres` inside Docker network)
  - Port: `5432`
  - Database: `weatherdb`
  - Username: `weather`
  - Password: `${POSTGRES_PASSWORD}` *(from `.env`)*

---

## 2. Quick Start (Running via Docker Compose)

### Step 1: Ensure Environment File Exists
Make sure `.env` is present in the project root. If not, copy from `.env.example`:
```powershell
# Windows PowerShell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

### Step 2: Start All Services
```powershell
docker compose up -d
```
> [!TIP]
> The `docker-compose.yml` mounts `./services/frontend:/app` and `./services/api:/app/api` as live volumes. Edits to React components or Python API code will hot-reload automatically without rebuilding containers.

### Step 3: Check Running Containers & Health
```powershell
docker ps
```
You should see all 11 containers running and healthy:
- `weather-frontend`
- `weather-api`
- `weather-postgres`
- `weather-kafka`
- `weather-zookeeper`
- `weather-kafka-ui`
- `weather-spark-master`
- `weather-spark-worker`
- `weather-stream-processor`
- `weather-pg-writer`
- `weather-ingestion`

---

## 3. Important Everyday Commands

### Managing Containers
```powershell
# Start all containers in background
docker compose up -d

# Stop all containers
docker compose stop

# Stop and remove containers and networks (preserves database data volume)
docker compose down

# Stop and remove EVERYTHING including volumes (CAUTION: resets database)
docker compose down -v

# Restart a specific service (e.g. backend api or frontend)
docker restart weather-api
docker restart weather-frontend

# Rebuild containers after Dockerfile or package.json changes
docker compose build frontend
docker compose build api
```

### Viewing Logs
```powershell
# Stream logs for all services
docker compose logs -f

# View logs for API server
docker logs -f weather-api

# View logs for React frontend
docker logs -f weather-frontend

# View logs for PostgreSQL
docker logs -f weather-postgres

# View logs for Kafka streaming & ingestion
docker logs -f weather-kafka
docker logs -f weather-stream-processor
docker logs -f weather-ingestion
```

---

## 4. Local Development (Running Without Docker)

### Running the Frontend Locally
If you want to run the React frontend directly on Windows with Vite:
```powershell
cd services\frontend

# Install dependencies (only needed once)
npm install

# Run Vite dev server (runs on http://localhost:5173 or configured port)
npm run dev

# Run production build check
npm run build
```

### Running API Backend Tests / Scripts Locally
```powershell
# Run smoke tests
python -m unittest discover -s tests -p "*test*.py"

# Test API health
powershell -Command "Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health' -UseBasicParsing"
```

---

## 5. Testing the Verification Pipeline

To test the complete end-to-end verification flow (Login -> Fetch Event -> Submit Verification -> Validate DB Update):

### Option A: Using PowerShell
```powershell
# 1. Acquire Admin JWT Token
$auth = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/auth/login" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"username":"admin","password":"admin"}'
$token = $auth.access_token
Write-Host "Acquired Token: $token"

# 2. Get Pending Events
$events = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/events?verification_status=pending&page_size=1"
$eventId = $events.items[0].event_id
Write-Host "Pending Event ID: $eventId"

# 3. Submit Verification
$payload = @{
    event_id = $eventId
    action = "verified"
    notes = "Manual verification via PowerShell"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/verification" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $token" } `
  -Body $payload
$result | ConvertTo-Json
```

### Option B: Using cURL
```bash
# Login
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Submit Verification Action
curl -X POST http://127.0.0.1:8000/api/v1/verification \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{"event_id":"<EVENT_UUID>","action":"verified","notes":"Approved by Operator"}'
```

---

## 6. Database Inspection Commands

### Connect to PostgreSQL CLI inside container:
```powershell
docker exec -it weather-postgres psql -U weather -d weatherdb
```

### Common SQL Queries:
```sql
-- View event counts by verification status
SELECT verification_status, count(*) 
FROM canonical_events 
GROUP BY verification_status;

-- View recent verification activity log
SELECT log_id, event_id, action, performed_by, performed_at, notes 
FROM verification_log 
ORDER BY performed_at DESC 
LIMIT 10;

-- Check pending verification outbox messages (Kafka dispatch queue)
SELECT id, event_id, action, published_to_kafka, created_at 
FROM verification_outbox 
ORDER BY created_at DESC 
LIMIT 10;

-- Exit psql
\q
```

---

## 7. Kafka Inspection Commands

### Check Kafka Topics via Web UI:
Open [http://localhost:8080](http://localhost:8080) in your browser.

### Inspect Kafka Topics via Command Line:
```powershell
# List all topics
docker exec -it weather-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Consume verified weather events in real-time
docker exec -it weather-kafka kafka-console-consumer `
  --bootstrap-server localhost:9092 `
  --topic weather.verified `
  --from-beginning
```

---

## 8. Windows & WSL Troubleshooting Tips

> [!IMPORTANT]
> **Use `127.0.0.1` instead of `localhost` in scripts:**
> On Windows, PowerShell and Python often attempt IPv6 `::1` before IPv4 `127.0.0.1`, which can cause `ConnectionRefusedError` or socket drops when communicating with Docker Desktop port forwards. Always use `http://127.0.0.1:8000` in automated scripts and curl commands.

> [!TIP]
> **WSL2 Memory Optimization (`.wslconfig`):**
> If Docker Desktop crashes or hangs with exit codes, ensure `C:\Users\<Username>\.wslconfig` has memory limits configured so JVM containers (Kafka, Zookeeper, Spark) do not exhaust physical host RAM:
> ```ini
> [wsl2]
> memory=3GB
> swap=4GB
> ```

> [!NOTE]
> **Resetting Hung Containers:**
> If a container is unresponsive, restart Docker Desktop or run:
> ```powershell
> docker compose restart api frontend
> ```

