-- Migration 072: Fix Step 2 Idempotency and Routing
-- ====================================================
-- Problem 1: Step 2 checked workflow history, not database state
--            Postings with NULL summary still routed to [SKIP]
-- Problem 2: [SKIP] routed to Step 10 (Save Summary) with unrendered placeholder
--
-- Solution 1: Check database state (summary exists and valid)
-- Solution 2: Route [SKIP] to Step 11 (bypass Save Summary)

-- Update Step 2's idempotency check to verify actual database state
UPDATE instructions
SET prompt_template = '{
  "query": "SELECT EXISTS(SELECT 1 FROM postings p WHERE p.posting_id = {posting_id} AND p.extracted_summary IS NOT NULL AND p.extracted_summary != ''{session_4_output}'' AND p.extracted_summary != ''{conversation_3341_output}'' AND LENGTH(p.extracted_summary) > 50) as summary_exists",
  "result_field": "summary_exists",
  "branch_map": {
    "true": "[SKIP]",
    "false": "[RUN]",
    "null": "[RUN]",
    "error": "[RUN]"
  }
}'::jsonb,
updated_at = CURRENT_TIMESTAMP
WHERE instruction_id = 3399;

-- Update Step 2's [SKIP] branch to bypass Save Summary step
UPDATE instruction_steps
SET next_conversation_id = 9185,  -- Check if Skills Exist (Step 11)
    updated_at = CURRENT_TIMESTAMP
WHERE instruction_id = 3399
  AND branch_condition = '[SKIP]'
  AND next_conversation_id = 9168;  -- Was: Save Summary (Step 10)
