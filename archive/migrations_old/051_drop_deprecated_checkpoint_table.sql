-- Migration 051: Drop Deprecated Checkpoint Table
-- Purpose: Remove _deprecated_posting_state_checkpoints and dependent views
-- Date: 2025-11-19
-- Author: Arden (Schema & Architecture Lead)
-- Context: Event sourcing architecture is now the standard (execution_events, posting_state_projection)

BEGIN;

-- Step 1: Drop dependent views first
DROP VIEW IF EXISTS latest_posting_checkpoints CASCADE;
DROP VIEW IF EXISTS workflow_health CASCADE;

-- Step 2: Drop the deprecated table
DROP TABLE IF EXISTS _deprecated_posting_state_checkpoints CASCADE;

-- Step 3: Recreate workflow_health view using event sourcing architecture
CREATE OR REPLACE VIEW workflow_health AS
SELECT 
    wr.workflow_run_id,
    wr.workflow_id,
    w.workflow_name,
    wr.status AS run_status,
    wr.started_at,
    wr.completed_at,
    EXTRACT(epoch FROM (COALESCE(wr.completed_at::timestamp with time zone, now()) - wr.started_at::timestamp with time zone)) AS duration_seconds,
    COUNT(DISTINCT ee_conv.event_id) FILTER (WHERE ee_conv.event_type = 'conversation_completed') AS conversations_executed,
    COUNT(DISTINCT ee_llm.event_id) FILTER (WHERE ee_llm.event_type IN ('llm_call_completed', 'llm_call_failed')) AS llm_calls_made,
    COUNT(DISTINCT psp.posting_id) AS postings_processed,
    COUNT(DISTINCT we.error_id) AS error_count,
    COUNT(DISTINCT we.posting_id) AS postings_with_errors,
    MAX(ee_all.event_timestamp) AS last_activity_at,
    MAX(psp.last_updated) AS last_projection_update
FROM workflow_runs wr
JOIN workflows w ON wr.workflow_id = w.workflow_id
LEFT JOIN execution_events ee_all ON wr.workflow_run_id = (ee_all.metadata->>'workflow_run_id')::INT
LEFT JOIN execution_events ee_conv ON ee_conv.event_type = 'conversation_completed' 
    AND wr.workflow_run_id = (ee_conv.metadata->>'workflow_run_id')::INT
LEFT JOIN execution_events ee_llm ON ee_llm.event_type IN ('llm_call_completed', 'llm_call_failed')
    AND wr.workflow_run_id = (ee_llm.metadata->>'workflow_run_id')::INT
LEFT JOIN posting_state_projection psp ON psp.posting_id IN (
    SELECT DISTINCT (ee.aggregate_id)::INT 
    FROM execution_events ee 
    WHERE ee.aggregate_type = 'posting' 
      AND (ee.metadata->>'workflow_run_id')::INT = wr.workflow_run_id
)
LEFT JOIN workflow_errors we ON wr.workflow_run_id = we.workflow_run_id
WHERE wr.started_at > (now() - interval '7 days')
GROUP BY wr.workflow_run_id, wr.workflow_id, w.workflow_name, wr.status, wr.started_at, wr.completed_at;

COMMENT ON VIEW workflow_health IS 
'Health monitoring view for workflow runs. Uses event sourcing (execution_events, posting_state_projection) instead of deprecated checkpoints.';

-- Step 4: Recreate latest_posting_checkpoints view using event sourcing projection
CREATE OR REPLACE VIEW latest_posting_checkpoints AS
SELECT DISTINCT ON (psp.posting_id)
    psp.posting_id AS checkpoint_id,
    psp.posting_id,
    psp.current_step AS execution_order,
    psp.conversation_history AS execution_sequence,
    psp.outputs AS conversation_outputs,
    psp.current_status AS status,
    psp.last_updated AS created_at
FROM posting_state_projection psp
WHERE psp.current_status NOT IN ('archived', 'deleted')
ORDER BY psp.posting_id, psp.current_step DESC, psp.last_updated DESC;

COMMENT ON VIEW latest_posting_checkpoints IS 
'Latest checkpoint state per posting. Migrated from deprecated checkpoint table to event sourcing projection.';

-- Step 5: Grant permissions
GRANT SELECT ON workflow_health TO base_admin;
GRANT SELECT ON latest_posting_checkpoints TO base_admin;

-- Step 6: Summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '================================================================================';
    RAISE NOTICE 'Migration 051 Complete: Dropped Deprecated Checkpoint Table';
    RAISE NOTICE '================================================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'DROPPED:';
    RAISE NOTICE '  - _deprecated_posting_state_checkpoints table';
    RAISE NOTICE '  - latest_posting_checkpoints view (old version)';
    RAISE NOTICE '  - workflow_health view (old version)';
    RAISE NOTICE '';
    RAISE NOTICE 'RECREATED:';
    RAISE NOTICE '  - workflow_health → Uses posting_state_projection + execution_events';
    RAISE NOTICE '  - latest_posting_checkpoints → Uses posting_state_projection';
    RAISE NOTICE '';
    RAISE NOTICE 'EVENT SOURCING ARCHITECTURE:';
    RAISE NOTICE '  - Source of truth: execution_events table';
    RAISE NOTICE '  - Projection: posting_state_projection (rebuilt from events)';
    RAISE NOTICE '  - Snapshots: posting_state_snapshots (periodic backups)';
    RAISE NOTICE '';
    RAISE NOTICE 'MIGRATION NOTES:';
    RAISE NOTICE '  - All checkpoint data was already migrated to event sourcing';
    RAISE NOTICE '  - No data loss - events are authoritative source';
    RAISE NOTICE '  - Views now use posting_state_projection instead of old checkpoints';
    RAISE NOTICE '';
    RAISE NOTICE '================================================================================';
END $$;

COMMIT;
