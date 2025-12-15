-- Migration 016: Operational Observability Infrastructure
-- ===========================================================
-- Adds error tracking, performance metrics, and health monitoring
-- All data stays in Turing - no log files to manage
--
-- Author: Arden & xai
-- Date: 2025-11-13

BEGIN;

-- 1. WORKFLOW ERRORS - Track failures with full context
-- ======================================================
CREATE TABLE IF NOT EXISTS workflow_errors (
    error_id SERIAL PRIMARY KEY,
    workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id),
    posting_id INTEGER REFERENCES postings(posting_id),
    conversation_id INTEGER REFERENCES conversations(conversation_id),
    actor_id INTEGER REFERENCES actors(actor_id),
    execution_order INTEGER,
    error_type TEXT NOT NULL, -- 'TIMEOUT', 'FAILED', 'ERROR', 'RATE_LIMITED', 'NO_BRANCH_MATCH'
    error_message TEXT,
    actor_output TEXT, -- The output that caused the error
    stack_trace TEXT,
    context JSONB, -- Additional context (prompt, state, etc.)
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution_notes TEXT
);

CREATE INDEX idx_workflow_errors_workflow_run ON workflow_errors(workflow_run_id);
CREATE INDEX idx_workflow_errors_posting ON workflow_errors(posting_id);
CREATE INDEX idx_workflow_errors_type ON workflow_errors(error_type);
CREATE INDEX idx_workflow_errors_created ON workflow_errors(created_at DESC);

COMMENT ON TABLE workflow_errors IS 
'Tracks all workflow execution errors with full context. Enables debugging without log files.';

-- 2. ACTOR PERFORMANCE - Aggregated metrics view
-- ===============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS actor_performance_summary AS
SELECT 
    a.actor_id,
    a.actor_name,
    a.actor_type,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE li.status = 'SUCCESS') as success_count,
    COUNT(*) FILTER (WHERE li.status != 'SUCCESS') as error_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE li.status = 'SUCCESS') / COUNT(*), 2) as success_rate,
    ROUND(AVG(li.latency_ms)::numeric, 2) as avg_latency_ms,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY li.latency_ms)::numeric, 2) as p50_latency_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY li.latency_ms)::numeric, 2) as p95_latency_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY li.latency_ms)::numeric, 2) as p99_latency_ms,
    MIN(li.started_at) as first_used,
    MAX(li.started_at) as last_used,
    -- Cost tracking (if available)
    COALESCE(SUM(li.cost_usd), 0) as total_cost_usd
FROM actors a
LEFT JOIN llm_interactions li ON a.actor_id = li.actor_id
WHERE li.started_at > NOW() - INTERVAL '30 days'
GROUP BY a.actor_id, a.actor_name, a.actor_type;

CREATE UNIQUE INDEX idx_actor_perf_actor_id ON actor_performance_summary(actor_id);

COMMENT ON MATERIALIZED VIEW actor_performance_summary IS
'Actor performance metrics over last 30 days. Refresh with: REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;';

-- 3. WORKFLOW HEALTH - Real-time status view
-- ===========================================
CREATE OR REPLACE VIEW workflow_health AS
SELECT 
    wr.workflow_run_id,
    wr.workflow_id,
    w.workflow_name,
    wr.status as run_status,
    wr.started_at,
    wr.completed_at,
    EXTRACT(EPOCH FROM (COALESCE(wr.completed_at, NOW()) - wr.started_at)) as duration_seconds,
    
    -- Progress metrics
    COUNT(DISTINCT cr.conversation_run_id) as conversations_executed,
    COUNT(DISTINCT li.interaction_id) as llm_calls_made,
    COUNT(DISTINCT psc.posting_id) as postings_checkpointed,
    
    -- Error metrics
    COUNT(DISTINCT we.error_id) as error_count,
    COUNT(DISTINCT we.posting_id) as postings_with_errors,
    
    -- Latest activity
    MAX(li.started_at) as last_activity_at,
    MAX(psc.created_at) as last_checkpoint_at
    
