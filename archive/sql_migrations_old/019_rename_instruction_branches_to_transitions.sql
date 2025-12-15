-- Migration 019: Rename instruction_branches to transitions and add transition_name
-- Date: 2025-10-31
-- Purpose: Rename instruction_branches to transitions (clearer, shorter).
--          Add transition_name as second column for better readability.
--          Transitions are the control flow that enables Turing completeness.

BEGIN;

-- Step 1: Create the new transitions table with correct structure
CREATE TABLE transitions (
    transition_id        INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    transition_name      TEXT NOT NULL,
    instruction_id       INTEGER NOT NULL,
    branch_condition     TEXT NOT NULL,
    next_instruction_id  INTEGER,
    next_conversation_id INTEGER,
    max_iterations       INTEGER,
    branch_priority      INTEGER DEFAULT 5,
    branch_description   TEXT,
    enabled              BOOLEAN DEFAULT true,
    created_at           TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_branch_target CHECK (
        (next_instruction_id IS NOT NULL AND next_conversation_id IS NULL) OR
        (next_instruction_id IS NULL AND next_conversation_id IS NOT NULL) OR
        (next_instruction_id IS NULL AND next_conversation_id IS NULL)
    ),
    CONSTRAINT chk_positive_iterations CHECK (max_iterations IS NULL OR max_iterations > 0),
    CONSTRAINT transitions_instruction_id_fkey FOREIGN KEY (instruction_id) REFERENCES instructions(instruction_id) ON DELETE CASCADE,
    CONSTRAINT transitions_next_instruction_id_fkey FOREIGN KEY (next_instruction_id) REFERENCES instructions(instruction_id) ON DELETE SET NULL,
    CONSTRAINT transitions_next_conversation_id_fkey FOREIGN KEY (next_conversation_id) REFERENCES conversations(conversation_id) ON DELETE SET NULL
);

-- Step 2: Copy data from instruction_branches to transitions, generating transition_name
INSERT INTO transitions (
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
) OVERRIDING SYSTEM VALUE
SELECT 
    branch_id,
    -- Generate transition_name from branch_description or condition
    COALESCE(
        CASE 
            WHEN branch_description IS NOT NULL AND LENGTH(branch_description) > 0 
            THEN LEFT(branch_description, 100)
            ELSE 'On ' || branch_condition
        END,
        'Branch ' || branch_id
    ) as transition_name,
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
FROM instruction_branches
ORDER BY branch_id;

-- Step 3: Update the sequence to match max branch_id
SELECT setval('transitions_transition_id_seq', (SELECT MAX(branch_id) FROM instruction_branches));

-- Step 4: Create indexes
CREATE INDEX idx_transitions_instruction ON transitions(instruction_id) WHERE enabled = true;
CREATE INDEX idx_transitions_priority ON transitions(instruction_id, branch_priority DESC) WHERE enabled = true;
CREATE INDEX idx_transitions_enabled ON transitions(enabled);

-- Step 5: Update foreign key in instruction_branch_executions
ALTER TABLE instruction_branch_executions DROP CONSTRAINT fk_branch;
ALTER TABLE instruction_branch_executions RENAME COLUMN branch_id TO transition_id;
ALTER TABLE instruction_branch_executions ADD CONSTRAINT fk_transition 
    FOREIGN KEY (transition_id) REFERENCES transitions(transition_id) ON DELETE CASCADE;

-- Step 6: Rename instruction_branch_executions to transition_executions for consistency
ALTER TABLE instruction_branch_executions RENAME TO transition_executions;

-- Step 7: Drop old table
DROP TABLE instruction_branches CASCADE;

-- Step 8: Add comprehensive comments
COMMENT ON TABLE transitions IS 
'Conditional control flow for instructions (6 entries).
Transitions define if/else/switch logic that routes execution between instructions or conversations.
Key to Turing completeness: enables conditionals, loops (max_iterations), and state transitions.
Evaluation order: branch_priority DESC → first matching branch_condition wins.
Pattern: transition_id (INTEGER PK) + transition_name (TEXT).';

COMMENT ON COLUMN transitions.transition_id IS 
'Primary key - unique identifier for this transition';

COMMENT ON COLUMN transitions.transition_name IS 
'Human-readable name for this transition (e.g., "Pass to format", "Fail to improvement", "Error handler")';

COMMENT ON COLUMN transitions.instruction_id IS 
'FK to instructions - source instruction. After this instruction executes, evaluate its transitions.';

COMMENT ON COLUMN transitions.branch_condition IS 
'Regex pattern to match against instruction output.
Examples:
  - "^\\[PASS\\]" for exact prefix match
  - ".*error.*" for substring match
  - "*" for catch-all (default/fallback)
Evaluated in branch_priority order.';

COMMENT ON COLUMN transitions.next_instruction_id IS 
'FK to instructions - target instruction to execute if condition matches (same conversation).
NULL with NULL next_conversation_id = end conversation.';

COMMENT ON COLUMN transitions.next_conversation_id IS 
'FK to conversations - target conversation to jump to if condition matches (cross-conversation jump).
Mutually exclusive with next_instruction_id (enforced by chk_branch_target).';

COMMENT ON COLUMN transitions.max_iterations IS 
'Maximum times this transition can be taken within a single execution (loop guard).
NULL = unlimited. Prevents infinite loops in retry logic.';

COMMENT ON COLUMN transitions.branch_priority IS 
'Evaluation order (DESC). Higher priority = evaluated first.
Guidelines:
  - 10 = exact match (specific patterns)
  - 5 = common patterns (PASS/FAIL) [default]
  - 1 = loose patterns (fuzzy matching)
  - 0 = catch-all (*)';

COMMENT ON COLUMN transitions.branch_description IS 
'Detailed explanation of what this transition does.
Examples:
  - "If grading passes, skip improvement and go directly to format"
  - "If failed 3 times, create error ticket"
  - "On unexpected output format, route to error handler"';

COMMENT ON COLUMN transitions.enabled IS 
'If false, this transition is skipped during evaluation (soft delete)';

COMMENT ON COLUMN transitions.created_at IS 
'Timestamp when this transition was first created';

COMMENT ON COLUMN transitions.updated_at IS 
'Timestamp when this transition was last modified';

-- Step 9: Verification
SELECT 
    'transitions' as new_table_name,
    COUNT(*) as row_count,
    'Renamed from instruction_branches, transition_name added' as status
FROM transitions;

COMMIT;
