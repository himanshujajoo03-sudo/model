-- ============================================================
-- SIH26069 — Canonical Events Migration
-- Adds canonical_events table + FK from events → canonical_events
-- Preserves all existing source records.
-- ============================================================

-- STEP 1: Create canonical_events table
CREATE TABLE IF NOT EXISTS canonical_events (
    canonical_event_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_category       TEXT NOT NULL
                             CHECK (event_category IN (
                                 'rainfall','heavy_rainfall','flood',
                                 'thunderstorm','lightning','heatwave',
                                 'fog','dust_storm','strong_wind',
                                 'hailstorm','cyclone','other'
                             )),
    severity             TEXT CHECK (severity IN ('low','moderate','high','extreme')),
    description          TEXT,
    latitude             NUMERIC(9,6),
    longitude            NUMERIC(10,6),
    geom                 GEOMETRY(Point,4326),
    city                 TEXT,
    district             TEXT,
    state                TEXT,
    country              TEXT NOT NULL DEFAULT 'India',
    first_seen           TIMESTAMPTZ NOT NULL,
    last_seen            TIMESTAMPTZ NOT NULL,
    source_count         INTEGER NOT NULL DEFAULT 1,
    report_count         INTEGER NOT NULL DEFAULT 1,
    contributing_sources TEXT[] NOT NULL DEFAULT '{}',
    classified_category  TEXT,
    classification_confidence NUMERIC(4,3)
                             CHECK (classification_confidence BETWEEN 0 AND 1),
    credibility_score    NUMERIC(4,3)
                             CHECK (credibility_score BETWEEN 0 AND 1),
    credibility_reasons  TEXT[],
    cluster_id           UUID,
    verification_status  TEXT NOT NULL DEFAULT 'pending'
                             CHECK (verification_status IN (
                                 'pending','verified','needs_review',
                                 'suspicious','duplicate'
                             )),
    verified_by          TEXT,
    verification_timestamp TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- STEP 2: Add canonical_event_id FK to events table
ALTER TABLE events
    ADD COLUMN IF NOT EXISTS canonical_event_id UUID
    REFERENCES canonical_events(canonical_event_id) ON DELETE SET NULL;

-- STEP 3: Indexes on canonical_events
CREATE INDEX IF NOT EXISTS idx_ce_timestamp ON canonical_events (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_ce_category ON canonical_events (event_category);
CREATE INDEX IF NOT EXISTS idx_ce_severity ON canonical_events (severity);
CREATE INDEX IF NOT EXISTS idx_ce_verification ON canonical_events (verification_status);
CREATE INDEX IF NOT EXISTS idx_ce_city ON canonical_events (city);
CREATE INDEX IF NOT EXISTS idx_ce_geom ON canonical_events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_ce_first_seen ON canonical_events (first_seen DESC);

-- STEP 4: Index on events.canonical_event_id
CREATE INDEX IF NOT EXISTS idx_events_canonical_event_id ON events (canonical_event_id);

-- STEP 5: Triggers for canonical_events
DROP TRIGGER IF EXISTS trg_ce_updated_at ON canonical_events;
CREATE TRIGGER trg_ce_updated_at
    BEFORE UPDATE ON canonical_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_ce_sync_geom ON canonical_events;
CREATE TRIGGER trg_ce_sync_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude ON canonical_events
    FOR EACH ROW EXECUTE FUNCTION sync_geom();

-- Canonical cluster relationship: Spark assigns, PostgreSQL persists.
UPDATE canonical_events ce
SET cluster_id = NULL
WHERE cluster_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM event_clusters ec WHERE ec.cluster_id = ce.cluster_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_canonical_events_cluster'
    ) THEN
        ALTER TABLE canonical_events
            ADD CONSTRAINT fk_canonical_events_cluster
            FOREIGN KEY (cluster_id) REFERENCES event_clusters(cluster_id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_canonical_events_cluster_id ON canonical_events(cluster_id);
