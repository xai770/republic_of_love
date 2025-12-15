-- Migration 303: Add current_conversation_id to posting_state_projection
-- Date: 2025-11-19
-- Purpose: Fix monitor JOIN mismatch - add current_conversation_id column
--
-- Background:
-- The monitor JOINs posting_state_projection with conversations table using current_step,
-- but current_step stores execution_order (1, 2, 3...) not conversation_id (9144, 3350...).
-- This causes monitor to show incorrect conversation names.
--
-- Solution:
-- Add current_conversation_id column to store actual conversation_id for accurate JOINs.

BEGIN;

-- Add current_conversation_id column
ALTER TABLE posting_state_projection
ADD COLUMN current_conversation_id INT;

-- Add index for performance (monitor queries will JOIN on this)
CREATE INDEX idx_projection_conversation_id ON posting_state_projection(current_conversation_id);

-- Add comment
COMMENT ON COLUMN posting_state_projection.current_conversation_id IS 
'Current conversation_id (e.g., 9144, 3350). Used by monitor for JOIN with conversations table. Distinct from current_step which stores execution_order.';

-- Update existing rows to NULL (will be populated by next workflow run)
-- No backfill needed since we just cleared all projection data

-- Update rebuild_posting_state() function to populate this column
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
    v_current_conversation_id INT := NULL;
    v_current_status TEXT := 'pending';
    v_conversation_history JSONB := '[]'::jsonb;
    v_outputs JSONB := '{}'::jsonb;
    v_total_tokens INT := 0;
    v_total_duration_ms INT := 0;
    v_failure_count INT := 0;
    v_last_event_id BIGINT;
BEGIN
    start_time := clock_timestamp();
    
    -- Replay events in order
    FOR event IN 
        SELECT * FROM execution_events
        WHERE aggregate_type = 'posting'
          AND aggregate_id = p_posting_id::TEXT
        ORDER BY event_id ASC
    LOOP
        event_count := event_count + 1;
        v_last_event_id := event.event_id;
        
        -- Handle different event types
        CASE event.event_type
            WHEN 'conversation_completed' THEN
                -- Extract conversation_id and execution_order
                v_current_step := (event.event_data->>'execution_order')::INT;
                v_current_conversation_id := (event.event_data->>'conversation_id')::INT;
                
                -- Add to conversation history
                v_conversation_history := v_conversation_history || 
                    jsonb_build_object(
                        'conversation_id', event.event_data->>'conversation_id',
                        'timestamp', event.event_timestamp
                    );
                
                -- Store output
                v_outputs := v_outputs || 
                    jsonb_build_object(
                        event.event_data->>'conversation_id',
                        event.event_data->'output'
                    );
                
                -- Update metrics
                v_total_tokens := v_total_tokens + COALESCE((event.event_data->>'tokens')::INT, 0);
                v_total_duration_ms := v_total_duration_ms + COALESCE((event.event_data->>'duration_ms')::INT, 0);
                
            WHEN 'script_execution_completed' THEN
                -- Extract conversation_id and execution_order
                v_current_step := (event.event_data->>'execution_order')::INT;
                v_current_conversation_id := (event.event_data->>'conversation_id')::INT;
                
                -- Add to conversation history
                v_conversation_history := v_conversation_history || 
                    jsonb_build_object(
                        'conversation_id', event.event_data->>'conversation_id',
                        'timestamp', event.event_timestamp
                    );
                
                -- Store output
                v_outputs := v_outputs || 
                    jsonb_build_object(
                        event.event_data->>'conversation_id',
                        event.event_data->'output'
                    );
                
                -- Check if terminal
                IF (event.event_data->>'is_terminal')::BOOLEAN = TRUE THEN
                    v_current_status := 'TERMINAL';
                    v_current_conversation_id := NULL;  -- No next conversation
                END IF;
                
            WHEN 'posting_branched_to' THEN
                -- Update next step
                v_current_step := (event.event_data->>'next_step')::INT;
                v_current_conversation_id := (event.event_data->>'next_step')::INT;
                
            WHEN 'posting_failed' THEN
                v_current_status := 'failed';
                v_failure_count := v_failure_count + 1;
                
            WHEN 'posting_terminal' THEN
                v_current_status := 'TERMINAL';
                v_current_conversation_id := NULL;
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
        last_updated,
        projection_version
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
        NOW(),
        1
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
        last_updated = NOW(),
        projection_version = posting_state_projection.projection_version + 1;
    
    -- Return performance metrics
    RETURN QUERY SELECT 
        EXTRACT(MILLISECONDS FROM (clock_timestamp() - start_time))::INT as rebuild_time_ms,
        event_count as events_replayed;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION rebuild_posting_state IS 
'Rebuild posting state projection by replaying events. Now includes current_conversation_id for accurate monitor JOINs.';

COMMIT;
