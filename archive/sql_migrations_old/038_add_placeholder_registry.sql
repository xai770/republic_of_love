-- Migration 038: Placeholder Registry System
-- Created: 2025-11-03
-- Purpose: First-class placeholder management - metadata as data, not code
-- Inspired by: Turing (data-driven computation), Lovelace (analytical precision), Pascal (elegant abstraction)

-- ============================================================================
-- PLACEHOLDER DEFINITIONS: The registry of all available placeholders
-- ============================================================================

CREATE TABLE placeholder_definitions (
    placeholder_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    placeholder_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    -- source_type values:
    --   'test_case_data' - from test_cases.test_data JSON
    --   'posting'        - from postings table
    --   'profile'        - from profiles table  
    --   'dialogue_output'- from previous dialogue step outputs
    --   'static'         - hardcoded default value
    --   'custom_query'   - custom SQL to resolve
    
    source_table TEXT,
    source_column TEXT,
    source_query TEXT,
    -- If source_query is provided, it takes precedence
    -- Query can use :job_id, :profile_id, :test_case_id parameters
    
    is_required BOOLEAN DEFAULT false,
    default_value TEXT,
    description TEXT NOT NULL,
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT placeholder_name_unique UNIQUE(placeholder_name),
    CONSTRAINT valid_source_type CHECK (source_type IN ('test_case_data', 'posting', 'profile', 'dialogue_output', 'static', 'custom_query'))
);

CREATE INDEX idx_placeholder_name ON placeholder_definitions(placeholder_name);
CREATE INDEX idx_placeholder_source ON placeholder_definitions(source_type, source_table);

COMMENT ON TABLE placeholder_definitions IS 'Registry of all available placeholders in the Turing system - first-class metadata management';
COMMENT ON COLUMN placeholder_definitions.placeholder_name IS 'The placeholder name used in templates: {placeholder_name}';
COMMENT ON COLUMN placeholder_definitions.source_type IS 'Where to fetch the value: test_case_data, posting, profile, dialogue_output, static, custom_query';
COMMENT ON COLUMN placeholder_definitions.source_query IS 'Custom SQL to resolve placeholder (overrides table/column). Use :job_id, :profile_id, :test_case_id parameters';

-- ============================================================================
-- WORKFLOW PLACEHOLDERS: Which workflows need which placeholders
-- ============================================================================

CREATE TABLE workflow_placeholders (
    workflow_id INTEGER NOT NULL REFERENCES workflows(workflow_id) ON DELETE CASCADE,
    placeholder_id INTEGER NOT NULL REFERENCES placeholder_definitions(placeholder_id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT false,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workflow_id, placeholder_id)
);

CREATE INDEX idx_workflow_placeholders_workflow ON workflow_placeholders(workflow_id);
CREATE INDEX idx_workflow_placeholders_required ON workflow_placeholders(workflow_id, is_required);

COMMENT ON TABLE workflow_placeholders IS 'Links workflows to their required/optional placeholders';

-- ============================================================================
-- DIALOGUE STEP PLACEHOLDERS: Which dialogue steps need which placeholders
-- ============================================================================

CREATE TABLE dialogue_step_placeholders (
    dialogue_step_id INTEGER NOT NULL REFERENCES conversation_dialogue(dialogue_step_id) ON DELETE CASCADE,
    placeholder_id INTEGER NOT NULL REFERENCES placeholder_definitions(placeholder_id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT false,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dialogue_step_id, placeholder_id)
);

CREATE INDEX idx_dialogue_step_placeholders_step ON dialogue_step_placeholders(dialogue_step_id);
CREATE INDEX idx_dialogue_step_placeholders_required ON dialogue_step_placeholders(dialogue_step_id, is_required);

COMMENT ON TABLE dialogue_step_placeholders IS 'Links dialogue steps to their required/optional placeholders';

-- ============================================================================
-- SEED DATA: Common placeholders
-- ============================================================================

