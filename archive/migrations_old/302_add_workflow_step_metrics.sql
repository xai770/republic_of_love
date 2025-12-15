-- Migration 302: Add workflow step metrics tracking
-- Purpose: Track timing and performance for each conversation/step in workflow execution
-- Author: System
-- Date: 2024-11-14

-- Create table to track metrics per conversation execution
CREATE TABLE IF NOT EXISTS workflow_step_metrics (
    metric_id SERIAL PRIMARY KEY,
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(workflow_run_id) ON DELETE CASCADE,
    conversation_id INTEGER NOT NULL REFERENCES conversations(conversation_id),
    conversation_name VARCHAR(255),
    execution_order INTEGER,
    
    -- Timing metrics
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds NUMERIC(10,2),
    
    -- Volume metrics
    postings_processed INTEGER DEFAULT 0,
    postings_succeeded INTEGER DEFAULT 0,
    postings_failed INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_time_per_posting NUMERIC(10,2),
    min_time_per_posting NUMERIC(10,2),
    max_time_per_posting NUMERIC(10,2),
    
    -- LLM metrics (aggregated)
    total_llm_calls INTEGER DEFAULT 0,
    total_tokens_input INTEGER DEFAULT 0,
    total_tokens_output INTEGER DEFAULT 0,
    total_cost_usd NUMERIC(10,6) DEFAULT 0,
    avg_latency_ms INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'in_progress',  -- in_progress, completed, failed
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_workflow_step_metrics_workflow_run ON workflow_step_metrics(workflow_run_id);
CREATE INDEX idx_workflow_step_metrics_conversation ON workflow_step_metrics(conversation_id);
CREATE INDEX idx_workflow_step_metrics_status ON workflow_step_metrics(status);
CREATE INDEX idx_workflow_step_metrics_started_at ON workflow_step_metrics(started_at DESC);

-- Add comment
COMMENT ON TABLE workflow_step_metrics IS 'Tracks performance metrics for each conversation/step execution in a workflow run';

COMMIT;
