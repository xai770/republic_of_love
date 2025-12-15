-- Migration 024: Rename workflow_steps to conversation_steps
-- Date: 2025-10-31
-- Purpose: Rename workflow_steps to conversation_steps for clarity
--          Reflects that these steps define which conversations run in a workflow
--          Part of consistent naming: conversation_steps (workflow level), instruction_steps (conversation level)

-- This migration renames workflow_steps to conversation_steps because:
-- 1. workflow_steps defines which CONVERSATIONS to run (not generic steps)
-- 2. Parallel naming with instruction_steps (migration 025)
-- 3. Makes hierarchy clear: workflows orchestrate conversations, conversations orchestrate instructions

BEGIN;

-- Step 1: Rename the sequence
ALTER SEQUENCE workflow_steps_step_id_seq RENAME TO conversation_steps_step_id_seq;

-- Step 2: Rename the history table if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'workflow_steps_history') THEN
        ALTER TABLE workflow_steps_history RENAME TO conversation_steps_history;
    END IF;
END $$;

-- Step 3: Rename the table
ALTER TABLE workflow_steps RENAME TO conversation_steps;

-- Step 4: Rename indexes
ALTER INDEX workflow_steps_pkey RENAME TO conversation_steps_pkey;
ALTER INDEX idx_workflow_steps_conversation RENAME TO idx_conversation_steps_conversation;
ALTER INDEX idx_workflow_steps_order RENAME TO idx_conversation_steps_order;
ALTER INDEX idx_workflow_steps_workflow RENAME TO idx_conversation_steps_workflow;
ALTER INDEX workflow_steps_workflow_id_execution_order_key RENAME TO conversation_steps_workflow_id_execution_order_key;

-- Step 5: Rename foreign key constraints
ALTER TABLE conversation_steps 
    DROP CONSTRAINT recipe_sessions_conversation_id_fkey,
    ADD CONSTRAINT conversation_steps_conversation_id_fkey 
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id);

ALTER TABLE conversation_steps 
    DROP CONSTRAINT recipe_sessions_workflow_id_fkey,
    ADD CONSTRAINT conversation_steps_workflow_id_fkey 
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id);

ALTER TABLE conversation_steps 
    DROP CONSTRAINT workflow_steps_depends_on_step_id_fkey,
    ADD CONSTRAINT conversation_steps_depends_on_step_id_fkey 
    FOREIGN KEY (depends_on_step_id) REFERENCES conversation_steps(step_id);

-- Step 6: Update check constraints
ALTER TABLE conversation_steps 
    DROP CONSTRAINT recipe_sessions_execute_condition_check,
    ADD CONSTRAINT conversation_steps_execute_condition_check 
    CHECK (execute_condition = ANY (ARRAY['always'::text, 'on_success'::text, 'on_failure'::text]));

ALTER TABLE conversation_steps 
    DROP CONSTRAINT recipe_sessions_on_failure_action_check,
    ADD CONSTRAINT conversation_steps_on_failure_action_check 
    CHECK (on_failure_action = ANY (ARRAY['stop'::text, 'retry'::text, 'skip_to'::text]));

ALTER TABLE conversation_steps 
    DROP CONSTRAINT recipe_sessions_on_success_action_check,
    ADD CONSTRAINT conversation_steps_on_success_action_check 
    CHECK (on_success_action = ANY (ARRAY['continue'::text, 'skip_to'::text, 'stop'::text]));

-- Step 7: Update foreign keys from other tables
ALTER TABLE conversation_runs 
    DROP CONSTRAINT conversation_runs_workflow_step_id_fkey,
    ADD CONSTRAINT conversation_runs_conversation_step_id_fkey 
    FOREIGN KEY (workflow_step_id) REFERENCES conversation_steps(step_id);

-- Step 8: Rename archive function if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'archive_workflow_steps') THEN
        ALTER FUNCTION archive_workflow_steps() RENAME TO archive_conversation_steps;
    END IF;
END $$;

-- Step 9: Create trigger if archive function exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'archive_conversation_steps') THEN
        EXECUTE 'DROP TRIGGER IF EXISTS workflow_steps_history_trigger ON conversation_steps';
        EXECUTE 'CREATE TRIGGER conversation_steps_history_trigger
                 BEFORE UPDATE ON conversation_steps
                 FOR EACH ROW
                 EXECUTE FUNCTION archive_conversation_steps()';
    END IF;
END $$;

-- Step 10: Add comprehensive comments
COMMENT ON TABLE conversation_steps IS 'Defines which conversations to execute within a workflow and in what order.
Each step links a workflow to a conversation with execution order and simple success/fail branching logic.

Hierarchy:
- workflows orchestrate conversations (via conversation_steps)
- conversations orchestrate instructions (via instruction_steps, formerly transitions)
- instructions execute tasks (via actors)

Branching Logic (Simple):
- execute_condition: always, on_success, on_failure
- on_success_action: continue, skip_to, stop
- on_failure_action: stop, retry, skip_to
- on_success_goto_order, on_failure_goto_order: target execution order for skip_to

Unlike instruction_steps (complex conditional branching), conversation_steps use simple success/fail outcomes
because conversations either succeed or fail as a unit (job found, posting analyzed, report sent).

Formerly: recipe_sessions → workflow_steps → conversation_steps (migration 020, 024).';

COMMENT ON COLUMN conversation_steps.step_id IS 'Unique identifier for this conversation step';
COMMENT ON COLUMN conversation_steps.workflow_id IS 'Foreign key to workflows table - which workflow this step belongs to';
COMMENT ON COLUMN conversation_steps.conversation_id IS 'Foreign key to conversations table - which conversation to execute';
COMMENT ON COLUMN conversation_steps.execution_order IS 'Sequential order of this conversation within the workflow (1, 2, 3...)';
COMMENT ON COLUMN conversation_steps.execute_condition IS 'When to execute this step: always, on_success (prev step succeeded), on_failure (prev step failed)';
COMMENT ON COLUMN conversation_steps.depends_on_step_id IS 'Foreign key to another conversation_step - dependency that must complete first';
COMMENT ON COLUMN conversation_steps.on_success_action IS 'What to do if conversation succeeds: continue (next step), skip_to (goto order), stop (end workflow)';
COMMENT ON COLUMN conversation_steps.on_failure_action IS 'What to do if conversation fails: stop (end workflow), retry (try again), skip_to (goto order)';
COMMENT ON COLUMN conversation_steps.on_success_goto_order IS 'Target execution_order to jump to if on_success_action=skip_to';
COMMENT ON COLUMN conversation_steps.on_failure_goto_order IS 'Target execution_order to jump to if on_failure_action=skip_to';
COMMENT ON COLUMN conversation_steps.max_retry_attempts IS 'Maximum number of retry attempts if on_failure_action=retry';
COMMENT ON COLUMN conversation_steps.created_at IS 'Timestamp when this conversation step was created';

COMMIT;

-- Verification queries (run after migration)
-- SELECT COUNT(*) FROM conversation_steps;  -- Should show 55
-- SELECT step_id, workflow_id, conversation_id, execution_order FROM conversation_steps LIMIT 5;
-- \d conversation_steps
