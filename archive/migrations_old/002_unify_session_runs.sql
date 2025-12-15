-- Migration 002: Unify Session Runs Run Tracking
-- Date: 2025-10-30
-- Purpose: Simplify dual-mode (testing/production) tracking in session_runs

BEGIN;

-- ============================================================================
-- 1. Add new unified columns
-- ============================================================================

ALTER TABLE session_runs ADD COLUMN run_id INTEGER;
ALTER TABLE session_runs ADD COLUMN run_type TEXT;

-- ============================================================================
-- 2. Populate from existing data
-- ============================================================================

-- Testing runs
UPDATE session_runs 
SET run_id = recipe_run_id,
    run_type = 'testing'
WHERE recipe_run_id IS NOT NULL;

-- Production runs
UPDATE session_runs 
SET run_id = production_run_id,
    run_type = 'production'
WHERE production_run_id IS NOT NULL;

-- ============================================================================
-- 3. Verify migration success
-- ============================================================================

-- Check for unmigrated rows (should return 0)
DO $$
DECLARE
    unmigrated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO unmigrated_count
    FROM session_runs
    WHERE run_id IS NULL OR run_type IS NULL;
    
    IF unmigrated_count > 0 THEN
        RAISE EXCEPTION 'Migration failed: % rows have NULL run_id or run_type', unmigrated_count;
    END IF;
    
    RAISE NOTICE 'Migration validation passed: all rows have run_id and run_type';
END $$;

-- ============================================================================
-- 4. Drop dependent views first
-- ============================================================================

DROP VIEW IF EXISTS v_pipeline_execution;
DROP VIEW IF EXISTS v_production_qa;

-- ============================================================================
-- 5. Drop old columns
-- ============================================================================

ALTER TABLE session_runs DROP COLUMN recipe_run_id;
ALTER TABLE session_runs DROP COLUMN production_run_id;

-- Also drop the old constraint that enforced mutual exclusivity
ALTER TABLE session_runs DROP CONSTRAINT IF EXISTS session_runs_check;

-- ============================================================================
-- 6. Add new constraints
-- ============================================================================

ALTER TABLE session_runs ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE session_runs ALTER COLUMN run_type SET NOT NULL;

ALTER TABLE session_runs ADD CONSTRAINT session_runs_run_type_check 
  CHECK (run_type IN ('testing', 'production'));

-- Note: run_id references different tables based on run_type:
--   - recipe_runs.recipe_run_id when run_type='testing'
--   - production_runs.production_run_id when run_type='production'
-- PostgreSQL doesn't support conditional FKs, so validation is in application layer

-- ============================================================================
-- 6. Update comments
-- ============================================================================

COMMENT ON COLUMN session_runs.run_id IS 
  'Unified run identifier. References either:
   - recipe_runs.recipe_run_id (when run_type=''testing'')
   - production_runs.production_run_id (when run_type=''production'')';

COMMENT ON COLUMN session_runs.run_type IS 
  'Execution mode: ''testing'' (synthetic variations) or ''production'' (real jobs).
   Determines which parent table run_id references.';

-- ============================================================================
-- 7. Recreate v_pipeline_execution with new schema
-- ============================================================================

CREATE VIEW v_pipeline_execution AS
SELECT 
    r.recipe_id,
    r.recipe_name,
    s.canonical_code,
    s.session_name,
    v.variation_id::text AS input_id,
    'test'::text AS execution_mode,
    rr.batch_id,
    sr.session_run_id,
    sr.started_at,
    sr.completed_at,
    sr.quality_score,
    sr.validation_status
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
JOIN variations v ON rr.variation_id = v.variation_id
JOIN session_runs sr ON rr.recipe_run_id = sr.run_id AND sr.run_type = 'testing'
JOIN sessions s ON sr.session_id = s.session_id

UNION ALL

SELECT 
    r.recipe_id,
    r.recipe_name,
    s.canonical_code,
    s.session_name,
    pr.posting_id AS input_id,
    'production'::text AS execution_mode,
    NULL::integer AS batch_id,
    sr.session_run_id,
    sr.started_at,
    sr.completed_at,
    sr.quality_score,
    sr.validation_status
FROM production_runs pr
JOIN recipes r ON pr.recipe_id = r.recipe_id
JOIN postings p ON pr.posting_id = p.job_id
JOIN session_runs sr ON pr.production_run_id = sr.run_id AND sr.run_type = 'production'
JOIN sessions s ON sr.session_id = s.session_id;

COMMENT ON VIEW v_pipeline_execution IS 
  'Unified view of all pipeline executions (testing + production).
   Now uses session_runs.run_id + run_type for cleaner joins.';

