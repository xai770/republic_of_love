-- Migration: 056_protect_interactions_and_add_history_UP.sql
-- Description: Protect interactions from cascade deletes and add history table
-- Purpose: Interactions are critical audit records and should NEVER be auto-deleted
-- Date: 2024-12-02

-- ============================================================================
-- PART 1: Change interactions FK from CASCADE to SET NULL
-- ============================================================================

-- Drop the existing CASCADE constraint
ALTER TABLE interactions
    DROP CONSTRAINT IF EXISTS interactions_posting_id_fkey;

-- Re-add with SET NULL - if posting is deleted, interaction keeps its record but posting_id becomes NULL
ALTER TABLE interactions
    ADD CONSTRAINT interactions_posting_id_fkey 
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id) ON DELETE SET NULL;

COMMENT ON CONSTRAINT interactions_posting_id_fkey ON interactions IS 
    'SET NULL on delete - interactions are audit records and must survive posting deletion';

-- ============================================================================
-- PART 2: Create interactions_history table
-- ============================================================================

CREATE TABLE IF NOT EXISTS interactions_history (
    history_id BIGSERIAL PRIMARY KEY,
    
    -- Original interaction data (copied from interactions table)
    interaction_id BIGINT NOT NULL,
    posting_id INTEGER,
    conversation_id INTEGER NOT NULL,
    workflow_run_id BIGINT,
    actor_id INTEGER NOT NULL,
    actor_type TEXT NOT NULL,
    status TEXT NOT NULL,
    execution_order INTEGER NOT NULL,
    parent_interaction_id BIGINT,
    trigger_interaction_id BIGINT,
    input_interaction_ids BIGINT[],
    input JSONB,
    output JSONB,
    error_message TEXT,
    retry_count INTEGER,
    max_retries INTEGER,
    enabled BOOLEAN,
    invalidated BOOLEAN,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- History metadata
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_by TEXT DEFAULT current_user,
    archive_reason TEXT
);

-- Indexes for history queries
CREATE INDEX IF NOT EXISTS idx_interactions_history_interaction_id 
    ON interactions_history(interaction_id);
CREATE INDEX IF NOT EXISTS idx_interactions_history_posting_id 
    ON interactions_history(posting_id);
CREATE INDEX IF NOT EXISTS idx_interactions_history_conversation_id 
    ON interactions_history(conversation_id);
CREATE INDEX IF NOT EXISTS idx_interactions_history_archived_at 
    ON interactions_history(archived_at);
CREATE INDEX IF NOT EXISTS idx_interactions_history_workflow_run 
    ON interactions_history(workflow_run_id);

COMMENT ON TABLE interactions_history IS 
    'Archive of deleted interactions - preserves audit trail even when source data is removed';

-- ============================================================================
-- PART 3: Create trigger to auto-archive interactions before delete
-- ============================================================================

CREATE OR REPLACE FUNCTION archive_interaction_before_delete()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO interactions_history (
        interaction_id,
        posting_id,
        conversation_id,
        workflow_run_id,
        actor_id,
        actor_type,
        status,
        execution_order,
        parent_interaction_id,
        trigger_interaction_id,
        input_interaction_ids,
        input,
        output,
        error_message,
        retry_count,
        max_retries,
        enabled,
        invalidated,
        created_at,
        updated_at,
        started_at,
        completed_at,
        archive_reason
    ) VALUES (
        OLD.interaction_id,
        OLD.posting_id,
        OLD.conversation_id,
        OLD.workflow_run_id,
        OLD.actor_id,
        OLD.actor_type,
        OLD.status,
        OLD.execution_order,
        OLD.parent_interaction_id,
        OLD.trigger_interaction_id,
        OLD.input_interaction_ids,
        OLD.input,
        OLD.output,
        OLD.error_message,
        OLD.retry_count,
        OLD.max_retries,
        OLD.enabled,
        OLD.invalidated,
        OLD.created_at,
        OLD.updated_at,
        OLD.started_at,
        OLD.completed_at,
        'deleted'
    );
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
DROP TRIGGER IF EXISTS archive_interactions_trigger ON interactions;
CREATE TRIGGER archive_interactions_trigger
    BEFORE DELETE ON interactions
    FOR EACH ROW
    EXECUTE FUNCTION archive_interaction_before_delete();

COMMENT ON TRIGGER archive_interactions_trigger ON interactions IS 
    'Automatically archives interactions to history table before deletion';

-- ============================================================================
-- PART 4: Verify the changes
-- ============================================================================

DO $$
DECLARE
    delete_rule TEXT;
BEGIN
    SELECT rc.delete_rule INTO delete_rule
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.referential_constraints AS rc ON rc.constraint_name = tc.constraint_name
    WHERE tc.table_name = 'interactions' AND tc.constraint_name = 'interactions_posting_id_fkey';
    
    IF delete_rule = 'SET NULL' THEN
        RAISE NOTICE '✅ interactions_posting_id_fkey is now SET NULL';
    ELSE
        RAISE EXCEPTION '❌ FK rule is % instead of SET NULL', delete_rule;
    END IF;
END $$;

-- Verify trigger exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'archive_interactions_trigger') THEN
        RAISE NOTICE '✅ archive_interactions_trigger created';
    ELSE
        RAISE EXCEPTION '❌ archive_interactions_trigger not found';
    END IF;
END $$;
