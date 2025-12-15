-- Migration: 004_enhance_actors_table_DOWN.sql
-- Description: Rollback actors table enhancements
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)

-- Drop indexes
DROP INDEX IF EXISTS idx_actors_sync_status;
DROP INDEX IF EXISTS idx_actors_qualified;
DROP INDEX IF EXISTS idx_actors_parent;

-- Drop columns
ALTER TABLE actors DROP COLUMN IF EXISTS auto_promote;
ALTER TABLE actors DROP COLUMN IF EXISTS active_history_id;
ALTER TABLE actors DROP COLUMN IF EXISTS script_sync_status;
ALTER TABLE actors DROP COLUMN IF EXISTS script_synced_at;
ALTER TABLE actors DROP COLUMN IF EXISTS script_file_mtime;
ALTER TABLE actors DROP COLUMN IF EXISTS script_file_path;
ALTER TABLE actors DROP COLUMN IF EXISTS script_code_hash;
ALTER TABLE actors DROP COLUMN IF EXISTS qualified;
ALTER TABLE actors DROP COLUMN IF EXISTS parent_actor_id;
