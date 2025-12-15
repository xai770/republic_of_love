-- Migration 015: Create posting_state_checkpoints table
-- Purpose: Store PostingState snapshots for crash recovery
-- Created: 2025-11-13
-- Author: Arden

-- Enable JSONB support (should already be enabled)
-- This table stores serialized PostingState objects for crash recovery

CREATE TABLE IF NOT EXISTS posting_state_checkpoints (
    checkpoint_id SERIAL PRIMARY KEY,
    workflow_run_id INTEGER NOT NULL,
    posting_id INTEGER NOT NULL,
    execution_order INTEGER NOT NULL,
    
    -- Serialized PostingState data
    state_snapshot JSONB NOT NULL,
    
    -- Metadata
    wave_number INTEGER NOT NULL,
    conversation_id INTEGER,
    conversation_name TEXT,
    
    -- Status tracking
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'superseded'
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_posting_state_workflow_run 
        FOREIGN KEY (workflow_run_id) 
        REFERENCES workflow_runs(workflow_run_id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_posting_state_posting 
        FOREIGN KEY (posting_id) 
        REFERENCES postings(posting_id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_posting_state_conversation 
        FOREIGN KEY (conversation_id) 
        REFERENCES conversations(conversation_id) 
        ON DELETE SET NULL
);

-- Indexes for fast lookups
CREATE INDEX idx_checkpoint_workflow_run ON posting_state_checkpoints(workflow_run_id);
CREATE INDEX idx_checkpoint_posting ON posting_state_checkpoints(posting_id);
CREATE INDEX idx_checkpoint_execution_order ON posting_state_checkpoints(workflow_run_id, execution_order);
CREATE INDEX idx_checkpoint_status ON posting_state_checkpoints(status);

-- Composite index for resume queries (most recent checkpoint per posting)
CREATE INDEX idx_checkpoint_resume 
    ON posting_state_checkpoints(workflow_run_id, posting_id, execution_order DESC, created_at DESC);

-- Comment on table
COMMENT ON TABLE posting_state_checkpoints IS 
'Stores serialized PostingState snapshots for crash recovery and workflow resume functionality';

COMMENT ON COLUMN posting_state_checkpoints.state_snapshot IS 
'JSONB serialization of PostingState object including outputs, conversation_run_ids, terminal flag, etc.';

COMMENT ON COLUMN posting_state_checkpoints.status IS 
'active=current checkpoint, completed=posting finished workflow, superseded=newer checkpoint exists';

-- View for latest checkpoint per posting
CREATE OR REPLACE VIEW latest_posting_checkpoints AS
SELECT DISTINCT ON (workflow_run_id, posting_id)
    checkpoint_id,
    workflow_run_id,
    posting_id,
    execution_order,
    state_snapshot,
    wave_number,
    conversation_id,
    conversation_name,
    status,
    created_at
FROM posting_state_checkpoints
WHERE status = 'active'
ORDER BY workflow_run_id, posting_id, execution_order DESC, created_at DESC;

COMMENT ON VIEW latest_posting_checkpoints IS 
'Shows the most recent active checkpoint for each posting in each workflow run';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON posting_state_checkpoints TO base_admin;
GRANT USAGE, SELECT ON SEQUENCE posting_state_checkpoints_checkpoint_id_seq TO base_admin;
GRANT SELECT ON latest_posting_checkpoints TO base_admin;
