# ============================================================
# End-to-End Smoke Test (PowerShell version)
# Source of truth: 06_IMPLEMENTATION_PLAN.md §5
# ============================================================

$FAIL = 0

function Check-Test {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    try {
        $result = & $Command 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ $Label"
        } else {
            Write-Host "  ❌ $Label"
            $global:FAIL = 1
        }
    } catch {
        Write-Host "  ❌ $Label"
        $global:FAIL = 1
    }
}

Write-Host "=== Smoke Test ==="
Write-Host ""

Write-Host "1. Kafka Topics"
Check-Test "weather.raw exists" { docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.raw }
Check-Test "citizen.raw exists" { docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic citizen.raw }
Check-Test "social.raw exists" { docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic social.raw }
Check-Test "government.raw exists" { docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic government.raw }
Check-Test "weather.processed exists" { docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.processed }
Check-Test "weather.events exists" { docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.events }
Check-Test "weather.verified exists" { docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --describe --topic weather.verified }

Write-Host ""
Write-Host "2. PostgreSQL"
Check-Test "events table exists" { docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT 1 FROM events LIMIT 0" }
Check-Test "event_clusters table exists" { docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT 1 FROM event_clusters LIMIT 0" }
Check-Test "sources table exists" { docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT 1 FROM sources LIMIT 0" }
Check-Test "verification_log table exists" { docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT 1 FROM verification_log LIMIT 0" }
Check-Test "canonical_events table exists" { docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT 1 FROM canonical_events LIMIT 0" }

Write-Host ""
Write-Host "3. API"
Check-Test "GET /health returns 200" { Invoke-WebRequest -Uri http://localhost:8000/api/v1/health -UseBasicParsing }

Write-Host ""
Write-Host "4. Frontend"
Check-Test "Frontend serves HTML" { (Invoke-WebRequest -Uri http://localhost:3000 -UseBasicParsing).Content | Select-String '<div id="root"' }

Write-Host ""
if ($FAIL -eq 0) {
    Write-Host "✅ All smoke tests passed."
    exit 0
} else {
    Write-Host "❌ Some tests failed. See above."
    exit 1
}
