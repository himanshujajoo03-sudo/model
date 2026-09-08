-- ============================================================
-- SIH26069 — Add verification_reasons to canonical_events
-- Supports the P0 verification decision engine.
-- ============================================================

ALTER TABLE canonical_events
    ADD COLUMN IF NOT EXISTS verification_reasons TEXT[] NOT NULL DEFAULT '{}';

-- Index for verification queries
CREATE INDEX IF NOT EXISTS idx_ce_verification_reasons
    ON canonical_events USING GIN (verification_reasons);
