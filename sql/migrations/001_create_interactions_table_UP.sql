-- Migration: 001_create_interactions_table_UP.sql
-- Description: Create interactions table (Wave Runner V2 core operational table)
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)

-- Create workflow_runs table first (metadata index for monitoring)
CREATE TABLE IF NOT EXISTS workflow_runs (
    workflow_run_id BIGSERIAL PRIMARY KEY,
    workflow_id INT NOT NULL REFERENCES workflows(workflow_id) ON DELETE CASCADE,
    posting_id INT REFERENCES postings(posting_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'running' 
        CHECK (status IN ('running', 'completed', 'failed', 'stopped')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_by TEXT,
    metadata JSONB
);

CREATE INDEX idx_workflow_runs_workflow ON workflow_runs(workflow_id, status);
CREATE INDEX idx_workflow_runs_posting ON workflow_runs(posting_id);

COMMENT ON TABLE workflow_runs IS 'Metadata index for workflow execution monitoring (NOT a container)';

-- Create interactions table
CREATE TABLE IF NOT EXISTS interactions (
    interaction_id BIGSERIAL PRIMARY KEY,
    
    -- Workflow context
    posting_id INT REFERENCES postings(posting_id) ON DELETE CASCADE,
    conversation_id INT NOT NULL,
    workflow_run_id BIGINT REFERENCES workflow_runs(workflow_run_id) ON DELETE SET NULL,
    
    -- Actor information
    actor_id INT NOT NULL REFERENCES actors(actor_id) ON DELETE RESTRICT,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('ai_model', 'script', 'human')),
    
    -- Execution state
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'invalidated')),
    execution_order INT NOT NULL,
    
    -- Parent relationships (Nov 23, 2025: Multi-parent support)
    parent_interaction_id BIGINT REFERENCES interactions(interaction_id) ON DELETE SET NULL,
    input_interaction_ids INT[] DEFAULT '{}',
    
    -- Input/Output
    input JSONB,
    output JSONB,
    
    -- Error handling
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    
    -- Control flags (Nov 23, 2025: Separate enabled/invalidated)
    enabled BOOLEAN DEFAULT TRUE,
    invalidated BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX idx_interactions_posting 
    ON interactions(posting_id, conversation_id, execution_order);

CREATE INDEX idx_interactions_status 
    ON interactions(status, updated_at) 
    WHERE status IN ('pending', 'running');

CREATE INDEX idx_interactions_workflow_run 
    ON interactions(workflow_run_id, status);

CREATE INDEX idx_interactions_actor 
    ON interactions(actor_id, status);

CREATE INDEX idx_interactions_parent 
    ON interactions(parent_interaction_id);

CREATE INDEX idx_interactions_conversation 
    ON interactions(posting_id, conversation_id);

-- Index for enabled/invalidated queries (Nov 23, 2025)
CREATE INDEX idx_interactions_enabled 
    ON interactions(enabled, invalidated) 
    WHERE enabled = TRUE AND invalidated = FALSE;

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_interactions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER interactions_updated_at_trigger
    BEFORE UPDATE ON interactions
    FOR EACH ROW
    EXECUTE FUNCTION update_interactions_updated_at();

-- Comments for documentation
COMMENT ON TABLE interactions IS 'Wave Runner V2 core operational table - tracks all workflow interactions';
COMMENT ON COLUMN interactions.enabled IS 'Flag to enable/disable interaction (NOT deletion)';
COMMENT ON COLUMN interactions.invalidated IS 'Flag to mark interaction as invalid (duplicate, bug, etc.)';
COMMENT ON COLUMN interactions.input_interaction_ids IS 'Array of parent interaction IDs for multi-parent cases';
