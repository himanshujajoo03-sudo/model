#!/usr/bin/env bash
# ============================================================
# Kafka Topic Initialization Script
# Source of truth: 03_KAFKA_CONTRACT.md
# ============================================================
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

echo "Creating Kafka topics on ${BOOTSTRAP}..."

TOPICS=(
  "weather.raw"
  "citizen.raw"
  "social.raw"
  "government.raw"
  "weather.processed"
  "weather.events"
  "weather.verified"
)

for topic in "${TOPICS[@]}"; do
  echo "  Creating topic: ${topic}"
  docker compose exec kafka kafka-topics \
    --bootstrap-server localhost:9092 \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions 1 \
    --replication-factor 1
done

echo ""
echo "Verifying topics..."
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list

echo ""
echo "All 7 topics created successfully."
