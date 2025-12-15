BEGIN;

-- Circuit Breaker Events Table
-- Tracks all circuit breaker state changes for operational visibility

CREATE TABLE IF NOT EXISTS circuit_breaker_events (
    event_id SERIAL PRIMARY KEY,
    actor_id INTEGER NOT NULL REFERENCES actors(actor_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('failure', 'open', 'half_open', 'closed', 'success')),
    failure_count INTEGER,
    cooldown_seconds INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    context JSONB
);

CREATE INDEX idx_circuit_breaker_actor ON circuit_breaker_events(actor_id, created_at DESC);
CREATE INDEX idx_circuit_breaker_type ON circuit_breaker_events(event_type, created_at DESC);

COMMENT ON TABLE circuit_breaker_events IS 'Historical log of circuit breaker state changes for monitoring';
COMMENT ON COLUMN circuit_breaker_events.event_type IS 'Type of event: failure (actor failed), open (circuit opened), half_open (testing), closed (circuit closed), success (call succeeded)';
COMMENT ON COLUMN circuit_breaker_events.failure_count IS 'Number of failures when circuit opened';
COMMENT ON COLUMN circuit_breaker_events.cooldown_seconds IS 'Cooldown period in seconds (when circuit opens)';

-- View: Current Circuit Breaker Status
CREATE OR REPLACE VIEW v_circuit_breaker_status AS
SELECT 
    a.actor_id,
    a.actor_name,
    a.actor_type,
    CASE 
        WHEN recent.event_type = 'open' THEN 'OPEN'
        WHEN recent.event_type = 'half_open' THEN 'HALF_OPEN'
        ELSE 'CLOSED'
    END as circuit_state,
    recent.failure_count,
    recent.created_at as last_state_change,
    recent.cooldown_seconds,
    GREATEST(0, EXTRACT(EPOCH FROM (recent.created_at + (COALESCE(recent.cooldown_seconds, 0) || ' seconds')::INTERVAL - NOW()))) as cooldown_remaining_sec
FROM actors a
LEFT JOIN LATERAL (
    SELECT event_type, failure_count, cooldown_seconds, created_at
    FROM circuit_breaker_events
    WHERE actor_id = a.actor_id
    ORDER BY created_at DESC
    LIMIT 1
) recent ON true
WHERE a.enabled = TRUE
ORDER BY recent.created_at DESC NULLS LAST;

COMMENT ON VIEW v_circuit_breaker_status IS 'Real-time circuit breaker state for all actors';

-- Log this migration
INSERT INTO migration_log (migration_number, migration_name, status)
VALUES ('019', 'circuit_breaker_state', 'SUCCESS');

COMMIT;
