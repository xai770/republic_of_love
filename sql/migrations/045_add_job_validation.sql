-- Migration 045: Add Job Description Validation
-- Date: November 26, 2025
-- Purpose: Defense-in-depth validation to prevent processing postings with NULL/short job_description
-- Issue: Run 179 processed posting 4797 through 13 interactions with NULL description, wasting LLM resources

BEGIN;

-- Step 1: Create validation conversation (auto-generate ID)
INSERT INTO conversations (conversation_name, actor_id, conversation_description)
VALUES ('Validate Job Description', 74, 'Validates job_description exists and meets minimum quality standards')
RETURNING conversation_id \gset validation_

-- Step 2: Create instruction (use captured conversation_id)
INSERT INTO instructions (conversation_id, instruction_name, step_number, prompt_template)
VALUES (:validation_conversation_id, 'Check job_description quality', 1, '{
  "query": "SELECT CASE WHEN job_description IS NULL THEN ''[NO_DESCRIPTION]'' WHEN LENGTH(job_description) < 100 THEN ''[TOO_SHORT]'' ELSE ''[VALID]'' END as validation_result FROM postings WHERE posting_id = {posting_id}",
  "result_field": "validation_result"
}')
RETURNING instruction_id \gset validation_

-- Step 3: Add branching logic (use captured instruction_id)
INSERT INTO instruction_steps (instruction_id, instruction_step_name, branch_condition, next_conversation_id, branch_priority)
VALUES 
  (:validation_instruction_id, 'Valid description - continue to Check Summary', '[VALID]', 9184, 10),
  (:validation_instruction_id, 'No description - end workflow', '[NO_DESCRIPTION]', NULL, 10),
  (:validation_instruction_id, 'Description too short - end workflow', '[TOO_SHORT]', NULL, 10);

-- Step 4: Shift workflow execution order (make room for step 2)
-- Use a temporary large offset to avoid conflicts, then set correct values
UPDATE workflow_conversations
SET execution_order = execution_order + 1000
WHERE workflow_id = 3001 AND execution_order >= 2;

UPDATE workflow_conversations
SET execution_order = execution_order - 999
WHERE workflow_id = 3001 AND execution_order > 1000;

-- Step 5: Insert validation into workflow at step 2 (use captured conversation_id)
INSERT INTO workflow_conversations (workflow_id, conversation_id, execution_order)
VALUES (3001, :validation_conversation_id, 2);

-- Step 6: Update Job Fetcher branching (both success and rate-limited)
UPDATE instruction_steps
SET next_conversation_id = :validation_conversation_id
WHERE instruction_step_id IN (32, 83);

-- Step 7: Add comment for documentation
COMMENT ON TABLE workflow_conversations IS 'Maps conversations to workflows in execution order. Step 2 (validation) added Nov 26, 2025 to prevent processing postings with NULL/short job_description.';

-- Verification query (will show after commit)
SELECT 'Migration 045 applied successfully!' as status;
SELECT 'New conversation_id: ' || :validation_conversation_id as conversation;
SELECT 'New instruction_id: ' || :validation_instruction_id as instruction;

COMMIT;

-- Post-commit verification
SELECT execution_order, c.conversation_id, c.conversation_name 
FROM workflow_conversations wc 
JOIN conversations c ON wc.conversation_id = c.conversation_id 
WHERE wc.workflow_id = 3001 
ORDER BY execution_order
LIMIT 5;
