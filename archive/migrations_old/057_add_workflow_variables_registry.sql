-- Migration 057: Add Workflow Variables Registry
-- Purpose: Central registry for workflow input/output contracts
-- Enables type validation, documentation, and ExecAgent integration
-- Date: 2025-11-06
-- Author: Arden (Option D: Hybrid Contracts + Registry)

-- ============================================================================
-- Workflow Variables Registry
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflow_variables (
    variable_id SERIAL PRIMARY KEY,
    variable_name TEXT NOT NULL,
    workflow_id INT REFERENCES workflows(workflow_id),
    scope TEXT NOT NULL CHECK (scope IN ('input', 'output', 'internal', 'global')),
    data_type TEXT NOT NULL,  -- 'string', 'integer', 'boolean', 'array', 'object', 'json'
    json_schema JSONB,  -- Full JSON Schema for validation
    is_required BOOLEAN DEFAULT false,
    default_value JSONB,
    description TEXT,
    example_value JSONB,
    python_type TEXT,  -- e.g., 'int', 'List[str]', 'Dict[str, Any]'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_current BOOLEAN DEFAULT true,
    version INT DEFAULT 1,
    
    -- Ensure unique current versions per workflow + variable
    UNIQUE (workflow_id, variable_name, version)
);

CREATE INDEX idx_workflow_variables_workflow ON workflow_variables(workflow_id);
CREATE INDEX idx_workflow_variables_scope ON workflow_variables(scope);
CREATE INDEX idx_workflow_variables_current ON workflow_variables(is_current);

COMMENT ON TABLE workflow_variables IS 'Registry of all workflow input/output variables with type contracts';
COMMENT ON COLUMN workflow_variables.scope IS 'Variable scope: input (passed to workflow), output (returned), internal (used during execution), global (cross-workflow)';
COMMENT ON COLUMN workflow_variables.json_schema IS 'JSON Schema for validation (auto-generated from Python dataclasses)';
COMMENT ON COLUMN workflow_variables.python_type IS 'Python type annotation for code generation';
COMMENT ON COLUMN workflow_variables.is_current IS 'False for deprecated versions, true for current contract';

-- ============================================================================
-- Example Data: Workflow 1121 (Job Skills Extraction)
-- ============================================================================

INSERT INTO workflow_variables (variable_name, workflow_id, scope, data_type, json_schema, is_required, description, example_value, python_type) VALUES
(
    'posting_id',
    1121,
    'input',
    'integer',
    '{"type": "integer", "minimum": 1}'::jsonb,
    true,
    'Database ID of job posting to extract skills from',
    '42'::jsonb,
    'int'
),
(
    'skills',
    1121,
    'output',
    'array',
    '{
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "skill": {"type": "string"},
                "importance": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "weight": {"type": "number", "minimum": 0, "maximum": 1},
                "proficiency": {"type": "string"},
                "years_required": {"type": "integer", "minimum": 0},
                "reasoning": {"type": "string"}
            },
            "required": ["skill"]
        }
    }'::jsonb,
    true,
    'Array of extracted skills with metadata',
    '[{"skill": "Python", "importance": "high", "weight": 0.9, "proficiency": "advanced", "years_required": 3, "reasoning": "Core technology mentioned 5 times"}]'::jsonb,
    'List[Dict[str, Any]]'
),
(
    'posting_id',
    1121,
    'output',
    'integer',
    '{"type": "integer", "minimum": 1}'::jsonb,
    true,
    'Same posting_id passed through for reference',
    '42'::jsonb,
    'int'
);

-- ============================================================================
-- Example Data: Deutsche Bank Job Fetcher (Internal Variables)
-- ============================================================================

INSERT INTO workflow_variables (variable_name, workflow_id, scope, data_type, json_schema, is_required, description, example_value, python_type) VALUES
(
    'ApplyURI',
    NULL,  -- Not workflow-specific, used in job_fetcher
    'internal',
    'array',
    '{
        "type": "array",
        "items": {"type": "string", "format": "uri"}
    }'::jsonb,
    false,
    'Workday job application URLs from API response (at TOP level after flattening)',
    '["https://db.wd3.myworkdayjobs.com/DBWebsite/job/Mumbai-Nirlon-Knowledge-Pk-B1/Risk-Analyst_R0405266/apply"]'::jsonb,
    'List[str]'
),
(
    'MatchedObjectId',
    NULL,
    'internal',
    'string',
    '{"type": "string", "pattern": "^[0-9]+$"}'::jsonb,
    true,
    'External job ID from Deutsche Bank API',
    '"68147"'::jsonb,
    'str'
),
(
    'PositionTitle',
    NULL,
    'internal',
    'string',
    '{"type": "string", "minLength": 1}'::jsonb,
    true,
    'Job title (at TOP level after flattening)',
    '"Risk Analyst"'::jsonb,
    'str'
);

-- ============================================================================
-- Helper Function: Get Current Contract for Workflow
-- ============================================================================

CREATE OR REPLACE FUNCTION get_workflow_contract(p_workflow_id INT)
RETURNS TABLE (
    input_vars JSONB,
    output_vars JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        jsonb_object_agg(
            CASE WHEN scope = 'input' THEN variable_name END,
            jsonb_build_object(
                'type', data_type,
                'required', is_required,
                'schema', json_schema,
                'description', description
            )
        ) FILTER (WHERE scope = 'input') as input_vars,
        jsonb_object_agg(
            CASE WHEN scope = 'output' THEN variable_name END,
            jsonb_build_object(
                'type', data_type,
                'required', is_required,
                'schema', json_schema,
                'description', description
            )
        ) FILTER (WHERE scope = 'output') as output_vars
    FROM workflow_variables
    WHERE workflow_id = p_workflow_id
    AND is_current = true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_workflow_contract IS 'Returns input and output contracts for a workflow as JSONB';

-- ============================================================================
-- Migration Complete
-- ============================================================================

SELECT 'Migration 057 complete: Workflow variables registry created' as status;
