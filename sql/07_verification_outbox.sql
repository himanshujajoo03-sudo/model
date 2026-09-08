-- Transactional outbox for verification actions.
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
CREATE INDEX IF NOT EXISTS idx_verification_outbox_pending
    ON verification_outbox (next_attempt_at, created_at)
    WHERE published_at IS NULL;


CREATE TABLE IF NOT EXISTS event_cluster_members (
    event_id UUID PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
    cluster_id UUID NOT NULL REFERENCES event_clusters(cluster_id) ON DELETE CASCADE,
    event_timestamp TIMESTAMPTZ NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_event_cluster_members_cluster_id ON event_cluster_members(cluster_id);

-- Cluster membership is authoritative; rebuild aggregates after migration.
UPDATE event_clusters ec SET member_count = COALESCE((SELECT COUNT(*) FROM event_cluster_members m WHERE m.cluster_id=ec.cluster_id),0);
