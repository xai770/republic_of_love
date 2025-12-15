-- =====================================================
-- Migration: Fix batch_id and add CHECK constraints
-- Date: 2024-10-24
-- Changes:
--   1. Remove batch_id from production_runs (batches are TEST-ONLY)
--   2. Drop instruction_run_status lookup table (use CHECK instead)
--   3. Add CHECK constraints for status fields
-- =====================================================

\echo '🔧 Applying schema fixes to existing database...'
\echo ''

-- Fix 1: Remove batch_id from production_runs
\echo '1. Removing batch_id from production_runs (batches are TEST-ONLY)...'
ALTER TABLE production_runs DROP CONSTRAINT IF EXISTS production_runs_batch_id_fkey;
ALTER TABLE production_runs DROP COLUMN IF EXISTS batch_id;
ALTER TABLE production_runs DROP CONSTRAINT IF EXISTS production_runs_recipe_id_posting_id_batch_id_key;
ALTER TABLE production_runs ADD CONSTRAINT production_runs_recipe_id_posting_id_key UNIQUE (recipe_id, posting_id);

-- Fix 2: Remove instruction_run_status lookup table
\echo '2. Removing instruction_run_status lookup table...'
ALTER TABLE instruction_runs DROP CONSTRAINT IF EXISTS instruction_runs_status_fkey;
DROP TABLE IF EXISTS instruction_run_status CASCADE;

-- Fix 3: Add CHECK constraints for status fields
\echo '3. Adding CHECK constraints...'

-- instruction_runs.status
ALTER TABLE instruction_runs DROP CONSTRAINT IF EXISTS instruction_runs_status_check;
ALTER TABLE instruction_runs ADD CONSTRAINT instruction_runs_status_check 
    CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'ERROR'));

-- session_runs.status
ALTER TABLE session_runs DROP CONSTRAINT IF EXISTS session_runs_status_check;
ALTER TABLE session_runs ADD CONSTRAINT session_runs_status_check 
    CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'ERROR'));

-- session_runs.quality_score (academic grades)
ALTER TABLE session_runs DROP CONSTRAINT IF EXISTS session_runs_quality_score_check;
ALTER TABLE session_runs ADD CONSTRAINT session_runs_quality_score_check 
    CHECK (quality_score IN ('A', 'B', 'C', 'D', 'F', NULL));

-- recipe_runs.status
ALTER TABLE recipe_runs DROP CONSTRAINT IF EXISTS recipe_runs_status_check;
ALTER TABLE recipe_runs ADD CONSTRAINT recipe_runs_status_check 
    CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL', 'ERROR'));

-- recipe_runs counters
ALTER TABLE recipe_runs DROP CONSTRAINT IF EXISTS recipe_runs_total_sessions_check;
ALTER TABLE recipe_runs DROP CONSTRAINT IF EXISTS recipe_runs_completed_sessions_check;
ALTER TABLE recipe_runs ADD CONSTRAINT recipe_runs_total_sessions_check 
    CHECK (total_sessions > 0);
ALTER TABLE recipe_runs ADD CONSTRAINT recipe_runs_completed_sessions_check 
    CHECK (completed_sessions >= 0);

-- production_runs.status
ALTER TABLE production_runs DROP CONSTRAINT IF EXISTS production_runs_status_check;
ALTER TABLE production_runs ADD CONSTRAINT production_runs_status_check 
    CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL', 'ERROR'));

-- production_runs counters
ALTER TABLE production_runs DROP CONSTRAINT IF EXISTS production_runs_total_sessions_check;
ALTER TABLE production_runs DROP CONSTRAINT IF EXISTS production_runs_completed_sessions_check;
ALTER TABLE production_runs ADD CONSTRAINT production_runs_total_sessions_check 
    CHECK (total_sessions > 0);
ALTER TABLE production_runs ADD CONSTRAINT production_runs_completed_sessions_check 
    CHECK (completed_sessions >= 0);

\echo ''
\echo '✅ Migration complete! Summary:'
\echo '   - Removed batch_id from production_runs'
\echo '   - Dropped instruction_run_status lookup table'
\echo '   - Added CHECK constraints for all status fields'
\echo '   - Added CHECK constraints for session counters'
\echo ''
\echo '💡 Your data is still intact! No need to re-migrate.'
