-- ============================================================================
-- Workflow 1125: Profile Career Deep Analysis
-- ============================================================================
-- Uses existing workflow 1122 (profile_skill_extraction) plus deeper analysis
-- Complements skill extraction with organizational dynamics understanding
-- ============================================================================

BEGIN;

-- Create Workflow first
INSERT INTO workflows (
    workflow_id,
    workflow_name,
    workflow_description,
    max_total_session_runs,
    enabled
) VALUES (
    1125,
    'Profile Career Deep Analysis',
    'Multi-model career analysis: organizational dynamics, stakeholder patterns, technical/soft skills. Stores in career_analyses table for querying.',
    150,
    true
);

-- Note: This will be run via Python runner (workflow_1125_runner.py)
-- The runner handles chunking and orchestration
-- Results stored in career_analyses table

COMMIT;

-- Verify
SELECT workflow_id, workflow_name FROM workflows WHERE workflow_id = 1125;
