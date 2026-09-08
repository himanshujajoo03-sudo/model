#!/usr/bin/env bash
# ============================================================
# End-to-End Smoke Test
# Source of truth: 06_IMPLEMENTATION_PLAN.md §5
# ============================================================
set -euo pipefail

FAIL=0

check() {
  local label="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✅ ${label}"
  else
    echo "  ❌ ${label}"
    FAIL=1
  fi
}

echo "=== Smoke Test ==="
echo ""

echo "1. Kafka Topics"
check "weather.raw exists"      "docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.raw"
check "citizen.raw exists"      "docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic citizen.raw"
check "social.raw exists"       "docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic social.raw"
check "government.raw exists"   "docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic government.raw"
check "weather.processed exists" "docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.processed"
check "weather.events exists"   "docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.events"
check "weather.verified exists" "docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.verified"

echo ""
echo "2. PostgreSQL"
check "events table exists"       "docker compose exec -T postgres psql -U weather -d weatherdb -c 'SELECT 1 FROM events LIMIT 0'"
check "event_clusters table exists" "docker compose exec -T postgres psql -U weather -d weatherdb -c 'SELECT 1 FROM event_clusters LIMIT 0'"
check "sources table exists"      "docker compose exec -T postgres psql -U weather -d weatherdb -c 'SELECT 1 FROM sources LIMIT 0'"
check "verification_log table exists" "docker compose exec -T postgres psql -U weather -d weatherdb -c 'SELECT 1 FROM verification_log LIMIT 0'"
check "canonical_events table exists"      "docker compose exec -T postgres psql -U weather -d weatherdb -c 'SELECT 1 FROM canonical_events LIMIT 0'"

echo ""
echo "3. API"
check "GET /health returns 200" "curl -sf http://localhost:8000/api/v1/health"

echo ""
echo "4. Frontend"
check "Frontend serves HTML" "curl -sf http://localhost:3000 | grep -q '<div id=\"root\"'"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "✅ All smoke tests passed."
else
  echo "❌ Some tests failed. See above."
  exit 1
fi
