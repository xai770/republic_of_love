-- Migration 044: Cleanup Legacy Tables
-- Date: November 24, 2025
-- Author: Arden
-- Purpose: Remove legacy tables from pre-Wave Runner V2 era and anti-pattern tables
-- Backup: by_pre_cleanup_20251124_143549.sql (72MB)
-- Reference: docs/DATA_CLEANUP_PROPOSAL_NOV24.md (approved by xai)

-- Safety Check: Verify no foreign keys (should return 0 rows)
DO $$
DECLARE
  fk_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO fk_count
  FROM information_schema.table_constraints AS tc 
  JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
  WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name IN (
      'production_runs', 'test_cases_history', 'career_analyses',
      'dialogue_step_placeholders', 'trigger_executions', 'workflow_scripts'
    );
  
  IF fk_count > 0 THEN
    RAISE EXCEPTION 'Foreign key constraints exist! Cannot safely drop tables. Found % constraints.', fk_count;
  END IF;
  
  RAISE NOTICE 'Safety check passed: No foreign key dependencies found.';
END $$;

BEGIN;

-- Category 1: Legacy Recipe System Tables
-- These reference deleted tables (recipe_runs, variations)

-- 1. production_runs
-- Comment: "Production execution of recipes using real job postings"
-- Problem: References deleted 'recipe_runs' table
-- Empty: 0 rows
DROP TABLE IF EXISTS production_runs CASCADE;
COMMENT ON SCHEMA public IS 'Migration 044 (Step 1/6): Dropped production_runs (legacy recipe system)';

-- 2. test_cases_history
-- Comment: "Audit trail of all changes to variations table"
-- Problem: 'variations' table was deleted Nov 24
-- Empty: 0 rows
DROP TABLE IF EXISTS test_cases_history CASCADE;
COMMENT ON SCHEMA public IS 'Migration 044 (Step 2/6): Dropped test_cases_history (variations table deleted)';

-- 3. career_analyses
-- Comment: "Stores comprehensive career analysis results from Recipe 1122"
-- Problem: Recipe 1122 deleted (pre-workflows era)
-- Empty: 0 rows
DROP TABLE IF EXISTS career_analyses CASCADE;
COMMENT ON SCHEMA public IS 'Migration 044 (Step 3/6): Dropped career_analyses (Recipe 1122 deleted)';

-- Category 2: Anti-Pattern Tables
-- These implement patterns we explicitly avoid

-- 4. dialogue_step_placeholders
-- Comment: "Links dialogue steps to their required/optional placeholders"
-- Problem: Template substitution anti-pattern (see CHECKPOINT_QUERY_PATTERN.md)
-- Empty: 0 rows
DROP TABLE IF EXISTS dialogue_step_placeholders CASCADE;
COMMENT ON SCHEMA public IS 'Migration 044 (Step 4/6): Dropped dialogue_step_placeholders (anti-pattern)';

-- Category 3: Superseded Tables
-- No code references, likely legacy infrastructure

-- 5. trigger_executions
-- Comment: (empty)
-- Problem: No foreign keys, no code references, likely legacy
-- Empty: 0 rows
DROP TABLE IF EXISTS trigger_executions CASCADE;
COMMENT ON SCHEMA public IS 'Migration 044 (Step 5/6): Dropped trigger_executions (superseded)';

-- 6. workflow_scripts
-- Comment: (empty)
-- Problem: Superseded by stored_scripts table
-- Empty: 0 rows
DROP TABLE IF EXISTS workflow_scripts CASCADE;
COMMENT ON SCHEMA public IS 'Migration 044 (Step 6/6): Dropped workflow_scripts (superseded by stored_scripts)';

-- Verification: Tables should not exist
DO $$
DECLARE
  remaining_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO remaining_count
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN (
      'production_runs', 'test_cases_history', 'career_analyses',
      'dialogue_step_placeholders', 'trigger_executions', 'workflow_scripts'
    );
  
  IF remaining_count > 0 THEN
    RAISE EXCEPTION 'Migration incomplete! % tables still exist.', remaining_count;
  END IF;
  
  RAISE NOTICE 'Verification passed: All 6 legacy tables successfully dropped.';
END $$;

-- Final comment update
COMMENT ON SCHEMA public IS 
'Migration 044 (Nov 24, 2025): Deleted 6 legacy tables (production_runs, test_cases_history, career_analyses, dialogue_step_placeholders, trigger_executions, workflow_scripts). All were empty and referenced deleted schemas or anti-patterns. Backup: by_pre_cleanup_20251124_143549.sql';

COMMIT;

-- Success message
DO $$
BEGIN
  RAISE NOTICE '================================================';
  RAISE NOTICE 'Migration 044 Complete!';
  RAISE NOTICE 'Deleted 6 legacy tables:';
  RAISE NOTICE '  1. production_runs (legacy recipes)';
  RAISE NOTICE '  2. test_cases_history (variations deleted)';
  RAISE NOTICE '  3. career_analyses (Recipe 1122 deleted)';
  RAISE NOTICE '  4. dialogue_step_placeholders (anti-pattern)';
  RAISE NOTICE '  5. trigger_executions (superseded)';
  RAISE NOTICE '  6. workflow_scripts (superseded)';
  RAISE NOTICE '';
  RAISE NOTICE 'Before: 74 tables, 23 empty (31%%)';
  RAISE NOTICE 'After:  68 tables, 17 empty (25%%)';
  RAISE NOTICE '';
  RAISE NOTICE 'Backup: by_pre_cleanup_20251124_143549.sql';
  RAISE NOTICE '================================================';
END $$;
