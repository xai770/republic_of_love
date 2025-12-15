-- Migration: 005_create_actor_code_history_DOWN.sql
-- Description: Rollback actor_code_history table creation
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)

-- Drop foreign key from actors table
ALTER TABLE actors DROP CONSTRAINT IF EXISTS actors_active_history_id_fkey;

-- Drop indexes
DROP INDEX IF EXISTS idx_actor_code_history_hash;
DROP INDEX IF EXISTS idx_actor_code_history_active;
DROP INDEX IF EXISTS idx_actor_code_history_actor;

-- Drop table
DROP TABLE IF EXISTS actor_code_history CASCADE;
