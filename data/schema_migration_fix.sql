-- ============================================================================
-- SCHEMA MIGRATION: Fix test_executions Table Structure
-- Date: 2025-10-03
-- Purpose: Replace incorrect test_executions with proper execution scheduler
-- ============================================================================

-- PROBLEM:
-- Current test_executions has wrong structure:
-- 1. Links to test_id (should be param_id)
-- 2. Links to model_id which doesn't exist (should be model_name)
-- 3. Duplicates test_runs data (should be lightweight scheduler)
-- 4. Missing execution_number field (1-5 enforcement)

-- SOLUTION:
-- Drop and recreate with correct structure from implementation plan

BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Backup existing data (if needed for analysis)
-- ============================================================================

-- Create backup table
CREATE TABLE IF NOT EXISTS test_executions_backup AS 
SELECT * FROM test_executions;

-- ============================================================================
-- STEP 2: Drop broken table
-- ============================================================================

DROP TABLE IF EXISTS test_executions;

-- ============================================================================
-- STEP 3: Create correct test_executions table
-- ============================================================================

CREATE TABLE test_executions (
    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    param_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    execution_number INTEGER NOT NULL CHECK(execution_number BETWEEN 1 AND 5),
    exec_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    test_passed INTEGER,
    timeout_occurred INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    execution_metadata TEXT,
    FOREIGN KEY (param_id) REFERENCES test_parameters(param_id),
    FOREIGN KEY (model_name) REFERENCES models(model_name),
    UNIQUE(param_id, model_name, execution_number)
);

-- ============================================================================
-- STEP 4: Create indexes for performance
-- ============================================================================

CREATE INDEX idx_test_executions_status ON test_executions(status);
CREATE INDEX idx_test_executions_param_model ON test_executions(param_id, model_name);
CREATE INDEX idx_test_executions_exec_id ON test_executions(exec_id);

-- ============================================================================
-- STEP 5: Pre-generate execution slots (5 per param per enabled model)
-- ============================================================================

-- This creates the 5-execution enforcement structure
INSERT INTO test_executions (param_id, model_name, execution_number, exec_id, status)
SELECT 
    tp.param_id,
    m.model_name,
    n.num,
    tp.param_id || '_' || m.model_name || '_exec_' || n.num,
    'pending'
FROM test_parameters tp
CROSS JOIN models m 
CROSS JOIN (
    SELECT 1 as num UNION ALL 
    SELECT 2 UNION ALL 
    SELECT 3 UNION ALL 
    SELECT 4 UNION ALL 
    SELECT 5
) n
WHERE m.enabled = 1
  AND tp.enabled = 1;

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check table structure
-- PRAGMA table_info(test_executions);

-- Count execution slots created
-- SELECT 
--     COUNT(*) as total_slots,
--     COUNT(DISTINCT param_id) as unique_params,
--     COUNT(DISTINCT model_name) as unique_models
-- FROM test_executions;

-- Verify 5 executions per param per model
-- SELECT 
--     param_id,
--     model_name,
--     COUNT(*) as execution_count
-- FROM test_executions
-- GROUP BY param_id, model_name
-- HAVING COUNT(*) != 5;
-- -- Should return empty (all have exactly 5)

-- Check status distribution
-- SELECT 
--     status,
--     COUNT(*) as count,
--     ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM test_executions), 2) as percentage
-- FROM test_executions
-- GROUP BY status;

-- ============================================================================
-- NOTES FOR ARDEN
-- ============================================================================

-- 1. RELATIONSHIP BETWEEN TABLES:
--    test_executions (scheduler) -> test_runs (results)
--    Linked by exec_id field
--
-- 2. EXECUTION FLOW:
--    a. Query test_executions WHERE status='pending' to find next work
--    b. Mark as status='running'
--    c. Execute test and store result in test_runs with matching exec_id
--    d. Update test_executions: status='completed', test_passed=result
--
-- 3. DATA MIGRATION:
--    Old test_executions data is backed up in test_executions_backup
--    If you need to preserve any execution history, map it to test_runs
--    The old execution_id values are NOT preserved (new autoincrement)
--
-- 4. NEXT STEPS:
--    a. Run this migration script
--    b. Update run_unrun_tests.py to query new test_executions structure
--    c. Update validation logic (see validation_fix_spec artifact)
--    d. Rerun Phase 1.3 with corrected schema and validation
--
-- 5. FOREIGN KEY COMPLIANCE:
--    This script assumes test_parameters table exists with param_id
--    This script assumes models table has model_name as primary key (it does)
--    Verify: SELECT * FROM models LIMIT 1;
