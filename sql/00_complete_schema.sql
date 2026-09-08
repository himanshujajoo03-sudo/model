-- ============================================================================
-- SIH26069 — National Weather Big Data Analytics Platform
-- Complete PostgreSQL + PostGIS Schema Initialization
-- Combines all migrations in dependency order for single-run setup
-- ============================================================================

-- ============================================================================
-- PHASE 1: Extensions (must come before types, functions, tables)
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- PHASE 2: Helper Functions
-- ============================================================================
CREATE OR REPLACE FUNCTION sync_geom()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PHASE 3: Base Tables (in dependency order)
-- ============================================================================

-- 3a. event_clusters (no dependencies)
CREATE TABLE IF NOT EXISTS event_clusters (
    cluster_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    representative_id   UUID,
    event_category      TEXT NOT NULL,
    city                TEXT,
    state               TEXT,
    centroid_geom       GEOMETRY(Point, 4326),
    member_count        INTEGER NOT NULL DEFAULT 1,
    first_event_at      TIMESTAMPTZ NOT NULL,
    last_event_at       TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3b. events (FK → event_clusters, → canonical_events)
CREATE TABLE IF NOT EXISTS events (
    event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           TEXT NOT NULL,
    source_type         TEXT NOT NULL
                            CHECK (source_type IN (
                                'weather_api','rss','website','social',
                                'simulated_social','government_dataset',
                                'citizen','synthetic'
                            )),
    source_name         TEXT NOT NULL,
    source_url          TEXT,
    source_trust_score  NUMERIC(4,3) CHECK (source_trust_score BETWEEN 0 AND 1),
    event_timestamp     TIMESTAMPTZ NOT NULL,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latitude            NUMERIC(9,6) CHECK (latitude  BETWEEN -90  AND 90),
    longitude           NUMERIC(10,6) CHECK (longitude BETWEEN -180 AND 180),
    city                TEXT,
    district            TEXT,
    state               TEXT,
    country             TEXT NOT NULL DEFAULT 'India',
    geom                GEOMETRY(Point, 4326),
    event_category      TEXT NOT NULL
                            CHECK (event_category IN (
                                'rainfall','heavy_rainfall','flood',
                                'thunderstorm','lightning','heatwave',
                                'fog','dust_storm','strong_wind',
                                'hailstorm','cyclone','other'
                            )),
    severity            TEXT CHECK (severity IN ('low','moderate','high','extreme')),
    description         TEXT CHECK (char_length(description) <= 2000),
    hashtags            TEXT[],
    author_id           TEXT,
    platform            TEXT,
    photo_urls          TEXT[],
    video_urls          TEXT[],
    classified_category TEXT CHECK (classified_category IN (
                                'rainfall','heavy_rainfall','flood',
                                'thunderstorm','lightning','heatwave',
                                'fog','dust_storm','strong_wind',
                                'hailstorm','cyclone','other'
                              )),
    classification_confidence NUMERIC(4,3) CHECK (classification_confidence BETWEEN 0 AND 1),
    duplicate_score           NUMERIC(4,3) CHECK (duplicate_score BETWEEN 0 AND 1),
    credibility_score         NUMERIC(4,3) CHECK (credibility_score BETWEEN 0 AND 1),
    credibility_reasons       TEXT[],
    cluster_id                UUID REFERENCES event_clusters(cluster_id) ON DELETE SET NULL,
    canonical_event_id        UUID,
    verification_status     TEXT NOT NULL DEFAULT 'pending'
                                CHECK (verification_status IN (
                                    'pending','verified','needs_review',
                                    'suspicious','duplicate'
                                )),
    verified_by             TEXT,
    verification_timestamp  TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3c. sources (no dependencies)
CREATE TABLE IF NOT EXISTS sources (
    source_name         TEXT PRIMARY KEY,
    source_type         TEXT NOT NULL,
    base_url            TEXT,
    trust_score         NUMERIC(4,3) NOT NULL DEFAULT 0.5
                            CHECK (trust_score BETWEEN 0 AND 1),
    total_reports       INTEGER NOT NULL DEFAULT 0,
    verified_reports    INTEGER NOT NULL DEFAULT 0,
    rejected_reports    INTEGER NOT NULL DEFAULT 0,
    last_seen_at        TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3d. verification_log (FK → events)
CREATE TABLE IF NOT EXISTS verification_log (
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    action          TEXT NOT NULL,
    performed_by    TEXT NOT NULL,
    notes           TEXT,
    performed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- PHASE 4: Canonical Events Table (references by events.canonical_event_id)
-- ============================================================================
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
    classified_category  TEXT CHECK (classified_category IN (
                                'rainfall','heavy_rainfall','flood',
                                'thunderstorm','lightning','heatwave',
                                'fog','dust_storm','strong_wind',
                                'hailstorm','cyclone','other'
                              )),
    classification_confidence NUMERIC(4,3)
                             CHECK (classification_confidence BETWEEN 0 AND 1),
    credibility_score    NUMERIC(4,3)
                             CHECK (credibility_score BETWEEN 0 AND 1),
    credibility_reasons  TEXT[] NOT NULL DEFAULT '{}',
    verification_reasons TEXT[] NOT NULL DEFAULT '{}',
    cluster_id           UUID REFERENCES event_clusters(cluster_id) ON DELETE SET NULL,
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

-- Add FK constraint for events.canonical_event_id
ALTER TABLE events
    ADD CONSTRAINT fk_events_canonical_event_id
    FOREIGN KEY (canonical_event_id) REFERENCES canonical_events(canonical_event_id) ON DELETE SET NULL;

-- ============================================================================
-- PHASE 5: Update verification_log Action Constraint
-- ============================================================================
ALTER TABLE verification_log
    DROP CONSTRAINT IF EXISTS verification_log_action_check;

ALTER TABLE verification_log
    ADD CONSTRAINT verification_log_action_check CHECK (
        action = ANY (ARRAY[
            'verified'::text,
            'rejected'::text,
            'marked_suspicious'::text,
            'marked_duplicate'::text,
            'needs_review'::text
        ])
    );

-- ============================================================================
-- PHASE 6: Outbox Tables (for transactional event publishing)
-- ============================================================================
CREATE TABLE IF NOT EXISTS verification_outbox (
    outbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES canonical_events(canonical_event_id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS event_cluster_members (
    event_id UUID PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
    cluster_id UUID NOT NULL REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
    event_timestamp TIMESTAMPTZ NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- PHASE 7: All Indexes
-- ============================================================================

-- Events table indexes
CREATE INDEX IF NOT EXISTS idx_events_geom ON events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_category ON events (event_category);
CREATE INDEX IF NOT EXISTS idx_events_verification_status ON events (verification_status);
CREATE INDEX IF NOT EXISTS idx_events_city ON events (city);
CREATE INDEX IF NOT EXISTS idx_events_cluster_id ON events (cluster_id);
CREATE INDEX IF NOT EXISTS idx_events_source_name ON events (source_name);
CREATE INDEX IF NOT EXISTS idx_events_source_id ON events (source_id);
CREATE INDEX IF NOT EXISTS idx_events_source_type ON events (source_type);
CREATE INDEX IF NOT EXISTS idx_events_canonical_event_id ON events (canonical_event_id);

-- Canonical events indexes
CREATE INDEX IF NOT EXISTS idx_ce_timestamp ON canonical_events (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_ce_first_seen ON canonical_events (first_seen DESC);
CREATE INDEX IF NOT EXISTS idx_ce_category ON canonical_events (event_category);
CREATE INDEX IF NOT EXISTS idx_ce_severity ON canonical_events (severity);
CREATE INDEX IF NOT EXISTS idx_ce_verification ON canonical_events (verification_status);
CREATE INDEX IF NOT EXISTS idx_ce_city ON canonical_events (city);
CREATE INDEX IF NOT EXISTS idx_ce_geom ON canonical_events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_ce_verification_reasons ON canonical_events USING GIN (verification_reasons);

-- Event clusters indexes
CREATE INDEX IF NOT EXISTS idx_clusters_centroid ON event_clusters USING GIST (centroid_geom);

-- Verification log indexes
CREATE INDEX IF NOT EXISTS idx_verification_log_event_id ON verification_log (event_id);

-- Outbox indexes
CREATE INDEX IF NOT EXISTS idx_verification_outbox_pending
    ON verification_outbox (next_attempt_at, created_at)
    WHERE published_at IS NULL;

-- Event cluster members indexes
CREATE INDEX IF NOT EXISTS idx_event_cluster_members_cluster_id ON event_cluster_members(cluster_id);

-- ============================================================================
-- PHASE 8: All Triggers
-- ============================================================================

-- Events table triggers
DROP TRIGGER IF EXISTS trg_sync_geom ON events;
CREATE TRIGGER trg_sync_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude
    ON events
    FOR EACH ROW EXECUTE FUNCTION sync_geom();

DROP TRIGGER IF EXISTS trg_events_updated_at ON events;
CREATE TRIGGER trg_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Event clusters triggers
DROP TRIGGER IF EXISTS trg_event_clusters_updated_at ON event_clusters;
CREATE TRIGGER trg_event_clusters_updated_at
    BEFORE UPDATE ON event_clusters
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Sources triggers
DROP TRIGGER IF EXISTS trg_sources_updated_at ON sources;
CREATE TRIGGER trg_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Canonical events triggers
DROP TRIGGER IF EXISTS trg_ce_updated_at ON canonical_events;
CREATE TRIGGER trg_ce_updated_at
    BEFORE UPDATE ON canonical_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_ce_sync_geom ON canonical_events;
CREATE TRIGGER trg_ce_sync_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude ON canonical_events
    FOR EACH ROW EXECUTE FUNCTION sync_geom();

-- ============================================================================
-- PHASE 9: Data Cleanup (remove orphaned FKs)
-- ============================================================================
UPDATE canonical_events ce
SET cluster_id = NULL
WHERE cluster_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM event_clusters ec WHERE ec.cluster_id = ce.cluster_id);

UPDATE event_clusters ec
SET member_count = COALESCE((SELECT COUNT(*) FROM event_cluster_members m WHERE m.cluster_id=ec.cluster_id), 0)
WHERE EXISTS (SELECT 1 FROM event_cluster_members m WHERE m.cluster_id = ec.cluster_id)
   OR member_count != 0;

-- ============================================================================
-- PHASE 10: Sample Data (optional - useful for testing)
-- ============================================================================
-- Uncomment to load sample data

-- Insert sample sources
INSERT INTO sources (source_name, source_type, base_url, trust_score)
VALUES
    ('Open-Meteo', 'weather_api', 'https://open-meteo.com', 0.95),
    ('synthetic_gen', 'synthetic', NULL, 0.5),
    ('Twitter', 'social', 'https://twitter.com', 0.70),
    ('Government Data Portal', 'government_dataset', 'https://data.gov.in', 0.90),
    ('Citizen Reports', 'citizen', NULL, 0.65)
ON CONFLICT (source_name) DO NOTHING;

-- ============================================================================
-- PHASE 11: Final Verification
-- ============================================================================
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN (
          'events', 'canonical_events', 'sources', 'verification_log',
          'event_clusters', 'verification_outbox', 'event_cluster_members'
      );
    
    RAISE NOTICE 'Schema initialization complete. % required tables created.', table_count;
END $$;

COMMIT;
