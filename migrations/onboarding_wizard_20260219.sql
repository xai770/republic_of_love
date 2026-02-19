-- Migration: Onboarding wizard support
-- Date: 2026-02-19
-- Add language and formality preferences to users table

ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'de';
ALTER TABLE users ADD COLUMN IF NOT EXISTS formality TEXT DEFAULT 'du';
COMMENT ON COLUMN users.language IS 'UI language: de or en';
COMMENT ON COLUMN users.formality IS 'Anrede: du or sie (German only)';
