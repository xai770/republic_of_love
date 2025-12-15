-- Migration 073: Create Workflow 3002 - Taxonomy Maintenance and Organization
-- Purpose: Automate the infinite-depth taxonomy organization process
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

-- Step 1: Create workflow registry entry
INSERT INTO workflows (
    workflow_id,
    workflow_name,
    workflow_description,
    max_total_session_runs,
    enabled
) VALUES (
    3002,
    'Taxonomy Maintenance and Organization',
    'Exports skills from database → Organizes with infinite-depth AI → Generates navigation index. Preserves the revolutionary taxonomy system built Nov 9, 2025.',
    50,
    true
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

COMMIT;

-- Verify
SELECT workflow_id, workflow_name, workflow_description, enabled
FROM workflows 
WHERE workflow_id = 3002;
