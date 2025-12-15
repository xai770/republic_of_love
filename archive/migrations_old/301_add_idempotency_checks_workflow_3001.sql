-- Migration 301: Add Idempotency Checks to Workflow 3001
-- Purpose: Prevent re-running expensive operations on already-processed data
-- Date: 2025-11-13

-- Strategy: Add check actors before extraction, skills, and IHL scoring
-- These checks skip to next major step if work already done

BEGIN;

-- ============================================================================
-- STEP 1: Create Universal Idempotency Check Actor
-- ============================================================================

INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    execution_config,
    url,
    enabled
) VALUES (
    'idempotency_check',
    'script',
    'python_script',
    'tools/idempotency_check.py',
    '{}'::jsonb,
    'internal://idempotency_check',
    TRUE
) RETURNING actor_id;
-- Expected: actor_id ~ 68

-- ============================================================================
-- STEP 2: Create Check Conversations
-- ============================================================================

-- 2a. Check if Summary Exists (before extraction)
INSERT INTO conversations (
    conversation_name,
    canonical_name,
    actor_id
) VALUES (
    'Check if Summary Exists',
    'check_summary_exists',
    (SELECT actor_id FROM actors WHERE actor_name = 'idempotency_check')
) RETURNING conversation_id;
-- Expected: conversation_id ~ 9201

-- 2b. Check if Skills Exist (before skills extraction)
INSERT INTO conversations (
    conversation_name,
    canonical_name,
    actor_id
) VALUES (
    'Check if Skills Exist',
    'check_skills_exist',
    (SELECT actor_id FROM actors WHERE actor_name = 'idempotency_check')
) RETURNING conversation_id;
-- Expected: conversation_id ~ 9202

-- 2c. Check if IHL Score Exists (before IHL scoring)
INSERT INTO conversations (
    conversation_name,
    canonical_name,
    actor_id
) VALUES (
    'Check if IHL Score Exists',
    'check_ihl_exists',
    (SELECT actor_id FROM actors WHERE actor_name = 'idempotency_check')
) RETURNING conversation_id;
-- Expected: conversation_id ~ 9203

-- ============================================================================
-- STEP 3: Update Workflow Execution Orders
-- ============================================================================

-- Make room for check conversations:
-- - Insert check_summary_exists between fetch (1) and extract (2)
-- - Insert check_skills_exist between save_summary (9) and skills (10)
-- - Insert check_ihl_exists between skills (11) and IHL scoring (14)

-- Current structure (execution_order):
--  1: fetch_db_jobs
--  2: gemma3_extract
--  ...
--  9: save_summary_check_ihl
-- 10: taxonomy_skill_extraction
-- 11: taxonomy_skill_mapping
-- 14: ihl_score_gemma
-- 15: ihl_score_qwen
-- 16: ihl_score_phi

-- Target structure:
--  1: fetch_db_jobs
--  2: check_summary_exists (NEW)
--  3: gemma3_extract (was 2)
--  ...
-- 10: save_summary_check_ihl (was 9)
-- 11: check_skills_exist (NEW)
-- 12: taxonomy_skill_extraction (was 10)
-- 13: taxonomy_skill_mapping (was 11)
-- 16: check_ihl_exists (NEW)
-- 17: ihl_score_gemma (was 14)
-- 18: ihl_score_qwen (was 15)
-- 19: ihl_score_phi (was 16)

-- Shift execution orders to make room (use temp high values to avoid collisions)
-- Step 1: Move conversations to temp positions (100+)
UPDATE workflow_conversations
SET execution_order = execution_order + 100
WHERE workflow_id = 3001 AND execution_order >= 2;

-- Step 2: Move them back to final positions
UPDATE workflow_conversations
SET execution_order = CASE
    WHEN execution_order >= 114 THEN execution_order - 100 + 5  -- IHL (was 14-16, now 19-21)
    WHEN execution_order >= 110 THEN execution_order - 100 + 2  -- Skills (was 10-13, now 12-15)
    WHEN execution_order >= 102 THEN execution_order - 100 + 1  -- Extract (was 2-9, now 3-10)
    ELSE execution_order
END
WHERE workflow_id = 3001 AND execution_order >= 100;

-- ============================================================================
-- STEP 4: Fix sequence after UPDATEs
-- ============================================================================

-- The UPDATE operations don't affect the sequence, so we need to manually advance it
SELECT setval('workflow_conversations_step_id_seq', 
              (SELECT MAX(step_id) FROM workflow_conversations) + 1);

-- ============================================================================
-- STEP 5: Insert Check Conversations into Workflow
-- ============================================================================

-- 5a. Add check_summary_exists at position 2
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order
) VALUES (
    3001,
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'check_summary_exists'),
    2
);

-- 4b. Add check_skills_exist at position 11
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order
) VALUES (
    3001,
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'check_skills_exist'),
    11
);

-- 4c. Add check_ihl_exists at position 16
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order
) VALUES (
    3001,
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'check_ihl_exists'),
    16
);

-- ============================================================================
-- STEP 6: Create Instructions for Check Conversations
-- ============================================================================

-- 6a. Instruction for check_summary_exists
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    prompt_template,
    timeout_seconds
) VALUES (
    'Check if extracted_summary exists',
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'check_summary_exists'),
    1,
    '{"posting_id": {posting_id}, "check_field": "extracted_summary", "check_type": "min_length", "min_length": 50}',
    10
) RETURNING instruction_id;
-- Expected: instruction_id ~ 3410

-- 6b. Instruction for check_skills_exist
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    prompt_template,
    timeout_seconds
) VALUES (
    'Check if taxonomy_skills exists',
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'check_skills_exist'),
    1,
    '{"posting_id": {posting_id}, "check_field": "taxonomy_skills", "check_type": "not_null"}',
    10
) RETURNING instruction_id;
-- Expected: instruction_id ~ 3411

