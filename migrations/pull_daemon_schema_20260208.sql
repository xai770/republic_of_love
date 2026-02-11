-- Migration: pull_daemon_schema_20260208
-- Purpose: Make 'task_types' (a VIEW on 'actors') compatible with core/pull_daemon.py
--          by adding missing columns to 'actors' and rebuilding the view.
--          Also adds tickets.task_type_id and creates task_routes table.
--
-- KEY INSIGHT: task_types is a VIEW on actors, not a table!
--   The actors table already has: execution_type, scale_limit, poll_priority, 
--   script_code_hash, batch_size, timeout_seconds, subject_type
--   But the view only exposes a subset. We need to:
--   1. Add missing columns to actors (requires_model, last_poll_at, lint_*)
--   2. Rebuild the view to expose all columns pull_daemon needs
--   3. Add INSTEAD OF trigger so UPDATE task_types writes through to actors
--
-- Run via MCP pgsql tools or:
--   PGPASSWORD='base_yoga_secure_2025' psql -h localhost -U base_admin -d turing \
--     -f migrations/pull_daemon_schema_20260208.sql

BEGIN;

-- ============================================================================
-- 1. actors: Add columns that don't exist yet (pull_daemon needs these)
-- ============================================================================

-- requires_model: LLM model needed (e.g. 'gemma3:4b', 'qwen2.5:7b')
-- NULL = no model needed. Daemon groups by model to minimize GPU model-switching.
ALTER TABLE actors ADD COLUMN IF NOT EXISTS requires_model TEXT;

-- last_poll_at: When the daemon last checked this task_type for work
ALTER TABLE actors ADD COLUMN IF NOT EXISTS last_poll_at TIMESTAMPTZ;

-- Lint gate columns: prevent unvetted scripts from running in production
ALTER TABLE actors ADD COLUMN IF NOT EXISTS lint_status TEXT;           -- 'passed' / 'failed' / NULL
ALTER TABLE actors ADD COLUMN IF NOT EXISTS lint_checked_at TIMESTAMPTZ;
ALTER TABLE actors ADD COLUMN IF NOT EXISTS lint_errors JSONB;          -- [{description, rule, line}]


-- ============================================================================
-- 2. Rebuild task_types VIEW to expose all columns pull_daemon.py needs
-- ============================================================================
-- pull_daemon._get_pull_task_types() queries:
--   c.task_type_id, c.task_type_name, c.work_query, c.scale_limit,
--   c.batch_size, c.poll_priority, c.requires_model, c.execution_type,
--   c.script_path, c.script_code_hash, c.actor_id, c.enabled
-- pull_daemon._check_lint_gate() queries:
--   lint_status, lint_checked_at, lint_errors FROM task_types
-- pull_daemon._update_last_poll() does:
--   UPDATE task_types SET last_poll_at = NOW()

DROP VIEW IF EXISTS task_types;

CREATE VIEW task_types AS
SELECT
    a.actor_id          AS task_type_id,
    a.actor_id,
    a.actor_name        AS task_type_name,
    a.actor_type        AS task_type_description,
    a.script_file_path  AS script_path,
    a.work_query,
    a.subject_type,
    a.priority,
    a.poll_priority,
    a.scale_limit,
    a.execution_type,
    a.requires_model,
    a.last_poll_at,
    a.lint_status,
    a.lint_checked_at,
    a.lint_errors,
    0.0::double precision AS llm_temperature,
    42                  AS llm_seed,
    a.raq_config,
    a.enabled,
    a.script_code_hash,
    a.batch_size,
    a.timeout_seconds
FROM actors a
WHERE a.actor_type = ANY (ARRAY['thick'::text, 'script'::text]);


-- ============================================================================
-- 3. INSTEAD OF UPDATE trigger: allow pull_daemon to UPDATE through the view
-- ============================================================================
-- pull_daemon does: UPDATE task_types SET last_poll_at = NOW() WHERE task_type_id = %s
-- Also need to support lint_status/lint_errors UPDATEs from turing_lint.py

CREATE OR REPLACE FUNCTION task_types_update_trigger()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE actors SET
        last_poll_at    = COALESCE(NEW.last_poll_at,    OLD.last_poll_at),
        lint_status     = COALESCE(NEW.lint_status,     OLD.lint_status),
        lint_checked_at = COALESCE(NEW.lint_checked_at, OLD.lint_checked_at),
        lint_errors     = COALESCE(NEW.lint_errors,     OLD.lint_errors),
        poll_priority   = COALESCE(NEW.poll_priority,   OLD.poll_priority),
        scale_limit     = COALESCE(NEW.scale_limit,     OLD.scale_limit),
        requires_model  = COALESCE(NEW.requires_model,  OLD.requires_model),
        execution_type  = COALESCE(NEW.execution_type,  OLD.execution_type)
    WHERE actor_id = OLD.actor_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_task_types_update ON task_types;

