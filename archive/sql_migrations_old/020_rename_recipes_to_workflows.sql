-- Migration 020: Rename recipes to workflows
-- Date: 2025-10-31
-- Purpose: Rename recipes to workflows for better clarity.
--          "Workflows" is industry-standard, instantly intuitive, and self-documenting.
--          No column reordering needed (workflow_id, workflow_name already in correct order).

BEGIN;

-- Step 1: Rename the table
ALTER TABLE recipes RENAME TO workflows;

-- Step 2: Rename the primary key sequence
ALTER SEQUENCE recipes_recipe_id_seq RENAME TO workflows_workflow_id_seq;

-- Step 3: Rename columns
ALTER TABLE workflows RENAME COLUMN recipe_id TO workflow_id;
ALTER TABLE workflows RENAME COLUMN recipe_name TO workflow_name;
ALTER TABLE workflows RENAME COLUMN recipe_description TO workflow_description;
ALTER TABLE workflows RENAME COLUMN recipe_version TO workflow_version;

-- Step 4: Rename constraints
ALTER TABLE workflows RENAME CONSTRAINT recipes_pkey TO workflows_pkey;
ALTER TABLE workflows RENAME CONSTRAINT recipes_recipe_name_recipe_version_key TO workflows_workflow_name_workflow_version_key;

-- Step 5: Rename indexes
ALTER INDEX idx_recipes_enabled RENAME TO idx_workflows_enabled;
ALTER INDEX idx_recipes_name RENAME TO idx_workflows_name;
ALTER INDEX idx_recipes_documentation_fts RENAME TO idx_workflows_documentation_fts;

-- Step 6: Rename history table and columns
ALTER TABLE recipes_history RENAME TO workflows_history;
ALTER TABLE workflows_history RENAME COLUMN recipe_id TO workflow_id;
ALTER TABLE workflows_history RENAME COLUMN recipe_name TO workflow_name;
ALTER TABLE workflows_history RENAME COLUMN recipe_description TO workflow_description;
ALTER TABLE workflows_history RENAME COLUMN recipe_version TO workflow_version;

-- Step 7: Rename archive function and trigger
ALTER FUNCTION archive_recipes RENAME TO archive_workflows;
DROP TRIGGER recipes_history_trigger ON workflows;
CREATE TRIGGER workflows_history_trigger
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION archive_workflows();

-- Step 8: Update foreign keys in other tables
ALTER TABLE production_runs DROP CONSTRAINT production_runs_recipe_id_fkey;
ALTER TABLE production_runs RENAME COLUMN recipe_id TO workflow_id;
ALTER TABLE production_runs ADD CONSTRAINT production_runs_workflow_id_fkey 
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id);

ALTER TABLE recipe_runs DROP CONSTRAINT recipe_runs_recipe_id_fkey;
ALTER TABLE recipe_runs RENAME COLUMN recipe_id TO workflow_id;
ALTER TABLE recipe_runs ADD CONSTRAINT recipe_runs_workflow_id_fkey 
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id);

ALTER TABLE recipe_sessions DROP CONSTRAINT recipe_sessions_recipe_id_fkey;
ALTER TABLE recipe_sessions RENAME COLUMN recipe_id TO workflow_id;
ALTER TABLE recipe_sessions ADD CONSTRAINT recipe_sessions_workflow_id_fkey 
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id);

ALTER TABLE variations DROP CONSTRAINT variations_recipe_id_fkey;
ALTER TABLE variations RENAME COLUMN recipe_id TO workflow_id;
ALTER TABLE variations ADD CONSTRAINT variations_workflow_id_fkey 
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id) ON DELETE CASCADE;

-- Step 9: Rename recipe_runs table for consistency
ALTER TABLE recipe_runs RENAME TO workflow_runs;
ALTER TABLE workflow_runs RENAME COLUMN recipe_run_id TO workflow_run_id;
ALTER SEQUENCE recipe_runs_recipe_run_id_seq RENAME TO workflow_runs_workflow_run_id_seq;
ALTER TABLE workflow_runs RENAME CONSTRAINT recipe_runs_pkey TO workflow_runs_pkey;
ALTER INDEX idx_recipe_runs_recipe RENAME TO idx_workflow_runs_workflow;
ALTER INDEX idx_recipe_runs_status RENAME TO idx_workflow_runs_status;
ALTER INDEX idx_recipe_runs_batch RENAME TO idx_workflow_runs_batch;
ALTER INDEX idx_recipe_runs_variation RENAME TO idx_workflow_runs_variation;
ALTER INDEX idx_recipe_runs_user RENAME TO idx_workflow_runs_user;
ALTER INDEX idx_recipe_runs_batch_tracking RENAME TO idx_workflow_runs_batch_tracking;
ALTER INDEX idx_recipe_runs_execution_mode RENAME TO idx_workflow_runs_execution_mode;
ALTER INDEX recipe_runs_unique_success_batch RENAME TO workflow_runs_unique_success_batch;

