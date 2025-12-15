-- Migration 052: Drop Legacy workflow_runs Table
-- Author: Sandy + Arden
-- Date: 2025-11-19
-- Purpose: Remove vestigial workflow_runs table after event sourcing migration
-- Context: Table was polluting database with orphaned records (47,434 found)
--          Event sourcing (execution_events) is now the source of truth

BEGIN;

-- Step 1: Clean up orphaned workflow_run records (mark as completed)
UPDATE workflow_runs 
SET status = 'SUCCESS',
    completed_at = started_at + interval '1 second'
WHERE status = 'RUNNING'
AND completed_at IS NULL;

-- Step 2: Drop foreign key constraints referencing workflow_runs
-- These tables will keep their workflow_run_id columns but without FK constraint

ALTER TABLE career_analyses 
    DROP CONSTRAINT IF EXISTS career_analyses_workflow_run_id_fkey;

ALTER TABLE llm_interactions 
    DROP CONSTRAINT IF EXISTS llm_interactions_workflow_run_id_fkey;

ALTER TABLE posting_fetch_runs 
    DROP CONSTRAINT IF EXISTS job_fetch_runs_workflow_run_id_fkey;

ALTER TABLE posting_processing_status 
    DROP CONSTRAINT IF EXISTS posting_processing_status_ihl_workflow_run_id_fkey,
    DROP CONSTRAINT IF EXISTS posting_processing_status_summary_workflow_run_id_fkey,
    DROP CONSTRAINT IF EXISTS posting_processing_status_skills_workflow_run_id_fkey,
    DROP CONSTRAINT IF EXISTS posting_processing_status_matching_workflow_run_id_fkey;

ALTER TABLE posting_skills 
    DROP CONSTRAINT IF EXISTS posting_skills_workflow_run_id_fkey;

ALTER TABLE profile_skills 
    DROP CONSTRAINT IF EXISTS profile_skills_recipe_run_id_fkey;

ALTER TABLE trigger_executions 
    DROP CONSTRAINT IF EXISTS trigger_executions_workflow_run_id_fkey;

ALTER TABLE user_posting_decisions 
    DROP CONSTRAINT IF EXISTS user_posting_decisions_decision_workflow_run_id_fkey;

ALTER TABLE workflow_errors 
    DROP CONSTRAINT IF EXISTS workflow_errors_workflow_run_id_fkey;

ALTER TABLE workflow_metrics 
    DROP CONSTRAINT IF EXISTS workflow_metrics_workflow_run_id_fkey;

ALTER TABLE workflow_step_metrics 
    DROP CONSTRAINT IF EXISTS workflow_step_metrics_workflow_run_id_fkey;

-- Step 3: Drop dependent views
DROP VIEW IF EXISTS workflow_health CASCADE;
DROP VIEW IF EXISTS latest_posting_checkpoints CASCADE;

-- Step 4: Drop the workflow_runs table
DROP TABLE IF EXISTS workflow_runs CASCADE;

-- Step 5: Recreate workflow_health view using event sourcing
CREATE VIEW workflow_health AS
WITH workflow_events AS (
    SELECT 
        (metadata->>'workflow_run_id')::TEXT as workflow_run_id,
        (metadata->>'workflow_id')::INT as workflow_id,
        event_type,
        event_timestamp,
        aggregate_id
    FROM execution_events
    WHERE event_timestamp > (NOW() - interval '7 days')
    AND metadata->>'workflow_run_id' IS NOT NULL
),
workflow_stats AS (
    SELECT 
        workflow_run_id,
        workflow_id,
        MIN(CASE WHEN event_type = 'workflow.started' THEN event_timestamp END) as started_at,
        MAX(CASE WHEN event_type IN ('workflow.completed', 'workflow.failed') THEN event_timestamp END) as completed_at,
        COUNT(DISTINCT CASE WHEN event_type = 'conversation.completed' THEN aggregate_id END) as conversations_executed,
        COUNT(CASE WHEN event_type = 'llm.call' THEN 1 END) as llm_calls_made,
        COUNT(DISTINCT aggregate_id) as postings_processed,
        BOOL_OR(event_type = 'workflow.completed') as is_completed,
        BOOL_OR(event_type = 'workflow.failed') as is_failed
    FROM workflow_events
    GROUP BY workflow_run_id, workflow_id
)
SELECT 
    ws.workflow_run_id,
    ws.workflow_id,
    w.workflow_name,
    CASE 
        WHEN ws.is_completed THEN 'COMPLETED'
        WHEN ws.is_failed THEN 'FAILED'
        ELSE 'RUNNING'
    END as status,
    ws.started_at,
    ws.completed_at,
    EXTRACT(EPOCH FROM (
        COALESCE(ws.completed_at, NOW()) - ws.started_at
    )) as runtime_seconds,
    ws.conversations_executed,
    ws.llm_calls_made,
    ws.postings_processed
FROM workflow_stats ws
JOIN workflows w ON w.workflow_id = ws.workflow_id
ORDER BY ws.started_at DESC;

GRANT SELECT ON workflow_health TO base_admin;

-- Step 6: Create helper view for debugging (optional)
CREATE VIEW workflow_runs_legacy_mapping AS
SELECT 
    (metadata->>'workflow_run_id')::TEXT as legacy_workflow_run_id,
    (metadata->>'workflow_id')::INT as workflow_id,
    aggregate_id as posting_id,
    MIN(event_timestamp) as first_event,
    MAX(event_timestamp) as last_event,
    COUNT(*) as event_count
FROM execution_events
WHERE metadata->>'workflow_run_id' IS NOT NULL
GROUP BY metadata->>'workflow_run_id', metadata->>'workflow_id', aggregate_id
ORDER BY first_event DESC;

GRANT SELECT ON workflow_runs_legacy_mapping TO base_admin;

COMMIT;

-- Post-migration notes:
-- 1. workflow_run_id columns in dependent tables now contain orphaned IDs
--    These can be NULL'd out or left as-is (they're just integers now, not FK references)
-- 2. Event sourcing (execution_events) is now the single source of truth
-- 3. workflow_health view rebuilt from execution_events
-- 4. Code changes required:
--    - core/wave_executor.py: Remove workflow_run creation (already done by Sandy)
--    - tools/debug_posting.py: Update to query execution_events instead of workflow_runs
--    - Any monitoring scripts using workflow_runs table

-- Migration 052 Complete
