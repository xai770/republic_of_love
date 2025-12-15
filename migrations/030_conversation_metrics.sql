-- Migration 030: Create conversation_metrics table for latency tracking
-- Date: 2025-12-14
-- Author: Copilot
-- Purpose: Store daily latency percentiles per conversation for adaptive timeouts

-- 1. Create the metrics table
CREATE TABLE IF NOT EXISTS conversation_metrics (
    metric_id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(conversation_id),
    metric_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Sample size
    sample_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    
    -- Latency percentiles (in seconds)
    latency_p50 NUMERIC(10,2),
    latency_p95 NUMERIC(10,2),
    latency_p99 NUMERIC(10,2),
    latency_max NUMERIC(10,2),
    latency_avg NUMERIC(10,2),
    
    -- Suggested timeout (p99 * 1.5, rounded up)
    suggested_timeout INTEGER GENERATED ALWAYS AS (
        CASE WHEN latency_p99 IS NOT NULL 
             THEN CEIL(latency_p99 * 1.5)::INTEGER 
             ELSE NULL 
        END
    ) STORED,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(conversation_id, metric_date)
);

COMMENT ON TABLE conversation_metrics IS 
    'Daily latency metrics per conversation. Used for adaptive timeout tuning.';
COMMENT ON COLUMN conversation_metrics.suggested_timeout IS 
    'Auto-calculated: p99 * 1.5, rounded up. Compare with conversations.timeout_seconds.';

-- 2. Create indexes
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_date ON conversation_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_conversation ON conversation_metrics(conversation_id);

-- 3. Create function to compute daily metrics
CREATE OR REPLACE FUNCTION compute_conversation_metrics(target_date DATE DEFAULT CURRENT_DATE - 1)
RETURNS INTEGER AS $$
DECLARE
    rows_inserted INTEGER;
BEGIN
    -- Insert/update metrics for each conversation with completed interactions
    INSERT INTO conversation_metrics (
        conversation_id,
        metric_date,
        sample_count,
        success_count,
        failure_count,
        latency_p50,
        latency_p95,
        latency_p99,
        latency_max,
        latency_avg
    )
    SELECT 
        i.conversation_id,
        target_date,
        COUNT(*) as sample_count,
        COUNT(*) FILTER (WHERE i.status = 'completed') as success_count,
        COUNT(*) FILTER (WHERE i.status = 'failed') as failure_count,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p50,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p95,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p99,
        MAX(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as max_latency,
        AVG(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as avg_latency
    FROM interactions i
    WHERE i.started_at IS NOT NULL
      AND i.completed_at IS NOT NULL
      AND i.started_at::date = target_date
      AND i.status IN ('completed', 'failed')
    GROUP BY i.conversation_id
    ON CONFLICT (conversation_id, metric_date) 
    DO UPDATE SET
        sample_count = EXCLUDED.sample_count,
        success_count = EXCLUDED.success_count,
        failure_count = EXCLUDED.failure_count,
        latency_p50 = EXCLUDED.latency_p50,
        latency_p95 = EXCLUDED.latency_p95,
        latency_p99 = EXCLUDED.latency_p99,
        latency_max = EXCLUDED.latency_max,
        latency_avg = EXCLUDED.latency_avg;
    
    GET DIAGNOSTICS rows_inserted = ROW_COUNT;
    RETURN rows_inserted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION compute_conversation_metrics IS 
    'Compute daily latency metrics. Run via cron: SELECT compute_conversation_metrics();';

-- 4. Create view for timeout recommendations
CREATE OR REPLACE VIEW v_timeout_recommendations AS
SELECT 
    c.conversation_id,
    c.canonical_name,
    c.timeout_seconds as current_timeout,
    cm.suggested_timeout,
    cm.latency_p99,
    cm.sample_count,
    CASE 
        WHEN cm.suggested_timeout IS NULL THEN 'NO_DATA'
        WHEN c.timeout_seconds < cm.suggested_timeout THEN 'TOO_LOW'
        WHEN c.timeout_seconds > cm.suggested_timeout * 2 THEN 'TOO_HIGH'
        ELSE 'OK'
    END as status
FROM conversations c
LEFT JOIN conversation_metrics cm ON c.conversation_id = cm.conversation_id
    AND cm.metric_date = (SELECT MAX(metric_date) FROM conversation_metrics WHERE conversation_id = c.conversation_id)
WHERE c.enabled = true
ORDER BY 
    CASE 
        WHEN c.timeout_seconds < cm.suggested_timeout THEN 1
        WHEN c.timeout_seconds > cm.suggested_timeout * 2 THEN 2
        ELSE 3
    END,
    c.canonical_name;

COMMENT ON VIEW v_timeout_recommendations IS 
    'Shows conversations where timeout_seconds may need adjustment based on actual latency data.';

-- 5. Backfill last 7 days of metrics
SELECT compute_conversation_metrics(CURRENT_DATE - i) FROM generate_series(1, 7) as i;

-- 6. Show results
SELECT * FROM v_timeout_recommendations WHERE status != 'NO_DATA' LIMIT 20;