-- Posting-related placeholders
INSERT INTO placeholder_definitions (placeholder_name, source_type, source_table, source_column, description) VALUES
('job_description', 'posting', 'postings', 'job_description', 'Full job posting description text'),
('job_title', 'posting', 'postings', 'job_title', 'Job title from posting'),
('skill_keywords', 'posting', 'postings', 'skill_keywords', 'Extracted skills JSONB array from posting'),
('organization_name', 'posting', 'postings', 'organization_name', 'Company/organization name'),
('organization_division', 'posting', 'postings', 'organization_division', 'Division/department within organization'),
('location_city', 'posting', 'postings', 'location_city', 'City location of job'),
('location_state', 'posting', 'postings', 'location_state', 'State/province location'),
('location_country', 'posting', 'postings', 'location_country', 'Country location'),
('employment_type', 'posting', 'postings', 'employment_type', 'Employment type (full-time, contract, etc)'),
('employment_career_level', 'posting', 'postings', 'employment_career_level', 'Career level (junior, senior, etc)'),
('employment_salary_range', 'posting', 'postings', 'employment_salary_range', 'Salary range if specified'),
('posting_name', 'posting', 'postings', 'posting_name', 'Posting name/title'),
('extracted_summary', 'posting', 'postings', 'extracted_summary', 'AI-extracted summary of posting');

-- Profile-related placeholders
INSERT INTO placeholder_definitions (placeholder_name, source_type, source_table, source_column, description) VALUES
('profile_name', 'profile', 'profiles', 'profile_name', 'Candidate profile name'),
('profile_summary', 'profile', 'profiles', 'profile_summary', 'Candidate profile summary/bio'),
('profile_skills', 'profile', 'profiles', 'skill_keywords', 'Candidate skills JSONB array'),
('years_experience', 'profile', 'profiles', 'years_experience', 'Years of professional experience'),
('current_location', 'profile', 'profiles', 'location_city', 'Candidate current location');

-- Dialogue output placeholders (for multi-actor workflows)
INSERT INTO placeholder_definitions (placeholder_name, source_type, description) VALUES
('step_1_output', 'dialogue_output', 'Output from dialogue step with execution_order=1'),
('step_2_output', 'dialogue_output', 'Output from dialogue step with execution_order=2'),
('step_3_output', 'dialogue_output', 'Output from dialogue step with execution_order=3'),
('step_4_output', 'dialogue_output', 'Output from dialogue step with execution_order=4'),
('step_5_output', 'dialogue_output', 'Output from dialogue step with execution_order=5');

-- Test case data placeholders (dynamic - passed directly from test_case.test_data JSON)
INSERT INTO placeholder_definitions (placeholder_name, source_type, description) VALUES
('job_id', 'test_case_data', 'Job/posting ID from test case'),
('profile_id', 'test_case_data', 'Profile ID from test case'),
('test_input', 'test_case_data', 'Generic test input data');

-- ============================================================================
-- LINK WORKFLOW 1124 (Fake Job Detector) to its placeholders
-- ============================================================================

INSERT INTO workflow_placeholders (workflow_id, placeholder_id, is_required, description) VALUES
-- Required: Must have job description
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'job_description'), true, 'Core input for red flag analysis'),
-- Required: Need skills for analysis
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'skill_keywords'), true, 'Skills to analyze for narrowness/specificity'),
-- Optional: Context helps but not required
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'job_title'), false, 'Adds context to analysis'),
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'organization_name'), false, 'Company context for analysis'),
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'location_city'), false, 'Geographic constraint analysis'),
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'employment_career_level'), false, 'Level-specific IHL patterns'),
-- Dialogue outputs (for multi-actor debate)
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'step_1_output'), true, 'Analyst findings (for Skeptic and HR Expert)'),
(1124, (SELECT placeholder_id FROM placeholder_definitions WHERE placeholder_name = 'step_2_output'), true, 'Skeptic challenge (for HR Expert)');

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: What placeholders does a workflow need?
CREATE VIEW v_workflow_placeholder_requirements AS
SELECT 
    w.workflow_id,
    w.workflow_name,
    pd.placeholder_name,
    pd.source_type,
    COALESCE(pd.source_table || '.' || pd.source_column, pd.source_query, 'dynamic') as source_location,
    wp.is_required,
    pd.description
