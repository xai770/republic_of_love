-- Migration: Add situation_context column to users
-- Date: 2026-03-02
-- Purpose: Store Step 1 (Situation) questionnaire answers as JSONB
-- Schema: { confidence: int|null, openness: int|null, hours: int|null, environment: int|null, intention: int|null }
-- Already applied via ALTER TABLE in this session.

ALTER TABLE users ADD COLUMN IF NOT EXISTS situation_context jsonb DEFAULT '{}';

COMMENT ON COLUMN users.situation_context IS 'Step 1 situation questionnaire: {confidence, openness, hours, environment, intention}';
