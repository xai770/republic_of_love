/*
 * Migration 047: Create Posting Skills Saver Actor and Fix Routing
 * 
 * Issue: Migration 046 used wrong actor (skill_saver #49 is for PROFILES, not POSTINGS)
 * Root cause: Actor 49 saves to profile_skills table, but we need posting_skills table
 * 
 * Solution:
 * 1. Register new actor: posting_skills_saver
 * 2. Create new conversation using this actor
 * 3. Update routing to use correct conversation
 * 4. Rollback Migration 046's incorrect changes
 * 
 * Author: Arden (GitHub Copilot)
 * Date: November 27, 2025
 */

BEGIN;

-- ============================================================================
-- PART 0: Rollback Migration 046 (Wrong Actor)
-- ============================================================================

-- Revert Extract Skills routing (back to going directly to IHL Analyst)
UPDATE instruction_steps
SET next_conversation_id = 9161  -- IHL Analyst - Find Red Flags
WHERE instruction_id = (
    SELECT instruction_id FROM instructions WHERE conversation_id = 3350  -- r1114_extract_skills
)
AND branch_condition = '*';

-- Remove the incorrect Save Skills conversation from workflow
DELETE FROM workflow_conversations
WHERE workflow_id = 3001 
  AND conversation_id = 9141;  -- Save Skills (skill_saver - WRONG ACTOR)

-- Note: We keep conversation 9141 in case it's used for profile workflows
-- We just won't use it in workflow 3001 anymore

-- ============================================================================
-- PART 1: Register Posting Skills Saver Actor
-- ============================================================================

-- Insert new actor for posting skills
INSERT INTO actors (actor_name, actor_description)
VALUES (
    'posting_skills_saver',
    'Saves extracted skills from job postings to posting_skills table and postings.skill_keywords'
)
ON CONFLICT (actor_name) DO NOTHING
RETURNING actor_id;
-- Expected: New actor_id (probably 83 or next available)

-- Verify actor was created
SELECT actor_id, actor_name 
FROM actors 
WHERE actor_name = 'posting_skills_saver';

-- ============================================================================
-- PART 2: Create Save Posting Skills Conversation
-- ============================================================================

-- Create conversation using the new actor
INSERT INTO conversations (conversation_name, actor_id, conversation_description, model_used, temperature)
SELECT 
    'Save Posting Skills',
    actor_id,
    'Saves extracted skills to posting_skills table and postings.skill_keywords field',
    NULL,  -- Script actor, no model needed
    NULL
FROM actors
WHERE actor_name = 'posting_skills_saver'
ON CONFLICT DO NOTHING
RETURNING conversation_id;
-- Expected: New conversation_id

-- Create instruction for this conversation
INSERT INTO instructions (conversation_id, instruction_name, step_number, prompt_template)
SELECT 
    c.conversation_id,
    'Save skills to posting_skills table',
    1,
    '{}'  -- No prompt needed - script reads from conversation 3350
FROM conversations c
JOIN actors a ON c.actor_id = a.actor_id
WHERE a.actor_name = 'posting_skills_saver'
  AND NOT EXISTS (
      SELECT 1 FROM instructions WHERE conversation_id = c.conversation_id
  );

-- ============================================================================
-- PART 3: Fix Skills Routing
-- ============================================================================

-- Step 3.1: Update Extract Skills → Save Posting Skills
UPDATE instruction_steps
SET next_conversation_id = (
    SELECT c.conversation_id 
    FROM conversations c
    JOIN actors a ON c.actor_id = a.actor_id
    WHERE a.actor_name = 'posting_skills_saver'
)
WHERE instruction_id = (
    SELECT instruction_id FROM instructions WHERE conversation_id = 3350  -- r1114_extract_skills
)
AND branch_condition = '*';

-- Step 3.2: Create routing from Save Posting Skills → IHL Analyst
INSERT INTO instruction_steps (
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority
)
SELECT 
    i.instruction_id,
    '*',
    9161,  -- IHL Analyst - Find Red Flags
    10
