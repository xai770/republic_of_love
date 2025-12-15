-- Migration 025: Rename transitions to instruction_steps
-- Date: 2025-10-31
-- Purpose: Rename transitions to instruction_steps for clarity and consistency
--          Reflects that these steps define control flow between instructions
--          Part of consistent naming: conversation_steps (workflow level), instruction_steps (conversation level)

-- This migration renames transitions to instruction_steps because:
-- 1. transitions defines which INSTRUCTIONS to run next (conditional routing)
-- 2. Parallel naming with conversation_steps (migration 024)
-- 3. Makes hierarchy clear: workflows → conversations → instructions
-- 4. "steps" implies both sequencing and branching

BEGIN;

-- Step 1: Rename the sequence
ALTER SEQUENCE transitions_transition_id_seq RENAME TO instruction_steps_instruction_step_id_seq;

-- Step 2: Rename the history table if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'transitions_history') THEN
        ALTER TABLE transitions_history RENAME TO instruction_steps_history;
        ALTER TABLE instruction_steps_history RENAME COLUMN transition_id TO instruction_step_id;
    END IF;
END $$;

-- Step 3: Rename transition_executions table
ALTER TABLE transition_executions RENAME TO instruction_step_executions;

-- Step 4: Rename column in instruction_step_executions
ALTER TABLE instruction_step_executions RENAME COLUMN transition_id TO instruction_step_id;

-- Step 5: Fix duplicate transition_name values first
UPDATE transitions 
SET transition_name = transition_name || '_' || transition_id 
WHERE transition_id IN (
    SELECT transition_id 
    FROM (
        SELECT transition_id, transition_name, 
               ROW_NUMBER() OVER (PARTITION BY transition_name ORDER BY transition_id) as rn
        FROM transitions
    ) sub 
    WHERE rn > 1
);

-- Step 6: Export data and prepare for column rename
CREATE TABLE instruction_steps_temp (
    instruction_step_id INTEGER PRIMARY KEY,
    instruction_step_name TEXT UNIQUE NOT NULL,
    instruction_id INTEGER NOT NULL,
    branch_condition TEXT NOT NULL,
    next_instruction_id INTEGER,
    next_conversation_id INTEGER,
    max_iterations INTEGER,
    branch_priority INTEGER DEFAULT 5,
    branch_description TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Copy data from transitions (renaming transition_id → instruction_step_id, transition_name → instruction_step_name)
INSERT INTO instruction_steps_temp (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_instruction_id,
    next_conversation_id,
    max_iterations,
    branch_priority,
    branch_description,
    enabled,
    created_at,
    updated_at
)
SELECT 
    transition_id,
    transition_name,
    instruction_id,
    branch_condition,
    next_instruction_id,
    next_conversation_id,
    max_iterations,
    branch_priority,
    branch_description,
    enabled,
    created_at,
    updated_at
FROM transitions;

-- Step 7: Drop old table (CASCADE will drop FK constraints)
DROP TABLE transitions CASCADE;

-- Step 8: Create new table with renamed columns
CREATE TABLE instruction_steps (
    instruction_step_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instruction_step_name TEXT UNIQUE NOT NULL,
    instruction_id INTEGER NOT NULL,
    branch_condition TEXT NOT NULL,
    next_instruction_id INTEGER,
    next_conversation_id INTEGER,
    max_iterations INTEGER,
    branch_priority INTEGER DEFAULT 5,
    branch_description TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_branch_target CHECK (
        (next_instruction_id IS NOT NULL AND next_conversation_id IS NULL) OR
        (next_instruction_id IS NULL AND next_conversation_id IS NOT NULL) OR
        (next_instruction_id IS NULL AND next_conversation_id IS NULL)
    ),
    CONSTRAINT chk_positive_iterations CHECK (max_iterations IS NULL OR max_iterations > 0)
);

-- Step 9: Set the sequence to continue from the last value
SELECT setval('instruction_steps_instruction_step_id_seq', (SELECT MAX(instruction_step_id) FROM instruction_steps_temp));

-- Step 10: Insert data with OVERRIDING SYSTEM VALUE
INSERT INTO instruction_steps (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_instruction_id,
    next_conversation_id,
    max_iterations,
    branch_priority,
    branch_description,
    enabled,
    created_at,
    updated_at
) OVERRIDING SYSTEM VALUE
SELECT 
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_instruction_id,
    next_conversation_id,
    max_iterations,
    branch_priority,
    branch_description,
    enabled,
    created_at,
    updated_at
FROM instruction_steps_temp;

-- Step 11: Drop temporary table
DROP TABLE instruction_steps_temp;

-- Step 12: Recreate indexes
CREATE INDEX idx_instruction_steps_enabled ON instruction_steps(enabled);
CREATE INDEX idx_instruction_steps_instruction ON instruction_steps(instruction_id) WHERE enabled = true;
CREATE INDEX idx_instruction_steps_priority ON instruction_steps(instruction_id, branch_priority DESC) WHERE enabled = true;

-- Step 13: Add foreign key constraints
ALTER TABLE instruction_steps 
    ADD CONSTRAINT instruction_steps_instruction_id_fkey 
    FOREIGN KEY (instruction_id) REFERENCES instructions(instruction_id) ON DELETE CASCADE;

ALTER TABLE instruction_steps 
    ADD CONSTRAINT instruction_steps_next_conversation_id_fkey 
    FOREIGN KEY (next_conversation_id) REFERENCES conversations(conversation_id) ON DELETE SET NULL;

ALTER TABLE instruction_steps 
    ADD CONSTRAINT instruction_steps_next_instruction_id_fkey 
    FOREIGN KEY (next_instruction_id) REFERENCES instructions(instruction_id) ON DELETE SET NULL;

-- Step 14: Update foreign keys from instruction_step_executions
ALTER TABLE instruction_step_executions 
    ADD CONSTRAINT instruction_step_executions_instruction_step_id_fkey 
    FOREIGN KEY (instruction_step_id) REFERENCES instruction_steps(instruction_step_id) ON DELETE CASCADE;

-- Step 15: Rename archive function if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'archive_transitions') THEN
        ALTER FUNCTION archive_transitions() RENAME TO archive_instruction_steps;
    END IF;
