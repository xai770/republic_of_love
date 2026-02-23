-- Track B: append-only audit log + user freeze flag
-- Run once: psql -d turing -f migrations/yogi_audit_log_20260223.sql

-- ─────────────────────────────────────────────────────────
-- 1. User freeze flag
-- ─────────────────────────────────────────────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS freeze_flag BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN users.freeze_flag IS
    'When TRUE, the user is frozen (Han Solo mode) — all LLM features blocked.';

-- ─────────────────────────────────────────────────────────
-- 2. Immutable audit log
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS yogi_audit_log (
    audit_id    BIGSERIAL PRIMARY KEY,
    user_id     INTEGER         NOT NULL,   -- FK to users.user_id (soft — no cascade needed)
    actor       TEXT            NOT NULL,   -- 'system' | 'adele' | 'mira' | 'yogi' | 'admin'
    event_type  TEXT            NOT NULL,   -- 'login' | 'logout' | 'cv_upload' | 'adele_save'
                                            --   | 'profile_translate' | 'freeze' | 'unfreeze' | …
    detail      JSONB           NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE yogi_audit_log IS
    'Append-only legal/compliance record. Never UPDATE or DELETE rows here.';

-- Prevent accidental UPDATE/DELETE at the DB level
CREATE RULE yogi_audit_log_no_update AS ON UPDATE TO yogi_audit_log DO INSTEAD NOTHING;
CREATE RULE yogi_audit_log_no_delete AS ON DELETE TO yogi_audit_log DO INSTEAD NOTHING;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_audit_user_id   ON yogi_audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON yogi_audit_log (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON yogi_audit_log (created_at DESC);