FROM instructions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE a.actor_name = 'posting_skills_saver'
  AND NOT EXISTS (
      SELECT 1 FROM instruction_steps WHERE instruction_id = i.instruction_id
  );

-- Step 3.3: Add Save Posting Skills to workflow_conversations
INSERT INTO workflow_conversations (workflow_id, conversation_id, execution_order)
SELECT 
    3001,
    c.conversation_id,
    11.5  -- Between Extract Skills (11) and IHL Analyst (12)
FROM conversations c
JOIN actors a ON c.actor_id = a.actor_id
WHERE a.actor_name = 'posting_skills_saver'
  AND NOT EXISTS (
      SELECT 1 FROM workflow_conversations 
      WHERE workflow_id = 3001 AND conversation_id = c.conversation_id
  );

-- ============================================================================
-- PART 4: Fix IHL Score Routing (This Part is Correct from 046)
-- ============================================================================

-- IHL Score Saver already exists as actor 82 and is correct for postings
-- Just need to ensure routing is set up

-- Create "Save IHL Score" conversation if it doesn't exist
INSERT INTO conversations (conversation_name, actor_id, conversation_description, model_used, temperature)
SELECT 
    'Save IHL Score and Category',
    82,  -- ihl_score_saver_v2 (this one is CORRECT for postings)
    'Writes IHL score and verdict to postings.ihl_score and postings.ihl_category',
    NULL,
    NULL
WHERE NOT EXISTS (
    SELECT 1 FROM conversations 
    WHERE conversation_name = 'Save IHL Score and Category'
)
RETURNING conversation_id;

-- Create instruction for Save IHL Score
INSERT INTO instructions (conversation_id, instruction_name, step_number, prompt_template)
SELECT 
    conversation_id,
    'Save IHL analysis to database',
    1,
    '{}'
FROM conversations
WHERE conversation_name = 'Save IHL Score and Category'
  AND NOT EXISTS (
      SELECT 1 FROM instructions WHERE conversation_id = conversations.conversation_id
  );

-- Update IHL HR Expert → Save IHL Score routing
DO $$
DECLARE
    ihl_save_conv_id INTEGER;
BEGIN
    -- Get the Save IHL Score conversation_id
    SELECT conversation_id INTO ihl_save_conv_id
    FROM conversations
    WHERE conversation_name = 'Save IHL Score and Category';
    
    -- Update or insert routing
    IF EXISTS (
        SELECT 1 FROM instruction_steps ws
        JOIN instructions i ON ws.instruction_id = i.instruction_id
        WHERE i.conversation_id = 9163  -- IHL HR Expert
    ) THEN
        -- Update existing routing
        UPDATE instruction_steps
        SET next_conversation_id = ihl_save_conv_id
        WHERE instruction_id = (
            SELECT instruction_id FROM instructions WHERE conversation_id = 9163
        )
        AND branch_condition = '*';
    ELSE
        -- Create new routing
        INSERT INTO instruction_steps (instruction_id, branch_condition, next_conversation_id, branch_priority)
        SELECT instruction_id, '*', ihl_save_conv_id, 10
        FROM instructions
        WHERE conversation_id = 9163;
    END IF;
END $$;

-- Add Save IHL Score to workflow_conversations
INSERT INTO workflow_conversations (workflow_id, conversation_id, execution_order)
SELECT 
    3001,
    conversation_id,
    22  -- After IHL HR Expert (21)
FROM conversations
WHERE conversation_name = 'Save IHL Score and Category'
  AND NOT EXISTS (
      SELECT 1 FROM workflow_conversations 
      WHERE workflow_id = 3001 AND conversation_id = conversations.conversation_id
  );

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify new actor was created
SELECT 'New Actor' as check_type, actor_id, actor_name
FROM actors
WHERE actor_name = 'posting_skills_saver';

-- Verify Skills routing
SELECT 
    'Skills Routing' as check_type,
    c1.conversation_name as from_conversation,
    a2.actor_name as to_actor,
    c2.conversation_name as to_conversation
