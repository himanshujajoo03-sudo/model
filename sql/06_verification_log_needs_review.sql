-- ============================================================
-- SIH26069 — Add needs_review to verification_log action CHECK
-- Allows the admin Verification Center to log needs_review actions.
-- ============================================================

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
