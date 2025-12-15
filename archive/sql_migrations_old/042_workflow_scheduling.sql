-- Migration 042: Workflow Scheduling System
-- ============================================
-- Enable Turing to know WHEN to run workflows autonomously
-- Philosophy: "The system that knows what it needs to do next"
--
-- Purpose:
--   - Time-based triggers (cron schedules)
--   - Event-based triggers (condition monitoring)
--   - Dependency management between workflows
--   - Execution priority and throttling
--   - Complete audit trail of autonomous decisions

-- =====================================================================
-- CORE TABLES
-- =====================================================================

-- Workflow triggers: Define WHEN workflows should run
CREATE TABLE IF NOT EXISTS workflow_triggers (
    trigger_id SERIAL PRIMARY KEY,
    workflow_id INTEGER REFERENCES workflows(workflow_id),
    
    -- Trigger identification
    trigger_name VARCHAR(255) NOT NULL,
    trigger_description TEXT,
    
    -- Trigger type
    trigger_type VARCHAR(50) NOT NULL CHECK (trigger_type IN ('SCHEDULE', 'EVENT', 'MANUAL', 'DEPENDENCY')),
    
    -- Time-based scheduling (for SCHEDULE type)
    schedule_cron VARCHAR(100), -- Standard cron format: '0 8 * * *'
    schedule_timezone VARCHAR(50) DEFAULT 'Europe/Berlin',
    
    -- Event-based conditions (for EVENT type)
    event_condition TEXT, -- SQL query that returns boolean or count
    event_threshold INTEGER DEFAULT 1, -- Minimum threshold to trigger
    event_check_interval_minutes INTEGER DEFAULT 5, -- How often to check
    
    -- Execution control
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 50, -- Higher = more urgent (0-100)
    max_concurrent_runs INTEGER DEFAULT 1, -- Prevent duplicate runs
    timeout_minutes INTEGER DEFAULT 60,
    
    -- Dependencies
    depends_on_trigger_ids INTEGER[], -- Must complete before this runs
    run_after_workflow_ids INTEGER[], -- Run after these workflows complete
    
    -- Throttling
    min_interval_minutes INTEGER, -- Minimum time between runs
    max_runs_per_day INTEGER,
    max_runs_per_hour INTEGER,
    
    -- Context
    default_parameters JSONB, -- Default parameters to pass to workflow
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    last_triggered_at TIMESTAMP,
    next_scheduled_run TIMESTAMP,
    
    -- Statistics
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    
    UNIQUE(workflow_id, trigger_name)
);

CREATE INDEX idx_workflow_triggers_enabled ON workflow_triggers(enabled) WHERE enabled = true;
CREATE INDEX idx_workflow_triggers_type ON workflow_triggers(trigger_type);
CREATE INDEX idx_workflow_triggers_next_run ON workflow_triggers(next_scheduled_run) WHERE enabled = true;

-- Trigger execution log: Every time a trigger fires
CREATE TABLE IF NOT EXISTS trigger_executions (
    execution_id SERIAL PRIMARY KEY,
    trigger_id INTEGER REFERENCES workflow_triggers(trigger_id),
    workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id),
    
    -- Execution details
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trigger_reason TEXT, -- Why did this fire?
    trigger_condition_value TEXT, -- What was the condition result?
    
    -- Outcome
    status VARCHAR(50), -- TRIGGERED, SKIPPED, THROTTLED, FAILED
    status_reason TEXT,
    
    -- Timing
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- Context
    execution_context JSONB
);

CREATE INDEX idx_trigger_executions_trigger ON trigger_executions(trigger_id);
CREATE INDEX idx_trigger_executions_time ON trigger_executions(triggered_at DESC);
CREATE INDEX idx_trigger_executions_status ON trigger_executions(status);

-- Workflow dependencies: Track which workflows must complete before others
CREATE TABLE IF NOT EXISTS workflow_dependencies (
    dependency_id SERIAL PRIMARY KEY,
    workflow_id INTEGER REFERENCES workflows(workflow_id),
    depends_on_workflow_id INTEGER REFERENCES workflows(workflow_id),
    
    -- Dependency type
    dependency_type VARCHAR(50) CHECK (dependency_type IN ('MUST_COMPLETE', 'MUST_SUCCEED', 'OPTIONAL')),
    
    -- Optional data passing
    pass_output_as_input BOOLEAN DEFAULT false,
    output_mapping JSONB, -- Map output fields to input fields
    
    UNIQUE(workflow_id, depends_on_workflow_id)
);

-- =====================================================================
-- VIEWS
-- =====================================================================

