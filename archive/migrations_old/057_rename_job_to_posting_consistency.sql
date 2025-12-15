-- Migration 057: Rename job_* tables to posting_* for consistency
-- Created: 2025-11-12
-- Rationale: Primary table is "postings", related tables should follow same naming
--
-- Tables to rename:
--   job_skills       → posting_skills
--   job_sources      → posting_sources
--   job_fetch_runs   → posting_fetch_runs
--
-- DO NOT EXECUTE YET - Review first!

BEGIN;

-- =============================================================================
-- STEP 1: Rename Tables
-- =============================================================================

-- Rename job_skills to posting_skills
ALTER TABLE job_skills RENAME TO posting_skills;

-- NOTE: job_sources CANNOT be renamed to posting_sources because posting_sources
-- already exists as a DIFFERENT table (simple scraper config vs workflow automation)
-- SKIP: ALTER TABLE job_sources RENAME TO posting_sources;

-- Rename job_fetch_runs to posting_fetch_runs
ALTER TABLE job_fetch_runs RENAME TO posting_fetch_runs;

-- =============================================================================
-- STEP 2: Rename Sequences (auto-created with tables)
-- =============================================================================

-- Rename job_skills sequence
ALTER SEQUENCE job_skills_job_skill_id_seq RENAME TO posting_skills_posting_skill_id_seq;

-- SKIP: job_sources sequence (table not renamed)
-- ALTER SEQUENCE job_sources_source_id_seq RENAME TO posting_sources_source_id_seq;

-- Rename job_fetch_runs sequence
ALTER SEQUENCE job_fetch_runs_fetch_run_id_seq RENAME TO posting_fetch_runs_fetch_run_id_seq;

-- =============================================================================
-- STEP 3: Rename Primary Key Column in posting_skills
-- =============================================================================

-- Rename job_skill_id to posting_skill_id for consistency
ALTER TABLE posting_skills RENAME COLUMN job_skill_id TO posting_skill_id;

-- =============================================================================
-- STEP 4: Rename Constraints (FK, PK, Unique)
-- =============================================================================

-- posting_skills constraints
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_pkey TO posting_skills_pkey;
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_posting_id_fkey TO posting_skills_posting_id_fkey;
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_skill_id_fkey TO posting_skills_skill_id_fkey;
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_recipe_run_id_fkey TO posting_skills_workflow_run_id_fkey;
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_posting_id_skill_id_key TO posting_skills_posting_id_skill_id_key;

-- Check constraints
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_importance_check TO posting_skills_importance_check;
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_proficiency_check TO posting_skills_proficiency_check;
ALTER TABLE posting_skills RENAME CONSTRAINT job_skills_weight_check TO posting_skills_weight_check;

-- SKIP: job_sources constraints (table not renamed)

-- posting_fetch_runs constraints
ALTER TABLE posting_fetch_runs RENAME CONSTRAINT job_fetch_runs_pkey TO posting_fetch_runs_pkey;
ALTER TABLE posting_fetch_runs RENAME CONSTRAINT job_fetch_runs_source_id_fkey TO posting_fetch_runs_source_id_fkey;

-- =============================================================================
-- STEP 5: Rename Indexes
-- =============================================================================

-- posting_skills indexes
ALTER INDEX idx_job_skills_posting RENAME TO idx_posting_skills_posting;
ALTER INDEX idx_job_skills_skill RENAME TO idx_posting_skills_skill;
ALTER INDEX idx_job_skills_importance RENAME TO idx_posting_skills_importance;
ALTER INDEX idx_job_skills_weight RENAME TO idx_posting_skills_weight;

-- SKIP: job_sources indexes (table not renamed)

-- posting_fetch_runs indexes (use actual index names from \d job_fetch_runs)
ALTER INDEX idx_fetch_runs_source RENAME TO idx_posting_fetch_runs_source;
ALTER INDEX idx_fetch_runs_status RENAME TO idx_posting_fetch_runs_status;
ALTER INDEX idx_fetch_runs_workflow RENAME TO idx_posting_fetch_runs_workflow;

-- =============================================================================
-- STEP 6: Rename Triggers (if any exist with job_ prefix)
-- =============================================================================

-- Check and rename triggers on posting_skills
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at' AND tgrelid = 'posting_skills'::regclass) THEN
        -- Trigger name is generic (set_updated_at), no rename needed
        NULL;
    END IF;
END $$;

-- Same for posting_sources and posting_fetch_runs (triggers should be generic)

-- =============================================================================
-- STEP 7: Update Comments (if any)
-- =============================================================================

COMMENT ON TABLE posting_skills IS 'Skills extracted from job postings, normalized to skill_aliases taxonomy';
-- NOTE: job_sources remains as-is (different table from posting_sources)
COMMENT ON TABLE job_sources IS 'Workflow-driven job fetching sources (fetch_workflow_id, scheduling)';
COMMENT ON TABLE posting_fetch_runs IS 'History of fetch operations from job_sources';

-- =============================================================================
-- VERIFICATION QUERIES (run these AFTER migration)
-- =============================================================================

-- Verify tables exist with new names
-- SELECT tablename FROM pg_tables WHERE tablename LIKE 'posting_%' ORDER BY tablename;

-- Verify no old tables remain
-- SELECT tablename FROM pg_tables WHERE tablename LIKE 'job_%' ORDER BY tablename;

-- Verify constraints renamed
-- SELECT conname FROM pg_constraint WHERE conname LIKE 'job_%';

-- Verify indexes renamed
-- SELECT indexname FROM pg_indexes WHERE indexname LIKE 'idx_job_%';

-- Verify data integrity
-- SELECT COUNT(*) FROM posting_skills;
-- SELECT COUNT(*) FROM posting_sources;
-- SELECT COUNT(*) FROM posting_fetch_runs;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (in case something goes wrong)
-- =============================================================================

/*
BEGIN;

-- Rollback table renames
ALTER TABLE posting_skills RENAME TO job_skills;
ALTER TABLE posting_sources RENAME TO job_sources;
ALTER TABLE posting_fetch_runs RENAME TO job_fetch_runs;

-- Rollback sequence renames
ALTER SEQUENCE posting_skills_posting_skill_id_seq RENAME TO job_skills_job_skill_id_seq;
ALTER SEQUENCE posting_sources_source_id_seq RENAME TO job_sources_source_id_seq;
ALTER SEQUENCE posting_fetch_runs_fetch_run_id_seq RENAME TO job_fetch_runs_fetch_run_id_seq;

-- Rollback column rename
ALTER TABLE job_skills RENAME COLUMN posting_skill_id TO job_skill_id;

-- Rollback constraints (reverse all the constraint renames above)
-- ... (full rollback script available if needed)

COMMIT;
*/
