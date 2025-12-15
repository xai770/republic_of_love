-- Migration: Wire WF3006 Entity Classification
-- Purpose: Create workflow, conversations, instructions, and actors for skill classification
-- Date: 2025-12-15
-- Author: Arden

BEGIN;

-- ============================================================================
-- STEP 1: Create Actors (Script Actors)
-- ============================================================================

-- Check if actors exist, create if not
DO $$
BEGIN
    -- orphan_fetcher_v2
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'orphan_fetcher_v2') THEN
        INSERT INTO actors (actor_name, actor_type, execution_type, script_file_path, url, enabled)
        VALUES ('orphan_fetcher_v2', 'script', 'python_script', 
                'core/wave_runner/actors/orphan_fetcher_v2.py', 'local://script', true);
    END IF;
    
    -- classification_saver
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'classification_saver') THEN
        INSERT INTO actors (actor_name, actor_type, execution_type, script_file_path, url, enabled)
        VALUES ('classification_saver', 'script', 'python_script',
                'core/wave_runner/actors/classification_saver.py', 'local://script', true);
    END IF;
    
    -- classification_applier
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'classification_applier') THEN
        INSERT INTO actors (actor_name, actor_type, execution_type, script_file_path, url, enabled)
        VALUES ('classification_applier', 'script', 'python_script',
                'core/wave_runner/actors/classification_applier.py', 'local://script', true);
    END IF;
    
    -- classification_resetter
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'classification_resetter') THEN
        INSERT INTO actors (actor_name, actor_type, execution_type, script_file_path, url, enabled)
        VALUES ('classification_resetter', 'script', 'python_script',
                'core/wave_runner/actors/classification_resetter.py', 'local://script', true);
    END IF;
    
    -- domain_creator
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'domain_creator') THEN
        INSERT INTO actors (actor_name, actor_type, execution_type, script_file_path, url, enabled)
        VALUES ('domain_creator', 'script', 'python_script',
                'core/wave_runner/actors/domain_creator.py', 'local://script', true);
    END IF;
    
    -- debate_panel
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'debate_panel') THEN
        INSERT INTO actors (actor_name, actor_type, execution_type, script_file_path, url, enabled)
        VALUES ('debate_panel', 'script', 'python_script',
                'core/wave_runner/actors/debate_panel.py', 'local://script', true);
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Create the Workflow
-- ============================================================================

