-- ============================================================================
-- Migration 046: Enhanced workflow_runs for dual-mode execution
-- ============================================================================
-- Purpose: Support both ad-hoc testing (quick iteration) and tracked testing
--          (audit trail for comparisons across runs)
-- Date: 2025-11-04
-- 
-- Two Modes:
--   1. Ad-hoc: test_case_id=NULL, batch_id=NULL (dev/debug)
--   2. Tracked: Links to test_cases and batches (regression testing)
-- ============================================================================

BEGIN;

-- Make test_case_id and batch_id nullable for ad-hoc execution
ALTER TABLE workflow_runs 
ALTER COLUMN test_case_id DROP NOT NULL;

ALTER TABLE workflow_runs
ALTER COLUMN batch_id DROP NOT NULL;

-- Add parameter storage columns
ALTER TABLE workflow_runs
ADD COLUMN IF NOT EXISTS input_parameters JSONB,
ADD COLUMN IF NOT EXISTS output_result JSONB;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_workflow_runs_adhoc 
ON workflow_runs(workflow_id, started_at DESC) 
WHERE test_case_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_workflow_runs_input_params 
ON workflow_runs USING gin(input_parameters);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_output_result 
ON workflow_runs USING gin(output_result);

-- Comments explaining the dual-mode design
COMMENT ON COLUMN workflow_runs.test_case_id IS 
'Optional: NULL for ad-hoc runs, FK to test_cases for tracked regression testing';

COMMENT ON COLUMN workflow_runs.batch_id IS
'Optional: NULL for ad-hoc runs, FK to batches for comparing multiple runs of same test';

COMMENT ON COLUMN workflow_runs.input_parameters IS
'JSONB: Always stores workflow input (e.g., {document_text: "...", profile_id: 123})';

COMMENT ON COLUMN workflow_runs.output_result IS
'JSONB: Always stores workflow output (e.g., {profile_id: 456, skills_extracted: 12})';

COMMIT;

-- Verification
SELECT 
    'workflow_runs enhanced' as status,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE test_case_id IS NULL) as adhoc_runs,
    COUNT(*) FILTER (WHERE test_case_id IS NOT NULL) as tracked_runs
FROM workflow_runs;

-- Success message
DO $$ BEGIN
    RAISE NOTICE '✅ workflow_runs enhanced for dual-mode execution';
    RAISE NOTICE '   Mode 1 (Ad-hoc): test_case_id=NULL, batch_id=NULL - quick testing';
    RAISE NOTICE '   Mode 2 (Tracked): Links to test_cases/batches - audit trail';
    RAISE NOTICE '   Both modes store input_parameters and output_result (JSONB)';
END $$;