-- View: Active triggers ready to run
CREATE OR REPLACE VIEW v_triggers_ready_to_run AS
SELECT 
    t.trigger_id,
    t.trigger_name,
    t.workflow_id,
    w.workflow_name,
    t.trigger_type,
    t.priority,
    t.next_scheduled_run,
    t.last_triggered_at,
    CASE 
        WHEN t.trigger_type = 'SCHEDULE' THEN 
            'Next run: ' || COALESCE(t.next_scheduled_run::TEXT, 'Not scheduled')
        WHEN t.trigger_type = 'EVENT' THEN
            'Checking condition every ' || t.event_check_interval_minutes || ' min'
        ELSE t.trigger_type
    END as status_text
FROM workflow_triggers t
JOIN workflows w ON t.workflow_id = w.workflow_id
WHERE t.enabled = true
AND (
    -- Schedule triggers due to run
    (t.trigger_type = 'SCHEDULE' AND t.next_scheduled_run <= CURRENT_TIMESTAMP)
    OR
    -- Event triggers need checking
    (t.trigger_type = 'EVENT')
)
ORDER BY t.priority DESC, t.next_scheduled_run;

-- View: Trigger execution history
CREATE OR REPLACE VIEW v_trigger_execution_history AS
SELECT 
    t.trigger_name,
    w.workflow_name,
    te.triggered_at,
    te.status,
    te.trigger_reason,
    te.duration_ms,
    wr.status as workflow_status,
    te.execution_id
FROM trigger_executions te
JOIN workflow_triggers t ON te.trigger_id = t.trigger_id
JOIN workflows w ON t.workflow_id = w.workflow_id
LEFT JOIN workflow_runs wr ON te.workflow_run_id = wr.workflow_run_id
ORDER BY te.triggered_at DESC;

-- View: Trigger health monitoring
CREATE OR REPLACE VIEW v_trigger_health AS
SELECT 
    t.trigger_id,
    t.trigger_name,
    t.trigger_type,
    t.enabled,
    t.total_runs,
    t.successful_runs,
    t.failed_runs,
    CASE 
        WHEN t.total_runs = 0 THEN NULL
        ELSE ROUND(100.0 * t.successful_runs / t.total_runs, 1)
    END as success_rate_pct,
    t.last_triggered_at,
    AGE(CURRENT_TIMESTAMP, t.last_triggered_at) as time_since_last_run,
    CASE
        WHEN NOT t.enabled THEN '⏸️ DISABLED'
        WHEN t.last_triggered_at IS NULL THEN '🆕 NEVER RUN'
        WHEN t.last_triggered_at < CURRENT_TIMESTAMP - INTERVAL '1 day' THEN '⚠️ STALE'
        WHEN t.failed_runs::FLOAT / NULLIF(t.total_runs, 0) > 0.5 THEN '❌ UNHEALTHY'
        ELSE '✅ HEALTHY'
    END as health_status
FROM workflow_triggers t
ORDER BY t.enabled DESC, t.priority DESC;

-- View: Workflow execution schedule (next 24 hours)
CREATE OR REPLACE VIEW v_workflow_schedule_24h AS
SELECT 
    t.trigger_name,
    w.workflow_name,
    t.next_scheduled_run,
    t.priority,
    t.schedule_cron,
    AGE(t.next_scheduled_run, CURRENT_TIMESTAMP) as time_until_run
FROM workflow_triggers t
JOIN workflows w ON t.workflow_id = w.workflow_id
WHERE t.enabled = true
AND t.trigger_type = 'SCHEDULE'
AND t.next_scheduled_run BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL '24 hours'
ORDER BY t.next_scheduled_run;

-- =====================================================================
-- FUNCTIONS
-- =====================================================================

-- Function: Calculate next cron run time
CREATE OR REPLACE FUNCTION calculate_next_cron_run(
    p_cron VARCHAR,
    p_from_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) RETURNS TIMESTAMP AS $$
DECLARE
    v_next_run TIMESTAMP;
BEGIN
    -- Simplified cron parser (extend this for production)
    -- For now, support basic patterns like '0 8 * * *' (daily at 8 AM)
    
    -- This is a placeholder - in production, use pg_cron or similar
    -- For demo: if cron is '0 8 * * *', next run is tomorrow at 8 AM
    IF p_cron ~ '^\d+ \d+ \* \* \*$' THEN
        v_next_run := DATE_TRUNC('day', p_from_time + INTERVAL '1 day') + 
                      (SPLIT_PART(p_cron, ' ', 2) || ' hours')::INTERVAL +
                      (SPLIT_PART(p_cron, ' ', 1) || ' minutes')::INTERVAL;
    ELSE
        -- Default: run in 1 hour
        v_next_run := p_from_time + INTERVAL '1 hour';
    END IF;
    
    RETURN v_next_run;
END;
$$ LANGUAGE plpgsql;

