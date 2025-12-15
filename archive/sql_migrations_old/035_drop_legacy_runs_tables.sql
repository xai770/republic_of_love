-- Migration 035: Drop legacy execution tracking tables
-- Purpose: Remove instruction_runs and dialogue_step_runs (replaced by llm_interactions)
-- Author: Data Architect & User
-- Date: 2025-11-02
-- SAFETY: Backup exists in base_yoga_legacy_20251031

BEGIN;

-- =====================================================================
-- Safety Check: Verify llm_interactions has all the data
-- =====================================================================

DO $$
DECLARE
    instruction_runs_count INTEGER;
    dialogue_step_runs_count INTEGER;
    llm_interactions_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO instruction_runs_count FROM instruction_runs;
    SELECT COUNT(*) INTO dialogue_step_runs_count FROM dialogue_step_runs;
    SELECT COUNT(*) INTO llm_interactions_count FROM llm_interactions;
    
    RAISE NOTICE 'Pre-drop counts:';
    RAISE NOTICE '  instruction_runs: %', instruction_runs_count;
    RAISE NOTICE '  dialogue_step_runs: %', dialogue_step_runs_count;
    RAISE NOTICE '  llm_interactions: %', llm_interactions_count;
    RAISE NOTICE '  Expected: llm_interactions >= instruction_runs + dialogue_step_runs';
    
    IF llm_interactions_count < (instruction_runs_count + dialogue_step_runs_count) THEN
        RAISE EXCEPTION 'Data loss detected! llm_interactions (%) < instruction_runs (%) + dialogue_step_runs (%)',
            llm_interactions_count, instruction_runs_count, dialogue_step_runs_count;
    END IF;
    
    RAISE NOTICE '✅ Safety check passed - llm_interactions has sufficient data';
END $$;

-- =====================================================================
-- Update llm_interactions foreign keys
-- =====================================================================

-- Drop the foreign key to dialogue_step_runs (we're about to drop that table)
ALTER TABLE llm_interactions 
    DROP CONSTRAINT IF EXISTS llm_interactions_dialogue_step_run_id_fkey;

-- The dialogue_step_run_id column can stay as an integer for historical reference
-- but it won't be a foreign key anymore

COMMENT ON COLUMN llm_interactions.dialogue_step_run_id IS 
    'Historical reference to dialogue_step_runs (table dropped in migration 035). 
     For multi-actor dialogues, this ID can be used to correlate with archived dialogue_step_runs data if needed.';

-- =====================================================================
-- Drop legacy tables
-- =====================================================================

-- Drop instruction_runs (replaced by llm_interactions with instruction_id)
DROP TABLE IF EXISTS instruction_runs CASCADE;

-- Drop dialogue_step_runs (replaced by llm_interactions with dialogue_step_run_id reference)
DROP TABLE IF EXISTS dialogue_step_runs CASCADE;

-- =====================================================================
-- Update conversation_runs to remove dependencies
-- =====================================================================

-- The conversation_runs table had triggers and constraints related to instruction_runs
-- Those are automatically removed by CASCADE, but let's verify

DO $$
BEGIN
    -- Check if any triggers remain that reference the dropped tables
    IF EXISTS (
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        WHERE c.relname = 'conversation_runs'
        AND t.tgname LIKE '%instruction%'
    ) THEN
        RAISE NOTICE 'Warning: Found triggers referencing instruction_runs on conversation_runs';
    END IF;
END $$;

-- =====================================================================
-- Create helper views for backward compatibility (optional)
-- =====================================================================

-- View that mimics instruction_runs for any legacy queries
CREATE OR REPLACE VIEW instruction_runs AS
SELECT 
    interaction_id as instruction_run_id,
    conversation_run_id as session_run_id,
    instruction_id,
    execution_order as step_number,
    prompt_sent as prompt_rendered,
    response_received,
    latency_ms,
    error_message as error_details,
    status,
    completed_at as created_at
FROM llm_interactions
WHERE instruction_id IS NOT NULL;

COMMENT ON VIEW instruction_runs IS 
    'LEGACY VIEW - Compatibility layer for old queries. 
     Maps llm_interactions data to old instruction_runs schema.
     DO NOT USE IN NEW CODE - Query llm_interactions directly instead.';

-- View that mimics dialogue_step_runs for any legacy queries
CREATE OR REPLACE VIEW dialogue_step_runs AS
SELECT 
    dialogue_step_run_id,
    conversation_run_id,
    NULL::INTEGER as dialogue_step_id,  -- We don't track this in llm_interactions
    actor_id,
    execution_order,
    prompt_sent as prompt_rendered,
    response_received,
    latency_ms,
    status,
    completed_at
FROM llm_interactions
WHERE dialogue_step_run_id IS NOT NULL;

COMMENT ON VIEW dialogue_step_runs IS 
    'LEGACY VIEW - Compatibility layer for old queries. 
     Maps llm_interactions data to old dialogue_step_runs schema.
     DO NOT USE IN NEW CODE - Query llm_interactions directly instead.
     Note: dialogue_step_id is NULL as it is not tracked in llm_interactions.';

-- =====================================================================
-- Update runner code references
-- =====================================================================

COMMENT ON TABLE llm_interactions IS 
    'PRIMARY SOURCE OF TRUTH for all LLM interactions.
     Replaces legacy instruction_runs and dialogue_step_runs tables (dropped in migration 035).
     Use this table for all new queries and analytics.';

COMMIT;

-- =====================================================================
-- Verification
-- =====================================================================

-- Show what we have now
SELECT 
    'Tables remaining' as category,
    tablename as name,
    'Active' as status
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('workflow_runs', 'conversation_runs', 'llm_interactions', 'interaction_lineage')

UNION ALL

SELECT 
    'Views created' as category,
    viewname as name,
    'Legacy compatibility' as status
FROM pg_views
WHERE schemaname = 'public'
  AND viewname IN ('instruction_runs', 'dialogue_step_runs')

ORDER BY category, name;

-- Show final interaction count
SELECT 
    '✅ Final llm_interactions count' as metric,
    COUNT(*)::TEXT as value
FROM llm_interactions;
