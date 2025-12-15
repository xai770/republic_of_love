-- Migration: 002_create_audit_table_DOWN.sql
-- Description: Rollback interaction_events table creation
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)

-- Drop trigger and function
DROP TRIGGER IF EXISTS event_hash_trigger ON interaction_events;
DROP FUNCTION IF EXISTS compute_event_hash();

-- Drop indexes
DROP INDEX IF EXISTS idx_interaction_events_causation;
DROP INDEX IF EXISTS idx_interaction_events_type;
DROP INDEX IF EXISTS idx_interaction_events_correlation;
DROP INDEX IF EXISTS idx_interaction_events_interaction;

-- Drop table
DROP TABLE IF EXISTS interaction_events CASCADE;
