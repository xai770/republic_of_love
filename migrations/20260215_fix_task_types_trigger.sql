-- Migration: Fix task_types VIEW trigger to handle all columns
-- Date: 2026-02-15
-- Purpose: The INSTEAD OF UPDATE trigger on the task_types view only propagated
--          8 of ~16 updatable columns to the actors table. Updates to priority,
--          enabled, work_query, batch_size, timeout_seconds, raq_config,
--          script_code_hash, and subject_type were SILENTLY IGNORED.
--
-- This caused a debugging trap: UPDATE task_types SET priority = 30 WHERE ...
-- would succeed (no error) but the value in actors would not change.

CREATE OR REPLACE FUNCTION task_types_update_trigger()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE actors SET
        -- Previously handled columns
        last_poll_at    = COALESCE(NEW.last_poll_at,    OLD.last_poll_at),
        lint_status     = COALESCE(NEW.lint_status,     OLD.lint_status),
        lint_checked_at = COALESCE(NEW.lint_checked_at, OLD.lint_checked_at),
        lint_errors     = COALESCE(NEW.lint_errors,     OLD.lint_errors),
        poll_priority   = COALESCE(NEW.poll_priority,   OLD.poll_priority),
        scale_limit     = COALESCE(NEW.scale_limit,     OLD.scale_limit),
        requires_model  = COALESCE(NEW.requires_model,  OLD.requires_model),
        execution_type  = COALESCE(NEW.execution_type,  OLD.execution_type),
        -- Previously MISSING columns (silent-fail trap)
        priority        = COALESCE(NEW.priority,        OLD.priority),
        enabled         = COALESCE(NEW.enabled,         OLD.enabled),
        work_query      = COALESCE(NEW.work_query,      OLD.work_query),
        batch_size      = COALESCE(NEW.batch_size,      OLD.batch_size),
        timeout_seconds = COALESCE(NEW.timeout_seconds, OLD.timeout_seconds),
        raq_config      = COALESCE(NEW.raq_config,      OLD.raq_config),
        script_code_hash = COALESCE(NEW.script_code_hash, OLD.script_code_hash),
        subject_type    = COALESCE(NEW.subject_type,    OLD.subject_type)
    WHERE actor_id = OLD.actor_id;
    RETURN NEW;
END;
$function$;
