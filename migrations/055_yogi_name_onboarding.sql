-- Migration 055: Yogi name + onboarding support
-- Purpose: Add yogi_name for privacy-first identity, onboarding tracking
-- Date: 2026-02-12
--
-- Design: yogis choose their own name (not from Google OAuth).
-- yogi_name is the ONLY name Mira uses. Case-insensitive unique.
-- notification_email already exists. We add onboarding_completed_at.
-- PII columns (email, display_name, avatar_url) are NOT dropped yet —
-- existing auth code references them. Will be phased out separately.

BEGIN;

-- 1. Add yogi_name to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS yogi_name TEXT;

-- Case-insensitive unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_yogi_name_lower
    ON users (LOWER(yogi_name))
    WHERE yogi_name IS NOT NULL;

-- 2. Add onboarding tracking
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;

COMMENT ON COLUMN users.yogi_name IS
'Yogi-chosen display name. This is the ONLY name shown in UI and used by Mira.
Not from Google OAuth. Case-insensitive unique. 2-20 chars, alphanumeric + limited special.';

COMMENT ON COLUMN users.onboarding_completed_at IS
'Set when yogi completes onboarding: has yogi_name + either has profile or skipped.
NULL means onboarding not yet completed — Mira should guide them.';

COMMIT;
