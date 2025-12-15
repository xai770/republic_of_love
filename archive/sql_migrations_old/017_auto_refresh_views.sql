-- Migration 017: Auto-refresh Performance Views with pg_cron
-- ============================================================
-- 
-- Automatically refresh actor_performance_summary materialized view
-- every 5 minutes so dashboard shows current data without manual refresh.
--
-- Uses pg_cron extension for in-database scheduling.
--
-- Author: Arden
-- Date: 2025-11-13

BEGIN;

-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Create function to refresh performance view
CREATE OR REPLACE FUNCTION refresh_performance_views()
RETURNS TABLE(refreshed_at timestamptz, rows_refreshed bigint) AS $$
DECLARE
    row_count bigint;
BEGIN
    -- Refresh actor performance summary
    REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;
    
    -- Get row count
    SELECT COUNT(*) INTO row_count FROM actor_performance_summary;
    
    -- Return status
    RETURN QUERY SELECT NOW() as refreshed_at, row_count as rows_refreshed;
END;
$$ LANGUAGE plpgsql;

-- Schedule refresh every 5 minutes
-- Format: minute hour day month weekday
-- */5 * * * * = every 5 minutes
SELECT cron.schedule(
    'refresh-performance-views',  -- job name
    '*/5 * * * *',                 -- every 5 minutes
    $$SELECT refresh_performance_views()$$
);

-- Initial refresh
SELECT refresh_performance_views();

-- Record migration
INSERT INTO migration_log (migration_number, migration_name, status)
VALUES (
    '017',
    'Auto-refresh performance views with pg_cron',
    'SUCCESS'
);

COMMIT;

-- Verification queries:
-- List all cron jobs:         SELECT * FROM cron.job;
-- View recent job runs:       SELECT * FROM cron.job_run_details WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'refresh-performance-views') ORDER BY start_time DESC LIMIT 5;
-- Manual refresh:             SELECT * FROM refresh_performance_views();
-- Unschedule job (if needed): SELECT cron.unschedule('refresh-performance-views');
