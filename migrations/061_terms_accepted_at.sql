-- Migration 061: Add terms_accepted_at to users table
-- Records when the yogi accepted the Terms & Conditions during onboarding.
-- Date: 2026-02-22

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN users.terms_accepted_at IS
    'When the yogi accepted the T&Cs during onboarding. NULL = not yet accepted.';
