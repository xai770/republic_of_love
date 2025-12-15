-- Migration 072: Fix instruction_steps foreign key constraints
-- Date: 2025-11-10
-- Purpose: Ensure instruction_steps.instruction_id and next_instruction_id properly link to instructions table

BEGIN;

-- Add foreign key constraint for instruction_id (the source instruction)
ALTER TABLE instruction_steps
    DROP CONSTRAINT IF EXISTS fk_instruction_steps_instruction_id;

ALTER TABLE instruction_steps
    ADD CONSTRAINT fk_instruction_steps_instruction_id
    FOREIGN KEY (instruction_id)
    REFERENCES instructions(instruction_id)
    ON DELETE CASCADE;

-- Add foreign key constraint for next_instruction_id (the target instruction)
ALTER TABLE instruction_steps
    DROP CONSTRAINT IF EXISTS fk_instruction_steps_next_instruction_id;

ALTER TABLE instruction_steps
    ADD CONSTRAINT fk_instruction_steps_next_instruction_id
    FOREIGN KEY (next_instruction_id)
    REFERENCES instructions(instruction_id)
    ON DELETE SET NULL;  -- If target instruction is deleted, set to NULL (workflow will end)

-- Add foreign key constraint for next_conversation_id (alternative branching target)
ALTER TABLE instruction_steps
    DROP CONSTRAINT IF EXISTS fk_instruction_steps_next_conversation_id;

ALTER TABLE instruction_steps
    ADD CONSTRAINT fk_instruction_steps_next_conversation_id
    FOREIGN KEY (next_conversation_id)
    REFERENCES conversations(conversation_id)
    ON DELETE SET NULL;  -- If target conversation is deleted, set to NULL

-- Add check constraint: must have either next_instruction_id OR next_conversation_id (or both NULL for terminal)
ALTER TABLE instruction_steps
    DROP CONSTRAINT IF EXISTS chk_instruction_steps_has_next_target;

ALTER TABLE instruction_steps
    ADD CONSTRAINT chk_instruction_steps_has_next_target
    CHECK (
        next_instruction_id IS NOT NULL 
        OR next_conversation_id IS NOT NULL 
        OR branch_condition = 'TERMINAL'
    );

COMMIT;

-- Verify constraints
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'instruction_steps'
    AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.constraint_name;