-- Function: Check if trigger should run (throttling, dependencies)
CREATE OR REPLACE FUNCTION should_trigger_run(p_trigger_id INTEGER)
RETURNS TABLE(can_run BOOLEAN, reason TEXT) AS $$
DECLARE
    v_trigger RECORD;
    v_last_run TIMESTAMP;
    v_runs_today INTEGER;
    v_runs_this_hour INTEGER;
    v_active_runs INTEGER;
BEGIN
    -- Get trigger details
    SELECT * INTO v_trigger FROM workflow_triggers WHERE trigger_id = p_trigger_id;
    
    -- Check if enabled
    IF NOT v_trigger.enabled THEN
        RETURN QUERY SELECT false, 'Trigger is disabled';
        RETURN;
    END IF;
    
    -- Check concurrent runs
    SELECT COUNT(*) INTO v_active_runs
    FROM trigger_executions te
    WHERE te.trigger_id = p_trigger_id
    AND te.status = 'TRIGGERED'
    AND te.completed_at IS NULL;
    
    IF v_active_runs >= v_trigger.max_concurrent_runs THEN
        RETURN QUERY SELECT false, 'Max concurrent runs reached: ' || v_active_runs;
        RETURN;
    END IF;
    
    -- Check minimum interval
    IF v_trigger.min_interval_minutes IS NOT NULL THEN
        SELECT MAX(triggered_at) INTO v_last_run
        FROM trigger_executions
        WHERE trigger_id = p_trigger_id
        AND status = 'TRIGGERED';
        
        IF v_last_run IS NOT NULL AND 
           v_last_run > CURRENT_TIMESTAMP - (v_trigger.min_interval_minutes || ' minutes')::INTERVAL THEN
            RETURN QUERY SELECT false, 'Too soon since last run (min interval: ' || v_trigger.min_interval_minutes || ' min)';
            RETURN;
        END IF;
    END IF;
    
    -- Check daily limit
    IF v_trigger.max_runs_per_day IS NOT NULL THEN
        SELECT COUNT(*) INTO v_runs_today
        FROM trigger_executions
        WHERE trigger_id = p_trigger_id
        AND triggered_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        AND status = 'TRIGGERED';
        
        IF v_runs_today >= v_trigger.max_runs_per_day THEN
            RETURN QUERY SELECT false, 'Daily limit reached: ' || v_runs_today || '/' || v_trigger.max_runs_per_day;
            RETURN;
        END IF;
    END IF;
    
    -- All checks passed
    RETURN QUERY SELECT true, 'Ready to run';
END;
$$ LANGUAGE plpgsql;

-- Function: Evaluate event condition
CREATE OR REPLACE FUNCTION evaluate_event_condition(p_trigger_id INTEGER)
RETURNS TABLE(should_trigger BOOLEAN, condition_value TEXT) AS $$
DECLARE
    v_trigger RECORD;
    v_result INTEGER;
BEGIN
    SELECT * INTO v_trigger FROM workflow_triggers WHERE trigger_id = p_trigger_id;
    
    IF v_trigger.event_condition IS NULL THEN
        RETURN QUERY SELECT false, 'No condition defined';
        RETURN;
    END IF;
    
    -- Execute the condition query (must return a single integer/boolean)
    BEGIN
        EXECUTE v_trigger.event_condition INTO v_result;
        
        IF v_result >= v_trigger.event_threshold THEN
            RETURN QUERY SELECT true, 'Condition met: ' || v_result || ' >= ' || v_trigger.event_threshold;
        ELSE
            RETURN QUERY SELECT false, 'Condition not met: ' || v_result || ' < ' || v_trigger.event_threshold;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT false, 'Error evaluating condition: ' || SQLERRM;
    END;
END;
$$ LANGUAGE plpgsql;

