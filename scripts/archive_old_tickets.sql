-- Archive tickets older than 1 month
-- 
-- Usage:
--   DRY RUN:  ./tools/turing/turing-q -f scripts/archive_old_tickets.sql
--   EXECUTE:  ./tools/turing/turing-q -v EXECUTE=1 -f scripts/archive_old_tickets.sql
-- 
-- Policy: Tickets older than 1 month move to _archive_tickets_history
-- Rationale: Keep Turing lean; archived data is in the basement if needed
--
-- Note: postings.created_by_task_log_id FK is ON DELETE SET NULL, so safe

-- Show what would be archived
SELECT 
    'DRY RUN - Would archive' as phase,
    COUNT(*) as ticket_count,
    pg_size_pretty(pg_total_relation_size('tickets')) as current_size
FROM tickets
WHERE created_at < NOW() - INTERVAL '1 month'
  AND status IN ('completed', 'failed', 'skipped');

-- Uncomment below to actually run (or use -v EXECUTE=1)
-- BEGIN;

-- Count before
SELECT 'Before archive' as phase, COUNT(*) as tickets_count FROM tickets;

-- Insert into archive (completed/failed only - don't archive pending work)
INSERT INTO _archive_tickets_history (
    task_log_id, posting_id, task_type_id, workflow_run_id,
    actor_id, actor_type, status, execution_order,
    parent_task_log_id, trigger_task_log_id, input_task_log_ids,
    input, output, error_message, retry_count, max_retries,
    enabled, invalidated, created_at, updated_at, started_at, completed_at,
    archive_reason
)
SELECT 
    t.ticket_id, t.posting_id, t.task_type_id, t.workflow_run_id,
    t.actor_id, a.actor_type, t.status, COALESCE(t.execution_order, 0),
    t.parent_ticket_id, t.trigger_ticket_id, t.input_ticket_ids,
    t.input, t.output, t.error_message, t.retry_count, t.max_retries,
    t.enabled, t.invalidated, t.created_at, t.updated_at, t.started_at, t.completed_at,
    'age > 1 month'
FROM tickets t
JOIN actors a ON t.actor_id = a.actor_id
WHERE t.created_at < NOW() - INTERVAL '1 month'
  AND t.status IN ('completed', 'failed', 'skipped');

-- Delete archived tickets
DELETE FROM tickets
WHERE created_at < NOW() - INTERVAL '1 month'
  AND status IN ('completed', 'failed', 'skipped');

-- Count after
SELECT 'After archive' as phase, COUNT(*) as tickets_count FROM tickets;

-- Show archive stats
SELECT 
    'Archived' as phase,
    COUNT(*) as total_archived,
    COUNT(*) FILTER (WHERE archived_at > NOW() - INTERVAL '1 minute') as just_now
FROM _archive_tickets_history;

COMMIT;
