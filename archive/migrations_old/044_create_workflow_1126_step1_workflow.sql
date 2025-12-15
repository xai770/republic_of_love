-- ============================================================================
-- Migration 044: Create Workflow 1126 - Profile Document Import
-- ============================================================================
-- Purpose: Extract structured profile data from documents using LLM extraction
--          with validation and database import
-- Author: Arden
-- Date: 2025-11-04
-- Follows: WORKFLOW_CREATION_COOKBOOK.md
--
-- Architecture:
--   Conversation 1: Extract profile data (qwen2.5:7b)
--   Conversation 2: Validate extracted data (gemma2:latest)  
--   Conversation 3: Import to database (taxonomy_gopher script)
--   Conversation 4: Error handling (qwen2.5:7b)
--
-- Output: profile_id (ready for Workflow 1122 skill extraction)
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Create Workflow (Registry Entry)
-- ============================================================================

INSERT INTO workflows (
    workflow_id,
    workflow_name,
    workflow_description,
    max_total_session_runs,
    enabled
) VALUES (
    1126,
    'Profile Document Import',
    'LLM-based profile extraction: Parse documents → Extract structured data → Validate with second model → Import to profiles/work_history. Output: profile_id for Workflow 1122.',
    100,
    true
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

COMMIT;

-- Success message
DO $$ BEGIN
    RAISE NOTICE '✅ Step 1 Complete: Workflow 1126 created';
END $$;

-- ============================================================================
-- Verification Step 1
-- ============================================================================
SELECT workflow_id, workflow_name, workflow_description, enabled 
FROM workflows WHERE workflow_id = 1126;
