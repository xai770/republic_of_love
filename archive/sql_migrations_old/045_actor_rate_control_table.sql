-- Migration 045: Actor Rate Control Table
-- ==========================================
--
-- Purpose: Move rate limiting from JSONB execution_config to proper relational table
--          with full audit trail of rate limit checks.
--
-- Motivation: Currently rate limiting data lives in actors.execution_config JSONB:
--             {
--               "rate_limit_hours": 24,
--               "last_run_at": "2025-11-13T08:00:00",
--               "run_count": 142
--             }
--             This makes it hard to:
--             - Query "which actors were rate-limited today?"
--             - Track denied vs accepted access attempts
--             - Analyze rate limit effectiveness
--             - Generate observability metrics
--
-- Schema Changes:
--   - New table: actor_rate_control
--   - Tracks: actor_id, check_time, was_allowed, next_allowed_at, reason
--   - Index on (actor_id, check_time DESC) for fast lookups
--
-- Migration Strategy:
--   - Create table
--   - Populate from actors.execution_config where rate_limit_hours exists
--   - Keep execution_config for backwards compatibility (for now)
--   - Future: Deprecate execution_config rate limit fields
--
-- Author: Arden
-- Date: 2025-11-13

-- Create rate control table
CREATE TABLE actor_rate_control (
    rate_control_id SERIAL PRIMARY KEY,
    actor_id INTEGER NOT NULL REFERENCES actors(actor_id) ON DELETE CASCADE,
    check_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    was_allowed BOOLEAN NOT NULL,
    next_allowed_at TIMESTAMP,
    rate_limit_hours NUMERIC(5,2),
    last_successful_run TIMESTAMP,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast "can this actor run now?" queries
CREATE INDEX idx_actor_rate_control_actor_time 
ON actor_rate_control(actor_id, check_time DESC);

-- Index for observability queries
CREATE INDEX idx_actor_rate_control_denied
ON actor_rate_control(check_time DESC) 
WHERE was_allowed = FALSE;

-- Comments
COMMENT ON TABLE actor_rate_control IS 
'Audit trail of rate limit checks for actors. Tracks both allowed and denied access attempts, enabling observability and rate limit effectiveness analysis.';

COMMENT ON COLUMN actor_rate_control.was_allowed IS 
'TRUE if actor was allowed to run, FALSE if rate-limited (denied).';

COMMENT ON COLUMN actor_rate_control.next_allowed_at IS 
'When the actor will next be allowed to run (NULL if currently allowed).';

COMMENT ON COLUMN actor_rate_control.reason IS 
'Human-readable reason for decision, e.g., "Rate limited: actor ran 2.3h ago, next run in 21.7h"';

-- Populate initial data from actors.execution_config
-- (for actors that have rate_limit_hours set)
INSERT INTO actor_rate_control (
    actor_id,
    check_time,
    was_allowed,
    next_allowed_at,
    rate_limit_hours,
    last_successful_run,
    reason
)
SELECT 
    actor_id,
    COALESCE(
        (execution_config->>'last_run_at')::TIMESTAMP,
        CURRENT_TIMESTAMP - INTERVAL '1 day'
    ) as check_time,
    TRUE as was_allowed,
    NULL as next_allowed_at,
    (execution_config->>'rate_limit_hours')::NUMERIC as rate_limit_hours,
    (execution_config->>'last_run_at')::TIMESTAMP as last_successful_run,
    'Migrated from execution_config' as reason
FROM actors
WHERE execution_config->>'rate_limit_hours' IS NOT NULL
  AND enabled = TRUE;

-- Show actors with rate limiting
SELECT 
    a.actor_id,
    a.actor_name,
    arc.rate_limit_hours,
    arc.last_successful_run,
    arc.next_allowed_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - arc.last_successful_run))/3600 as hours_since_last_run
FROM actors a
JOIN actor_rate_control arc ON a.actor_id = arc.actor_id
WHERE arc.rate_control_id IN (
    SELECT MAX(rate_control_id) 
    FROM actor_rate_control 
    GROUP BY actor_id
)
ORDER BY a.actor_id;