-- Function: Record trigger execution
CREATE OR REPLACE FUNCTION record_trigger_execution(
    p_trigger_id INTEGER,
    p_workflow_run_id INTEGER DEFAULT NULL,
    p_status VARCHAR DEFAULT 'TRIGGERED',
    p_trigger_reason TEXT DEFAULT NULL,
    p_condition_value TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_execution_id INTEGER;
BEGIN
    INSERT INTO trigger_executions (
        trigger_id,
        workflow_run_id,
        status,
        trigger_reason,
        trigger_condition_value
    ) VALUES (
        p_trigger_id,
        p_workflow_run_id,
        p_status,
        p_trigger_reason,
        p_condition_value
    )
    RETURNING execution_id INTO v_execution_id;
    
    -- Update trigger statistics
    UPDATE workflow_triggers
    SET 
        last_triggered_at = CURRENT_TIMESTAMP,
        total_runs = total_runs + 1,
        successful_runs = CASE WHEN p_status = 'TRIGGERED' THEN successful_runs + 1 ELSE successful_runs END,
        failed_runs = CASE WHEN p_status = 'FAILED' THEN failed_runs + 1 ELSE failed_runs END,
        next_scheduled_run = CASE 
            WHEN trigger_type = 'SCHEDULE' THEN calculate_next_cron_run(schedule_cron)
            ELSE next_scheduled_run
        END
    WHERE trigger_id = p_trigger_id;
    
    RETURN v_execution_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- SEED DATA: Essential Triggers
-- =====================================================================

-- Trigger 1: Daily job fetch at 8 AM
INSERT INTO workflow_triggers (
    workflow_id, 
    trigger_name, 
    trigger_description,
    trigger_type,
    schedule_cron,
    priority,
    max_concurrent_runs,
    enabled
) VALUES (
    (SELECT workflow_id FROM workflows WHERE workflow_name = 'Job Ingestion Pipeline' LIMIT 1),
    'daily_job_fetch',
    'Fetch new jobs from Deutsche Bank API every morning at 8 AM',
    'SCHEDULE',
    '0 8 * * *',
    90,
    1,
    false  -- Will enable once Workflow 2001 exists
) ON CONFLICT (workflow_id, trigger_name) DO NOTHING;

-- Trigger 2: Event-based IHL analysis
INSERT INTO workflow_triggers (
    workflow_id,
    trigger_name,
    trigger_description,
    trigger_type,
    event_condition,
    event_threshold,
    event_check_interval_minutes,
    priority,
    max_concurrent_runs,
    min_interval_minutes,
    enabled
) VALUES (
    1124,  -- Fake Job Detector workflow
    'analyze_new_postings_ihl',
    'Analyze IHL for postings without scores when count >= 5',
    'EVENT',
    'SELECT COUNT(*) FROM postings WHERE ihl_score IS NULL AND LENGTH(COALESCE(job_description, '''')) > 500',
    5,
    15,
    80,
    1,
    30,
    true
) ON CONFLICT (workflow_id, trigger_name) DO NOTHING;

-- Trigger 3: Event-based user matching
INSERT INTO workflow_triggers (
    workflow_id,
    trigger_name,
    trigger_description,
    trigger_type,
    event_condition,
    event_threshold,
    event_check_interval_minutes,
    priority,
    enabled
) VALUES (
    (SELECT workflow_id FROM workflows WHERE workflow_name = 'Candidate Matching' LIMIT 1),
    'match_open_positions',
    'Match users to jobs with IHL <= 60% (genuine external searches)',
    'EVENT',
    'SELECT COUNT(*) FROM postings WHERE ihl_score <= 60 AND ihl_score IS NOT NULL AND posting_status = ''active''',
    1,
    30,
    70,
    false  -- Will enable once matching workflow exists
) ON CONFLICT (workflow_id, trigger_name) DO NOTHING;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON workflow_triggers TO base_admin;
GRANT SELECT, INSERT, UPDATE ON trigger_executions TO base_admin;
GRANT SELECT ON v_triggers_ready_to_run TO base_admin;
GRANT SELECT ON v_trigger_execution_history TO base_admin;
GRANT SELECT ON v_trigger_health TO base_admin;

-- Record migration
SELECT record_migration(
    '042',
    'Workflow Scheduling System',
    'SUCCESS',
    NULL,
    NULL,
    'Time-based and event-based triggers, throttling, dependencies - Turing knows what to do next'
);

COMMIT;

-- Summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Migration 042: Workflow Scheduling System - COMPLETE';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - workflow_triggers table (time & event-based triggers)';
    RAISE NOTICE '  - trigger_executions table (audit trail)';
    RAISE NOTICE '  - workflow_dependencies table (orchestration)';
    RAISE NOTICE '  - Functions: should_trigger_run(), evaluate_event_condition()';
    RAISE NOTICE '  - Views: v_triggers_ready_to_run, v_trigger_health, v_workflow_schedule_24h';
    RAISE NOTICE '';
    RAISE NOTICE 'Seeded Triggers:';
    RAISE NOTICE '  ✅ Daily job fetch (8 AM) - disabled until Workflow 2001 ready';
    RAISE NOTICE '  ✅ IHL analysis (when 5+ postings need scoring) - ENABLED';
    RAISE NOTICE '  ✅ User matching (for open positions) - disabled until matching ready';
    RAISE NOTICE '';
    RAISE NOTICE 'Philosophy: "The system that knows what it needs to do next"';
    RAISE NOTICE '';
    RAISE NOTICE 'Next: Build Workflow 2001, then start turing_scheduler.py daemon';
    RAISE NOTICE '=================================================================';
END $$;
