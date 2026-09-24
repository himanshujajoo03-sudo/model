-- ============================================================
-- SIH26069 — Add Processing Latency Timestamps Migration
-- Additive migration: adds spark_processed_at and db_written_at
-- to canonical_events table
-- ============================================================

ALTER TABLE canonical_events
    ADD COLUMN IF NOT EXISTS spark_processed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS db_written_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_canonical_events_spark_processed_at ON canonical_events(spark_processed_at);
CREATE INDEX IF NOT EXISTS idx_canonical_events_db_written_at ON canonical_events(db_written_at);
