-- Migration 036: Add Performance Indexes for QA Tool Queries
-- Purpose: Speed up lineage queries joining postings → test_cases → workflow_runs → llm_interactions
-- Date: 2025-11-02

-- Index on test_data JSONB for job_id lookups (critical for posting → test_case join)
CREATE INDEX IF NOT EXISTS idx_test_cases_test_data_job_id 
ON test_cases ((test_data->>'job_id'));

-- Index on workflow_runs for test_case_id lookups (workflow_runs → test_cases join)
CREATE INDEX IF NOT EXISTS idx_workflow_runs_test_case_id 
ON workflow_runs (test_case_id);

-- Index on llm_interactions for workflow_run_id lookups (already might exist, but ensure it)
CREATE INDEX IF NOT EXISTS idx_llm_interactions_workflow_run_id 
ON llm_interactions (workflow_run_id);

-- Composite index for getting latest workflow_run per test_case
CREATE INDEX IF NOT EXISTS idx_workflow_runs_test_case_id_desc 
ON workflow_runs (test_case_id, workflow_run_id DESC);

-- Index on postings for skill_keywords IS NOT NULL filter
CREATE INDEX IF NOT EXISTS idx_postings_with_skills 
ON postings (posting_id) 
WHERE skill_keywords IS NOT NULL;

COMMENT ON INDEX idx_test_cases_test_data_job_id IS 'JSONB index for fast job_id lookups in test_data';
COMMENT ON INDEX idx_workflow_runs_test_case_id IS 'Speed up workflow_runs → test_cases joins';
COMMENT ON INDEX idx_llm_interactions_workflow_run_id IS 'Speed up llm_interactions → workflow_runs joins';
COMMENT ON INDEX idx_workflow_runs_test_case_id_desc IS 'Optimize ORDER BY workflow_run_id DESC LIMIT 1 queries';
COMMENT ON INDEX idx_postings_with_skills IS 'Partial index for postings with extracted skills';
