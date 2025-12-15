-- Migration 066: Add Taxonomy Mapping to Workflow 2001
-- Adds Step 30: Map extracted skills to taxonomy hierarchy
-- 
-- Flow: Skills Extraction (10) → IHL Calculator (20) → Taxonomy Mapping (30)
--
-- Author: GitHub Copilot + xai
-- Date: 2025-11-09

BEGIN;

-- Add Step 30: Map skills to taxonomy using fuzzy matching
-- Uses conversation 9140 (simple_skill_mapper with fuzzy matching)
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order,
    execute_condition,
    on_success_action,
    on_failure_action,
    max_retry_attempts
) VALUES (
    2001,  -- Job Ingestion Pipeline
    9140,  -- conv_1127_step4_map: Taxonomy Mapping with fuzzy matching
    30,    -- After skills extraction (10) and IHL (20)
    'always',
    'continue',
    'continue',  -- Don't stop if taxonomy mapping fails
    1
)
ON CONFLICT (workflow_id, conversation_id) DO UPDATE SET
    execution_order = EXCLUDED.execution_order,
    execute_condition = EXCLUDED.execute_condition,
    on_success_action = EXCLUDED.on_success_action,
    on_failure_action = EXCLUDED.on_failure_action;

-- Update workflow description to reflect new step
UPDATE workflows 
SET workflow_description = 'Job Ingestion Pipeline: Extract skills (1121) → Calculate IHL (1124) → Map to taxonomy hierarchy (fuzzy matching)'
WHERE workflow_id = 2001;

-- Register output placeholder for Step 30
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r30_output',
    'dialogue_output',
    false,
    'Taxonomy mapping output from execution_order=30 (skills mapped to hierarchy with match scores)'
)
ON CONFLICT (placeholder_name) DO UPDATE SET
    description = EXCLUDED.description;

COMMIT;

-- Verification
\echo ''
\echo '=== Updated Workflow 2001 Structure ==='
SELECT 
    w.workflow_id,
    w.workflow_name,
    w.enabled,
    wc.execution_order,
    c.conversation_id,
    c.canonical_name,
    c.conversation_name,
    a.actor_name
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
LEFT JOIN actors a ON c.actor_id = a.actor_id
WHERE w.workflow_id = 2001
ORDER BY wc.execution_order;

\echo ''
\echo '=== Workflow 2001 Flow ==='
\echo 'Step 10: gopher_skill_extraction → Extract skills from job_description'
\echo 'Step 20: IHL Calculator → Detect fake jobs'
\echo 'Step 30: Taxonomy Mapper (simple_skill_mapper) → Map skills to hierarchy with fuzzy matching'
\echo ''
\echo '✅ Workflow 2001 now includes automatic taxonomy categorization!'
\echo '   This uses the fuzzy matching functions from sql/fuzzy_skill_matching.sql'