END $$;

-- Step 16: Create trigger if archive function exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'archive_instruction_steps') THEN
        EXECUTE 'CREATE TRIGGER instruction_steps_history_trigger
                 BEFORE UPDATE ON instruction_steps
                 FOR EACH ROW
                 EXECUTE FUNCTION archive_instruction_steps()';
    END IF;
END $$;

-- Step 17: Add comprehensive comments
COMMENT ON TABLE instruction_steps IS 'Defines conditional control flow between instructions within conversations.
Each step evaluates a branch_condition to determine which instruction or conversation executes next.
Key to Turing completeness: enables if/else/switch logic, loops (max_iterations), and state transitions.

Hierarchy:
- workflows orchestrate conversations (via conversation_steps)
- conversations orchestrate instructions (via instruction_steps)
- instructions execute tasks (via actors)

Branching Logic (Complex):
- branch_condition: expression to evaluate (e.g., "[PASS]", "[FAIL]", "[SCORE > 80]")
- branch_priority: evaluation order (DESC) - higher priority evaluated first
- next_instruction_id: continue within same conversation
- next_conversation_id: jump to different conversation
- max_iterations: enable loops (NULL = no looping)

Unlike conversation_steps (simple success/fail), instruction_steps support complex conditional logic
because instructions may have nuanced outcomes requiring sophisticated routing decisions.

Evaluation: Ordered by branch_priority DESC → first matching branch_condition wins.

Formerly: instruction_branches → transitions → instruction_steps (migrations 019, 025).';

COMMENT ON COLUMN instruction_steps.instruction_step_id IS 'Unique identifier for this instruction step (formerly transition_id)';
COMMENT ON COLUMN instruction_steps.instruction_step_name IS 'Human-readable name for this instruction step (formerly transition_name)';
COMMENT ON COLUMN instruction_steps.instruction_id IS 'Foreign key to instructions table - the instruction whose output triggers this conditional routing';
COMMENT ON COLUMN instruction_steps.branch_condition IS 'Expression to evaluate for this branch (e.g., "[PASS]", "[FAIL]", "[SCORE > 80]")';
COMMENT ON COLUMN instruction_steps.next_instruction_id IS 'Foreign key to instructions table - next instruction to execute if condition matches (within same conversation)';
COMMENT ON COLUMN instruction_steps.next_conversation_id IS 'Foreign key to conversations table - next conversation to execute if condition matches (jump to different conversation)';
COMMENT ON COLUMN instruction_steps.max_iterations IS 'Maximum loop iterations if this creates a cycle (NULL = no looping, >0 = max iterations)';
COMMENT ON COLUMN instruction_steps.branch_priority IS 'Evaluation priority (DESC order) - higher values evaluated first. Default: 5';
COMMENT ON COLUMN instruction_steps.branch_description IS 'Human-readable explanation of what this branch does and when it fires';
COMMENT ON COLUMN instruction_steps.enabled IS 'Whether this instruction step is active (true) or disabled (false)';
COMMENT ON COLUMN instruction_steps.created_at IS 'Timestamp when this instruction step was created';
COMMENT ON COLUMN instruction_steps.updated_at IS 'Timestamp when this instruction step was last modified';

COMMIT;

-- Verification queries (run after migration)
-- SELECT COUNT(*) FROM instruction_steps;  -- Should show 6
-- SELECT instruction_step_id, instruction_step_name, instruction_id, branch_condition FROM instruction_steps LIMIT 5;
-- \d instruction_steps
