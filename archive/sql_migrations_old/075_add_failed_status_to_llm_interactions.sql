-- Migration 075: Add FAILED status to llm_interactions constraint
-- Date: 2025-11-14
-- Purpose: Allow FAILED status for SQL query actors and circuit breaker states

ALTER TABLE llm_interactions
DROP CONSTRAINT IF EXISTS llm_interactions_status_check;

ALTER TABLE llm_interactions
ADD CONSTRAINT llm_interactions_status_check 
CHECK (status IN ('PENDING', 'SUCCESS', 'TIMEOUT', 'ERROR', 'RATE_LIMITED', 'QUOTA_EXCEEDED', 'INVALID_REQUEST', 'FAILED'));

-- Note: FAILED is used when:
-- 1. SQL query execution fails  
-- 2. Script actors return [FAILED] branch
-- 3. Circuit breaker is open (logged as ERROR status as of wave_executor fix)
