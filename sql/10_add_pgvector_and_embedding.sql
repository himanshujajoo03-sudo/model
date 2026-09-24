-- ============================================================
-- SIH26069 — Multilingual Embeddings & pgvector Migration
-- Additive migration: enables vector extension, adds 384-dim
-- embedding column to canonical_events, and creates HNSW index
-- ============================================================

DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS vector;
    EXCEPTION
        WHEN OTHERS THEN
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
