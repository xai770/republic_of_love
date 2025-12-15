-- Migration 065: Build Workflow 2001 - Job Ingestion Pipeline
-- Reuses existing conversations from workflows 1121 (skills) and 1124 (IHL)
-- 
-- Author: Arden
-- Date: 2025-11-07

BEGIN;

-- Step 1: Link existing conversations to Workflow 2001
DO $$
DECLARE
    v_conv_skills INTEGER;
    v_conv_ihl INTEGER;
BEGIN
    -- Get conversation IDs
    SELECT conversation_id INTO v_conv_skills 
    FROM conversations 
    WHERE canonical_name = 'gopher_skill_extraction';
    
    SELECT conversation_id INTO v_conv_ihl 
    FROM conversations 
    WHERE conversation_name = 'Fake Job Detector Debate';
    
    -- Clear any existing links
    DELETE FROM workflow_conversations WHERE workflow_id = 2001;
    
    -- Link conversations to Workflow 2001
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES 
        -- Step 1: Extract skills from job description
        (2001, v_conv_skills, 10, 'always', 'continue', 'stop', 1),
        
        -- Step 2: Calculate IHL (fake job likelihood)
        (2001, v_conv_ihl, 20, 'always', 'continue', 'stop', 1);
    
    RAISE NOTICE 'Linked conversations to Workflow 2001:';
    RAISE NOTICE '  - Skills Extraction (conversation_id=%)', v_conv_skills;
    RAISE NOTICE '  - IHL Calculator (conversation_id=%)', v_conv_ihl;
END $$;

-- Step 2: Register placeholders for Workflow 2001
-- Input: job_description text
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'job_description',
    'test_case_data',
    true,
    'Job description text for Workflow 2001 (from postings.job_description)'
)
ON CONFLICT (placeholder_name) DO UPDATE SET
    description = EXCLUDED.description;

-- Output from conversation 1 (skills)
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r10_output',
    'dialogue_output',
    false,
    'Skills extraction output from execution_order=10 (JSON array of skills)'
)
ON CONFLICT (placeholder_name) DO NOTHING;

-- Output from conversation 2 (IHL)
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r20_output',
    'dialogue_output',
    false,
    'IHL calculation output from execution_order=20 (IHL score and reasoning)'
)
ON CONFLICT (placeholder_name) DO NOTHING;

-- Map variations_param_1 to job_description for backward compatibility
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'variations_param_1',
    'test_case_data',
    true,
    'Legacy placeholder - maps to job_description for backward compatibility with Recipe 1121'
)
ON CONFLICT (placeholder_name) DO UPDATE SET
    description = EXCLUDED.description;

-- Step 3: Enable Workflow 2001
UPDATE workflows 
SET enabled = true,
    workflow_description = 'Job Ingestion Pipeline: Extract skills (1121) → Calculate IHL (1124) → Save results'
WHERE workflow_id = 2001;

COMMIT;

-- Verification
\echo '=== Workflow 2001 Structure ==='
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
\echo '=== Registered Placeholders ==='
SELECT 
    placeholder_name,
    source_type,
    is_required,
    description
FROM placeholder_definitions
WHERE placeholder_name IN ('job_description', 'variations_param_1', 'session_r10_output', 'session_r20_output')
ORDER BY placeholder_name;
