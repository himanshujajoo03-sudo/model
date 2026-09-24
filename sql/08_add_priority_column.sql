-- ============================================================
-- SIH26069 — Add Priority Column for Fast-Path Lane
-- Additive migration: adds priority column to canonical_events and events
-- ============================================================

ALTER TABLE canonical_events
    ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';

CREATE INDEX IF NOT EXISTS idx_canonical_events_priority ON canonical_events(priority);
CREATE INDEX IF NOT EXISTS idx_events_priority ON events(priority);
