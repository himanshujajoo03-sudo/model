#!/usr/bin/env bash
# ============================================================
# PostgreSQL Database Initialization Script
# Source of truth: 02_DATA_SCHEMA.md §17
# ============================================================
set -euo pipefail

echo "Initializing PostgreSQL database..."

# Base schema: extensions, helper functions, base tables (events, sources, ...)
docker compose exec -T postgres psql -U weather -d weatherdb < sql/init.sql

# Migrations (in dependency order) — the API reads canonical_events, so these
# MUST be applied for the backend to function.
docker compose exec -T postgres psql -U weather -d weatherdb < sql/02_canonical_events.sql
docker compose exec -T postgres psql -U weather -d weatherdb < sql/05_verification_reasons.sql
docker compose exec -T postgres psql -U weather -d weatherdb < sql/06_verification_log_needs_review.sql
docker compose exec -T postgres psql -U weather -d weatherdb < sql/07_verification_outbox.sql

echo ""
echo "Verifying tables..."
docker compose exec -T postgres psql -U weather -d weatherdb -c "\dt"

echo ""
echo "Verifying canonical_events exists..."
docker compose exec -T postgres psql -U weather -d weatherdb -c "SELECT COUNT(*) FROM canonical_events;"

echo ""
echo "Database initialized successfully."
