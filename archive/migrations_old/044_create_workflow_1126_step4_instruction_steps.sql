-- ============================================================================
-- Migration 044: Create Workflow 1126 - Step 4: Instruction Steps
-- ============================================================================
-- Purpose: Define branching logic (what happens after each instruction)
-- Follows: WORKFLOW_CREATION_COOKBOOK.md Step 4
-- ============================================================================

BEGIN;

-- ============================================================================
-- Instruction Steps for Instruction 1: Extract Profile Data
-- ============================================================================

-- Branch 1.1: Extraction successful → Go to validation
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
SELECT
    'Extraction successful - validate data',
    i.instruction_id,
    '[SUCCESS]',
    c_next.conversation_id,
    10,
    'If extraction produced valid JSON with required fields, proceed to validation',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
JOIN conversations c_next ON c_next.canonical_name = 'w1126_c2_validate'
WHERE c_from.canonical_name = 'w1126_c1_extract'
  AND i.step_number = 1;

-- Branch 1.2: Extraction failed → Go to error handling
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
SELECT
    'Extraction failed - generate error report',
    i.instruction_id,
    '[FAIL]',
    c_next.conversation_id,
    5,
    'If extraction failed or produced invalid JSON, generate error report',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
JOIN conversations c_next ON c_next.canonical_name = 'w1126_c4_error'
WHERE c_from.canonical_name = 'w1126_c1_extract'
  AND i.step_number = 1;

-- ============================================================================
-- Instruction Steps for Instruction 2: Validate Extracted Data
-- ============================================================================

-- Branch 2.1: Validation passed → Go to import
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
SELECT
    'Validation passed - import to database',
    i.instruction_id,
    '[PASS]',
    c_next.conversation_id,
    10,
    'If validation status is PASS or WARNING (with corrections), proceed to database import',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
JOIN conversations c_next ON c_next.canonical_name = 'w1126_c3_import'
WHERE c_from.canonical_name = 'w1126_c2_validate'
  AND i.step_number = 1;

-- Branch 2.2: Validation failed → Go to error handling
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
SELECT
    'Validation failed - cannot recover',
    i.instruction_id,
    '[FAIL]',
    c_next.conversation_id,
    5,
    'If validation found unrecoverable errors (missing required fields), generate error report',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
JOIN conversations c_next ON c_next.canonical_name = 'w1126_c4_error'
WHERE c_from.canonical_name = 'w1126_c2_validate'
  AND i.step_number = 1;

-- ============================================================================
-- Instruction Steps for Instruction 3: Import to Database
-- ============================================================================

-- Branch 3.1: Import successful → TERMINAL (workflow complete)
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    next_instruction_id,
    branch_priority,
    branch_description,
    enabled
)
SELECT
    'Import successful - workflow complete',
    i.instruction_id,
    '[SUCCESS]',
    NULL,
    NULL,
    10,
    'Database import successful. profile_id available for Workflow 1122 (skill extraction)',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
WHERE c_from.canonical_name = 'w1126_c3_import'
  AND i.step_number = 1;

-- Branch 3.2: Import failed → Go to error handling
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
SELECT
    'Import failed - database error',
    i.instruction_id,
    '[FAIL]',
    c_next.conversation_id,
    5,
    'Database import failed (constraint violation, connection error, etc.)',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
JOIN conversations c_next ON c_next.canonical_name = 'w1126_c4_error'
WHERE c_from.canonical_name = 'w1126_c3_import'
  AND i.step_number = 1;

COMMIT;

-- ============================================================================
-- Verification Step 4
-- ============================================================================
SELECT 
    ist.instruction_step_id,
    ist.instruction_step_name,
    c_from.conversation_name as from_conversation,
    i.instruction_name as from_instruction,
    ist.branch_condition,
    c_next.conversation_name as next_conversation,
    ist.branch_priority,
    ist.enabled
FROM instruction_steps ist
JOIN instructions i ON ist.instruction_id = i.instruction_id
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
LEFT JOIN conversations c_next ON ist.next_conversation_id = c_next.conversation_id
WHERE c_from.canonical_name LIKE 'w1126_%'
ORDER BY c_from.conversation_id, ist.branch_priority DESC;

-- Success message
DO $$ BEGIN
    RAISE NOTICE '✅ Step 4 Complete: Branching logic defined for all instructions';
    RAISE NOTICE '🎉 Workflow 1126 is COMPLETE and ready for testing!';
END $$;
