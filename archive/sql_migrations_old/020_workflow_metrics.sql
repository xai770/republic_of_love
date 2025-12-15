BEGIN;

-- Workflow Metrics Table
-- Tracks performance metrics per conversation execution

CREATE TABLE IF NOT EXISTS workflow_metrics (
    metric_id SERIAL PRIMARY KEY,
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(workflow_run_id),
    conversation_id INTEGER REFERENCES conversations(conversation_id),
    posting_id INTEGER,  -- Denormalized for faster querying
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    metric_unit TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_metrics_run ON workflow_metrics(workflow_run_id);
CREATE INDEX idx_metrics_conversation ON workflow_metrics(conversation_id, created_at DESC);
CREATE INDEX idx_metrics_name ON workflow_metrics(metric_name, created_at DESC);
CREATE INDEX idx_metrics_posting ON workflow_metrics(posting_id, created_at DESC);

COMMENT ON TABLE workflow_metrics IS 'Performance metrics for workflow executions';
COMMENT ON COLUMN workflow_metrics.metric_name IS 'Metric type: latency_ms, tokens_input, tokens_output, cost_usd, throughput';
COMMENT ON COLUMN workflow_metrics.metric_value IS 'Numeric value of metric';
COMMENT ON COLUMN workflow_metrics.metric_unit IS 'Unit of measurement: ms, tokens, usd, postings/sec';

-- View: Workflow Performance Summary
CREATE OR REPLACE VIEW v_workflow_performance AS
SELECT 
    w.workflow_name,
    c.conversation_name,
    a.actor_name,
    DATE_TRUNC('hour', wm.created_at) as metric_hour,
    COUNT(DISTINCT wm.workflow_run_id) as execution_count,
    AVG(wm.metric_value) FILTER (WHERE wm.metric_name = 'latency_ms') as avg_latency_ms,
    SUM(wm.metric_value) FILTER (WHERE wm.metric_name = 'tokens_input') as total_tokens_input,
    SUM(wm.metric_value) FILTER (WHERE wm.metric_name = 'tokens_output') as total_tokens_output,
    SUM(wm.metric_value) FILTER (WHERE wm.metric_name = 'cost_usd') as total_cost_usd,
    COUNT(DISTINCT wm.posting_id) as postings_processed
FROM workflow_metrics wm
JOIN workflow_runs wr ON wr.workflow_run_id = wm.workflow_run_id
JOIN workflows w ON w.workflow_id = wr.workflow_id
LEFT JOIN conversations c ON c.conversation_id = wm.conversation_id
LEFT JOIN actors a ON a.actor_id = c.actor_id
WHERE wm.created_at > NOW() - INTERVAL '24 hours'
GROUP BY w.workflow_name, c.conversation_name, a.actor_name, metric_hour
ORDER BY metric_hour DESC, total_cost_usd DESC NULLS LAST;

COMMENT ON VIEW v_workflow_performance IS '24-hour workflow performance metrics by conversation';

-- View: Current Workflow Costs
CREATE OR REPLACE VIEW v_workflow_costs_today AS
SELECT 
    w.workflow_name,
    COUNT(DISTINCT wr.workflow_run_id) as runs_today,
    SUM(wm.metric_value) FILTER (WHERE wm.metric_name = 'cost_usd') as cost_usd_today,
    SUM(wm.metric_value) FILTER (WHERE wm.metric_name = 'tokens_input') as tokens_in_today,
    SUM(wm.metric_value) FILTER (WHERE wm.metric_name = 'tokens_output') as tokens_out_today,
    COUNT(DISTINCT wm.posting_id) as postings_today
FROM workflows w
LEFT JOIN workflow_runs wr ON wr.workflow_id = w.workflow_id 
    AND wr.started_at >= CURRENT_DATE
LEFT JOIN workflow_metrics wm ON wm.workflow_run_id = wr.workflow_run_id
GROUP BY w.workflow_id, w.workflow_name
ORDER BY cost_usd_today DESC NULLS LAST;

COMMENT ON VIEW v_workflow_costs_today IS 'Daily cost tracking per workflow';

-- Log this migration
INSERT INTO migration_log (migration_number, migration_name, status)
VALUES ('020', 'workflow_metrics', 'SUCCESS');

COMMIT;
