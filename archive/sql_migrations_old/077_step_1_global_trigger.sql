-- Migration 077: Add global workflow trigger for Step 1 (Fetch Jobs)
--
-- Problem: Step 1 doesn't operate on postings - it CREATES them
-- Solution: Add workflow-level "pre-execution" step that runs ONCE per workflow execution
--
-- This allows Step 1 to:
-- 1. Check if it's been 24h since last fetch
-- 2. Fetch new jobs if needed
-- 3. Then proceed with normal posting-based processing

-- Add column to workflow_conversations for global execution (not per-posting)
ALTER TABLE workflow_conversations 
ADD COLUMN IF NOT EXISTS execute_once_per_run BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN workflow_conversations.execute_once_per_run IS 
'If TRUE, this step executes ONCE at workflow start (not per-posting). Used for data ingestion steps like "Fetch Jobs from API".';

-- Mark Step 1 as execute-once-per-run
UPDATE workflow_conversations
SET execute_once_per_run = TRUE
WHERE workflow_id = 3001 
  AND execution_order = 1;

-- Verify configuration
SELECT 
    wc.execution_order,
    c.conversation_name,
    wc.execute_once_per_run,
    wc.is_entry_point,
    LEFT(wc.entry_condition, 60) as condition_preview
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
WHERE wc.workflow_id = 3001 
  AND (wc.execute_once_per_run = TRUE OR wc.is_entry_point = TRUE)
ORDER BY wc.execution_order;
