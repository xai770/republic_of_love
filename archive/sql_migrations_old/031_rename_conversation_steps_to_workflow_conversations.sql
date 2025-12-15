-- Migration 031: Rename conversation_steps → workflow_conversations
-- Purpose: Clarify that this table orchestrates which conversations belong to which workflows
-- Date: 2025-11-01
-- Author: Arden (AI) + User

BEGIN;

-- Drop existing constraints and indexes
ALTER TABLE conversation_steps DROP CONSTRAINT IF EXISTS conversation_steps_conversation_id_fkey;
ALTER TABLE conversation_steps DROP CONSTRAINT IF EXISTS conversation_steps_depends_on_step_id_fkey;
ALTER TABLE conversation_steps DROP CONSTRAINT IF EXISTS conversation_steps_workflow_id_fkey;
ALTER TABLE conversation_steps DROP CONSTRAINT IF EXISTS conversation_steps_execute_condition_check;
ALTER TABLE conversation_steps DROP CONSTRAINT IF EXISTS conversation_steps_on_failure_action_check;
ALTER TABLE conversation_steps DROP CONSTRAINT IF EXISTS conversation_steps_on_success_action_check;

-- Rename the table
ALTER TABLE conversation_steps RENAME TO workflow_conversations;

-- Rename the primary key sequence
ALTER SEQUENCE conversation_steps_step_id_seq RENAME TO workflow_conversations_step_id_seq;

-- Rename indexes
ALTER INDEX conversation_steps_pkey RENAME TO workflow_conversations_pkey;
ALTER INDEX conversation_steps_workflow_id_execution_order_key RENAME TO workflow_conversations_workflow_id_execution_order_key;
ALTER INDEX idx_conversation_steps_conversation RENAME TO idx_workflow_conversations_conversation;
ALTER INDEX idx_conversation_steps_order RENAME TO idx_workflow_conversations_order;
ALTER INDEX idx_conversation_steps_workflow RENAME TO idx_workflow_conversations_workflow;

-- Recreate foreign keys with new names
ALTER TABLE workflow_conversations 
    ADD CONSTRAINT workflow_conversations_conversation_id_fkey 
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id);

ALTER TABLE workflow_conversations 
    ADD CONSTRAINT workflow_conversations_depends_on_step_id_fkey 
    FOREIGN KEY (depends_on_step_id) REFERENCES workflow_conversations(step_id);

ALTER TABLE workflow_conversations 
    ADD CONSTRAINT workflow_conversations_workflow_id_fkey 
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id);

-- Recreate check constraints with new names
ALTER TABLE workflow_conversations 
    ADD CONSTRAINT workflow_conversations_execute_condition_check 
    CHECK (execute_condition = ANY (ARRAY['always'::text, 'on_success'::text, 'on_failure'::text]));

ALTER TABLE workflow_conversations 
    ADD CONSTRAINT workflow_conversations_on_failure_action_check 
    CHECK (on_failure_action = ANY (ARRAY['stop'::text, 'retry'::text, 'skip_to'::text]));

ALTER TABLE workflow_conversations 
    ADD CONSTRAINT workflow_conversations_on_success_action_check 
    CHECK (on_success_action = ANY (ARRAY['continue'::text, 'skip_to'::text, 'stop'::text]));

-- Update the foreign key reference in conversation_runs
ALTER TABLE conversation_runs DROP CONSTRAINT IF EXISTS conversation_runs_conversation_step_id_fkey;
ALTER TABLE conversation_runs 
    ADD CONSTRAINT conversation_runs_workflow_step_id_fkey 
    FOREIGN KEY (workflow_step_id) REFERENCES workflow_conversations(step_id);

-- Add comment explaining the table's purpose
COMMENT ON TABLE workflow_conversations IS 
'Cross-reference table orchestrating which conversations belong to which workflows. 
Each row defines: workflow X executes conversation Y at position Z with specified control flow.
This enables conversation reusability across multiple workflows.';

COMMENT ON COLUMN workflow_conversations.step_id IS 'Primary key for this workflow-conversation association';
COMMENT ON COLUMN workflow_conversations.workflow_id IS 'Which workflow this conversation belongs to';
COMMENT ON COLUMN workflow_conversations.conversation_id IS 'Which conversation to execute (reusable across workflows)';
COMMENT ON COLUMN workflow_conversations.execution_order IS 'Sequential position within the workflow (1, 2, 3...)';
COMMENT ON COLUMN workflow_conversations.execute_condition IS 'When to execute: always, on_success, on_failure';
COMMENT ON COLUMN workflow_conversations.depends_on_step_id IS 'Optional: this step depends on another step completing first';
COMMENT ON COLUMN workflow_conversations.on_success_action IS 'What to do if conversation succeeds: continue, skip_to, stop';
COMMENT ON COLUMN workflow_conversations.on_failure_action IS 'What to do if conversation fails: stop, retry, skip_to';
COMMENT ON COLUMN workflow_conversations.on_success_goto_order IS 'If on_success_action=skip_to, jump to this execution_order';
COMMENT ON COLUMN workflow_conversations.on_failure_goto_order IS 'If on_failure_action=skip_to, jump to this execution_order';
COMMENT ON COLUMN workflow_conversations.max_retry_attempts IS 'Maximum retry attempts if on_failure_action=retry';

COMMIT;

-- Verification query
SELECT 
    'workflow_conversations' as table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT workflow_id) as unique_workflows,
    COUNT(DISTINCT conversation_id) as unique_conversations
FROM workflow_conversations;
