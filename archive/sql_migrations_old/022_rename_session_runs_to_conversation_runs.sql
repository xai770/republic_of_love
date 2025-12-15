-- Migration 022: Rename session_runs to conversation_runs
-- Date: 2025-10-31
-- Purpose: Rename session_runs table to conversation_runs for consistency
--          Update session_run_id to conversation_run_id
--          Add conversation_run_name column (position 2)

-- This migration renames session_runs to conversation_runs because:
-- 1. Sessions were already renamed to conversations (migration 017)
-- 2. This table tracks execution instances of conversations
-- 3. Consistency: conversation → conversation_runs (not session_runs)

BEGIN;

-- Step 1: Rename the sequence
ALTER SEQUENCE session_runs_session_run_id_seq RENAME TO conversation_runs_conversation_run_id_seq;

-- Step 2: Rename the history table if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'session_runs_history') THEN
        ALTER TABLE session_runs_history RENAME TO conversation_runs_history;
        ALTER TABLE conversation_runs_history RENAME COLUMN session_run_id TO conversation_run_id;
    END IF;
END $$;

-- Step 3: Export data and prepare for column addition
CREATE TABLE conversation_runs_temp (
    conversation_run_id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    workflow_step_id INTEGER NOT NULL,
    execution_order INTEGER NOT NULL,
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    status TEXT DEFAULT 'PENDING',
    llm_conversation_id TEXT,
    quality_score TEXT,
    validation_status TEXT,
    error_details TEXT,
    run_id INTEGER NOT NULL,
    run_type TEXT NOT NULL
);

-- Copy data from session_runs
INSERT INTO conversation_runs_temp (
    conversation_run_id,
    conversation_id,
    workflow_step_id,
    execution_order,
    started_at,
    completed_at,
    status,
    llm_conversation_id,
    quality_score,
    validation_status,
    error_details,
    run_id,
    run_type
)
SELECT 
    session_run_id,
    conversation_id,
    workflow_step_id,
    execution_order,
    started_at,
    completed_at,
    status,
    llm_conversation_id,
    quality_score,
    validation_status,
    error_details,
    run_id,
    run_type
FROM session_runs;

-- Step 4: Drop old table (CASCADE will drop FK constraints)
DROP TABLE session_runs CASCADE;

-- Step 5: Create new table with conversation_run_name in position 2
CREATE TABLE conversation_runs (
    conversation_run_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_run_name TEXT UNIQUE NOT NULL,
    conversation_id INTEGER NOT NULL,
    workflow_step_id INTEGER NOT NULL,
    execution_order INTEGER NOT NULL,
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    status TEXT DEFAULT 'PENDING',
    llm_conversation_id TEXT,
    quality_score TEXT,
    validation_status TEXT,
    error_details TEXT,
    run_id INTEGER NOT NULL,
    run_type TEXT NOT NULL,
    CONSTRAINT conversation_runs_status_check CHECK (status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'TIMEOUT'::text, 'ERROR'::text])),
    CONSTRAINT conversation_runs_quality_score_check CHECK (quality_score = ANY (ARRAY['A'::text, 'B'::text, 'C'::text, 'D'::text, 'F'::text, NULL::text])),
    CONSTRAINT conversation_runs_validation_status_check CHECK (validation_status = ANY (ARRAY['PASS'::text, 'FAIL'::text, NULL::text])),
    CONSTRAINT conversation_runs_run_type_check CHECK (run_type = ANY (ARRAY['testing'::text, 'production'::text]))
);

-- Step 6: Set the sequence to continue from the last value
SELECT setval('conversation_runs_conversation_run_id_seq', (SELECT MAX(conversation_run_id) FROM conversation_runs_temp));

-- Step 7: Insert data with OVERRIDING SYSTEM VALUE and generate conversation_run_name
INSERT INTO conversation_runs (
    conversation_run_id,
    conversation_run_name,
    conversation_id,
    workflow_step_id,
    execution_order,
    started_at,
    completed_at,
    status,
    llm_conversation_id,
    quality_score,
    validation_status,
    error_details,
    run_id,
    run_type
) OVERRIDING SYSTEM VALUE
SELECT 
    conversation_run_id,
    'conv_run_' || conversation_run_id AS conversation_run_name,
    conversation_id,
    workflow_step_id,
    execution_order,
    started_at,
    completed_at,
    status,
    llm_conversation_id,
    quality_score,
    validation_status,
    error_details,
    run_id,
    run_type
