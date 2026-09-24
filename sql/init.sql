-- ============================================================
-- SIH26069 — National Weather Big Data Analytics Platform
-- Complete, Authoritative PostgreSQL + PostGIS Schema
-- Single source of truth for full database setup.
-- 00_complete_schema.sql and all numbered migrations (01-10) are
-- idempotent and safe to re-run on top without conflict.
-- Source of truth: 02_DATA_SCHEMA.md §17
-- ============================================================

-- ============================================================
-- STEP 1: Extensions (must come before any table or function)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS postgis;       -- GEOMETRY types, ST_* functions

-- ============================================================
-- STEP 2: Helper functions
-- ============================================================
CREATE OR REPLACE FUNCTION sync_geom()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- STEP 3: Tables (in dependency order)
-- ============================================================

-- 3a. event_clusters (no FK dependencies)
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

-- 3b. canonical_events (authoritative aggregated weather incidents)
CREATE TABLE IF NOT EXISTS canonical_events (
    canonical_event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_category            TEXT NOT NULL
                                  CHECK (event_category IN (
                                      'rainfall','heavy_rainfall','flood',
                                      'thunderstorm','lightning','heatwave',
                                      'fog','dust_storm','strong_wind',
                                      'hailstorm','cyclone','other'
                                  )),
    severity                  TEXT CHECK (severity IN ('low','moderate','high','extreme')),
    description               TEXT CHECK (char_length(description) <= 2000),
    latitude                  NUMERIC(9,6) CHECK (latitude BETWEEN -90 AND 90),
    longitude                 NUMERIC(10,6) CHECK (longitude BETWEEN -180 AND 180),
    geom                      GEOMETRY(Point, 4326),
    city                      TEXT,
    district                  TEXT,
    state                     TEXT,
    country                   TEXT NOT NULL DEFAULT 'India',
    first_seen                TIMESTAMPTZ NOT NULL,
    last_seen                 TIMESTAMPTZ NOT NULL,
    source_count              INTEGER NOT NULL DEFAULT 1,
    report_count              INTEGER NOT NULL DEFAULT 1,
    contributing_sources      TEXT[] NOT NULL DEFAULT '{}',
    classified_category       TEXT CHECK (classified_category IN (
                                  'rainfall','heavy_rainfall','flood',
                                  'thunderstorm','lightning','heatwave',
                                  'fog','dust_storm','strong_wind',
                                  'hailstorm','cyclone','other'
                              )),
    classification_confidence NUMERIC(4,3) CHECK (classification_confidence BETWEEN 0 AND 1),
    credibility_score         NUMERIC(4,3) CHECK (credibility_score BETWEEN 0 AND 1),
    credibility_reasons       TEXT[] NOT NULL DEFAULT '{}',
    verification_reasons      TEXT[] NOT NULL DEFAULT '{}',
    cluster_id                UUID,
    CONSTRAINT fk_canonical_events_cluster
        FOREIGN KEY (cluster_id) REFERENCES event_clusters(cluster_id) ON DELETE SET NULL,
    verification_status       TEXT NOT NULL DEFAULT 'pending'
                                  CHECK (verification_status IN (
                                      'pending','verified','needs_review',
                                      'suspicious','duplicate'
                                  )),
    verified_by               TEXT,
    verification_timestamp    TIMESTAMPTZ,
    priority                  VARCHAR(20) DEFAULT 'normal',
    spark_processed_at        TIMESTAMPTZ,
    db_written_at             TIMESTAMPTZ,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3c. Optional pgvector embedding column setup
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Extension "vector" is unavailable in this PostgreSQL installation. Skipping pgvector setup: %', SQLERRM;
    END;

    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        EXECUTE 'ALTER TABLE canonical_events ADD COLUMN IF NOT EXISTS embedding VECTOR(384);';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_canonical_events_embedding ON canonical_events USING hnsw (embedding vector_cosine_ops);';
    ELSE
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
            CREATE DOMAIN vector AS text;
        END IF;
        ALTER TABLE canonical_events ADD COLUMN IF NOT EXISTS embedding vector;
        RAISE NOTICE 'Extension "vector" is not installed. Created fallback embedding column of domain vector (text).';
    END IF;
END $$;

-- 3d. events (FK → event_clusters, FK → canonical_events)
CREATE TABLE IF NOT EXISTS events (
    event_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id                 TEXT NOT NULL,
    source_type               TEXT NOT NULL
                                  CHECK (source_type IN (
                                      'weather_api','rss','website','social',
                                      'simulated_social','government_dataset',
                                      'citizen','synthetic'
                                  )),
    source_name               TEXT NOT NULL,
    source_url                TEXT,
    source_trust_score        NUMERIC(4,3) CHECK (source_trust_score BETWEEN 0 AND 1),
    event_timestamp           TIMESTAMPTZ NOT NULL,
    ingestion_timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latitude                  NUMERIC(9,6) CHECK (latitude BETWEEN -90 AND 90),
    longitude                 NUMERIC(10,6) CHECK (longitude BETWEEN -180 AND 180),
    city                      TEXT,
    district                  TEXT,
    state                     TEXT,
    country                   TEXT NOT NULL DEFAULT 'India',
    geom                      GEOMETRY(Point, 4326),
    event_category            TEXT NOT NULL
                                  CHECK (event_category IN (
                                      'rainfall','heavy_rainfall','flood',
                                      'thunderstorm','lightning','heatwave',
                                      'fog','dust_storm','strong_wind',
                                      'hailstorm','cyclone','other'
                                  )),
    severity                  TEXT CHECK (severity IN ('low','moderate','high','extreme')),
    description               TEXT CHECK (char_length(description) <= 2000),
    hashtags                  TEXT[],
    author_id                 TEXT,
    platform                  TEXT,
    photo_urls                TEXT[],
    video_urls                TEXT[],
    classified_category       TEXT CHECK (classified_category IN (
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
    CONSTRAINT fk_events_canonical_event_id
        FOREIGN KEY (canonical_event_id) REFERENCES canonical_events(canonical_event_id) ON DELETE SET NULL,
    verification_status       TEXT NOT NULL DEFAULT 'pending'
                                  CHECK (verification_status IN (
                                      'pending','verified','needs_review',
                                      'suspicious','duplicate'
                                  )),
    verified_by               TEXT,
    verification_timestamp    TIMESTAMPTZ,
    priority                  VARCHAR(20) DEFAULT 'normal',
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3e. sources (no FK dependencies)
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

-- 3f. verification_log (FK → events, includes 'needs_review')
CREATE TABLE IF NOT EXISTS verification_log (
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    action          TEXT NOT NULL,
    performed_by    TEXT NOT NULL,
    notes           TEXT,
    performed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT verification_log_action_check CHECK (
        action IN (
            'verified','rejected','marked_suspicious','marked_duplicate','needs_review'
        )
    )
);

-- 3g. verification_outbox (transactional publishing)
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

-- 3h. event_cluster_members (cluster-event mapping)
CREATE TABLE IF NOT EXISTS event_cluster_members (
    event_id UUID PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
    cluster_id UUID NOT NULL REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
    event_timestamp TIMESTAMPTZ NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- STEP 4: Indexes
-- ============================================================

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
CREATE INDEX IF NOT EXISTS idx_events_priority ON events (priority);

-- Canonical events indexes
CREATE INDEX IF NOT EXISTS idx_ce_timestamp ON canonical_events (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_ce_first_seen ON canonical_events (first_seen DESC);
CREATE INDEX IF NOT EXISTS idx_ce_category ON canonical_events (event_category);
CREATE INDEX IF NOT EXISTS idx_ce_severity ON canonical_events (severity);
CREATE INDEX IF NOT EXISTS idx_ce_verification ON canonical_events (verification_status);
CREATE INDEX IF NOT EXISTS idx_ce_city ON canonical_events (city);
CREATE INDEX IF NOT EXISTS idx_ce_geom ON canonical_events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_ce_verification_reasons ON canonical_events USING GIN (verification_reasons);
CREATE INDEX IF NOT EXISTS idx_canonical_events_cluster_id ON canonical_events (cluster_id);
CREATE INDEX IF NOT EXISTS idx_canonical_events_priority ON canonical_events (priority);
CREATE INDEX IF NOT EXISTS idx_canonical_events_spark_processed_at ON canonical_events (spark_processed_at);
CREATE INDEX IF NOT EXISTS idx_canonical_events_db_written_at ON canonical_events (db_written_at);

-- Event clusters & log indexes
CREATE INDEX IF NOT EXISTS idx_clusters_centroid ON event_clusters USING GIST (centroid_geom);
CREATE INDEX IF NOT EXISTS idx_verification_log_event_id ON verification_log (event_id);
CREATE INDEX IF NOT EXISTS idx_verification_outbox_pending ON verification_outbox (next_attempt_at, created_at) WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_event_cluster_members_cluster_id ON event_cluster_members (cluster_id);

-- ============================================================
-- STEP 5: Triggers
-- ============================================================
DROP TRIGGER IF EXISTS trg_sync_geom ON events;
CREATE TRIGGER trg_sync_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude
    ON events
    FOR EACH ROW EXECUTE FUNCTION sync_geom();

DROP TRIGGER IF EXISTS trg_events_updated_at ON events;
CREATE TRIGGER trg_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_ce_sync_geom ON canonical_events;
CREATE TRIGGER trg_ce_sync_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude
    ON canonical_events
    FOR EACH ROW EXECUTE FUNCTION sync_geom();

DROP TRIGGER IF EXISTS trg_ce_updated_at ON canonical_events;
CREATE TRIGGER trg_ce_updated_at
    BEFORE UPDATE ON canonical_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_event_clusters_updated_at ON event_clusters;
CREATE TRIGGER trg_event_clusters_updated_at
    BEFORE UPDATE ON event_clusters
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_sources_updated_at ON sources;
CREATE TRIGGER trg_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
