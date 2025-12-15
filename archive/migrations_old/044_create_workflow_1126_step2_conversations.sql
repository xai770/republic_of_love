-- ============================================================================
-- Migration 044: Create Workflow 1126 - Step 2: Conversations
-- ============================================================================
-- Purpose: Create 4 conversations and link them to Workflow 1126
-- Follows: WORKFLOW_CREATION_COOKBOOK.md Step 2
-- ============================================================================

BEGIN;

DO $$
DECLARE
    v_actor_qwen INTEGER;
    v_actor_gemma INTEGER;
    v_actor_gopher INTEGER;
    v_conv_extract INTEGER;
    v_conv_validate INTEGER;
    v_conv_import INTEGER;
    v_conv_error INTEGER;
BEGIN
    -- Get actor IDs
    SELECT actor_id INTO v_actor_qwen FROM actors WHERE actor_name = 'qwen2.5:7b' LIMIT 1;
    SELECT actor_id INTO v_actor_gemma FROM actors WHERE actor_name = 'gemma2:latest' LIMIT 1;
    SELECT actor_id INTO v_actor_gopher FROM actors WHERE actor_name = 'taxonomy_gopher' LIMIT 1;

    -- Validate actors exist
    IF v_actor_qwen IS NULL THEN
        RAISE EXCEPTION 'Actor qwen2.5:7b not found';
    END IF;
    IF v_actor_gemma IS NULL THEN
        RAISE EXCEPTION 'Actor gemma2:latest not found';
    END IF;
    IF v_actor_gopher IS NULL THEN
        RAISE EXCEPTION 'Actor taxonomy_gopher not found';
    END IF;

    -- Conversation 1: Extract Profile Data
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        max_instruction_runs,
        enabled
    ) VALUES (
        'w1126_extract_profile_data',
        'w1126_c1_extract',
        'Parse document and extract structured profile data (work history, education, skills, languages) into JSON format',
        v_actor_qwen,
        'single_actor',
        'isolated',
        5,
        true
    )
    RETURNING conversation_id INTO v_conv_extract;

    RAISE NOTICE 'Created conversation 1: extract (id=%)', v_conv_extract;

    -- Conversation 2: Validate Extracted Data
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        max_instruction_runs,
        enabled
    ) VALUES (
        'w1126_validate_profile_data',
        'w1126_c2_validate',
        'Independent validation of extracted profile data. Check required fields, date formats, data quality. Provide corrections if needed.',
        v_actor_gemma,
        'single_actor',
        'isolated',
        5,
        true
    )
    RETURNING conversation_id INTO v_conv_validate;

    RAISE NOTICE 'Created conversation 2: validate (id=%)', v_conv_validate;

    -- Conversation 3: Import to Database
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        max_instruction_runs,
        enabled
    ) VALUES (
        'w1126_import_to_database',
        'w1126_c3_import',
        'Merge validated data and insert into profiles, profile_work_history, profile_languages, profile_education tables. Returns profile_id.',
        v_actor_gopher,
        'single_actor',
        'isolated',
        5,
        true
    )
    RETURNING conversation_id INTO v_conv_import;

    RAISE NOTICE 'Created conversation 3: import (id=%)', v_conv_import;

    -- Conversation 4: Error Handling
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        max_instruction_runs,
        enabled
    ) VALUES (
        'w1126_generate_error_report',
        'w1126_c4_error',
        'Generate human-readable error report when extraction/validation/import fails',
        v_actor_qwen,
        'single_actor',
        'isolated',
        5,
        true
    )
    RETURNING conversation_id INTO v_conv_error;

    RAISE NOTICE 'Created conversation 4: error (id=%)', v_conv_error;

    -- Link conversations to workflow (defines execution order)
    DELETE FROM workflow_conversations WHERE workflow_id = 1126;
    
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES 
        (1126, v_conv_extract, 1, 'always', 'continue', 'stop', 1),
        (1126, v_conv_validate, 2, 'always', 'continue', 'stop', 1),
        (1126, v_conv_import, 3, 'always', 'continue', 'stop', 1),
        (1126, v_conv_error, 4, 'always', 'stop', 'stop', 1);

    RAISE NOTICE '✅ Step 2 Complete: 4 conversations created and linked to Workflow 1126';
END $$;

COMMIT;

-- ============================================================================
-- Verification Step 2
-- ============================================================================
SELECT 
    w.workflow_id,
    w.workflow_name,
    wc.execution_order,
    c.conversation_id,
    c.conversation_name,
    c.canonical_name,
    a.actor_name
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE w.workflow_id = 1126
ORDER BY wc.execution_order;