FROM conversation_runs_temp;

-- Step 8: Drop temporary table
DROP TABLE conversation_runs_temp;

-- Step 9: Recreate indexes
CREATE INDEX idx_conversation_runs_conversation ON conversation_runs(conversation_id);
CREATE INDEX idx_conversation_runs_status ON conversation_runs(status);

-- Step 10: Add foreign key constraints
ALTER TABLE conversation_runs 
    ADD CONSTRAINT conversation_runs_conversation_id_fkey 
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id);

ALTER TABLE conversation_runs 
    ADD CONSTRAINT conversation_runs_workflow_step_id_fkey 
    FOREIGN KEY (workflow_step_id) REFERENCES workflow_steps(step_id);

-- Step 11: Recreate foreign keys from other tables
ALTER TABLE human_tasks 
    ADD CONSTRAINT human_tasks_conversation_run_id_fkey 
    FOREIGN KEY (session_run_id) REFERENCES conversation_runs(conversation_run_id);

ALTER TABLE instruction_runs 
    ADD CONSTRAINT instruction_runs_conversation_run_id_fkey 
    FOREIGN KEY (session_run_id) REFERENCES conversation_runs(conversation_run_id);

-- Step 12: Rename archive function if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'archive_session_runs') THEN
        ALTER FUNCTION archive_session_runs() RENAME TO archive_conversation_runs;
    END IF;
END $$;

-- Step 13: Create trigger if archive function exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'archive_conversation_runs') THEN
        EXECUTE 'CREATE TRIGGER conversation_runs_history_trigger
                 BEFORE UPDATE ON conversation_runs
                 FOR EACH ROW
                 EXECUTE FUNCTION archive_conversation_runs()';
    END IF;
END $$;

-- Step 14: Add comprehensive comments
COMMENT ON TABLE conversation_runs IS 'Execution instances of conversations within workflow steps. Each conversation_run tracks when and how a conversation was executed, maintaining output history for all instructions. Primary actors have access to ALL previous instruction outputs, enabling multi-step reasoning chains and data transformation pipelines. Execution flow: workflow_run → conversation_runs (ordered by execution_order) → instruction_runs (sequential). Run types: testing (uses test_cases) or production (uses real job postings).';
COMMENT ON COLUMN conversation_runs.conversation_run_id IS 'Unique identifier for this conversation execution instance';
COMMENT ON COLUMN conversation_runs.conversation_run_name IS 'Human-readable name for this conversation run';
COMMENT ON COLUMN conversation_runs.conversation_id IS 'Foreign key to conversations table - which conversation was executed';
COMMENT ON COLUMN conversation_runs.workflow_step_id IS 'Foreign key to workflow_steps table - which workflow step this execution belongs to';
COMMENT ON COLUMN conversation_runs.execution_order IS 'Sequential order of this conversation run within the workflow step';
COMMENT ON COLUMN conversation_runs.started_at IS 'Timestamp when this conversation run started';
COMMENT ON COLUMN conversation_runs.completed_at IS 'Timestamp when this conversation run completed (NULL if still running)';
COMMENT ON COLUMN conversation_runs.status IS 'Execution status: PENDING, RUNNING, SUCCESS, FAILED, TIMEOUT, or ERROR';
COMMENT ON COLUMN conversation_runs.llm_conversation_id IS 'External LLM conversation identifier for tracking API calls';
COMMENT ON COLUMN conversation_runs.quality_score IS 'Quality grade for this execution: A, B, C, D, or F';
COMMENT ON COLUMN conversation_runs.validation_status IS 'Validation result: PASS or FAIL';
COMMENT ON COLUMN conversation_runs.error_details IS 'Error message or stack trace if status is FAILED or ERROR';
COMMENT ON COLUMN conversation_runs.run_id IS 'Identifier for the parent run (workflow_run_id or production_run_id)';
COMMENT ON COLUMN conversation_runs.run_type IS 'Type of run: testing (test_cases) or production (real data)';

COMMIT;

-- Verification queries (run after migration)
-- SELECT COUNT(*) FROM conversation_runs;  -- Should show 1267
-- SELECT conversation_run_id, conversation_run_name, conversation_id, status FROM conversation_runs LIMIT 5;
-- \d conversation_runs
