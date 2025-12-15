-- Migration 076: Add Data Lineage Tracking for extracted_summary
-- Date: 2025-11-18
-- Purpose: Link postings.extracted_summary to its source LLM interaction
--
-- This enables:
-- - Forensic analysis (trace any summary back to exact LLM input/output)
-- - Data integrity validation (verify summary wasn't manually modified)
-- - Audit compliance (prove data provenance)
-- - Recovery (recompute from checkpoints if needed)

BEGIN;

-- Add column to track which LLM interaction produced the summary
ALTER TABLE postings 
ADD COLUMN summary_llm_interaction_id INTEGER 
REFERENCES llm_interactions(interaction_id);

-- Add index for reverse lookups (find all postings using a specific interaction)
CREATE INDEX idx_postings_summary_llm_interaction 
ON postings(summary_llm_interaction_id) 
WHERE summary_llm_interaction_id IS NOT NULL;

-- Add comment documenting the lineage requirement
COMMENT ON COLUMN postings.extracted_summary IS 
'Job posting summary extracted by LLM workflow. 
MUST be derived from llm_interactions via posting_state_checkpoints.
Source interaction ID stored in summary_llm_interaction_id.';

COMMENT ON COLUMN postings.summary_llm_interaction_id IS 
'References the llm_interactions.interaction_id that produced this summary.
Enables complete data lineage tracking from LLM input → output → database.
Populated automatically by workflow_executor via posting_state_checkpoints.';

COMMIT;
