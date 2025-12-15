-- Migration 069: Add Skip Logic to Workflow 3001
-- ================================================
-- Make workflow 3001 restartable and idempotent by adding execute conditions
-- that check if work is already done.
--
-- Philosophy: "Don't redo work that's already complete"
--
-- Skip Logic:
-- - Conversation 1 (fetch_db_jobs): Always skip (we process existing jobs, not fetch new ones)
-- - Conversations 2-8 (summary extraction): Skip if extracted_summary already exists
-- - Conversations 9-12 (skill extraction): Skip if posting_skills already exist
-- - Conversations 13-15 (IHL scoring): Skip if ihl_score already exists
--
-- Result: Workflow can run on ANY posting, only does what's needed
--
-- Author: Arden & xai
-- Date: 2025-11-12

BEGIN;

-- ============================================================================
-- CONVERSATION 1: Job Fetcher - DISABLE (not needed for existing postings)
-- ============================================================================

UPDATE workflow_conversations
SET 
    enabled = false  -- Disable job fetcher (we process existing jobs, not fetch new ones)
WHERE workflow_id = 3001
  AND conversation_id = (
      SELECT conversation_id 
      FROM conversations 
      WHERE canonical_name = 'fetch_db_jobs'
  );

COMMENT ON COLUMN workflow_conversations.execute_condition IS 
'SQL expression or keyword to determine if conversation should execute. 
Examples: 
  - "always" (default)
  - "skip" (never execute)
  - SQL expression that returns boolean (future enhancement)';


-- ============================================================================
-- CONVERSATIONS 2-8: Summary Extraction - Skip if extracted_summary exists
-- ============================================================================

-- For now, we use enabled=true with execute_condition='always' because
-- the workflow executor doesn't yet support SQL-based execute conditions.
-- 
-- FUTURE ENHANCEMENT: Implement SQL-based skip logic like:
--   execute_condition = 'SELECT extracted_summary IS NULL FROM postings WHERE posting_id = {posting_id}'
--
-- For now, we rely on the batch processor to ONLY query postings WHERE extracted_summary IS NULL

UPDATE workflow_conversations
SET 
    execute_condition = 'always'  -- TODO: Change to SQL check when executor supports it
WHERE workflow_id = 3001
  AND conversation_id IN (
      SELECT conversation_id 
      FROM conversations 
      WHERE canonical_name IN (
          'gemma3_extract',
          'gemma2_grade',
          'qwen25_grade',
          'qwen25_improve',
          'qwen25_regrade',
          'create_ticket',
          'format_standardization'
      )
  );


-- ============================================================================
-- CONVERSATIONS 9-12: Skill Extraction - Skip if skills exist
-- ============================================================================

-- These conversations should be skipped if posting already has skills extracted
-- For now, batch processor will filter before calling workflow

UPDATE workflow_conversations
SET 
    execute_condition = 'always'  -- TODO: SQL check for posting_skills existence
WHERE workflow_id = 3001
  AND conversation_id IN (
      SELECT conversation_id 
      FROM conversations 
      WHERE canonical_name IN (
          'taxonomy_skill_extraction',  -- Two conversations have this name (9 & 10)
          'gopher_skill_extraction',
          'save_job_skills'
      )
  );


-- ============================================================================
-- CONVERSATIONS 13-15: IHL Scoring - Skip if ihl_score exists
-- ============================================================================

-- These conversations should be skipped if posting already has IHL score
-- CRITICAL: Don't re-run IHL scoring (already 100% complete for all postings)

UPDATE workflow_conversations
SET 
    execute_condition = 'always'  -- TODO: SQL check for ihl_score IS NOT NULL
WHERE workflow_id = 3001
  AND conversation_id IN (
      SELECT conversation_id 
      FROM conversations 
      WHERE canonical_name IN (
          'w1124_c1_analyst',
          'w1124_c2_skeptic',
          'w1124_c3_expert'
      )
  );


-- ============================================================================
-- Verify Changes
-- ============================================================================

DO $$
DECLARE
    v_disabled_count INTEGER;
    v_total_count INTEGER;
    v_fetcher_disabled BOOLEAN;
BEGIN
    -- Count disabled conversations
    SELECT COUNT(*) INTO v_disabled_count
    FROM workflow_conversations
    WHERE workflow_id = 3001 AND enabled = false;
    
    -- Count total conversations
    SELECT COUNT(*) INTO v_total_count
    FROM workflow_conversations
    WHERE workflow_id = 3001;
    
    -- Check if fetch_db_jobs is disabled
    SELECT wc.enabled = false INTO v_fetcher_disabled
    FROM workflow_conversations wc
    JOIN conversations c ON wc.conversation_id = c.conversation_id
    WHERE wc.workflow_id = 3001 
      AND c.canonical_name = 'fetch_db_jobs';
    
    RAISE NOTICE 'Workflow 3001 Skip Logic Applied:';
    RAISE NOTICE '  Total conversations: %', v_total_count;
    RAISE NOTICE '  Disabled conversations: %', v_disabled_count;
    RAISE NOTICE '  Active conversations: %', v_total_count - v_disabled_count;
    RAISE NOTICE '  Job fetcher disabled: %', v_fetcher_disabled;
    
    IF NOT v_fetcher_disabled THEN
        RAISE EXCEPTION 'Expected fetch_db_jobs to be disabled, but it is still enabled';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE workflow_conversations IS 
'Maps workflows to conversations with execution control.

Skip Logic (Migration 069):
- Conversation 1 (fetch_db_jobs): DISABLED - we process existing jobs
- Conversations 2-8: Run if extracted_summary IS NULL (batch processor filters)
- Conversations 9-12: Run if posting_skills empty (batch processor filters)
- Conversations 13-15: Run if ihl_score IS NULL (batch processor filters)

Future Enhancement: Implement SQL-based execute_condition evaluation in
WorkflowExecutor to make skip logic automatic (no batch processor filtering needed).';


-- ============================================================================
-- ROLLBACK INSTRUCTIONS
-- ============================================================================

-- To rollback this migration:
-- 
-- UPDATE workflow_conversations
-- SET 
--     enabled = true,
--     execute_condition = 'always'
-- WHERE workflow_id = 3001;
