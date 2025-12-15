-- Migration 071: Simplify Summary Saver - Remove Dual Concern
-- ============================================================
-- Split summary_saver_ihl_checker into two separate concerns:
-- 1. Step 10: Save summary only (new summary_saver script)
-- 2. Step 16: Check IHL exists (already using SQL - instruction 3401)
--
-- This removes the confusing dual-purpose actor and relies on
-- SQL-based idempotency checks throughout the workflow.
--
-- Author: xai & Arden
-- Date: 2025-11-14

BEGIN;

-- 1. Create new simple summary_saver actor
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    url,
    enabled,
    script_version
) VALUES (
    'summary_saver',
    'script',
    'python_script',
    'tools/save_summary.py',
    'file://tools/save_summary.py',
    true,
    1
);

-- 2. Update conversation to use new actor
UPDATE conversations
SET actor_id = (SELECT actor_id FROM actors WHERE actor_name = 'summary_saver')
WHERE conversation_name = 'Save Summary and Check IHL Status';

-- 4. Update instruction branches (do BEFORE renaming conversation)
DO $$
DECLARE
    v_instruction_id INTEGER;
    v_save_branch_id INTEGER;
    v_failed_branch_id INTEGER;
    v_next_conv_id INTEGER;  -- Step 11 (check_skills_exist)
BEGIN
    -- Get instruction ID (using OLD conversation name)
    SELECT i.instruction_id INTO v_instruction_id
    FROM instructions i
    JOIN conversations c ON i.conversation_id = c.conversation_id
    WHERE c.conversation_name = 'Save Summary and Check IHL Status';
    
    IF v_instruction_id IS NULL THEN
        RAISE EXCEPTION 'Could not find instruction for Save Summary and Check IHL Status';
    END IF;
    
    -- Get Step 11 conversation ID (skills check)
    SELECT conversation_id INTO v_next_conv_id
    FROM conversations
    WHERE conversation_name = 'Check if Skills Exist';
    
    IF v_next_conv_id IS NULL THEN
        RAISE EXCEPTION 'Could not find conversation check_skills_exist';
    END IF;
    
    -- Delete old branches (HAS_IHL, NO_IHL)
    DELETE FROM instruction_steps
    WHERE instruction_id = v_instruction_id;
    
    -- Create new simple branches:
    -- [SAVED] → Step 11 (check skills)
    INSERT INTO instruction_steps (
        instruction_id,
        instruction_step_name,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        v_instruction_id,
        'summary_saved',
        '[SAVED]',
        v_next_conv_id,
        100
    );
    
    -- [FAILED] → TERMINAL (error)
    INSERT INTO instruction_steps (
        instruction_id,
        instruction_step_name,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        v_instruction_id,
        'save_failed',
        '[FAILED]',
        NULL,  -- TERMINAL
        50
    );
    
    RAISE NOTICE 'Updated Step 10 branches: [SAVED] → Step 11, [FAILED] → TERMINAL';
END $$;

-- 3. Rename the conversation to reflect its new single purpose (do AFTER branch updates)
UPDATE conversations
SET conversation_name = 'Save Summary'
WHERE conversation_name = 'Save Summary and Check IHL Status';

-- 5. Disable old actor (keep for historical reference)
UPDATE actors
SET enabled = false
WHERE actor_name = 'summary_saver_ihl_checker';

COMMIT;

-- Verification
SELECT 
    wc.execution_order as step,
    c.conversation_name,
    a.actor_name,
    a.actor_type,
    s.branch_condition,
    nc.conversation_name as next_step
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN instructions i ON c.conversation_id = i.conversation_id
LEFT JOIN instruction_steps s ON i.instruction_id = s.instruction_id
LEFT JOIN conversations nc ON s.next_conversation_id = nc.conversation_id
WHERE wc.workflow_id = 3001
  AND wc.execution_order IN (10, 11, 16)
ORDER BY wc.execution_order, s.branch_priority DESC;