-- Step 10: Rename recipe_sessions table for consistency
ALTER TABLE recipe_sessions RENAME TO workflow_steps;
ALTER SEQUENCE recipe_sessions_recipe_session_id_seq RENAME TO workflow_steps_step_id_seq;
ALTER TABLE workflow_steps RENAME COLUMN recipe_session_id TO step_id;
ALTER TABLE workflow_steps RENAME CONSTRAINT recipe_sessions_pkey TO workflow_steps_pkey;
ALTER TABLE workflow_steps RENAME CONSTRAINT recipe_sessions_recipe_id_execution_order_key TO workflow_steps_workflow_id_execution_order_key;
ALTER TABLE workflow_steps RENAME CONSTRAINT recipe_sessions_depends_on_recipe_session_id_fkey TO workflow_steps_depends_on_step_id_fkey;
ALTER TABLE workflow_steps RENAME COLUMN depends_on_recipe_session_id TO depends_on_step_id;
ALTER INDEX idx_recipe_sessions_recipe RENAME TO idx_workflow_steps_workflow;
ALTER INDEX idx_recipe_sessions_order RENAME TO idx_workflow_steps_order;
ALTER INDEX idx_recipe_sessions_session RENAME TO idx_workflow_steps_conversation;

-- Step 11: Update foreign keys referencing recipe_session_id
ALTER TABLE session_runs DROP CONSTRAINT session_runs_recipe_session_id_fkey;
ALTER TABLE session_runs RENAME COLUMN recipe_session_id TO workflow_step_id;
ALTER TABLE session_runs ADD CONSTRAINT session_runs_workflow_step_id_fkey 
    FOREIGN KEY (workflow_step_id) REFERENCES workflow_steps(step_id);

-- Step 12: Update table and column comments
COMMENT ON TABLE workflows IS 
'Executable workflows that orchestrate multiple conversations (66 entries).
A workflow is a program: it sequences conversations, handles dependencies, and manages control flow.
Think of it as a function that calls multiple subroutines (conversations) in a specific order.
Key to Turing completeness: workflows compose atomic conversations into complex algorithms.
Versioned for iteration: workflow_name + workflow_version = unique workflow definition.
Renamed from recipes 2025-10-31 for clarity (workflows is industry-standard term).
Pattern: workflow_id (INTEGER PK) + workflow_name (TEXT).';

COMMENT ON COLUMN workflows.workflow_id IS 
'Primary key - unique identifier for this workflow';

COMMENT ON COLUMN workflows.workflow_name IS 
'Human-readable name (e.g., "Job Quality Pipeline", "Skill Extraction Workflow")';

COMMENT ON COLUMN workflows.workflow_description IS 
'Brief description of what this workflow does and when to use it';

COMMENT ON COLUMN workflows.workflow_version IS 
'Version number for iterating on workflow logic (1, 2, 3...). workflow_name + workflow_version must be unique.';

COMMENT ON COLUMN workflows.max_total_session_runs IS 
'Maximum total conversation executions allowed across all workflow steps (prevents infinite loops).
Workflow-level execution budget. Default: 100.';

COMMENT ON TABLE workflow_steps IS 
'Workflow execution steps: which conversations to run in which order (formerly recipe_sessions).
Each step links a workflow to a conversation with execution order and control flow logic.';

COMMENT ON COLUMN workflow_steps.step_id IS 
'Primary key - unique identifier for this workflow step';

COMMENT ON COLUMN workflow_steps.workflow_id IS 
'FK to workflows - which workflow this step belongs to';

COMMENT ON COLUMN workflow_steps.conversation_id IS 
'FK to conversations - which conversation to execute in this step';

COMMENT ON COLUMN workflow_steps.execution_order IS 
'Sequential order of execution within the workflow (1, 2, 3, ...)';

-- Step 13: Verification
SELECT 
    'workflows' as new_table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT workflow_name) as unique_names,
    'Renamed from recipes for clarity' as status
FROM workflows;

COMMIT;
