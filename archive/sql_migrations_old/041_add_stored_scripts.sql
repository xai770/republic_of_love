-- Migration 041: Stored Scripts System
-- =====================================
-- Store Python scripts directly in Turing database for version control
-- Philosophy: Code as data. Everything version-controlled.
--
-- Purpose:
--   - Version control Python scripts IN database
--   - Track dependencies between scripts and workflows
--   - Enable workflow execution of stored scripts
--   - Audit trail for all code changes
--   - Complete system reproducibility

-- Create stored_scripts table
CREATE TABLE IF NOT EXISTS stored_scripts (
    script_id SERIAL PRIMARY KEY,
    script_name VARCHAR(255) NOT NULL UNIQUE,
    script_description TEXT,
    script_version VARCHAR(50) NOT NULL,
    script_language VARCHAR(50) DEFAULT 'python',
    script_category VARCHAR(100),
    script_code TEXT NOT NULL,
    
    -- Dependencies
    requires_packages TEXT[], -- Python packages required
    requires_scripts INTEGER[], -- Other script_ids needed
    
    -- Execution metadata
    entry_point VARCHAR(255), -- Main function/class to call
    expected_args TEXT[], -- Required arguments
    returns_data_type VARCHAR(100), -- What it returns
    
    -- Version control
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    is_current_version BOOLEAN DEFAULT true,
    replaces_script_id INTEGER REFERENCES stored_scripts(script_id),
    
    -- Documentation
    usage_example TEXT,
    change_log TEXT,
    
    -- Metadata
    tags TEXT[],
    is_production BOOLEAN DEFAULT false,
    last_executed_at TIMESTAMP,
    execution_count INTEGER DEFAULT 0
);

-- Create index for fast lookups
CREATE INDEX idx_stored_scripts_name ON stored_scripts(script_name);
CREATE INDEX idx_stored_scripts_category ON stored_scripts(script_category);
CREATE INDEX idx_stored_scripts_current ON stored_scripts(is_current_version) WHERE is_current_version = true;

-- Create script_executions table
CREATE TABLE IF NOT EXISTS script_executions (
    execution_id SERIAL PRIMARY KEY,
    script_id INTEGER REFERENCES stored_scripts(script_id),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR(100),
    
    -- Execution context
    execution_args JSONB,
    execution_context JSONB, -- Environment, workflow_id, etc.
    
    -- Results
    status VARCHAR(50), -- SUCCESS, ERROR, TIMEOUT
    duration_ms INTEGER,
    return_value JSONB,
    stdout_log TEXT,
    stderr_log TEXT,
    error_message TEXT
);

CREATE INDEX idx_script_executions_script ON script_executions(script_id);
CREATE INDEX idx_script_executions_date ON script_executions(executed_at DESC);

-- Create workflow_scripts table (link workflows to scripts)
CREATE TABLE IF NOT EXISTS workflow_scripts (
    workflow_id INTEGER REFERENCES workflows(workflow_id),
    script_id INTEGER REFERENCES stored_scripts(script_id),
    execution_order INTEGER, -- For workflows with multiple scripts
    is_required BOOLEAN DEFAULT true,
    
    PRIMARY KEY (workflow_id, script_id)
);

-- View: Current script versions
CREATE OR REPLACE VIEW v_current_scripts AS
SELECT 
    s.script_id,
    s.script_name,
    s.script_version,
    s.script_category,
    s.script_description,
    s.entry_point,
    s.created_at,
    s.is_production,
    s.execution_count,
    s.last_executed_at,
    COALESCE(array_length(s.requires_packages, 1), 0) as dependency_count,
    COALESCE(
        (SELECT COUNT(*) FROM workflow_scripts ws WHERE ws.script_id = s.script_id),
        0
    ) as workflow_count
FROM stored_scripts s
WHERE s.is_current_version = true
ORDER BY s.script_category, s.script_name;

-- View: Script execution history
CREATE OR REPLACE VIEW v_script_execution_history AS
SELECT 
    s.script_name,
    s.script_version,
    e.execution_id,
    e.executed_at,
    e.status,
    e.duration_ms,
    e.error_message,
    e.execution_context->>'workflow_id' as workflow_id
FROM script_executions e
JOIN stored_scripts s ON e.script_id = s.script_id
ORDER BY e.executed_at DESC;

-- View: Workflow script dependencies
CREATE OR REPLACE VIEW v_workflow_script_dependencies AS
SELECT 
    w.workflow_id,
    w.workflow_name,
    ws.execution_order,
    s.script_id,
    s.script_name,
    s.script_version,
    s.is_production,
    ws.is_required
FROM workflow_scripts ws
JOIN workflows w ON ws.workflow_id = w.workflow_id
JOIN stored_scripts s ON ws.script_id = s.script_id
WHERE s.is_current_version = true
ORDER BY w.workflow_id, ws.execution_order;

