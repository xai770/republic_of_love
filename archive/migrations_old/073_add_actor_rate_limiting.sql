-- Migration 073: Add Rate Limiting Support for Actors
-- =====================================================
-- 
-- Purpose: Add execution_config fields for rate limiting script actors
--          to prevent excessive API calls or resource usage
--
-- Use Cases:
--   - API fetchers that should run max once per day
--   - Expensive operations that need throttling
--   - External service integrations with rate limits
--
-- Schema Changes: None (uses existing execution_config JSONB field)
--
-- Config Fields Added to execution_config:
--   - rate_limit_hours: Minimum hours between executions
--   - last_run_at: ISO timestamp of last successful run
--   - run_count: Total number of successful runs
--
-- Example:
--   {
--     "mode": "stdin_json",
--     "rate_limit_hours": 24,
--     "last_run_at": "2025-11-12T10:30:00",
--     "run_count": 5
--   }

-- Update db_job_fetcher to run max once per 24 hours
UPDATE actors
SET execution_config = jsonb_set(
    execution_config,
    '{rate_limit_hours}',
    '24'
)
WHERE actor_name = 'db_job_fetcher';

-- Document the new config fields
COMMENT ON COLUMN actors.execution_config IS 
'JSONB config for actor execution. Common fields:
- mode: "stdin_json" | "args" | "env_vars"
- output_format: "json" | "text" | "yaml"
- rate_limit_hours: integer (min hours between runs, optional)
- last_run_at: ISO timestamp of last successful run (managed by actor_router)
- run_count: integer (total successful runs, managed by actor_router)
- args: array of command-line arguments (for script actors)
- timeout: integer seconds (default 300)
- retry_on_failure: boolean (default false)
- max_retries: integer (default 0)';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 073 Complete: Actor rate limiting support added';
    RAISE NOTICE '   - db_job_fetcher now limited to once per 24 hours';
    RAISE NOTICE '   - actor_router will check rate_limit_hours before execution';
END $$;
