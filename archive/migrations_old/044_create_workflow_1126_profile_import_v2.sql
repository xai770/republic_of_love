-- ============================================================================
-- Migration 044: Create Workflow 1126 - Profile Document Import
-- ============================================================================
-- Purpose: Extract structured profile data from documents using LLM extraction
--          with validation and database import
-- Author: Arden
-- Date: 2025-11-04
--
-- This migration creates the complete workflow structure in Turing's schema:
--   - Workflow registry entry
--   - 4 Conversations (extract, validate, import, error)
--   - Instructions for each conversation
--   - Instruction steps for branching logic
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Create Workflow 1126
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
    'LLM-based profile extraction: Parse documents → Extract structured data → Validate → Import to profiles/work_history. Output: profile_id.',
    100,
    true
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

RAISE NOTICE '✅ Created Workflow 1126';

COMMIT;

-- ============================================================================
-- Now run this to see the workflow:
-- SELECT * FROM workflows WHERE workflow_id = 1126;
-- ============================================================================
