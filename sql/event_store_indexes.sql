-- Event Store Performance Indexes
-- Created: November 19, 2025
-- Purpose: Optimize event store queries for production workload
-- Run this in DEV first, then PROD

-- Lookup events by posting (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_execution_events_aggregate 
ON execution_events(aggregate_type, aggregate_id);

-- Filter by conversation (used in debugging and monitoring)
CREATE INDEX IF NOT EXISTS idx_execution_events_conversation 
ON execution_events((metadata->>'conversation_id'));

-- Time-based queries (used in monitoring dashboards)
CREATE INDEX IF NOT EXISTS idx_execution_events_timestamp 
ON execution_events(event_timestamp DESC);

-- Event type filtering (useful for analytics)
CREATE INDEX IF NOT EXISTS idx_execution_events_type 
ON execution_events(event_type);

-- Composite index for common query pattern: posting + time
CREATE INDEX IF NOT EXISTS idx_execution_events_aggregate_time 
ON execution_events(aggregate_id, event_timestamp DESC);

-- Query performance validation
-- Run this to verify indexes are being used:
EXPLAIN ANALYZE 
SELECT * FROM execution_events 
WHERE aggregate_id = '12345' 
ORDER BY event_timestamp;

-- Expected result: Should use idx_execution_events_aggregate_time
-- Execution time should be <10ms for single posting lookup
