/*
 * Migration 046: Fix Skills and IHL Score Routing
 * 
 * Issue: Skills and IHL scores extracted but not saved to postings table
 * Root cause: Workflow routing skips save conversations
 * 
 * Fixes:
 * 1. Update r1114_extract_skills → Save Skills (9141) instead of → IHL Analyst
 * 2. Update Save Skills (9141) → IHL Analyst (9161)
 * 3. Create IHL Score Saver conversation using existing actor (82)
 * 4. Update IHL HR Expert → Save IHL Score
 * 5. Add both savers to workflow_conversations
 * 
 * Author: Arden (GitHub Copilot)
 * Date: November 27, 2025
 */

BEGIN;

-- ============================================================================
-- PART 1: Fix Skills Routing
-- ============================================================================

-- Step 1.1: Update Extract Skills → Save Skills
UPDATE instruction_steps
SET next_conversation_id = 9141  -- Save Skills (skill_saver)
WHERE instruction_id = (
    SELECT instruction_id FROM instructions WHERE conversation_id = 3350  -- r1114_extract_skills
)
AND branch_condition = '*';

-- Verify routing from Extract Skills
SELECT 
    c1.conversation_name as from_conversation,
    ws.branch_condition,
    c2.conversation_name as to_conversation
FROM instruction_steps ws
JOIN instructions i ON ws.instruction_id = i.instruction_id
JOIN conversations c1 ON i.conversation_id = c1.conversation_id
LEFT JOIN conversations c2 ON ws.next_conversation_id = c2.conversation_id
WHERE c1.conversation_id = 3350;
-- Should show: r1114_extract_skills → Save Skills (skill_saver)

-- Step 1.2: Update Save Skills → IHL Analyst (if not already set)
UPDATE instruction_steps
SET next_conversation_id = 9161  -- IHL Analyst
WHERE instruction_id = (
    SELECT instruction_id FROM instructions WHERE conversation_id = 9141  -- Save Skills
)
AND (next_conversation_id IS NULL OR next_conversation_id != 9161);

-- If instruction_step doesn't exist for Save Skills, create it
INSERT INTO instruction_steps (
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority
)
SELECT 
    instruction_id,
    '*',
    9161,  -- IHL Analyst
    10
FROM instructions
WHERE conversation_id = 9141  -- Save Skills
AND NOT EXISTS (
    SELECT 1 FROM instruction_steps 
    WHERE instruction_id = instructions.instruction_id
);

-- Step 1.3: Add Save Skills to workflow_conversations (if not already there)
INSERT INTO workflow_conversations (workflow_id, conversation_id, execution_order)
SELECT 3001, 9141, 11.5
WHERE NOT EXISTS (
    SELECT 1 FROM workflow_conversations 
    WHERE workflow_id = 3001 AND conversation_id = 9141
);

-- ============================================================================
-- PART 2: Fix IHL Score Routing
-- ============================================================================

-- Step 2.1: Create "Save IHL Score" conversation using existing actor
INSERT INTO conversations (conversation_name, actor_id, conversation_description)
VALUES (
    'Save IHL Score and Category',
    82,  -- ihl_score_saver_v2
    'Writes IHL score and verdict to postings.ihl_score and postings.ihl_category'
)
RETURNING conversation_id;  -- Will be auto-assigned, let's call it :ihl_save_conv_id

-- Note: In psql, use \gset to capture the ID:
-- RETURNING conversation_id \gset ihl_save_

-- Step 2.2: Create instruction for Save IHL Score
-- (Replace :ihl_save_conv_id with actual ID from previous step)
INSERT INTO instructions (conversation_id, instruction_name, step_number, prompt_template)
SELECT 
    conversation_id,
    'Save IHL analysis to database',
    1,
    '{}'  -- No prompt needed, script reads from parent
FROM conversations
WHERE conversation_name = 'Save IHL Score and Category'
AND actor_id = 82;

-- Step 2.3: Update IHL HR Expert → Save IHL Score
-- First, try to update existing routing (if it exists)
UPDATE instruction_steps
SET next_conversation_id = (
    SELECT conversation_id FROM conversations 
    WHERE conversation_name = 'Save IHL Score and Category'
)
WHERE instruction_id = (
    SELECT instruction_id FROM instructions WHERE conversation_id = 9163  -- IHL HR Expert
)
AND branch_condition = '*';

-- If no instruction_step exists, create it
INSERT INTO instruction_steps (
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority
)
SELECT 
    i.instruction_id,
    '*',
    c.conversation_id,  -- Save IHL Score
    10
FROM instructions i
CROSS JOIN conversations c
WHERE i.conversation_id = 9163  -- IHL HR Expert
  AND c.conversation_name = 'Save IHL Score and Category'
  AND NOT EXISTS (
      SELECT 1 FROM instruction_steps 
      WHERE instruction_id = i.instruction_id
  );

-- Step 2.4: Add Save IHL Score to workflow_conversations
INSERT INTO workflow_conversations (workflow_id, conversation_id, execution_order)
SELECT 
    3001,
    conversation_id,
    22  -- After IHL HR Expert (21)
FROM conversations
WHERE conversation_name = 'Save IHL Score and Category'
AND NOT EXISTS (
    SELECT 1 FROM workflow_conversations wc
    WHERE wc.workflow_id = 3001 
      AND wc.conversation_id = conversations.conversation_id
);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify Skills routing
SELECT 
    'Skills Routing' as check_type,
    c1.conversation_name as from_conversation,
    c2.conversation_name as to_conversation
FROM instruction_steps ws
JOIN instructions i ON ws.instruction_id = i.instruction_id
JOIN conversations c1 ON i.conversation_id = c1.conversation_id
LEFT JOIN conversations c2 ON ws.next_conversation_id = c2.conversation_id
WHERE c1.conversation_id IN (3350, 9141)  -- Extract Skills, Save Skills
ORDER BY c1.conversation_id;

-- Verify IHL routing
SELECT 
    'IHL Routing' as check_type,
    c1.conversation_name as from_conversation,
    c2.conversation_name as to_conversation
FROM instruction_steps ws
JOIN instructions i ON ws.instruction_id = i.instruction_id
JOIN conversations c1 ON i.conversation_id = c1.conversation_id
LEFT JOIN conversations c2 ON ws.next_conversation_id = c2.conversation_id
WHERE c1.conversation_id = 9163  -- IHL HR Expert
   OR c1.conversation_name = 'Save IHL Score and Category';

-- Verify both savers in workflow_conversations
SELECT 
    'Workflow Conversations' as check_type,
    wc.execution_order,
    c.conversation_name
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
WHERE wc.workflow_id = 3001
  AND (c.conversation_id = 9141 OR c.conversation_name = 'Save IHL Score and Category')
ORDER BY wc.execution_order;

-- Expected results:
-- Skills: r1114_extract_skills → Save Skills → IHL Analyst
-- IHL: IHL HR Expert → Save IHL Score → (end)
-- Both savers in workflow_conversations with correct execution_order

COMMIT;

-- ============================================================================
-- POST-MIGRATION TEST
-- ============================================================================

-- Run after committing to verify the fix works:
-- 
-- 1. Run 1 posting through workflow
-- 2. Check postings table:
--    SELECT posting_id, 
--           skill_keywords IS NOT NULL as has_skills,
--           ihl_score IS NOT NULL as has_score,
--           ihl_category
--    FROM postings 
--    WHERE posting_id = <test_posting_id>;
--
-- 3. Expected: both has_skills and has_score = TRUE
