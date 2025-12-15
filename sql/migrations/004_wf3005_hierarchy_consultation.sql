-- Migration: Create WF3005 (Hierarchy Consultation)
-- Purpose: Batch categorize orphan skills with grader pattern
-- Date: 2025-12-07
-- Author: Sandy (per Arden's design)

BEGIN;

-- ============================================================================
-- STEP 1: Create the Workflow
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
    3005,
    'Hierarchy Consultation',
    'Batch categorize orphan skills using classifier + grader pattern. Writes decisions to registry_decisions for human QA.',
    200,
    true,
    'talent',
    'dev'
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

-- ============================================================================
-- STEP 2: Create Conversations (without ON CONFLICT)
-- ============================================================================

DO $$
DECLARE
    v_actor_qwen INTEGER := 45;      -- qwen2.5:7b
    v_actor_mistral INTEGER := 23;   -- mistral:latest
    v_actor_fetcher INTEGER;
    v_actor_saver INTEGER;
    v_conv_fetcher INTEGER;
    v_conv_classifier INTEGER;
    v_conv_grader INTEGER;
    v_conv_saver INTEGER;
BEGIN
    -- Get script actor IDs
    SELECT actor_id INTO v_actor_fetcher FROM actors WHERE actor_name = 'orphan_skills_fetcher';
    SELECT actor_id INTO v_actor_saver FROM actors WHERE actor_name = 'hierarchy_applier';

    -- Check for existing conversations and delete if re-running
    DELETE FROM workflow_conversations WHERE workflow_id = 3005;
    DELETE FROM instructions WHERE conversation_id IN (
        SELECT conversation_id FROM conversations WHERE canonical_name LIKE 'w3005_%'
    );
    DELETE FROM conversations WHERE canonical_name LIKE 'w3005_%';

    -- Conversation 1: Orphan Skill Fetcher (Script)
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3005_fetch_orphan_skills',
        'w3005_c1_fetch',
        'Fetch next batch of 25 orphan skills from entities table',
        v_actor_fetcher,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_fetcher;

    -- Conversation 2: Skill Classifier (qwen2.5:7b)
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3005_classify_skills',
        'w3005_c2_classify',
        'Categorize batch of orphan skills into domains with reasoning',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_classifier;

    -- Conversation 3: Classification Grader (mistral:latest)
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3005_grade_classifications',
        'w3005_c3_grade',
        'Review classifier decisions, confirm or correct with reasoning',
        v_actor_mistral,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_grader;

    -- Conversation 4: Hierarchy Decision Saver (Script)
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3005_save_decisions',
        'w3005_c4_save',
        'Write decisions to registry_decisions, auto-approve if high confidence + grader agrees',
        v_actor_saver,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_saver;

    -- ============================================================================
    -- STEP 3: Link Conversations to Workflow
    -- ============================================================================

    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES
        (3005, v_conv_fetcher, 1, 'always', 'continue', 'stop', 1),
        (3005, v_conv_classifier, 2, 'always', 'continue', 'stop', 2),
        (3005, v_conv_grader, 3, 'always', 'continue', 'stop', 2),
        (3005, v_conv_saver, 4, 'always', 'continue', 'stop', 1);

    -- ============================================================================
    -- STEP 4: Create Instructions
    -- ============================================================================

    -- Instruction for Classifier
    INSERT INTO instructions (
        instruction_name,
        prompt_template,
        step_number,
        is_terminal,
        conversation_id,
        created_at
    ) VALUES (
        'w3005_classify_orphans',
        'You are a professional skills taxonomy expert. Your task is to categorize orphan skills into the appropriate domain.

CURRENT DOMAINS (choose from these, or prefix with NEW: if none fit):
- Technology (programming, software, infrastructure)
- Data_And_Analytics (data science, BI, statistics)
- Business_Operations (operations, logistics, supply chain)
- People_And_Communication (leadership, teamwork, presentation)
- Compliance_And_Risk (legal, audit, regulatory)
- Project_And_Product (PM, product management, agile)
- Corporate_Culture (DEI, values, ethics)
- Specialized_Knowledge (domain-specific expertise)

SKILLS TO CATEGORIZE:
{orphan_skills}

For EACH skill, output a JSON object on its own line:
{"skill": "skill_name", "parent": "Domain_Name", "confidence": 0.85, "reasoning": "One sentence explanation"}

If no domain fits, use: {"skill": "skill_name", "parent": "NEW:Suggested_Category", "confidence": 0.7, "reasoning": "Why new category needed"}

Output ONLY the JSON objects, one per line. No other text.',
        1,
        true,
        v_conv_classifier,
        now()
    );

    -- Instruction for Grader
    INSERT INTO instructions (
        instruction_name,
        prompt_template,
        step_number,
        is_terminal,
        conversation_id,
        created_at
    ) VALUES (
        'w3005_grade_classifications',
        'You are a senior taxonomy reviewer. A classifier has assigned skills to categories. Review each decision.

CLASSIFIER''S DECISIONS:
{classifier_output}

For EACH decision, output a JSON object:
{"skill": "skill_name", "agree": true, "original_parent": "Technology", "corrected_parent": null, "reasoning": "Agree because..."}

OR if you disagree:
{"skill": "skill_name", "agree": false, "original_parent": "Technology", "corrected_parent": "Data_And_Analytics", "reasoning": "Should be Data_And_Analytics because..."}

Be strict. If the classification is wrong, say so. If you''re unsure, set agree to false and explain.

Output ONLY the JSON objects, one per line. No other text.',
        1,
        true,
        v_conv_grader,
        now()
    );

    RAISE NOTICE 'WF3005 created: fetcher=%, classifier=%, grader=%, saver=%',
        v_conv_fetcher, v_conv_classifier, v_conv_grader, v_conv_saver;

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
    a.actor_name
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE w.workflow_id = 3005
ORDER BY wc.execution_order;