CREATE TRIGGER trg_task_types_update
    INSTEAD OF UPDATE ON task_types
    FOR EACH ROW
    EXECUTE FUNCTION task_types_update_trigger();


-- ============================================================================
-- 4. tickets: Add task_type_id for tracking which task_type created the ticket
-- ============================================================================

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS task_type_id INTEGER;

-- Index for the daemon's capacity check: 
-- SELECT COUNT(*) FROM tickets WHERE task_type_id = X AND status = 'running'
CREATE INDEX IF NOT EXISTS idx_tickets_task_type_status 
    ON tickets (task_type_id, status) 
    WHERE task_type_id IS NOT NULL;

-- Index for the daemon's work exclusion:
-- WHERE NOT EXISTS (SELECT 1 FROM tickets WHERE task_type_id = X AND subject_id = Y ...)
CREATE INDEX IF NOT EXISTS idx_tickets_task_type_subject 
    ON tickets (task_type_id, subject_id, subject_type, status) 
    WHERE task_type_id IS NOT NULL;


-- ============================================================================
-- 5. task_routes: Branching routes for conversational task_types
-- ============================================================================
-- The pull_daemon checks for existence to determine thick vs conversational.

CREATE TABLE IF NOT EXISTS task_routes (
    route_id SERIAL PRIMARY KEY,
    from_instruction_id INTEGER REFERENCES instructions(instruction_id),
    to_instruction_id INTEGER REFERENCES instructions(instruction_id),
    condition_field TEXT,           -- output field to check
    condition_operator TEXT,        -- 'equals', 'contains', 'regex', 'exists'
    condition_value TEXT,           -- expected value
    priority INTEGER DEFAULT 0,    -- higher = checked first
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_routes_from 
    ON task_routes (from_instruction_id) 
    WHERE enabled = TRUE;


-- ============================================================================
-- 6. Set sensible defaults for existing actors with work_queries
-- ============================================================================

-- Grandfather existing scripts: mark as lint-passed so pull_daemon runs them
UPDATE actors
SET lint_status     = 'passed',
    lint_checked_at = NOW(),
    scale_limit     = COALESCE(scale_limit, 1),
    poll_priority   = COALESCE(NULLIF(poll_priority, 0), 50)
WHERE work_query IS NOT NULL
  AND lint_status IS NULL;

-- Mark non-LLM pipeline actors with higher scale_limit (they're fast, I/O-bound)
UPDATE actors
SET scale_limit = 3
WHERE actor_name IN (
    'domain_gate_detector',
    'Arbeitsagentur Job Fetcher'
)
AND work_query IS NOT NULL;


COMMIT;

-- ============================================================================
-- ROLLBACK (if needed):
-- ============================================================================
-- DROP TRIGGER IF EXISTS trg_task_types_update ON task_types;
-- DROP FUNCTION IF EXISTS task_types_update_trigger();
-- DROP VIEW IF EXISTS task_types;
-- -- Recreate original view:
-- CREATE VIEW task_types AS
-- SELECT actors.actor_id AS task_type_id, actors.actor_id,
--     actors.actor_name AS task_type_name, actors.actor_type AS task_type_description,
--     actors.script_file_path AS script_path, actors.work_query, actors.subject_type,
--     actors.priority, 0.0::double precision AS llm_temperature, 42 AS llm_seed,
--     actors.raq_config, actors.enabled, actors.script_code_hash,
--     actors.batch_size, actors.timeout_seconds
-- FROM actors WHERE actors.actor_type = ANY (ARRAY['thick'::text, 'script'::text]);
-- ALTER TABLE actors DROP COLUMN IF EXISTS requires_model;
-- ALTER TABLE actors DROP COLUMN IF EXISTS last_poll_at;
-- ALTER TABLE actors DROP COLUMN IF EXISTS lint_status;
-- ALTER TABLE actors DROP COLUMN IF EXISTS lint_checked_at;
-- ALTER TABLE actors DROP COLUMN IF EXISTS lint_errors;
-- ALTER TABLE tickets DROP COLUMN IF EXISTS task_type_id;
-- DROP TABLE IF EXISTS task_routes;
-- ALTER TABLE tickets DROP COLUMN IF EXISTS task_type_id;
-- DROP INDEX IF EXISTS idx_tickets_task_type_status;
-- DROP INDEX IF EXISTS idx_tickets_task_type_subject;
-- DROP TABLE IF EXISTS task_routes;