-- 6c. Instruction for check_ihl_exists
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    prompt_template,
    timeout_seconds
) VALUES (
    'Check if ihl_score exists',
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'check_ihl_exists'),
    1,
    '{"posting_id": {posting_id}, "check_field": "ihl_score", "check_type": "not_null"}',
    10
) RETURNING instruction_id;
-- Expected: instruction_id ~ 3412

-- ============================================================================
-- STEP 7: Create Branch Conditions
-- ============================================================================

-- 7a. Branches for check_summary_exists
INSERT INTO instruction_steps (
    instruction_id,
    instruction_step_name,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description
) VALUES
    -- If summary exists, skip to save_summary (conversation 10)
    ((SELECT instruction_id FROM instructions WHERE instruction_name = 'Check if extracted_summary exists'),
     'Skip extraction if summary exists',
     '[SKIP]',
     (SELECT conversation_id FROM conversations WHERE canonical_name = 'save_summary_check_ihl'),
     100,
     'Summary already exists, skip extraction and grading'),
    -- If summary missing, proceed to extraction (conversation 3)
    ((SELECT instruction_id FROM instructions WHERE instruction_name = 'Check if extracted_summary exists'),
     'Run extraction if summary missing',
     '[RUN]',
     (SELECT conversation_id FROM conversations WHERE canonical_name = 'gemma3_extract'),
     90,
     'Summary missing, proceed with extraction');

-- 7b. Branches for check_skills_exist
INSERT INTO instruction_steps (
    instruction_id,
    instruction_step_name,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description
) VALUES
    -- If skills exist, skip to IHL check (conversation 16)
    ((SELECT instruction_id FROM instructions WHERE instruction_name = 'Check if taxonomy_skills exists'),
     'Skip skills extraction if exists',
     '[SKIP]',
     (SELECT conversation_id FROM conversations WHERE canonical_name = 'check_ihl_exists'),
     100,
     'Skills already exist, skip extraction'),
    -- If skills missing, proceed to extraction (conversation 12)
    ((SELECT instruction_id FROM instructions WHERE instruction_name = 'Check if taxonomy_skills exists'),
     'Run skills extraction if missing',
     '[RUN]',
     (SELECT c.conversation_id 
      FROM conversations c
      JOIN workflow_conversations wc ON wc.conversation_id = c.conversation_id
      WHERE c.canonical_name = 'taxonomy_skill_extraction'
        AND wc.workflow_id = 3001
        AND wc.execution_order = 12
      LIMIT 1),
     90,
     'Skills missing, proceed with extraction');

-- 7c. Branches for check_ihl_exists
INSERT INTO instruction_steps (
    instruction_id,
    instruction_step_name,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description
) VALUES
    -- If IHL score exists, terminate (NULL = terminal)
    ((SELECT instruction_id FROM instructions WHERE instruction_name = 'Check if ihl_score exists'),
     'Skip IHL scoring if exists',
     '[SKIP]',
     NULL,  -- TERMINAL
     100,
     'IHL score already exists, workflow complete'),
    -- If IHL score missing, proceed to scoring (conversation 17)
    ((SELECT instruction_id FROM instructions WHERE instruction_name = 'Check if ihl_score exists'),
     'Run IHL scoring if missing',
     '[RUN]',
     (SELECT c.conversation_id 
      FROM conversations c
      JOIN workflow_conversations wc ON wc.conversation_id = c.conversation_id
      WHERE c.canonical_name = 'w1124_c1_analyst'  -- First IHL conversation
        AND wc.workflow_id = 3001
        AND wc.execution_order = 19
      LIMIT 1),
     90,
     'IHL score missing, proceed with scoring');

-- ============================================================================
-- STEP 8: Update save_summary_check_ihl Branches
-- ============================================================================

-- The save_summary conversation currently branches to:
-- [HAS_IHL] → TERMINAL
-- [NO_IHL] → taxonomy_skill_extraction

-- Update [NO_IHL] to point to check_skills_exist instead
UPDATE instruction_steps ist
SET next_conversation_id = c_target.conversation_id
FROM conversations c_target,
     conversations c_source,
     instructions i
WHERE c_target.canonical_name = 'check_skills_exist'
  AND c_source.canonical_name = 'save_summary_check_ihl'
  AND i.conversation_id = c_source.conversation_id
  AND ist.instruction_id = i.instruction_id
  AND ist.branch_condition = '[NO_IHL]';

COMMIT;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check actor created
SELECT actor_id, actor_name 
FROM actors 
WHERE actor_name = 'idempotency_check';

-- Check conversations created
SELECT conversation_id, conversation_name, canonical_name
FROM conversations
WHERE canonical_name IN ('check_summary_exists', 'check_skills_exist', 'check_ihl_exists');

-- Check workflow order
SELECT 
    wc.execution_order,
    c.canonical_name,
    c.conversation_name
FROM workflows w
JOIN workflow_conversations wc ON wc.workflow_id = w.workflow_id
JOIN conversations c ON c.conversation_id = wc.conversation_id
WHERE w.workflow_id = 3001
ORDER BY wc.execution_order;

-- Check branches
SELECT 
    i.instruction_name,
    ist.branch_condition,
    ist.branch_priority,
    c2.canonical_name as next_conversation
FROM instructions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN instruction_steps ist ON ist.instruction_id = i.instruction_id
LEFT JOIN conversations c2 ON ist.next_conversation_id = c2.conversation_id
WHERE c.canonical_name IN ('check_summary_exists', 'check_skills_exist', 'check_ihl_exists')
ORDER BY c.canonical_name, ist.branch_priority DESC;
