-- Migration 045: Cleanup Disabled Workflows and Rename Actors
-- Date: 2025-11-28
-- Author: Arden
-- 
-- Purpose:
-- 1. Delete 69 disabled workflows (0 runs, cluttering the system)
-- 2. Rename v2 actors to drop the suffix (v2 is the only version that works)
-- 3. Drop empty workflows/ folder reference (handled outside SQL)

BEGIN;

-- ============================================================================
-- PART 1: Delete disabled workflows
-- ============================================================================
-- These workflows have enabled=false, 0 runs, and are just clutter.
-- Keeping only: 1114, 1121, 1122, 1123, 1124, 1125, 1126, 2001, 2002, 3001, 3003

-- First, delete workflow_variables for disabled workflows
DELETE FROM workflow_variables 
WHERE workflow_id IN (
    SELECT workflow_id FROM workflows 
    WHERE enabled = false OR enabled IS NULL
);

-- Delete workflow_triggers for disabled workflows
DELETE FROM workflow_triggers 
WHERE workflow_id IN (
    SELECT workflow_id FROM workflows 
    WHERE enabled = false OR enabled IS NULL
);

-- Delete workflow_dependencies for disabled workflows
DELETE FROM workflow_dependencies 
WHERE workflow_id IN (
    SELECT workflow_id FROM workflows 
    WHERE enabled = false OR enabled IS NULL
);

-- Delete workflow_placeholders for disabled workflows
DELETE FROM workflow_placeholders 
WHERE workflow_id IN (
    SELECT workflow_id FROM workflows 
    WHERE enabled = false OR enabled IS NULL
);

-- Delete workflow_doc_queue for disabled workflows
DELETE FROM workflow_doc_queue 
WHERE workflow_id IN (
    SELECT workflow_id FROM workflows 
    WHERE enabled = false OR enabled IS NULL
);

-- Delete test_cases for disabled workflows
DELETE FROM test_cases 
WHERE workflow_id IN (
    SELECT workflow_id FROM workflows 
    WHERE enabled = false OR enabled IS NULL
);

-- Then delete workflow_conversations for disabled workflows
DELETE FROM workflow_conversations 
WHERE workflow_id IN (
    SELECT workflow_id FROM workflows 
    WHERE enabled = false OR enabled IS NULL
);

-- Then delete the workflows themselves
DELETE FROM workflows 
WHERE enabled = false OR enabled IS NULL;

-- Log what we kept
DO $$
DECLARE
    remaining_count INT;
BEGIN
    SELECT COUNT(*) INTO remaining_count FROM workflows;
    RAISE NOTICE 'Remaining workflows after cleanup: %', remaining_count;
END $$;

-- ============================================================================
-- PART 2: Rename v2 actors (drop the "_v2" suffix)
-- ============================================================================
-- The v2 versions are the ones that work. No need for version suffix.
-- Old names become the canonical names.

-- Check for conflicts first (old non-v2 actors)
DO $$
DECLARE
    conflict_count INT;
BEGIN
    SELECT COUNT(*) INTO conflict_count
    FROM actors 
    WHERE actor_name IN ('summary_saver', 'skills_saver', 'ihl_score_saver', 'sql_query_executor', 'postings_staging_validator')
      AND actor_name NOT LIKE '%_v2';
    
    IF conflict_count > 0 THEN
        RAISE NOTICE 'Found % non-v2 actors with same base name - will be renamed to _legacy', conflict_count;
    END IF;
END $$;

-- Rename old actors to _legacy (if they exist)
UPDATE actors SET actor_name = 'summary_saver_legacy' WHERE actor_name = 'summary_saver' AND actor_id != 80;
UPDATE actors SET actor_name = 'skills_saver_legacy' WHERE actor_name = 'skills_saver' AND actor_id != 81;
UPDATE actors SET actor_name = 'ihl_score_saver_legacy' WHERE actor_name = 'ihl_score_saver' AND actor_id != 82;
UPDATE actors SET actor_name = 'sql_query_executor_legacy' WHERE actor_name = 'sql_query_executor' AND actor_id != 83;
UPDATE actors SET actor_name = 'postings_staging_validator_legacy' WHERE actor_name = 'postings_staging_validator' AND actor_id != 79;

-- Now rename v2 actors to canonical names
UPDATE actors SET actor_name = 'summary_saver' WHERE actor_name = 'summary_saver_v2';
UPDATE actors SET actor_name = 'skills_saver' WHERE actor_name = 'skills_saver_v2';
UPDATE actors SET actor_name = 'ihl_score_saver' WHERE actor_name = 'ihl_score_saver_v2';
UPDATE actors SET actor_name = 'sql_query_executor' WHERE actor_name = 'sql_query_executor_v2';
UPDATE actors SET actor_name = 'postings_staging_validator' WHERE actor_name = 'postings_staging_validator_v2';

-- Log renamed actors
DO $$
DECLARE
    v2_remaining INT;
BEGIN
    SELECT COUNT(*) INTO v2_remaining FROM actors WHERE actor_name LIKE '%_v2';
    RAISE NOTICE 'Remaining v2 actors after rename: %', v2_remaining;
END $$;

COMMIT;

-- ============================================================================
-- Verification queries (run manually)
-- ============================================================================
-- SELECT workflow_id, workflow_name, enabled FROM workflows ORDER BY workflow_id;
-- SELECT actor_id, actor_name FROM actors WHERE actor_name LIKE '%saver%' OR actor_name LIKE '%validator%' ORDER BY actor_id;
