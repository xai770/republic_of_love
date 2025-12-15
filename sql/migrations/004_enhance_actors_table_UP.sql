-- Migration: 004_enhance_actors_table_UP.sql
-- Description: Add Wave Runner V2 columns to actors table
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)
-- Reference: docs/WAVE_RUNNER_V2_DESIGN_DECISIONS.md

-- Add actor hierarchy columns
ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS parent_actor_id INT REFERENCES actors(actor_id) ON DELETE SET NULL;

ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS qualified BOOLEAN DEFAULT FALSE;

-- Add script drift detection columns
ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS script_code_hash TEXT;

ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS script_file_path TEXT;

ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS script_file_mtime TIMESTAMPTZ;

ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS script_synced_at TIMESTAMPTZ;

ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS script_sync_status TEXT DEFAULT 'synced' 
        CHECK (script_sync_status IN ('synced', 'drift_detected', 'file_missing', 'sync_failed'));

ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS active_history_id BIGINT;

-- Add auto-promote flag for validators
ALTER TABLE actors 
    ADD COLUMN IF NOT EXISTS auto_promote BOOLEAN DEFAULT FALSE;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_actors_parent ON actors(parent_actor_id);
CREATE INDEX IF NOT EXISTS idx_actors_qualified ON actors(qualified) WHERE qualified = TRUE;
CREATE INDEX IF NOT EXISTS idx_actors_sync_status ON actors(script_sync_status) WHERE script_sync_status != 'synced';

-- Comments
COMMENT ON COLUMN actors.parent_actor_id IS 'Parent actor in hierarchy (NULL for root actors)';
COMMENT ON COLUMN actors.qualified IS 'Can this actor start workflows? (workflows 1-4 qualified flag)';
COMMENT ON COLUMN actors.script_code_hash IS 'SHA256 hash of script_code for drift detection';
COMMENT ON COLUMN actors.script_file_path IS 'Canonical filesystem path to script';
COMMENT ON COLUMN actors.script_sync_status IS 'Drift detection status (synced/drift_detected/file_missing)';
COMMENT ON COLUMN actors.active_history_id IS 'Foreign key to actor_code_history (current active version)';
COMMENT ON COLUMN actors.auto_promote IS 'Auto-promote staging records to production (for validators)';