-- Recreate v_production_qa with new schema
CREATE VIEW v_production_qa AS
SELECT 
    pr.production_run_id,
    p.job_id,
    p.job_title,
    p.organization_name,
    r.recipe_id,
    r.recipe_name,
    pr.status AS run_status,
    pr.started_at,
    pr.completed_at,
    pr.completed_at - pr.started_at AS total_duration,
    COUNT(sr.session_run_id) AS session_count,
    SUM(CASE WHEN sr.validation_status = 'PASS' THEN 1 ELSE 0 END) AS passed_sessions,
    SUM(CASE WHEN sr.validation_status = 'FAIL' THEN 1 ELSE 0 END) AS failed_sessions,
    SUM(CASE WHEN sr.status = 'ERROR' THEN 1 ELSE 0 END) AS error_sessions,
    AVG(ir.latency_ms) AS avg_instruction_latency_ms
FROM production_runs pr
JOIN postings p ON p.job_id = pr.posting_id
JOIN recipes r ON r.recipe_id = pr.recipe_id
LEFT JOIN session_runs sr ON sr.run_id = pr.production_run_id AND sr.run_type = 'production'
LEFT JOIN instruction_runs ir ON ir.session_run_id = sr.session_run_id
GROUP BY pr.production_run_id, p.job_id, p.job_title, p.organization_name, 
         r.recipe_id, r.recipe_name, pr.status, pr.started_at, pr.completed_at
ORDER BY pr.started_at DESC;

COMMENT ON VIEW v_production_qa IS 
  'Production run quality metrics.
   Now uses session_runs.run_id + run_type for cleaner joins.';

-- ============================================================================
-- 8. Create convenience views
-- ============================================================================

-- View for testing runs
CREATE OR REPLACE VIEW session_runs_testing AS
SELECT 
    sr.session_run_id,
    sr.run_id,
    sr.session_id,
    sr.recipe_session_id,
    sr.execution_order,
    sr.started_at,
    sr.completed_at,
    sr.status,
    sr.error_details,
    rr.recipe_id,
    rr.variation_id,
    rr.batch_id
FROM session_runs sr
JOIN recipe_runs rr ON sr.run_id = rr.recipe_run_id
WHERE sr.run_type = 'testing';

COMMENT ON VIEW session_runs_testing IS 
  'Session runs in testing mode with recipe_runs context.
   Simplified query access without needing run_type filter.';

-- View for production runs
CREATE OR REPLACE VIEW session_runs_production AS
SELECT 
    sr.session_run_id,
    sr.run_id,
    sr.session_id,
    sr.recipe_session_id,
    sr.execution_order,
    sr.started_at,
    sr.completed_at,
    sr.status,
    sr.error_details,
    pr.recipe_id,
    pr.posting_id
FROM session_runs sr
JOIN production_runs pr ON sr.run_id = pr.production_run_id
WHERE sr.run_type = 'production';

COMMENT ON VIEW session_runs_production IS 
  'Session runs in production mode with production_runs context.
   Simplified query access without needing run_type filter.';

COMMIT;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Count by run type
-- SELECT run_type, COUNT(*) FROM session_runs GROUP BY run_type;

-- Verify no broken references
-- SELECT COUNT(*) FROM session_runs sr
-- WHERE run_type = 'testing' 
-- AND NOT EXISTS (SELECT 1 FROM recipe_runs WHERE recipe_run_id = sr.run_id);

-- SELECT COUNT(*) FROM session_runs sr
-- WHERE run_type = 'production'
-- AND NOT EXISTS (SELECT 1 FROM production_runs WHERE production_run_id = sr.run_id);

-- ============================================================================
-- Rollback Script (if needed):
-- ============================================================================
-- BEGIN;
-- 
-- ALTER TABLE session_runs ADD COLUMN recipe_run_id INTEGER;
-- ALTER TABLE session_runs ADD COLUMN production_run_id INTEGER;
-- 
-- UPDATE session_runs SET recipe_run_id = run_id WHERE run_type = 'testing';
-- UPDATE session_runs SET production_run_id = run_id WHERE run_type = 'production';
-- 
-- ALTER TABLE session_runs DROP COLUMN run_id;
-- ALTER TABLE session_runs DROP COLUMN run_type;
-- 
-- ALTER TABLE session_runs ADD CONSTRAINT session_runs_check 
--   CHECK ((recipe_run_id IS NOT NULL AND production_run_id IS NULL) OR 
--          (recipe_run_id IS NULL AND production_run_id IS NOT NULL));
-- 
-- DROP VIEW IF EXISTS session_runs_testing;
-- DROP VIEW IF EXISTS session_runs_production;
-- 
-- COMMIT;
