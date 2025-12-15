-- Migration 004: Drop session_actors table
-- Date: 2025-10-30
-- Reason: Unused multi-actor pattern. Simple pattern uses sessions.actor_id + instructions.delegate_actor_id
--
-- The session_actors table was designed for complex multi-actor sessions (primary/helper/validator)
-- but was never implemented. All 564 rows have enabled=False.
--
-- Current pattern (ACTIVE):
--   - sessions.actor_id = primary LLM actor for the session
--   - instructions.delegate_actor_id = optional override to call script actors (taxonomy_gopher, db_update_summary)
--   - This allows LLMs to delegate to custom Python scripts as tools
--
-- Rollback: Restore from schema backup if needed

BEGIN;

-- No views depend on this table, safe to drop
DROP TABLE IF EXISTS session_actors CASCADE;

COMMIT;

-- Verify
\echo '✅ session_actors table dropped'
\echo '✅ delegate_actor_id pattern remains active for script tool execution'
