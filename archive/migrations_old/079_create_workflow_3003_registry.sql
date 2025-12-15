-- Migration 079: Create Workflow 3003 - Taxonomy Maintenance (Turing Native)
-- Purpose: Implement taxonomy maintenance using Turing's conversation/branching logic
--          instead of monolithic Python scripts. A/B comparison with Workflow 3002.
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

INSERT INTO workflows (
    workflow_id,
    workflow_name,
    workflow_description,
    max_total_session_runs,
    enabled
) VALUES (
    3003,
    'Taxonomy Maintenance (Turing Native)',
    'Turing-native taxonomy maintenance: Query skills → LLM organization → File operations. Uses conversation branching instead of scripts. Compare with 3002.',
    100,
    true
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

COMMIT;

-- Verify
SELECT workflow_id, workflow_name, workflow_description, enabled
FROM workflows WHERE workflow_id = 3003;
