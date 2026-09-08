-- ============================================================
-- SIH26069 — National Weather Big Data Analytics Platform
-- PostgreSQL + PostGIS Initialization Script
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

-- 3b. events (FK → event_clusters)
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
    verification_status     TEXT NOT NULL DEFAULT 'pending'
                                CHECK (verification_status IN (
                                    'pending','verified','needs_review',
                                    'suspicious','duplicate'
                                )),
    verified_by             TEXT,
    verification_timestamp  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3c. sources (no FK dependencies)
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
    action          TEXT NOT NULL
                        CHECK (action IN (
                            'verified','rejected','marked_suspicious','marked_duplicate'
                        )),
    performed_by    TEXT NOT NULL,
    notes           TEXT,
    performed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- STEP 4: Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_events_geom ON events USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_category ON events (event_category);
CREATE INDEX IF NOT EXISTS idx_events_verification_status ON events (verification_status);
CREATE INDEX IF NOT EXISTS idx_events_city ON events (city);
CREATE INDEX IF NOT EXISTS idx_events_cluster_id ON events (cluster_id);
CREATE INDEX IF NOT EXISTS idx_events_source_name ON events (source_name);
CREATE INDEX IF NOT EXISTS idx_events_source_id ON events (source_id);
CREATE INDEX IF NOT EXISTS idx_events_source_type ON events (source_type);
CREATE INDEX IF NOT EXISTS idx_clusters_centroid ON event_clusters USING GIST (centroid_geom);
CREATE INDEX IF NOT EXISTS idx_verification_log_event_id ON verification_log (event_id);

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

DROP TRIGGER IF EXISTS trg_event_clusters_updated_at ON event_clusters;
CREATE TRIGGER trg_event_clusters_updated_at
    BEFORE UPDATE ON event_clusters
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_sources_updated_at ON sources;
CREATE TRIGGER trg_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