FROM workflow_runs wr
JOIN workflows w ON wr.workflow_id = w.workflow_id
LEFT JOIN conversation_runs cr ON wr.workflow_run_id = cr.run_id
LEFT JOIN llm_interactions li ON wr.workflow_run_id = li.workflow_run_id
LEFT JOIN posting_state_checkpoints psc ON wr.workflow_run_id = psc.workflow_run_id
LEFT JOIN workflow_errors we ON wr.workflow_run_id = we.workflow_run_id
WHERE wr.started_at > NOW() - INTERVAL '7 days'
GROUP BY wr.workflow_run_id, wr.workflow_id, w.workflow_name, wr.status, wr.started_at, wr.completed_at;

COMMENT ON VIEW workflow_health IS
'Real-time health metrics for workflow runs. Shows progress, errors, and activity.';

-- 4. ERROR SUMMARY - Quick diagnostics view
-- ==========================================
CREATE OR REPLACE VIEW error_summary AS
SELECT 
    DATE_TRUNC('hour', we.created_at) as error_hour,
    we.error_type,
    c.canonical_name as conversation,
    a.actor_name,
    COUNT(*) as error_count,
    COUNT(DISTINCT we.posting_id) as affected_postings,
    COUNT(DISTINCT we.workflow_run_id) as affected_runs,
    ARRAY_AGG(DISTINCT SUBSTRING(we.error_message, 1, 100)) FILTER (WHERE we.error_message IS NOT NULL) as sample_messages
FROM workflow_errors we
LEFT JOIN conversations c ON we.conversation_id = c.conversation_id
LEFT JOIN actors a ON we.actor_id = a.actor_id
WHERE we.created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', we.created_at), we.error_type, c.canonical_name, a.actor_name
ORDER BY error_hour DESC, error_count DESC;

COMMENT ON VIEW error_summary IS
'Hourly error aggregations for last 24h. Shows error patterns and affected components.';

-- 5. CONVERSATION PERFORMANCE - Which conversations are slow/failing?
-- ====================================================================
CREATE OR REPLACE VIEW conversation_performance AS
SELECT 
    c.conversation_id,
    c.canonical_name,
    c.conversation_name,
    a.actor_name,
    
    -- Execution stats (last 7 days)
    COUNT(DISTINCT cr.conversation_run_id) as total_runs,
    COUNT(DISTINCT cr.conversation_run_id) FILTER (WHERE cr.status = 'completed') as completed_runs,
    COUNT(DISTINCT cr.conversation_run_id) FILTER (WHERE cr.status = 'failed') as failed_runs,
    ROUND(100.0 * COUNT(DISTINCT cr.conversation_run_id) FILTER (WHERE cr.status = 'completed') 
          / NULLIF(COUNT(DISTINCT cr.conversation_run_id), 0), 2) as success_rate,
    
    -- Timing stats
    ROUND(AVG(EXTRACT(EPOCH FROM (cr.completed_at - cr.started_at)))::numeric, 2) as avg_duration_seconds,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (cr.completed_at - cr.started_at)))::numeric, 2) as p95_duration_seconds,
    
    -- LLM stats (if applicable)
    ROUND(AVG(li.latency_ms)::numeric, 2) as avg_llm_latency_ms,
    COUNT(li.interaction_id) as total_llm_calls,
    
    -- Error correlation
    COUNT(DISTINCT we.error_id) as error_count,
    ARRAY_AGG(DISTINCT we.error_type) FILTER (WHERE we.error_type IS NOT NULL) as error_types
    
FROM conversations c
LEFT JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN conversation_runs cr ON c.conversation_id = cr.conversation_id AND cr.started_at > NOW() - INTERVAL '7 days'
LEFT JOIN llm_interactions li ON cr.conversation_run_id = li.conversation_run_id
LEFT JOIN workflow_errors we ON c.conversation_id = we.conversation_id AND we.created_at > NOW() - INTERVAL '7 days'
GROUP BY c.conversation_id, c.canonical_name, c.conversation_name, a.actor_name
HAVING COUNT(DISTINCT cr.conversation_run_id) > 0
ORDER BY total_runs DESC;

COMMENT ON VIEW conversation_performance IS
'Performance metrics per conversation over last 7 days. Identifies bottlenecks and failure points.';