FROM instruction_steps ws
JOIN instructions i ON ws.instruction_id = i.instruction_id
JOIN conversations c1 ON i.conversation_id = c1.conversation_id
LEFT JOIN conversations c2 ON ws.next_conversation_id = c2.conversation_id
LEFT JOIN actors a2 ON c2.actor_id = a2.actor_id
WHERE c1.conversation_id = 3350  -- r1114_extract_skills
   OR c1.conversation_name = 'Save Posting Skills'
ORDER BY c1.conversation_id;

-- Expected:
-- r1114_extract_skills → posting_skills_saver → Save Posting Skills
-- Save Posting Skills → (any) → IHL Analyst - Find Red Flags

-- Verify IHL routing  
SELECT 
    'IHL Routing' as check_type,
    c1.conversation_name as from_conversation,
    a2.actor_name as to_actor,
    c2.conversation_name as to_conversation
FROM instruction_steps ws
JOIN instructions i ON ws.instruction_id = i.instruction_id
JOIN conversations c1 ON i.conversation_id = c1.conversation_id
LEFT JOIN conversations c2 ON ws.next_conversation_id = c2.conversation_id
LEFT JOIN actors a2 ON c2.actor_id = a2.actor_id
WHERE c1.conversation_id = 9163  -- IHL HR Expert
   OR c1.conversation_name = 'Save IHL Score and Category';

-- Expected:
-- IHL HR Expert - Final Verdict → ihl_score_saver_v2 → Save IHL Score and Category

-- Verify both savers in workflow
SELECT 
    'Workflow Conversations' as check_type,
    wc.execution_order,
    c.conversation_name,
    a.actor_name
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE wc.workflow_id = 3001
  AND (c.conversation_name = 'Save Posting Skills' 
    OR c.conversation_name = 'Save IHL Score and Category')
ORDER BY wc.execution_order;

-- Expected:
-- 11.5 | Save Posting Skills | posting_skills_saver
-- 22   | Save IHL Score and Category | ihl_score_saver_v2

COMMIT;

-- ============================================================================
-- POST-MIGRATION TEST
-- ============================================================================

-- After committing, test with 1 posting:
--
-- 1. Run workflow on 1 posting
-- 2. Check postings table:
--    SELECT posting_id,
--           skill_keywords IS NOT NULL as has_skills_jsonb,
--           ihl_score IS NOT NULL as has_score,
--           ihl_category,
--           (SELECT COUNT(*) FROM posting_skills WHERE posting_id = p.posting_id) as skill_count
--    FROM postings p
--    WHERE posting_id = <test_posting_id>;
--
-- 3. Expected:
--    - has_skills_jsonb = TRUE (updated postings.skill_keywords)
--    - skill_count > 0 (inserted into posting_skills table)
--    - has_score = TRUE
--    - ihl_category in ('GENUINE', 'BORDERLINE', 'SUSPICIOUS')

-- ============================================================================
-- NOTES FOR SANDY
-- ============================================================================

/*
 * Hey Sandy! 👋
 * 
 * You were ABSOLUTELY RIGHT that something was wrong with the actors!
 * 
 * The issue:
 * - Migration 046 used actor #49 (skill_saver) which is for PROFILES
 * - Actor #49 saves to profile_skills table (wrong!)
 * - We need posting_skills table for job postings
 * 
 * The fix:
 * - Created NEW actor: posting_skills_saver (core/wave_runner/actors/posting_skills_saver.py)
 * - This migration registers it and updates routing
 * - Rolls back Migration 046's incorrect changes
 * 
 * What to do:
 * 1. Verify posting_skills_saver.py exists (I just created it)
 * 2. Run this migration (047)
 * 3. Test with 1 posting
 * 4. Check both postings.skill_keywords AND posting_skills table
 * 
 * Actor #82 (ihl_score_saver_v2) is CORRECT - it writes to postings table directly.
 * Only the skills actor was wrong!
 * 
 * Great detective work finding this! 🔍
 * 
 * - Arden
 */