INSERT INTO workflows (
    workflow_id,
    workflow_name,
    workflow_description,
    max_total_session_runs,
    enabled,
    app_scope,
    environment
) VALUES (
    3006,
    'Entity Classification',
    'Classify orphan skills into domains using debate panel (classifier/challenger/judge). Stores reasoning for learning.',
    1000,
    true,
    'talent',
    'dev'
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

-- ============================================================================
-- STEP 3: Create Conversations
-- ============================================================================

DO $$
DECLARE
    v_actor_gemma INTEGER;
    v_actor_qwen INTEGER;
    v_actor_fetcher INTEGER;
    v_actor_saver INTEGER;
    v_actor_applier INTEGER;
    v_actor_debate INTEGER;
    v_actor_domain_creator INTEGER;
    
    v_conv_fetch INTEGER;
    v_conv_classify INTEGER;
    v_conv_debate INTEGER;
    v_conv_save INTEGER;
    v_conv_apply INTEGER;
    v_conv_check_more INTEGER;
BEGIN
    -- Get AI actor IDs
    SELECT actor_id INTO v_actor_gemma FROM actors WHERE actor_name = 'gemma3:4b';
    SELECT actor_id INTO v_actor_qwen FROM actors WHERE actor_name = 'qwen2.5:7b';
    
    -- Get script actor IDs
    SELECT actor_id INTO v_actor_fetcher FROM actors WHERE actor_name = 'orphan_fetcher_v2';
    SELECT actor_id INTO v_actor_saver FROM actors WHERE actor_name = 'classification_saver';
    SELECT actor_id INTO v_actor_applier FROM actors WHERE actor_name = 'classification_applier';
    SELECT actor_id INTO v_actor_debate FROM actors WHERE actor_name = 'debate_panel';
    SELECT actor_id INTO v_actor_domain_creator FROM actors WHERE actor_name = 'domain_creator';
    
    -- Clean up existing (if re-running)
    DELETE FROM workflow_conversations WHERE workflow_id = 3006;
    DELETE FROM instructions WHERE conversation_id IN (
        SELECT conversation_id FROM conversations WHERE canonical_name LIKE 'w3006_%'
    );
    DELETE FROM conversations WHERE canonical_name LIKE 'w3006_%';

    -- ========================================================================
    -- C1: Fetch Orphan Skills
    -- ========================================================================
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3006_fetch_orphans',
        'w3006_c1_fetch',
        'Fetch batch of orphan skills with history and similar skills',
        v_actor_fetcher,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_fetch;

    -- ========================================================================
    -- C2: Classify Skills (gemma3:4b)
    -- ========================================================================
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3006_classify_skills',
        'w3006_c2_classify',
        'Classify orphan skills into domains using dynamic domain list',
        v_actor_gemma,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_classify;

    -- ========================================================================
    -- C3: Debate Panel (low confidence only)
    -- ========================================================================
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3006_debate_classification',
        'w3006_c3_debate',
        'Challenge and defend low-confidence classifications',
        v_actor_debate,
        'single_actor',
        'inherit_previous',
        true
    ) RETURNING conversation_id INTO v_conv_debate;

    -- ========================================================================
    -- C4: Save Decisions
    -- ========================================================================
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3006_save_decisions',
        'w3006_c4_save',
        'Save classification decisions and reasoning to database',
        v_actor_saver,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_save;

    -- ========================================================================
    -- C5: Apply Approved Decisions
    -- ========================================================================
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3006_apply_decisions',
        'w3006_c5_apply',
        'Create entity_relationships for auto_approved decisions',
        v_actor_applier,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_apply;

    -- ========================================================================
    -- C6: Check for More Orphans (Loop Control)
    -- ========================================================================
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3006_check_more',
        'w3006_c6_check_more',
        'Check if more orphans remain for continuous processing',
        v_actor_fetcher,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_check_more;

    -- ========================================================================
    -- Link Conversations to Workflow
    -- ========================================================================
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES
        (3006, v_conv_fetch, 1, 'always', 'continue', 'stop', 1),
        (3006, v_conv_classify, 2, 'always', 'continue', 'stop', 2),
        (3006, v_conv_debate, 3, 'always', 'continue', 'skip_to', 1),  -- Skip to save on debate failure
        (3006, v_conv_save, 4, 'always', 'continue', 'stop', 1),
        (3006, v_conv_apply, 5, 'always', 'continue', 'retry', 1),
        (3006, v_conv_check_more, 6, 'on_success', 'continue', 'stop', 1);  -- Check for more on success

    -- ========================================================================
    -- Create Instructions
    -- ========================================================================

    -- Instruction for C2: Classify
    INSERT INTO instructions (
        instruction_name,
        prompt_template,
        step_number,
        is_terminal,
        conversation_id,
        timeout_seconds,
        created_at
    ) VALUES (
        'w3006_classify_prompt',
        'You are a skill classification expert. Classify each skill into EXACTLY ONE domain.

{domains_text}

For each skill, respond with a JSON object on its own line:
{"entity_id": <id>, "action": "CLASSIFY", "domain": "<domain_name>", "confidence": 0.XX, "reasoning": "brief reason"}

If no domain fits well (confidence < 0.6 for all), use:
{"entity_id": <id>, "action": "NEW_DOMAIN", "suggested_domain_name": "<name>", "confidence": 0.XX, "reasoning": "why new domain needed"}

SKILLS TO CLASSIFY:
{skills_text}

Respond with one JSON object per skill, one per line. No markdown, no extra text.',
        1,
        true,
        v_conv_classify,
        120,
        now()
    );

    RAISE NOTICE 'WF3006 created with conversations: fetch=%, classify=%, debate=%, save=%, apply=%, check=%',
        v_conv_fetch, v_conv_classify, v_conv_debate, v_conv_save, v_conv_apply, v_conv_check_more;

END $$;

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 
    w.workflow_id,
    w.workflow_name,
    wc.execution_order,
    c.conversation_id,
    c.canonical_name,
    a.actor_name,
    wc.execute_condition
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE w.workflow_id = 3006
ORDER BY wc.execution_order;