-- 6. HELPER FUNCTIONS - Query the data easily
-- ============================================

-- Get recent errors for a workflow run
CREATE OR REPLACE FUNCTION get_workflow_errors(run_id INTEGER, limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    error_id INTEGER,
    posting_id INTEGER,
    conversation_name TEXT,
    actor_name TEXT,
    error_type TEXT,
    error_message TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        we.error_id,
        we.posting_id,
        c.canonical_name,
        a.actor_name,
        we.error_type,
        we.error_message,
        we.created_at
    FROM workflow_errors we
    LEFT JOIN conversations c ON we.conversation_id = c.conversation_id
    LEFT JOIN actors a ON we.actor_id = a.actor_id
    WHERE we.workflow_run_id = run_id
    ORDER BY we.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_workflow_errors IS
'Get recent errors for a workflow run. Usage: SELECT * FROM get_workflow_errors(20920, 20);';

-- Get slowest actors
CREATE OR REPLACE FUNCTION get_slowest_actors(days INTEGER DEFAULT 7, limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    actor_name TEXT,
    actor_type TEXT,
    avg_latency_ms NUMERIC,
    p95_latency_ms NUMERIC,
    total_calls BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.actor_name,
        a.actor_type,
        ROUND(AVG(li.latency_ms)::numeric, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY li.latency_ms)::numeric, 2),
        COUNT(*)
    FROM actors a
    JOIN llm_interactions li ON a.actor_id = li.actor_id
    WHERE li.started_at > NOW() - (days || ' days')::INTERVAL
    GROUP BY a.actor_name, a.actor_type
    ORDER BY AVG(li.latency_ms) DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_slowest_actors IS
'Get slowest actors by average latency. Usage: SELECT * FROM get_slowest_actors(7, 10);';

-- 7. AUTO-REFRESH ACTOR PERFORMANCE (daily at 2am)
-- =================================================
-- This keeps the materialized view up to date automatically
-- Run manually if needed: REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;

CREATE OR REPLACE FUNCTION refresh_actor_performance()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;
    RAISE NOTICE 'Actor performance summary refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;

-- Note: To set up automatic refresh, use pg_cron extension or external scheduler:
-- SELECT cron.schedule('refresh-actor-perf', '0 2 * * *', 'SELECT refresh_actor_performance()');

-- 8. RECORD MIGRATION
-- ===================
INSERT INTO migration_log (migration_number, migration_name, status)
VALUES ('016', 'operational_observability', 'SUCCESS')
ON CONFLICT (migration_number) DO UPDATE
SET migration_name = EXCLUDED.migration_name,
    status = EXCLUDED.status;

COMMIT;

-- ===========================================================
-- USAGE EXAMPLES
-- ===========================================================

-- Check workflow health (last 7 days)
-- SELECT * FROM workflow_health ORDER BY started_at DESC;

-- See recent errors
-- SELECT * FROM error_summary;

-- Find slowest conversations
-- SELECT * FROM conversation_performance ORDER BY avg_duration_seconds DESC LIMIT 10;

-- Check actor performance
-- SELECT * FROM actor_performance_summary ORDER BY total_calls DESC;

-- Get errors for specific workflow run
-- SELECT * FROM get_workflow_errors(20920);

-- Find bottleneck actors
-- SELECT * FROM get_slowest_actors(7, 5);

-- ===========================================================
-- INTEGRATION WITH wave_batch_processor.py
-- ===========================================================
-- Add this to _process_wave() exception handling:
--
-- except Exception as e:
--     cursor = self.db_conn.cursor()
--     cursor.execute("""
--         INSERT INTO workflow_errors (
--             workflow_run_id, posting_id, conversation_id, actor_id,
--             execution_order, error_type, error_message, actor_output,
--             stack_trace, context
--         ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
--     """, (posting.workflow_run_id, posting.posting_id, conversation_id,
--           conv['actor_id'], conv['execution_order'], 'ERROR',
--           str(e), output[:5000], traceback.format_exc(),
--           json.dumps({'prompt': prompt[:1000]})))
--     self.db_conn.commit()
