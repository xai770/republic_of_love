-- Migration 044: Add Environment Flag to Workflows
-- ===================================================
-- 
-- Purpose: Add environment column to workflows table to distinguish between
--          development, UAT, production, and archived workflows.
--
-- Motivation: Multiple scripts write to skills_taxonomy/ with different approaches.
--             Need to know which workflow is "production" vs experimental.
--
-- Schema Changes:
--   - workflows.environment: VARCHAR(10) NOT NULL DEFAULT 'DEV'
--   - CHECK constraint: environment IN ('DEV', 'UAT', 'PROD', 'OLD')
--   - workflows_history gets same column
--
-- Data Migration:
--   - Workflow 3001 (Complete Job Processing) → PROD
--   - Workflow 3003 (Taxonomy Maintenance) → PROD
--   - All others → DEV
--
-- Author: Arden
-- Date: 2025-11-13

-- Add environment column to workflows
ALTER TABLE workflows 
ADD COLUMN environment VARCHAR(10) NOT NULL DEFAULT 'DEV'
CHECK (environment IN ('DEV', 'UAT', 'PROD', 'OLD'));

-- Add to workflows_history for audit trail
ALTER TABLE workflows_history
ADD COLUMN environment VARCHAR(10);

-- Set production workflows
UPDATE workflows 
SET environment = 'PROD' 
WHERE workflow_id IN (3001, 3003);

-- Add helpful comment
COMMENT ON COLUMN workflows.environment IS 
'Deployment environment: DEV (development/testing), UAT (user acceptance testing), PROD (production), OLD (archived/deprecated)';

-- Show current workflow environments
SELECT 
    workflow_id, 
    workflow_name, 
    environment,
    enabled 
FROM workflows 
ORDER BY environment, workflow_id;