-- Function: Store new script version
CREATE OR REPLACE FUNCTION store_script_version(
    p_script_name VARCHAR,
    p_script_code TEXT,
    p_version VARCHAR,
    p_description TEXT DEFAULT NULL,
    p_change_log TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_new_script_id INTEGER;
    v_old_script_id INTEGER;
BEGIN
    -- Get current version if exists
    SELECT script_id INTO v_old_script_id
    FROM stored_scripts
    WHERE script_name = p_script_name
    AND is_current_version = true;
    
    -- Mark old version as not current
    IF v_old_script_id IS NOT NULL THEN
        UPDATE stored_scripts
        SET is_current_version = false
        WHERE script_id = v_old_script_id;
    END IF;
    
    -- Insert new version
    INSERT INTO stored_scripts (
        script_name,
        script_code,
        script_version,
        script_description,
        change_log,
        replaces_script_id,
        is_current_version
    ) VALUES (
        p_script_name,
        p_script_code,
        p_version,
        p_description,
        p_change_log,
        v_old_script_id,
        true
    )
    RETURNING script_id INTO v_new_script_id;
    
    RETURN v_new_script_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get current script code
CREATE OR REPLACE FUNCTION get_script_code(p_script_name VARCHAR)
RETURNS TEXT AS $$
DECLARE
    v_code TEXT;
BEGIN
    SELECT script_code INTO v_code
    FROM stored_scripts
    WHERE script_name = p_script_name
    AND is_current_version = true;
    
    IF v_code IS NULL THEN
        RAISE EXCEPTION 'Script % not found', p_script_name;
    END IF;
    
    RETURN v_code;
END;
$$ LANGUAGE plpgsql;

-- Function: Record script execution
CREATE OR REPLACE FUNCTION record_script_execution(
    p_script_name VARCHAR,
    p_status VARCHAR,
    p_duration_ms INTEGER DEFAULT NULL,
    p_return_value JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_execution_context JSONB DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_script_id INTEGER;
    v_execution_id INTEGER;
BEGIN
    -- Get script_id
    SELECT script_id INTO v_script_id
    FROM stored_scripts
    WHERE script_name = p_script_name
    AND is_current_version = true;
    
    IF v_script_id IS NULL THEN
        RAISE EXCEPTION 'Script % not found', p_script_name;
    END IF;
    
    -- Insert execution record
    INSERT INTO script_executions (
        script_id,
        status,
        duration_ms,
        return_value,
        error_message,
        execution_context
    ) VALUES (
        v_script_id,
        p_status,
        p_duration_ms,
        p_return_value,
        p_error_message,
        p_execution_context
    )
    RETURNING execution_id INTO v_execution_id;
    
    -- Update script stats
    UPDATE stored_scripts
    SET 
        execution_count = execution_count + 1,
        last_executed_at = CURRENT_TIMESTAMP
    WHERE script_id = v_script_id;
    
    RETURN v_execution_id;
END;
$$ LANGUAGE plpgsql;

-- Seed with turing_job_fetcher.py
DO $$
DECLARE
    v_fetcher_code TEXT;
BEGIN
    -- Read from file and store
    -- (Note: In production, read actual file content)
    v_fetcher_code := '# See core/turing_job_fetcher.py for current code';
    
    PERFORM store_script_version(
        'turing_job_fetcher',
        v_fetcher_code,
        '7.0.0',
        'Turing-integrated job fetcher. Fetches from Deutsche Bank API, stores in database with deduplication.',
        'Initial version: Complete Turing integration, user preferences support, lifecycle tracking'
    );
    
    -- Update with metadata
    UPDATE stored_scripts
    SET 
        script_category = 'job_ingestion',
        entry_point = 'TuringJobFetcher.fetch_jobs_for_user',
        expected_args = ARRAY['user_id', 'max_jobs'],
        returns_data_type = 'Dict[str, int]',
        requires_packages = ARRAY['psycopg2', 'requests', 'beautifulsoup4'],
        tags = ARRAY['job-fetching', 'api', 'deutsche-bank', 'production'],
        usage_example = E'from turing_job_fetcher import TuringJobFetcher\nfetcher = TuringJobFetcher(source_id=1)\nstats = fetcher.fetch_jobs_for_user(user_id=1, max_jobs=50)\nfetcher.close()',
        is_production = true
    WHERE script_name = 'turing_job_fetcher';
    
    RAISE NOTICE '✅ Stored script: turing_job_fetcher v7.0.0';
END $$;

-- Grant permissions
GRANT SELECT ON stored_scripts TO base_admin;
GRANT INSERT, UPDATE ON stored_scripts TO base_admin;
GRANT SELECT, INSERT ON script_executions TO base_admin;
GRANT SELECT ON v_current_scripts TO base_admin;

COMMIT;

-- Summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Migration 041: Stored Scripts System - COMPLETE';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - stored_scripts table (version control)';
    RAISE NOTICE '  - script_executions table (audit trail)';
    RAISE NOTICE '  - workflow_scripts table (workflow integration)';
    RAISE NOTICE '  - Functions: store_script_version(), get_script_code(), record_script_execution()';
    RAISE NOTICE '  - Views: v_current_scripts, v_script_execution_history, v_workflow_script_dependencies';
    RAISE NOTICE '';
    RAISE NOTICE 'Seeded:';
    RAISE NOTICE '  - turing_job_fetcher v7.0.0';
    RAISE NOTICE '';
    RAISE NOTICE 'Philosophy: Code as data. Everything version-controlled.';
    RAISE NOTICE '=================================================================';
END $$;
