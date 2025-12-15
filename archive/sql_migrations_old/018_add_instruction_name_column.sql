-- Migration 018: Add instruction_name and clean up instructions table
-- Date: 2025-10-31
-- Purpose: Add instruction_name as second column for better readability.
--          Remove redundant delegate_actor_name text field (use delegate_actor_id FK instead).

BEGIN;

-- Step 1: Create the new instructions table with correct structure
CREATE TABLE instructions_new (
    instruction_id      INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    instruction_name    TEXT NOT NULL,
    conversation_id     INTEGER NOT NULL,
    step_number         INTEGER NOT NULL,
    step_description    TEXT,
    prompt_template     TEXT NOT NULL,
    timeout_seconds     INTEGER DEFAULT 300,
    expected_pattern    TEXT,
    validation_rules    TEXT,
    is_terminal         BOOLEAN DEFAULT false,
    delegate_actor_id   INTEGER,
    enabled             BOOLEAN DEFAULT true,
    created_at          TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT instructions_new_conversation_id_step_number_key UNIQUE (conversation_id, step_number),
    CONSTRAINT instructions_new_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
    CONSTRAINT instructions_new_delegate_actor_id_fkey FOREIGN KEY (delegate_actor_id) REFERENCES actors(actor_id) ON UPDATE CASCADE ON DELETE SET NULL
);

-- Step 2: Copy data from old instructions to new, generating instruction_name from step_description or step_number
INSERT INTO instructions_new (
    instruction_id,
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    expected_pattern,
    validation_rules,
    is_terminal,
    delegate_actor_id,
    enabled,
    created_at,
    updated_at
) OVERRIDING SYSTEM VALUE
SELECT 
    instruction_id,
    -- Generate instruction_name from step_description or use generic name
    COALESCE(
        CASE 
            WHEN step_description IS NOT NULL AND LENGTH(step_description) > 0 
            THEN LEFT(step_description, 100)
            ELSE 'Step ' || step_number
        END,
        'Step ' || step_number
    ) as instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    expected_pattern,
    validation_rules,
    is_terminal,
    delegate_actor_id,
    enabled,
    created_at,
    updated_at
FROM instructions
ORDER BY instruction_id;

-- Step 3: Update the sequence to match max instruction_id
SELECT setval('instructions_new_instruction_id_seq', (SELECT MAX(instruction_id) FROM instructions));

-- Step 4: Create indexes
CREATE INDEX idx_instructions_new_conversation ON instructions_new(conversation_id);
CREATE INDEX idx_instructions_new_enabled ON instructions_new(enabled);
CREATE INDEX idx_instructions_new_delegate_actor ON instructions_new(delegate_actor_id) WHERE delegate_actor_id IS NOT NULL;

-- Step 5: Drop the old table and rename new one
DROP TABLE instructions CASCADE;
ALTER TABLE instructions_new RENAME TO instructions;

-- Rename constraints
ALTER TABLE instructions RENAME CONSTRAINT instructions_new_conversation_id_step_number_key TO instructions_conversation_id_step_number_key;
ALTER TABLE instructions RENAME CONSTRAINT instructions_new_conversation_id_fkey TO instructions_conversation_id_fkey;
ALTER TABLE instructions RENAME CONSTRAINT instructions_new_delegate_actor_id_fkey TO instructions_delegate_actor_id_fkey;

-- Rename indexes
ALTER INDEX idx_instructions_new_conversation RENAME TO idx_instructions_conversation;
ALTER INDEX idx_instructions_new_enabled RENAME TO idx_instructions_enabled;
ALTER INDEX idx_instructions_new_delegate_actor RENAME TO idx_instructions_delegate_actor;

-- Rename sequence
ALTER SEQUENCE instructions_new_instruction_id_seq RENAME TO instructions_instruction_id_seq;

-- Step 6: Recreate foreign keys from other tables
ALTER TABLE instruction_branches ADD CONSTRAINT fk_instruction 
    FOREIGN KEY (instruction_id) REFERENCES instructions(instruction_id) ON DELETE CASCADE;
ALTER TABLE instruction_branches ADD CONSTRAINT fk_next_instruction 
    FOREIGN KEY (next_instruction_id) REFERENCES instructions(instruction_id) ON DELETE SET NULL;

ALTER TABLE instruction_runs ADD CONSTRAINT instruction_runs_instruction_id_fkey 
    FOREIGN KEY (instruction_id) REFERENCES instructions(instruction_id);

-- Step 7: Create history trigger
CREATE TRIGGER instructions_history_trigger
    BEFORE UPDATE ON instructions
    FOR EACH ROW
    EXECUTE FUNCTION archive_instructions();

-- Step 8: Update instructions_history table to match new structure
ALTER TABLE instructions_history ADD COLUMN instruction_name TEXT;
ALTER TABLE instructions_history DROP COLUMN IF EXISTS delegate_actor_name;

-- Step 9: Add comments
COMMENT ON TABLE instructions IS 
'Individual execution steps within conversations (568 entries).
Each instruction is a single prompt/action that executes in sequence within a conversation.
Instructions can branch conditionally, delegate to helper actors, and mark completion points.
Together with instruction_branches, instructions form a Turing-complete execution model.
Updated 2025-10-31 to add instruction_name and remove redundant delegate_actor_name.
Pattern: instruction_id (INTEGER PK) + instruction_name (TEXT).';

COMMENT ON COLUMN instructions.instruction_id IS 
'Primary key - unique identifier for this instruction';

COMMENT ON COLUMN instructions.instruction_name IS 
'Human-readable name for this instruction (e.g., "Generate joke", "Evaluate quality")';

COMMENT ON COLUMN instructions.conversation_id IS 
'FK to conversations - which conversation this instruction belongs to';

COMMENT ON COLUMN instructions.step_number IS 
'Sequential step number within the conversation (1, 2, 3, ...)';

COMMENT ON COLUMN instructions.step_description IS 
'Detailed description of what this instruction does';

COMMENT ON COLUMN instructions.prompt_template IS 
'The prompt template to send to the actor (can include {variables})';

COMMENT ON COLUMN instructions.timeout_seconds IS 
'Maximum time allowed for this instruction to execute (default 300)';

COMMENT ON COLUMN instructions.expected_pattern IS 
'Optional regex pattern for validating the response';

COMMENT ON COLUMN instructions.validation_rules IS 
'Optional validation rules or logic to apply to the response';

COMMENT ON COLUMN instructions.is_terminal IS 
'If true, this instruction marks a completion point (no automatic continuation)';

COMMENT ON COLUMN instructions.delegate_actor_id IS 
'Optional FK to actors - if set, delegate this instruction to a different actor (helper/script)';

-- Step 10: Verification
SELECT 
    'instructions' as table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT conversation_id) as unique_conversations,
    COUNT(CASE WHEN delegate_actor_id IS NOT NULL THEN 1 END) as with_delegation,
    'instruction_name added, delegate_actor_name removed' as status
FROM instructions;

COMMIT;
