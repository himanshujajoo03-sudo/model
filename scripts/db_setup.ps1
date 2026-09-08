# SIH26069 — Windows PowerShell Database & Kafka Setup Script
# Complete system initialization with comprehensive error handling and verification

param(
    [switch]$DbOnly,
    [switch]$KafkaOnly,
    [switch]$VerifyOnly,
    [switch]$Verbose,
    [switch]$Help
)

# ============================================================================
# Configuration & Helper Functions
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Config = @{
    PostgresContainer = "weather-postgres"
    KafkaContainer    = "weather-kafka"
    PostgresUser      = "weather"
    PostgresDb        = "weatherdb"
    SchemaFile        = "sql/00_complete_schema.sql"
    TimeoutSeconds    = 60
    MaxRetries        = 15
    RetryDelay        = 2
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Yellow
    Write-Host $Message -ForegroundColor Yellow
    Write-Host "=" * 70 -ForegroundColor Yellow
}

function Show-Help {
    @"
SIH26069 — Windows Database & Kafka Setup

Usage:
  .\scripts\db_setup.ps1                 # Full setup (database + Kafka)
  .\scripts\db_setup.ps1 -DbOnly         # Database only
  .\scripts\db_setup.ps1 -KafkaOnly      # Kafka only
  .\scripts\db_setup.ps1 -VerifyOnly     # Verify without changes
  .\scripts\db_setup.ps1 -Verbose        # Show detailed output
  .\scripts\db_setup.ps1 -Help           # Show this help

Requirements:
  • Docker Desktop running
  • All services started: docker compose up -d
  • .env file with POSTGRES_PASSWORD set
  • Sufficient permissions to run Docker commands

"@
}

# ============================================================================
# Database Functions
# ============================================================================

function Test-PostgresHealthy {
    param([int]$Retries = 3)
    
    Write-Info "Checking PostgreSQL health..."
    
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $result = docker exec $Config.PostgresContainer pg_isready `
                -U $Config.PostgresUser `
                -d $Config.PostgresDb 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "PostgreSQL is healthy ($($Config.PostgresContainer))"
                return $true
            }
        }
        catch {
            # Continue to next retry
        }
        
        if ($i -lt $Retries) {
            Write-Info "  PostgreSQL not ready yet ($i/$Retries), waiting..."
            Start-Sleep -Seconds $Config.RetryDelay
        }
    }
    
    Write-Error-Custom "PostgreSQL is not healthy after $Retries attempts"
    return $false
}

function Wait-PostgresHealthy {
    param([int]$Retries = 10)
    
    Write-Header "Waiting for PostgreSQL Service"
    
    for ($i = 1; $i -le $Retries; $i++) {
        if (Test-PostgresHealthy -Retries 1) {
            return $true
        }
        
        Write-Info "  Attempt $i/$Retries, waiting $($Config.RetryDelay)s..."
        Start-Sleep -Seconds $Config.RetryDelay
    }
    
    Write-Error-Custom "PostgreSQL did not become healthy in time"
    return $false
}

function Initialize-DatabaseSchema {
    Write-Header "Phase 1: Database Schema Initialization"
    
    # Check schema file
    if (-not (Test-Path $Config.SchemaFile)) {
        Write-Error-Custom "Schema file not found: $($Config.SchemaFile)"
        return $false
    }
    
    # Copy schema to container
    Write-Info "Copying schema file to container..."
    try {
        docker cp $Config.SchemaFile "$($Config.PostgresContainer):/tmp/schema.sql" 2>&1
        Write-Success "Schema file copied"
    }
    catch {
        Write-Error-Custom "Failed to copy schema file: $_"
        return $false
    }
    
    # Execute schema
    Write-Info "Executing database schema initialization..."
    try {
        $result = docker exec -T $Config.PostgresContainer psql `
            -U $Config.PostgresUser `
            -d $Config.PostgresDb `
            -v ON_ERROR_STOP=1 `
            -f /tmp/schema.sql 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Schema execution failed"
            Write-Host $result
            return $false
        }
        
        Write-Success "Database schema initialized"
        
        # Show any NOTICE output
        $notices = $result | Select-String "NOTICE"
        if ($notices) {
            foreach ($notice in $notices) {
                Write-Info "  $notice"
            }
        }
        
        return $true
    }
    catch {
        Write-Error-Custom "Failed to execute schema: $_"
        return $false
    }
}

