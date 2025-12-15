-- ============================================================================
-- Migration 044: Create Workflow 1126 - Step 5: Register Trigger
-- ============================================================================
-- Purpose: Register MANUAL trigger for Workflow 1126 (Profile Document Import)
-- This allows workflow execution through Turing's orchestration system
-- ============================================================================

BEGIN;

-- Create MANUAL trigger for on-demand execution
INSERT INTO workflow_triggers (
    workflow_id,
    trigger_name,
    trigger_description,
    trigger_type,
    enabled,
    priority,
    max_concurrent_runs,
    timeout_minutes,
    default_parameters
) VALUES (
    1126,
    'import_profile_document',
    'On-demand profile document import. Provide document_text in parameters.',
    'MANUAL',
    true,
    50,
    5,                              -- Allow 5 concurrent imports
    60,                             -- 1 hour timeout (qwen2.5 can be slow)
    '{
        "document_text": null
    }'::jsonb
) ON CONFLICT (workflow_id, trigger_name) DO UPDATE SET
    trigger_description = EXCLUDED.trigger_description,
    enabled = EXCLUDED.enabled,
    timeout_minutes = EXCLUDED.timeout_minutes;

COMMIT;

-- Verify
SELECT 
    trigger_id,
    workflow_id,
    trigger_name,
    trigger_type,
    enabled,
    timeout_minutes
FROM workflow_triggers
WHERE workflow_id = 1126;

-- Success message
DO $$ BEGIN
    RAISE NOTICE '✅ Step 5 Complete: MANUAL trigger registered for Workflow 1126';
    RAISE NOTICE '   Trigger: import_profile_document';
    RAISE NOTICE '   Usage: Execute via Turing orchestration system with document_text parameter';
END $$;
