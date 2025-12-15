-- Migration 018: Entry Point Routing
-- ====================================
--
-- Add is_entry_point flag to workflow_conversations to explicitly mark
-- where postings can enter the workflow (instead of complex SQL logic).
--
-- Benefits:
-- - Clear configuration (no hidden routing logic in code)
-- - Easy to modify entry points via database
-- - Simpler _get_pending_postings() query
--
-- Example workflow stages:
-- - extract_summary (is_entry_point=true) - postings without summary
-- - extract_skills (is_entry_point=true) - postings with summary but no skills
-- - calculate_ihl (is_entry_point=true) - postings with skills but no IHL
--
-- Author: Arden
-- Date: 2025-11-13

BEGIN;

-- Add is_entry_point column
ALTER TABLE workflow_conversations
ADD COLUMN is_entry_point BOOLEAN NOT NULL DEFAULT FALSE;

-- Add condition column to specify when this entry point applies
ALTER TABLE workflow_conversations
ADD COLUMN entry_condition TEXT;

-- Add comments
COMMENT ON COLUMN workflow_conversations.is_entry_point IS 'True if postings can enter workflow at this conversation';
COMMENT ON COLUMN workflow_conversations.entry_condition IS 'SQL condition for when this entry point applies (e.g., "extracted_summary IS NULL")';

-- For workflow 3001, mark entry points based on current SQL logic
UPDATE workflow_conversations
SET 
    is_entry_point = TRUE,
    entry_condition = 'extracted_summary IS NULL OR LENGTH(extracted_summary) < 50'
WHERE workflow_id = 3001 
  AND execution_order = 3;  -- gemma3_extract

UPDATE workflow_conversations
SET 
    is_entry_point = TRUE,
    entry_condition = 'extracted_summary IS NOT NULL AND LENGTH(extracted_summary) >= 50 AND NOT EXISTS (SELECT 1 FROM posting_skills ps WHERE ps.posting_id = postings.posting_id)'
WHERE workflow_id = 3001 
  AND execution_order = 12;  -- taxonomy_skill_extraction

UPDATE workflow_conversations
SET 
    is_entry_point = TRUE,
    entry_condition = 'extracted_summary IS NOT NULL AND LENGTH(extracted_summary) >= 50 AND EXISTS (SELECT 1 FROM posting_skills ps WHERE ps.posting_id = postings.posting_id) AND ihl_score IS NULL'
WHERE workflow_id = 3001 
  AND execution_order = 19;  -- w1124_c1_analyst

-- Create index for finding entry points
CREATE INDEX idx_workflow_conversations_entry_point 
ON workflow_conversations(workflow_id, is_entry_point) 
WHERE is_entry_point = TRUE;

-- Record migration
INSERT INTO migration_log (migration_number, migration_name, status)
VALUES (
    '018',
    'Entry point routing with is_entry_point flag',
    'SUCCESS'
);

COMMIT;

-- Verification:
-- SELECT wc.execution_order, c.canonical_name, wc.is_entry_point, wc.entry_condition
-- FROM workflow_conversations wc
-- JOIN conversations c ON c.conversation_id = wc.conversation_id
-- WHERE wc.workflow_id = 3001 AND wc.is_entry_point = TRUE
-- ORDER BY wc.execution_order;
