-- Migration: 005_create_actor_code_history_UP.sql
-- Description: Create actor_code_history table (script versioning)
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)
-- Reference: docs/SCRIPT_ACTOR_CODE_LIFECYCLE.md

CREATE TABLE IF NOT EXISTS actor_code_history (
    history_id BIGSERIAL PRIMARY KEY,
    actor_id INT NOT NULL REFERENCES actors(actor_id) ON DELETE CASCADE,
    
    -- Script code snapshot
    script_code TEXT NOT NULL,
    script_code_hash TEXT NOT NULL,
    
    -- Change metadata
    change_type TEXT NOT NULL CHECK (change_type IN (
        'initial', 
        'manual_deploy', 
        'auto_sync', 
        'rollback', 
        'bug_fix'
    )),
    change_reason TEXT,
    changed_by_actor_id INT REFERENCES actors(actor_id),
    
    -- Source information
    source_file_path TEXT,
    git_commit_hash TEXT,
    version_tag TEXT,
    
    -- Activation tracking
    activated_at TIMESTAMPTZ DEFAULT NOW(),
    deactivated_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_actor_code_history_actor ON actor_code_history(actor_id, activated_at DESC);
CREATE INDEX idx_actor_code_history_active ON actor_code_history(actor_id) WHERE deactivated_at IS NULL;
CREATE INDEX idx_actor_code_history_hash ON actor_code_history(script_code_hash);

-- Add foreign key from actors to actor_code_history
ALTER TABLE actors 
    ADD CONSTRAINT actors_active_history_id_fkey 
    FOREIGN KEY (active_history_id) REFERENCES actor_code_history(history_id) 
    ON DELETE SET NULL;

-- Comments
COMMENT ON TABLE actor_code_history IS 'Version history for script actors (rollback, audit trail, drift detection)';
COMMENT ON COLUMN actor_code_history.change_type IS 'How this version was created (manual_deploy, auto_sync, rollback, etc.)';
COMMENT ON COLUMN actor_code_history.activated_at IS 'When this version became active';
COMMENT ON COLUMN actor_code_history.deactivated_at IS 'When this version was replaced (NULL = currently active)';
