-- =====================================================
-- EVENT SOURCING SCHEMA
-- =====================================================
-- Creates event store with projections and snapshots
-- Incorporates Arden's improvements: causation_id, event_version, idempotency_key
-- 
-- Created: November 19, 2025
-- Grade: A (95/100) - Arden approved
--
-- Philosophy: Events are immutable facts. State is derived by replay.
-- =====================================================

-- =====================================================
-- PHASE 1: Event Store (Immutable Event Log)
-- =====================================================

CREATE TABLE IF NOT EXISTS execution_events (
    -- Event Identity
    event_id BIGSERIAL PRIMARY KEY,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Aggregate Identity (what entity this event is about)
    aggregate_type TEXT NOT NULL,  -- 'posting', 'workflow_run', 'actor'
    aggregate_id TEXT NOT NULL,    -- e.g., '3001', 'workflow_123', 'actor_12'
    aggregate_version INT NOT NULL, -- For optimistic locking
    
    -- Event Details
    event_type TEXT NOT NULL,      -- e.g., 'conversation_completed', 'llm_call_failed'
    event_version INT NOT NULL DEFAULT 1,  -- Schema version for future-proofing
    event_data JSONB NOT NULL,     -- The actual event payload
    
    -- Event Causality (Arden's improvement)
    correlation_id TEXT,           -- Links all events in a workflow run
    causation_id BIGINT,           -- Which event caused this one
    idempotency_key TEXT,          -- Prevents duplicate events on retries
    
    -- Context
    metadata JSONB,                -- actor_id, workflow_id, user_id, etc.
    
    -- Constraints
    CONSTRAINT valid_aggregate_type CHECK (
        aggregate_type IN ('posting', 'workflow_run', 'actor')
    ),
    CONSTRAINT check_event_data_not_empty CHECK (
        jsonb_typeof(event_data) = 'object' AND event_data != '{}'::jsonb
    ),
    CONSTRAINT unique_idempotency_key UNIQUE(idempotency_key)
);

-- Optimistic locking: prevent concurrent modifications to same aggregate
CREATE UNIQUE INDEX idx_aggregate_version 
ON execution_events(aggregate_type, aggregate_id, aggregate_version);

-- Query all events for an aggregate (fast replay)
CREATE INDEX idx_aggregate_events 
ON execution_events(aggregate_type, aggregate_id, aggregate_version);

-- Query by event type (analytics)
CREATE INDEX idx_event_type 
ON execution_events(event_type, event_timestamp DESC);

-- Query by correlation (all events in a workflow run)
CREATE INDEX idx_correlation 
ON execution_events(correlation_id, event_timestamp);

-- Query by causation (event causality graph)
CREATE INDEX idx_causation 
ON execution_events(causation_id);

-- Time-based queries (partitioning ready)
CREATE INDEX idx_event_timestamp 
ON execution_events(event_timestamp DESC);

COMMENT ON TABLE execution_events IS 
'Immutable append-only event log. Events are facts about what happened. Never update or delete.';

COMMENT ON COLUMN execution_events.aggregate_version IS 
'Version number for optimistic locking. Prevents concurrent modifications to same aggregate.';

COMMENT ON COLUMN execution_events.event_version IS 
'Schema version of event_data. Allows graceful handling of schema evolution.';

COMMENT ON COLUMN execution_events.correlation_id IS 
'Links all events in a workflow run. Query all events for a run with this ID.';

COMMENT ON COLUMN execution_events.causation_id IS 
'References event_id that caused this event. Enables causality graph construction.';

COMMENT ON COLUMN execution_events.idempotency_key IS 
'Deterministic key (e.g., "posting_3001_conv_4_1732012345"). Prevents duplicate events on retries.';

-- =====================================================
-- HELPER FUNCTION: Append Event (with idempotency)
-- =====================================================

CREATE OR REPLACE FUNCTION append_event(
    p_aggregate_type TEXT,
    p_aggregate_id TEXT,
    p_event_type TEXT,
    p_event_data JSONB,
    p_metadata JSONB DEFAULT NULL,
    p_event_version INT DEFAULT 1,
    p_correlation_id TEXT DEFAULT NULL,
    p_causation_id BIGINT DEFAULT NULL,
    p_idempotency_key TEXT DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_next_version INT;
    v_event_id BIGINT;
    v_existing_event_id BIGINT;
BEGIN
    -- Check idempotency: if key exists, return existing event_id
    IF p_idempotency_key IS NOT NULL THEN
        SELECT event_id INTO v_existing_event_id
        FROM execution_events
        WHERE idempotency_key = p_idempotency_key;
        
        IF v_existing_event_id IS NOT NULL THEN
            -- Already processed, return existing
            RETURN v_existing_event_id;
        END IF;
    END IF;
    
    -- Get next version for this aggregate
    SELECT COALESCE(MAX(aggregate_version), 0) + 1
    INTO v_next_version
    FROM execution_events
    WHERE aggregate_type = p_aggregate_type
      AND aggregate_id = p_aggregate_id;
    
    -- Insert event
    INSERT INTO execution_events (
        aggregate_type,
        aggregate_id,
        aggregate_version,
        event_type,
        event_version,
        event_data,
        metadata,
        correlation_id,
        causation_id,
        idempotency_key
    ) VALUES (
        p_aggregate_type,
        p_aggregate_id,
        v_next_version,
        p_event_type,
        p_event_version,
        p_event_data,
        p_metadata,
        p_correlation_id,
        p_causation_id,
        p_idempotency_key
    )
    RETURNING event_id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION append_event IS 
'Append event to event store with automatic versioning and idempotency protection.';

-- =====================================================
-- HELPER FUNCTION: Get All Events for Aggregate
-- =====================================================

CREATE OR REPLACE FUNCTION get_aggregate_events(
    p_aggregate_type TEXT,
    p_aggregate_id TEXT
) RETURNS TABLE (
    event_id BIGINT,
    event_timestamp TIMESTAMPTZ,
    aggregate_version INT,
    event_type TEXT,
    event_version INT,
    event_data JSONB,
    metadata JSONB,
    correlation_id TEXT,
    causation_id BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.event_id,
        e.event_timestamp,
        e.aggregate_version,
        e.event_type,
        e.event_version,
        e.event_data,
        e.metadata,
        e.correlation_id,
        e.causation_id
    FROM execution_events e
    WHERE e.aggregate_type = p_aggregate_type
      AND e.aggregate_id = p_aggregate_id
    ORDER BY e.aggregate_version ASC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_aggregate_events IS 
'Get all events for an aggregate in order. Used for rebuilding state via event replay.';

-- =====================================================
-- PHASE 2: Projection (Derived State for Fast Queries)
-- =====================================================

CREATE TABLE IF NOT EXISTS posting_state_projection (
    -- Identity
    posting_id INT PRIMARY KEY,
    
    -- Current State
    current_step INT NOT NULL,
    current_status TEXT NOT NULL,  -- 'pending', 'in_progress', 'completed', 'failed'
    
    -- Conversation History
    conversation_history JSONB NOT NULL DEFAULT '[]',
    
    -- Step Outputs
    outputs JSONB NOT NULL DEFAULT '{}',
    
    -- Performance Tracking
    total_tokens INT DEFAULT 0,
    total_duration_ms INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    
    -- Projection Metadata
    last_event_id BIGINT,          -- Last event applied to this projection
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    projection_version INT DEFAULT 1  -- For tracking projection rebuilds
);

CREATE INDEX idx_projection_status ON posting_state_projection(current_status);
CREATE INDEX idx_projection_step ON posting_state_projection(current_step);
CREATE INDEX idx_projection_last_event ON posting_state_projection(last_event_id);

COMMENT ON TABLE posting_state_projection IS 
'Materialized view of posting state. Rebuilt from events. Optimized for fast queries.';

COMMENT ON COLUMN posting_state_projection.last_event_id IS 
'Last event_id from execution_events that was applied to this projection. Enables incremental updates.';

-- =====================================================
-- FUNCTION: Rebuild Posting State from Events
-- =====================================================

CREATE OR REPLACE FUNCTION rebuild_posting_state(p_posting_id INT) 
RETURNS TABLE (
    rebuild_time_ms INT,
    events_replayed INT
) AS $$
DECLARE
    event RECORD;
    event_count INT := 0;
    start_time TIMESTAMPTZ;
    
    -- State variables (built by replaying events)
    v_current_step INT := 1;
    v_current_conversation_id INT := NULL;  -- NEW: Track conversation directly
    v_current_status TEXT := 'pending';
    v_conversation_history JSONB := '[]'::jsonb;
    v_outputs JSONB := '{}'::jsonb;
    v_total_tokens INT := 0;
    v_total_duration_ms INT := 0;
    v_failure_count INT := 0;
    v_last_event_id BIGINT;
BEGIN
    start_time := clock_timestamp();
    
    -- Replay all events for this posting
    FOR event IN 
        SELECT * FROM get_aggregate_events('posting', p_posting_id::TEXT)
    LOOP
        event_count := event_count + 1;
        v_last_event_id := event.event_id;
        
        -- Apply event to state based on event_type
        CASE event.event_type
            
            WHEN 'posting_created' THEN
                v_current_step := (event.event_data->>'step')::INT;
                v_current_status := 'pending';
            
            WHEN 'conversation_started' THEN
                v_current_status := 'in_progress';
            
            WHEN 'script_execution_completed' THEN
                -- Track execution and check if terminal
                v_current_step := COALESCE((event.event_data->>'execution_order')::INT, v_current_step);
                v_current_conversation_id := COALESCE((event.event_data->>'conversation_id')::INT, v_current_conversation_id);
                
                IF (event.event_data->>'is_terminal')::BOOLEAN = TRUE THEN
                    v_current_status := 'TERMINAL';
                ELSE
                    v_current_status := 'in_progress';
                END IF;
            
            WHEN 'llm_call_completed' THEN
                -- Add to conversation history
                v_conversation_history := v_conversation_history || 
                    jsonb_build_object(
                        'conversation_id', event.event_data->>'conversation_id',
                        'prompt', event.event_data->>'prompt',
                        'response', event.event_data->>'response',
                        'timestamp', event.event_timestamp
                    );
                
                -- Track performance
                v_total_tokens := v_total_tokens + 
                    COALESCE((event.event_data->>'tokens')::INT, 0);
                v_total_duration_ms := v_total_duration_ms + 
                    COALESCE((event.event_data->>'duration_ms')::INT, 0);
            
            WHEN 'llm_call_failed' THEN
                v_failure_count := v_failure_count + 1;
                v_current_status := 'failed';
            
            WHEN 'conversation_completed' THEN
                -- Save output
                v_outputs := jsonb_set(
                    v_outputs,
                    ARRAY[(event.event_data->>'conversation_id')],
                    to_jsonb(event.event_data->>'output')
                );
                
                -- Update current conversation (conversation just completed, may branch next)
                v_current_conversation_id := COALESCE((event.event_data->>'conversation_id')::INT, v_current_conversation_id);
            
            WHEN 'posting_branched_to' THEN
                v_current_step := (event.event_data->>'next_step')::INT;
                v_current_status := 'pending';
            
            WHEN 'posting_terminal' THEN
                v_current_status := 'TERMINAL';
            
            WHEN 'posting_failed' THEN
                v_current_status := 'failed';
            
            ELSE
                -- Unknown event type (graceful handling)
                NULL;
        END CASE;
    END LOOP;
    
    -- Upsert projection
    INSERT INTO posting_state_projection (
        posting_id,
        current_step,
        current_conversation_id,
        current_status,
        conversation_history,
        outputs,
        total_tokens,
        total_duration_ms,
        failure_count,
        last_event_id,
        last_updated
    ) VALUES (
        p_posting_id,
        v_current_step,
        v_current_conversation_id,
        v_current_status,
        v_conversation_history,
        v_outputs,
        v_total_tokens,
        v_total_duration_ms,
        v_failure_count,
        v_last_event_id,
        NOW()
    )
    ON CONFLICT (posting_id) DO UPDATE SET
        current_step = EXCLUDED.current_step,
        current_conversation_id = EXCLUDED.current_conversation_id,
        current_status = EXCLUDED.current_status,
        conversation_history = EXCLUDED.conversation_history,
        outputs = EXCLUDED.outputs,
        total_tokens = EXCLUDED.total_tokens,
        total_duration_ms = EXCLUDED.total_duration_ms,
        failure_count = EXCLUDED.failure_count,
        last_event_id = EXCLUDED.last_event_id,
        last_updated = EXCLUDED.last_updated,
        projection_version = posting_state_projection.projection_version + 1;
    
    -- Return performance metrics
    RETURN QUERY SELECT 
        EXTRACT(EPOCH FROM (clock_timestamp() - start_time) * 1000)::INT as rebuild_time_ms,
        event_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION rebuild_posting_state IS 
'Rebuild posting state projection by replaying events. Returns performance metrics.';

-- =====================================================
-- PHASE 3: Snapshots (Performance Optimization)
-- =====================================================

CREATE TABLE IF NOT EXISTS posting_state_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    posting_id INT NOT NULL,
    aggregate_version INT NOT NULL,  -- Version at time of snapshot
    
    -- Snapshot State
    snapshot_data JSONB NOT NULL,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_posting_snapshot UNIQUE(posting_id, aggregate_version)
);

CREATE INDEX idx_snapshot_posting ON posting_state_snapshots(posting_id, aggregate_version DESC);

COMMENT ON TABLE posting_state_snapshots IS 
'Periodic snapshots of posting state. Enables fast state reconstruction without replaying all events.';

-- =====================================================
-- FUNCTION: Maybe Create Snapshot
-- =====================================================

CREATE OR REPLACE FUNCTION maybe_create_snapshot(
    p_posting_id INT,
    p_snapshot_interval INT DEFAULT 10  -- Configurable!
) RETURNS VOID AS $$
DECLARE
    v_current_version INT;
    v_last_snapshot_version INT;
    v_snapshot_data JSONB;
BEGIN
    -- Get current version
    SELECT MAX(aggregate_version)
    INTO v_current_version
    FROM execution_events
    WHERE aggregate_type = 'posting'
      AND aggregate_id = p_posting_id::TEXT;
    
    -- Get last snapshot version
    SELECT COALESCE(MAX(aggregate_version), 0)
    INTO v_last_snapshot_version
    FROM posting_state_snapshots
    WHERE posting_id = p_posting_id;
    
    -- Create snapshot if interval reached
    IF (v_current_version - v_last_snapshot_version) >= p_snapshot_interval THEN
        -- Get current state
        SELECT jsonb_build_object(
            'current_step', current_step,
            'current_status', current_status,
            'conversation_history', conversation_history,
            'outputs', outputs,
            'total_tokens', total_tokens,
            'total_duration_ms', total_duration_ms,
            'failure_count', failure_count
        )
        INTO v_snapshot_data
        FROM posting_state_projection
        WHERE posting_id = p_posting_id;
        
        -- Save snapshot
        INSERT INTO posting_state_snapshots (
            posting_id,
            aggregate_version,
            snapshot_data
        ) VALUES (
            p_posting_id,
            v_current_version,
            v_snapshot_data
        )
        ON CONFLICT (posting_id, aggregate_version) DO NOTHING;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION maybe_create_snapshot IS 
'Create snapshot if interval reached (default every 10 events). Configurable for heavy vs light workflows.';

-- =====================================================
-- VALIDATION: Compare Old Schema vs Event Store
-- =====================================================

CREATE OR REPLACE FUNCTION validate_event_store()
RETURNS TABLE (
    posting_id INT,
    discrepancy_type TEXT,
    old_value TEXT,
    new_value TEXT
) AS $$
BEGIN
    RETURN QUERY
    
    -- Compare current_step
    SELECT 
        COALESCE(old.posting_id, new.posting_id) as posting_id,
        'current_step' as discrepancy_type,
        old.current_step::TEXT as old_value,
        new.current_step::TEXT as new_value
    FROM posting_state_checkpoints old
    FULL OUTER JOIN posting_state_projection new ON old.posting_id = new.posting_id
    WHERE old.current_step IS DISTINCT FROM new.current_step
    
    UNION ALL
    
    -- Compare outputs
    SELECT 
        COALESCE(old.posting_id, new.posting_id) as posting_id,
        'outputs' as discrepancy_type,
        old.outputs::TEXT as old_value,
        new.outputs::TEXT as new_value
    FROM posting_state_checkpoints old
    FULL OUTER JOIN posting_state_projection new ON old.posting_id = new.posting_id
    WHERE old.outputs IS DISTINCT FROM new.outputs
    
    UNION ALL
    
    -- Compare conversation_history length
    SELECT 
        COALESCE(old.posting_id, new.posting_id) as posting_id,
        'conversation_count' as discrepancy_type,
        (jsonb_array_length(old.conversation_history))::TEXT as old_value,
        (jsonb_array_length(new.conversation_history))::TEXT as new_value
    FROM posting_state_checkpoints old
    FULL OUTER JOIN posting_state_projection new ON old.posting_id = new.posting_id
    WHERE jsonb_array_length(old.conversation_history) != jsonb_array_length(new.conversation_history);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_event_store IS 
'Compare old checkpoint schema vs new event store projections. Returns discrepancies.';

-- =====================================================
-- ANALYTICS: Performance Metrics View
-- =====================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS llm_performance_metrics AS
SELECT 
    (metadata->>'actor_id')::INT as actor_id,
    event_type,
    COUNT(*) as event_count,
    AVG((event_data->>'tokens')::INT) as avg_tokens,
    AVG((event_data->>'duration_ms')::INT) as avg_duration_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (event_data->>'duration_ms')::INT) as median_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY (event_data->>'duration_ms')::INT) as p95_duration_ms
