#!/usr/bin/env bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-weather}"; do
  echo "...still waiting..."
  sleep 1
done
echo "PostgreSQL is ready. Applying migrations."

# Apply all .sql files in the mounted /migrations directory
for sql_file in /migrations/*.sql; do
  echo "Running migration $sql_file"
  psql -h "${POSTGRES_HOST:-postgres}" -U "${POSTGRES_USER:-weather}" -d "${POSTGRES_DB:-weatherdb}" -f "$sql_file"
done

echo "Migrations completed."

