-- Migration 052: Fix Workflow 1122 Conversation Routing
-- =====================================================
-- Purpose: Add instruction_steps to route between conversations
-- Issue: Workflow 1122 stops after conversation 1 because there are no instruction_steps
-- Solution: Add DEFAULT branches to route conversation 1 → 2 → 3 → TERMINAL

BEGIN;

-- Step 1: Get instruction IDs for each conversation
-- Conversation 3355 (r2_extract_profile_summary) → step 1 → instruction_id 3352
-- Conversation 3353 (r2_extract_skills) → step 1 → instruction_id 3350  
-- Conversation 3354 (r2_map_to_taxonomy) → step 1 → instruction_id 3351

-- Step 2: Add DEFAULT branch from conversation 1 → conversation 2
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
VALUES (
    'w1122_summary_to_skills',
    3352,  -- From: r2_extract_profile_summary instruction
    'DEFAULT',
    3353,  -- To: r2_extract_skills conversation
    10,
    'After summary extraction, proceed to skill extraction',
    TRUE
);

-- Step 3: Add DEFAULT branch from conversation 2 → conversation 3
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
VALUES (
    'w1122_skills_to_taxonomy',
    3350,  -- From: r2_extract_skills instruction
    'DEFAULT',
    3354,  -- To: r2_map_to_taxonomy conversation
    10,
    'After skill extraction, map skills to taxonomy',
    TRUE
);

-- Step 4: Add TERMINAL instruction step for conversation 3 (end of workflow)
-- (No instruction_step needed - instruction.is_terminal = TRUE will handle it)
-- Let's verify the is_terminal flag is set correctly
UPDATE instructions
SET is_terminal = TRUE
WHERE instruction_id = 3351  -- r2_map_to_taxonomy
  AND is_terminal = FALSE;

-- Verification
SELECT 'Migration 052 applied successfully!' as status;

-- Show the routing
SELECT 
    i.instruction_id,
    c.conversation_name,
    i.step_number,
    i.is_terminal,
    istep.instruction_step_name,
    istep.branch_condition,
    istep.next_conversation_id,
    nc.conversation_name as next_conversation
FROM instructions i
JOIN conversations c ON i.conversation_id = c.conversation_id
LEFT JOIN instruction_steps istep ON i.instruction_id = istep.instruction_id
LEFT JOIN conversations nc ON istep.next_conversation_id = nc.conversation_id
WHERE c.conversation_id IN (3355, 3353, 3354)
ORDER BY c.conversation_id, i.step_number;

COMMIT;