function Test-DatabaseSchema {
    Write-Header "Verification: Database Schema"
    
    $requiredTables = @(
        'events',
        'canonical_events',
        'sources',
        'verification_log',
        'event_clusters',
        'verification_outbox',
        'event_cluster_members'
    )
    
    # Get existing tables
    try {
        $result = docker exec -T $Config.PostgresContainer psql `
            -U $Config.PostgresUser `
            -d $Config.PostgresDb `
            -t `
            -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;" 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to query tables"
            return $false
        }
        
        $existingTables = $result | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() }
        
        # Check for missing tables
        $missing = @()
        foreach ($table in $requiredTables) {
            if ($existingTables -notcontains $table) {
                $missing += $table
            }
        }
        
        if ($missing) {
            Write-Error-Custom "Missing tables: $($missing -join ', ')"
            Write-Info "Found tables: $($existingTables -join ', ')"
            return $false
        }
        
        # Show table statistics
        Write-Success "All required tables exist:"
        foreach ($table in $requiredTables) {
            $countResult = docker exec -T $Config.PostgresContainer psql `
                -U $Config.PostgresUser `
                -d $Config.PostgresDb `
                -t `
                -c "SELECT COUNT(*) FROM $table;" 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                $count = $countResult.Trim()
                Write-Info "  • $table`: $count rows"
            }
        }
        
        return $true
    }
    catch {
        Write-Error-Custom "Failed to verify schema: $_"
        return $false
    }
}

# ============================================================================
# Kafka Functions
# ============================================================================

function Test-KafkaHealthy {
    param([int]$Retries = 3)
    
    Write-Info "Checking Kafka health..."
    
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $result = docker exec $Config.KafkaContainer kafka-broker-api-versions `
                --bootstrap-server localhost:9092 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Kafka is healthy ($($Config.KafkaContainer))"
                return $true
            }
        }
        catch {
            # Continue to next retry
        }
        
        if ($i -lt $Retries) {
            Write-Info "  Kafka not ready yet ($i/$Retries), waiting..."
            Start-Sleep -Seconds $Config.RetryDelay
        }
    }
    
    Write-Error-Custom "Kafka is not healthy after $Retries attempts"
    return $false
}

function Wait-KafkaHealthy {
    param([int]$Retries = 15)
    
    Write-Header "Waiting for Kafka Service"
    
    for ($i = 1; $i -le $Retries; $i++) {
        if (Test-KafkaHealthy -Retries 1) {
            return $true
        }
        
        Write-Info "  Attempt $i/$Retries, waiting $($Config.RetryDelay)s..."
        Start-Sleep -Seconds $Config.RetryDelay
    }
    
    Write-Error-Custom "Kafka did not become healthy in time"
    return $false
}

function Initialize-KafkaTopics {
    Write-Header "Phase 2: Kafka Topic Initialization"
    
    $topics = @(
        "weather.raw",
        "citizen.raw",
        "social.raw",
        "government.raw",
        "weather.processed",
        "weather.events",
        "weather.verified"
    )
    
    $allSuccess = $true
    
    foreach ($topic in $topics) {
        try {
            Write-Info "Creating topic: $topic..."
            $result = docker exec $Config.KafkaContainer kafka-topics `
                --bootstrap-server localhost:9092 `
                --create `
                --if-not-exists `
                --topic $topic `
                --partitions 1 `
                --replication-factor 1 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Topic created: $topic"
            }
            else {
                Write-Error-Custom "Failed to create topic: $topic"
                $allSuccess = $false
            }
        }
        catch {
            Write-Error-Custom "Exception creating topic $topic`: $_"
            $allSuccess = $false
        }
    }
    
    return $allSuccess
}

