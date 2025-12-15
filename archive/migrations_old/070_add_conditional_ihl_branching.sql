-- Migration 070: Add Conditional IHL Branching to Workflow 3001
-- ================================================================
-- Purpose: Make workflow 3001 skip IHL scoring if posting already has IHL score
--          This optimizes batch processing by avoiding redundant LLM calls
--
-- Architecture:
--   Format Standardization (conv 8)
--     ↓
--   Save Summary + Check IHL (NEW conv 8.5 - script actor)
--     ↓
--   [HAS_IHL] → TERMINAL (skip everything, end workflow)
--     ↓
--   [NO_IHL] → Taxonomy Skills Extraction (conv 9)
--     ↓
--   ... continues to IHL scoring (conv 13-15) if needed
--
-- Benefits:
--   - Batch summary extraction: ~40s/posting instead of ~70s (30s savings)
--   - Idempotent workflow: Can safely re-run on any posting
--   - Clean architecture: Branching logic in database, not hardcoded
--
-- Author: Arden & xai
-- Date: 2025-11-12

BEGIN;

-- Step 1: Create script actor for save_summary_and_check_ihl.py
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    url,
    enabled
) VALUES (
    'summary_saver_ihl_checker',
    'script',
    'python_script',
    'tools/save_summary_and_check_ihl.py',
    'file://tools/save_summary_and_check_ihl.py',
    true
)
RETURNING actor_id;

-- Note: Capture the actor_id returned above, then use it in the next step
-- For migration script, we'll query it

-- Step 2: Create conversation for summary saving + IHL checking
-- This conversation runs AFTER Format Standardization (execution_order=8)
-- and BEFORE Taxonomy Skills Extraction (execution_order=9)
INSERT INTO conversations (
    conversation_name,
    canonical_name,
    actor_id
) VALUES (
    'Save Summary and Check IHL Status',
    'save_summary_check_ihl',
    (SELECT actor_id FROM actors WHERE actor_name = 'summary_saver_ihl_checker')
)
RETURNING conversation_id;

-- Step 3: Create instruction for the conversation
-- The prompt_template passes the formatted summary (from session 8) and posting_id to the script
INSERT INTO instructions (
    conversation_id,
    instruction_name,
    prompt_template,
    step_number,
    timeout_seconds,
    delegate_actor_id,
    is_terminal,
    enabled
) VALUES (
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'save_summary_check_ihl'),
    'Save Summary and Check IHL',
    '{
  "posting_id": {posting_id},
  "summary": "{session_8_output}"
}',
    1,
    30,  -- Script execution is fast
    NULL,  -- No delegation needed (script actor runs directly)
    false,  -- Not terminal - we branch based on output
    true
)
RETURNING instruction_id;

-- Step 4: Add to workflow 3001 between conversations 8 and 9
-- Strategy: Shift execution_order using temporary offset to avoid unique constraint violations
-- First, shift all conversations >= 9 to temporary range (1000+)
UPDATE workflow_conversations
SET execution_order = execution_order + 1000
WHERE workflow_id = 3001
  AND execution_order >= 9;

-- Now insert the new conversation at position 9
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    step_id,
    execution_order,
    enabled
) VALUES (
    3001,
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'save_summary_check_ihl'),
    (SELECT COALESCE(MAX(step_id), 0) + 1 FROM workflow_conversations WHERE workflow_id = 3001),
    9,  -- Insert between old 8 and old 9
    true
);

-- Finally, shift the temporary range back down (1000+ → actual positions)
UPDATE workflow_conversations
SET execution_order = execution_order - 1000 + 1
WHERE workflow_id = 3001
  AND execution_order >= 1000;

-- Step 5: Add instruction_steps for conditional branching
-- [HAS_IHL] → TERMINAL (end workflow, skip everything else)
-- [NO_IHL] → Continue to conversation 10 (taxonomy skills, formerly conv 9)
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    enabled
) VALUES
    -- Branch 1: HAS_IHL → TERMINAL (highest priority)
    (
        'ihl_gate_has_ihl_terminal',
        (SELECT i.instruction_id FROM instructions i
         JOIN conversations c ON i.conversation_id = c.conversation_id
         WHERE c.canonical_name = 'save_summary_check_ihl'),
        '[HAS_IHL]',
        NULL,  -- NULL = terminal state
        100,
        true
    ),
    -- Branch 2: NO_IHL → Continue to taxonomy skills
    (
        'ihl_gate_no_ihl_continue',
        (SELECT i.instruction_id FROM instructions i
         JOIN conversations c ON i.conversation_id = c.conversation_id
         WHERE c.canonical_name = 'save_summary_check_ihl'),
        '[NO_IHL]',
        (SELECT conversation_id FROM conversations WHERE canonical_name = 'taxonomy_skill_extraction' LIMIT 1),
        50,
        true
    );

-- Step 6: Verification queries
DO $$
DECLARE
    v_actor_count INT;
    v_conv_count INT;
    v_workflow_conv_count INT;
    v_instruction_step_count INT;
    v_new_execution_order INT;
BEGIN
    -- Count new actor
    SELECT COUNT(*) INTO v_actor_count
    FROM actors
    WHERE actor_name = 'summary_saver_ihl_checker';
    
    -- Count new conversation
    SELECT COUNT(*) INTO v_conv_count
    FROM conversations
    WHERE canonical_name = 'save_summary_check_ihl';
    
    -- Count workflow_conversations (should be 16 now, was 15)
    SELECT COUNT(*) INTO v_workflow_conv_count
    FROM workflow_conversations
    WHERE workflow_id = 3001;
    
    -- Count instruction_steps for branching
    SELECT COUNT(*) INTO v_instruction_step_count
    FROM instruction_steps ist
    JOIN instructions i ON ist.instruction_id = i.instruction_id
    JOIN conversations c ON i.conversation_id = c.conversation_id
    WHERE c.canonical_name = 'save_summary_check_ihl';
    
    -- Check execution_order of new conversation
    SELECT execution_order INTO v_new_execution_order
    FROM workflow_conversations wc
    JOIN conversations c ON wc.conversation_id = c.conversation_id
    WHERE wc.workflow_id = 3001
      AND c.canonical_name = 'save_summary_check_ihl';
    
    RAISE NOTICE '===== Migration 070 Verification =====';
    RAISE NOTICE 'Actor created: % (expected: 1)', v_actor_count;
    RAISE NOTICE 'Conversation created: % (expected: 1)', v_conv_count;
    RAISE NOTICE 'Total workflow conversations: % (expected: 16, was 15)', v_workflow_conv_count;
    RAISE NOTICE 'Instruction steps (branches): % (expected: 2)', v_instruction_step_count;
    RAISE NOTICE 'New conversation execution_order: % (expected: 9)', v_new_execution_order;
    RAISE NOTICE '=====================================';
    
    IF v_actor_count != 1 OR v_conv_count != 1 OR v_workflow_conv_count != 16 OR 
       v_instruction_step_count != 2 OR v_new_execution_order != 9 THEN
        RAISE EXCEPTION 'Migration verification failed! Check output above.';
    END IF;
END $$;

COMMIT;

-- Post-migration verification
-- Show new workflow structure around the branching point
SELECT 
    wc.execution_order,
    c.conversation_name,
    c.canonical_name,
    wc.enabled,
    CASE WHEN c.canonical_name = 'save_summary_check_ihl' THEN '← NEW' ELSE '' END as marker
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
WHERE wc.workflow_id = 3001
  AND wc.execution_order BETWEEN 7 AND 12
ORDER BY wc.execution_order;
