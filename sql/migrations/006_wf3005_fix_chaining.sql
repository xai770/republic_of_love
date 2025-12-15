-- WF3005 Fix Chaining - Add missing instructions and instruction_steps
-- 
-- Problem: Wave Runner chains via instruction_steps.next_conversation_id
-- WF3005 had conversations but no complete instruction chain
--
-- Author: Sandy
-- Date: December 7, 2025

BEGIN;

-- Create instruction for c1_fetch (script actor)
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,  -- Not used for scripts, but required
    is_terminal
) VALUES (
    'w3005_fetch_orphans',
    9229,  -- w3005_c1_fetch
    1,
    'Fetch batch of orphan skills from UEO entities table',
    'Script execution - no prompt template',
    false
);

-- Get the instruction_id we just created
-- Create chain: c1_fetch → c2_classify
INSERT INTO instruction_steps (
    instruction_id,
    instruction_step_name,
    branch_condition,
    branch_description,
    branch_priority,
    next_conversation_id,
    enabled
)
SELECT 
    i.instruction_id,
    'w3005_fetch_to_classify',
    'always',  -- Always chain to classifier after fetch
    'Route fetched orphans to classifier',
    100,
    9230,  -- w3005_c2_classify
    true
FROM instructions i
WHERE i.instruction_name = 'w3005_fetch_orphans';

-- Create chain: c2_classify → c3_grade
INSERT INTO instruction_steps (
    instruction_id,
    instruction_step_name,
    branch_condition,
    branch_description,
    branch_priority,
    next_conversation_id,
    enabled
) VALUES (
    3436,  -- w3005_classify_orphans (existing)
    'w3005_classify_to_grade',
    'always',
    'Route classifications to grader for verification',
    100,
    9231,  -- w3005_c3_grade
    true
);

-- Create chain: c3_grade → c4_save
INSERT INTO instruction_steps (
    instruction_id,
    instruction_step_name,
    branch_condition,
    branch_description,
    branch_priority,
    next_conversation_id,
    enabled
) VALUES (
    3437,  -- w3005_grade_classifications (existing)
    'w3005_grade_to_save',
    'always',
    'Route graded decisions to saver for persistence',
    100,
    9232,  -- w3005_c4_save
    true
);

-- Create instruction for c4_save (script actor) - terminal
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    is_terminal
) VALUES (
    'w3005_save_decisions',
    9232,  -- w3005_c4_save
    1,
    'Save graded hierarchy decisions to registry_decisions table',
    'Script execution - no prompt template',
    true  -- Terminal - no next step
);

COMMIT;

-- Verify the chain
-- SELECT 
--     i.instruction_name,
--     c.canonical_name as from_conv,
--     s.instruction_step_name,
--     c2.canonical_name as next_conv
-- FROM instruction_steps s
-- JOIN instructions i ON s.instruction_id = i.instruction_id
-- JOIN conversations c ON i.conversation_id = c.conversation_id
-- LEFT JOIN conversations c2 ON s.next_conversation_id = c2.conversation_id
-- WHERE c.canonical_name LIKE 'w3005%'
-- ORDER BY c.canonical_name;
