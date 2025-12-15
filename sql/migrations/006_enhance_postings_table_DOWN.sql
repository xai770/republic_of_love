-- Migration: 006_enhance_postings_table_DOWN.sql
-- Description: Rollback postings table enhancements
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)

-- Drop indexes
DROP INDEX IF EXISTS idx_postings_invalidated;
DROP INDEX IF EXISTS idx_postings_staging;
DROP INDEX IF EXISTS idx_postings_created_by_interaction;

-- Drop columns
ALTER TABLE postings DROP COLUMN IF EXISTS invalidated_at;
ALTER TABLE postings DROP COLUMN IF EXISTS invalidated_reason;
ALTER TABLE postings DROP COLUMN IF EXISTS invalidated;
ALTER TABLE postings DROP COLUMN IF EXISTS created_by_staging_id;
ALTER TABLE postings DROP COLUMN IF EXISTS updated_by_interaction_id;
ALTER TABLE postings DROP COLUMN IF EXISTS created_by_interaction_id;