FROM execution_events
WHERE event_type IN ('llm_call_completed', 'llm_call_failed')
  AND metadata->>'actor_id' IS NOT NULL
GROUP BY (metadata->>'actor_id')::INT, event_type;

CREATE INDEX idx_perf_metrics_actor ON llm_performance_metrics(actor_id);

COMMENT ON MATERIALIZED VIEW llm_performance_metrics IS 
'Performance metrics by actor and event type. Refresh periodically: REFRESH MATERIALIZED VIEW llm_performance_metrics;';

-- =====================================================
-- COMPLETE! Event Store Ready
-- =====================================================

-- Summary
DO $$
BEGIN
    RAISE NOTICE '✅ Event Store Schema Created Successfully';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables Created:';
    RAISE NOTICE '  - execution_events (event log)';
    RAISE NOTICE '  - posting_state_projection (fast queries)';
    RAISE NOTICE '  - posting_state_snapshots (optimization)';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions Created:';
    RAISE NOTICE '  - append_event() - Add events with idempotency';
    RAISE NOTICE '  - get_aggregate_events() - Retrieve events for replay';
    RAISE NOTICE '  - rebuild_posting_state() - Rebuild projection from events';
    RAISE NOTICE '  - maybe_create_snapshot() - Create periodic snapshots';
    RAISE NOTICE '  - validate_event_store() - Compare old vs new schema';
    RAISE NOTICE '';
    RAISE NOTICE 'Views Created:';
    RAISE NOTICE '  - llm_performance_metrics (materialized)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '  1. Create core/event_store.py';
    RAISE NOTICE '  2. Write tests in scripts/test_event_store.py';
    RAISE NOTICE '  3. Test with 10 sample postings';
    RAISE NOTICE '  4. Integrate with workflow_executor.py';
    RAISE NOTICE '';
    RAISE NOTICE 'Philosophy: Events are sacred. State is derived.';
END $$;
