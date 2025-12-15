-- Migration 021: Rename variations to test_cases
-- Date: 2025-10-31
-- Purpose: Rename variations table to test_cases for clarity
--          Add test_case_name column (position 2)
--          Update all related references

-- This migration renames the variations table to test_cases because:
-- 1. "variations" is ambiguous (could mean versions, parameters, or test data)
-- 2. "test_cases" is self-documenting and clear
-- 3. Each entry is literally a test case with inputs and expected outputs
-- 4. Adds test_case_name column to follow xxx_id/xxx_name standard

BEGIN;

-- Step 1: Rename the sequence
ALTER SEQUENCE variations_variation_id_seq RENAME TO test_cases_test_case_id_seq;

-- Step 2: Rename the history table first
ALTER TABLE variations_history RENAME TO test_cases_history;

-- Step 3: Rename columns in history table
ALTER TABLE test_cases_history RENAME COLUMN variation_id TO test_case_id;

-- Step 4: Export data, rename table, and prepare for column addition
CREATE TABLE test_cases_temp (
    test_case_id INTEGER PRIMARY KEY,
    workflow_id INTEGER NOT NULL,
    test_data JSONB NOT NULL,
    difficulty_level INTEGER DEFAULT 1,
    expected_response TEXT,
    response_format TEXT,
    complexity_score REAL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Copy data from variations
INSERT INTO test_cases_temp (
    test_case_id,
    workflow_id,
    test_data,
    difficulty_level,
    expected_response,
    response_format,
    complexity_score,
    enabled,
    created_at,
    updated_at
)
SELECT 
    variation_id,
    workflow_id,
    test_data,
    difficulty_level,
    expected_response,
    response_format,
    complexity_score,
    enabled,
    created_at,
    updated_at
FROM variations;

-- Step 5: Drop old table (CASCADE will drop FK constraints)
DROP TABLE variations CASCADE;

-- Step 6: Create new table with test_case_name in position 2
CREATE TABLE test_cases (
    test_case_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    test_case_name TEXT UNIQUE NOT NULL,
    workflow_id INTEGER NOT NULL,
    test_data JSONB NOT NULL,
    difficulty_level INTEGER DEFAULT 1,
    expected_response TEXT,
    response_format TEXT,
    complexity_score REAL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 7: Set the sequence to continue from the last value
SELECT setval('test_cases_test_case_id_seq', (SELECT MAX(test_case_id) FROM test_cases_temp));

-- Step 8: Insert data with OVERRIDING SYSTEM VALUE and generate test_case_name
INSERT INTO test_cases (
    test_case_id,
    test_case_name,
    workflow_id,
    test_data,
    difficulty_level,
    expected_response,
    response_format,
    complexity_score,
    enabled,
    created_at,
    updated_at
) OVERRIDING SYSTEM VALUE
SELECT 
    test_case_id,
    'test_case_' || test_case_id AS test_case_name,
    workflow_id,
    test_data,
    difficulty_level,
    expected_response,
    response_format,
    complexity_score,
    enabled,
    created_at,
    updated_at
FROM test_cases_temp;

-- Step 9: Drop temporary table
DROP TABLE test_cases_temp;

-- Step 10: Recreate indexes
CREATE INDEX idx_test_cases_workflow ON test_cases(workflow_id);
CREATE INDEX idx_test_cases_difficulty ON test_cases(difficulty_level);
CREATE INDEX idx_test_cases_enabled ON test_cases(enabled);
CREATE INDEX idx_test_cases_test_data ON test_cases USING GIN(test_data);

-- Step 11: Add foreign key constraint to workflows
ALTER TABLE test_cases 
    ADD CONSTRAINT test_cases_workflow_id_fkey 
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id) ON DELETE CASCADE;

-- Step 12: Rename the archive function
ALTER FUNCTION archive_variations() RENAME TO archive_test_cases;

-- Step 13: Create updated trigger
CREATE TRIGGER test_cases_history_trigger
    BEFORE UPDATE ON test_cases
    FOR EACH ROW
    EXECUTE FUNCTION archive_test_cases();

-- Step 14: Update workflow_runs table FK constraint
ALTER TABLE workflow_runs 
    ADD CONSTRAINT workflow_runs_test_case_id_fkey 
    FOREIGN KEY (variation_id) REFERENCES test_cases(test_case_id);

-- Step 15: Rename the variation_id column in workflow_runs to test_case_id
ALTER TABLE workflow_runs RENAME COLUMN variation_id TO test_case_id;

-- Step 16: Add comprehensive comments
COMMENT ON TABLE test_cases IS 'Test cases for workflows with varying difficulty levels. Each test case contains input data (test_data) and expected outputs (expected_response) for validating workflow execution. Used in TESTING mode to verify workflows work correctly across different scenarios and complexity levels.';
COMMENT ON COLUMN test_cases.test_case_id IS 'Unique identifier for this test case';
COMMENT ON COLUMN test_cases.test_case_name IS 'Human-readable name for this test case';
COMMENT ON COLUMN test_cases.workflow_id IS 'Foreign key to workflows table - which workflow this test case validates';
COMMENT ON COLUMN test_cases.test_data IS 'JSONB object containing input parameters for the test case';
COMMENT ON COLUMN test_cases.difficulty_level IS 'Integer representing test complexity (1=easy, 2=medium, 3=hard, etc.)';
COMMENT ON COLUMN test_cases.expected_response IS 'Expected output from the workflow for validation';
COMMENT ON COLUMN test_cases.response_format IS 'Format specification for the expected response';
COMMENT ON COLUMN test_cases.complexity_score IS 'Computed complexity metric for this test case';
COMMENT ON COLUMN test_cases.enabled IS 'Whether this test case is active (true) or disabled (false)';
COMMENT ON COLUMN test_cases.created_at IS 'Timestamp when this test case was created';
COMMENT ON COLUMN test_cases.updated_at IS 'Timestamp when this test case was last modified';

COMMIT;

-- Verification queries (run after migration)
-- SELECT COUNT(*) FROM test_cases;  -- Should show 557
-- SELECT test_case_id, test_case_name, workflow_id, test_data FROM test_cases LIMIT 5;
-- \d test_cases
