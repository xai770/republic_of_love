-- Migration: 056_protect_interactions_and_add_history_DOWN.sql
-- Description: Rollback interactions protection (CAUTION: restores CASCADE delete!)
-- Date: 2024-12-02

-- WARNING: Rolling back will re-enable CASCADE deletes on interactions
-- This is generally NOT recommended as it can cause data loss

-- Drop the trigger
DROP TRIGGER IF EXISTS archive_interactions_trigger ON interactions;
DROP FUNCTION IF EXISTS archive_interaction_before_delete();

-- Drop history table indexes
DROP INDEX IF EXISTS idx_interactions_history_interaction_id;
DROP INDEX IF EXISTS idx_interactions_history_posting_id;
DROP INDEX IF EXISTS idx_interactions_history_conversation_id;
DROP INDEX IF EXISTS idx_interactions_history_archived_at;
DROP INDEX IF EXISTS idx_interactions_history_workflow_run;

-- Drop history table
DROP TABLE IF EXISTS interactions_history;

-- Restore CASCADE delete (CAUTION!)
ALTER TABLE interactions DROP CONSTRAINT IF EXISTS interactions_posting_id_fkey;
ALTER TABLE interactions
    ADD CONSTRAINT interactions_posting_id_fkey 
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id) ON DELETE CASCADE;
