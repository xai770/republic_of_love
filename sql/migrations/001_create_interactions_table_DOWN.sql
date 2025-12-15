-- Migration: 001_create_interactions_table_DOWN.sql
-- Description: Rollback interactions table creation
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)

-- Drop trigger first
DROP TRIGGER IF EXISTS interactions_updated_at_trigger ON interactions;
DROP FUNCTION IF EXISTS update_interactions_updated_at();

-- Drop indexes
DROP INDEX IF EXISTS idx_interactions_enabled;
DROP INDEX IF EXISTS idx_interactions_conversation;
DROP INDEX IF EXISTS idx_interactions_parent;
DROP INDEX IF EXISTS idx_interactions_actor;
DROP INDEX IF EXISTS idx_interactions_workflow_run;
DROP INDEX IF EXISTS idx_interactions_status;
DROP INDEX IF EXISTS idx_interactions_posting;

-- Drop table
DROP TABLE IF EXISTS interactions CASCADE;

-- Drop workflow_runs table
DROP INDEX IF EXISTS idx_workflow_runs_posting;
DROP INDEX IF EXISTS idx_workflow_runs_workflow;
DROP TABLE IF EXISTS workflow_runs CASCADE;
