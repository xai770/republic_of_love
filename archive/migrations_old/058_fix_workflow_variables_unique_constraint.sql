-- ============================================================================
-- Migration 058: Fix workflow_variables UNIQUE constraint
-- ============================================================================
-- Author: Arden & xai
-- Date: 2025-11-06
-- Description: Add scope to UNIQUE constraint to allow same variable name
--              in different scopes (e.g., posting_id as both input and output)

BEGIN;

-- Drop old constraint
ALTER TABLE workflow_variables 
DROP CONSTRAINT IF EXISTS workflow_variables_workflow_id_variable_name_version_key;

-- Add new constraint with scope
ALTER TABLE workflow_variables 
ADD CONSTRAINT workflow_variables_workflow_id_variable_name_scope_version_key 
UNIQUE (workflow_id, variable_name, scope, version);

COMMENT ON CONSTRAINT workflow_variables_workflow_id_variable_name_scope_version_key 
ON workflow_variables IS 
'Ensures uniqueness per workflow + variable name + scope + version. 
Same variable name can exist in different scopes (input vs output).';

COMMIT;

-- Test the fix
SELECT 'Migration 058 complete: Fixed UNIQUE constraint to include scope' AS status;