function Test-KafkaTopics {
    Write-Header "Verification: Kafka Topics"
    
    $requiredTopics = @(
        "weather.raw",
        "citizen.raw",
        "social.raw",
        "government.raw",
        "weather.processed",
        "weather.events",
        "weather.verified"
    )
    
    # Get existing topics
    try {
        $result = docker exec $Config.KafkaContainer kafka-topics `
            --bootstrap-server localhost:9092 `
            --list 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to list topics"
            return $false
        }
        
        $existingTopics = $result | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() }
        
        # Check for missing topics
        $missing = @()
        foreach ($topic in $requiredTopics) {
            if ($existingTopics -notcontains $topic) {
                $missing += $topic
            }
        }
        
        if ($missing) {
            Write-Error-Custom "Missing topics: $($missing -join ', ')"
            Write-Info "Found topics: $($existingTopics -join ', ')"
            return $false
        }
        
        # Show topics
        Write-Success "All required topics exist:"
        foreach ($topic in $requiredTopics) {
            Write-Info "  • $topic"
        }
        
        return $true
    }
    catch {
        Write-Error-Custom "Failed to verify topics: $_"
        return $false
    }
}

# ============================================================================
# Main Execution
# ============================================================================

function Main {
    if ($Help) {
        Show-Help
        exit 0
    }
    
    Write-Header "SIH26069 — Database & Kafka Setup (Windows PowerShell)"
    
    $dbSuccess = $true
    $kafkaSuccess = $true
    
    # Database Setup
    if (-not $KafkaOnly) {
        if (-not (Wait-PostgresHealthy)) {
            $dbSuccess = $false
        }
        else {
            if ($VerifyOnly) {
                $dbSuccess = Test-DatabaseSchema
            }
            else {
                $dbSuccess = Initialize-DatabaseSchema
                if ($dbSuccess) {
                    $dbSuccess = Test-DatabaseSchema
                }
            }
        }
    }
    
    # Kafka Setup
    if (-not $DbOnly) {
        if (-not (Wait-KafkaHealthy)) {
            $kafkaSuccess = $false
        }
        else {
            if ($VerifyOnly) {
                $kafkaSuccess = Test-KafkaTopics
            }
            else {
                $kafkaSuccess = Initialize-KafkaTopics
                if ($kafkaSuccess) {
                    $kafkaSuccess = Test-KafkaTopics
                }
            }
        }
    }
    
    # Final Status
    Write-Header "Setup Summary"
    
    if (-not $KafkaOnly) {
        if ($dbSuccess) {
            Write-Success "Database: OK"
        }
        else {
            Write-Error-Custom "Database: FAILED"
        }
    }
    
    if (-not $DbOnly) {
        if ($kafkaSuccess) {
            Write-Success "Kafka: OK"
        }
        else {
            Write-Error-Custom "Kafka: FAILED"
        }
    }
    
    if ($dbSuccess -and $kafkaSuccess) {
        Write-Header "✓ Setup Completed Successfully"
        Write-Info "Next steps:"
        Write-Info "  1. Access Frontend: http://localhost:3000"
        Write-Info "  2. Access API Docs: http://localhost:8000/docs"
        Write-Info "  3. View Kafka UI: http://localhost:8080"
        Write-Info "  4. Run smoke tests: .\scripts\smoke-test.ps1"
        exit 0
    }
    else {
        Write-Header "✗ Setup Encountered Errors"
        Write-Info "Check logs: docker compose logs <service>"
        exit 1
    }
}

# ============================================================================
# Entry Point
# ============================================================================

try {
    Main
}
catch {
    Write-Error-Custom "Unexpected error: $_"
    exit 1
}