FROM workflow_placeholders wp
JOIN workflows w ON w.workflow_id = wp.workflow_id
JOIN placeholder_definitions pd ON pd.placeholder_id = wp.placeholder_id
ORDER BY w.workflow_id, wp.is_required DESC, pd.placeholder_name;

COMMENT ON VIEW v_workflow_placeholder_requirements IS 'Shows all placeholder requirements for each workflow';

-- View: What placeholders are used across the system?
CREATE VIEW v_placeholder_usage AS
SELECT 
    pd.placeholder_name,
    pd.source_type,
    COUNT(DISTINCT wp.workflow_id) as workflow_count,
    COUNT(DISTINCT dsp.dialogue_step_id) as dialogue_step_count,
    STRING_AGG(DISTINCT w.workflow_name, ', ' ORDER BY w.workflow_name) as used_in_workflows
FROM placeholder_definitions pd
LEFT JOIN workflow_placeholders wp ON wp.placeholder_id = pd.placeholder_id
LEFT JOIN dialogue_step_placeholders dsp ON dsp.placeholder_id = pd.placeholder_id
LEFT JOIN workflows w ON w.workflow_id = wp.workflow_id
GROUP BY pd.placeholder_id, pd.placeholder_name, pd.source_type
ORDER BY workflow_count DESC, pd.placeholder_name;

COMMENT ON VIEW v_placeholder_usage IS 'Shows usage statistics for each placeholder';

-- ============================================================================
-- VALIDATION FUNCTION: Check if workflow has all required placeholders
-- ============================================================================

CREATE OR REPLACE FUNCTION validate_workflow_placeholders(
    p_workflow_id INTEGER,
    p_test_case_data JSONB
) RETURNS TABLE (
    is_valid BOOLEAN,
    missing_required TEXT[],
    available_optional TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH required_check AS (
        SELECT 
            pd.placeholder_name,
            wp.is_required,
            CASE 
                WHEN pd.source_type = 'test_case_data' THEN p_test_case_data ? pd.placeholder_name
                WHEN pd.source_type IN ('posting', 'profile') THEN true -- Will be fetched
                WHEN pd.source_type = 'dialogue_output' THEN true -- Will be computed
                WHEN pd.source_type = 'static' THEN true
                ELSE false
            END as is_available
        FROM workflow_placeholders wp
        JOIN placeholder_definitions pd ON pd.placeholder_id = wp.placeholder_id
        WHERE wp.workflow_id = p_workflow_id
    )
    SELECT 
        NOT EXISTS (SELECT 1 FROM required_check WHERE is_required AND NOT is_available) as is_valid,
        ARRAY_AGG(placeholder_name ORDER BY placeholder_name) FILTER (WHERE is_required AND NOT is_available) as missing_required,
        ARRAY_AGG(placeholder_name ORDER BY placeholder_name) FILTER (WHERE NOT is_required AND is_available) as available_optional
    FROM required_check;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_workflow_placeholders IS 'Validates that a workflow has all required placeholders before execution';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 038 complete: Placeholder Registry System';
    RAISE NOTICE '   - Created placeholder_definitions table';
    RAISE NOTICE '   - Created workflow_placeholders table';
    RAISE NOTICE '   - Created dialogue_step_placeholders table';
    RAISE NOTICE '   - Seeded % common placeholders', (SELECT COUNT(*) FROM placeholder_definitions);
    RAISE NOTICE '   - Linked workflow 1124 to % placeholders', (SELECT COUNT(*) FROM workflow_placeholders WHERE workflow_id = 1124);
    RAISE NOTICE '   - Created helper views and validation function';
    RAISE NOTICE '';
    RAISE NOTICE '💡 Query example:';
    RAISE NOTICE '   SELECT * FROM v_workflow_placeholder_requirements WHERE workflow_id = 1124;';
END $$;
