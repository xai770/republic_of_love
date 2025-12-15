-- Migration 058: Cleanup postings table - remove redundant columns
-- Date: 2025-12-02
-- Purpose: Remove columns that are never used or can be derived from interactions

BEGIN;

-- Drop columns that are never used (all have 0 values)
ALTER TABLE postings DROP COLUMN IF EXISTS ihl_category;
ALTER TABLE postings DROP COLUMN IF EXISTS raw_data;
ALTER TABLE postings DROP COLUMN IF EXISTS summary_llm_interaction_id;
ALTER TABLE postings DROP COLUMN IF EXISTS created_by_staging_id;

-- Drop columns that can be derived from interactions
ALTER TABLE postings DROP COLUMN IF EXISTS ihl_analyzed_at;
ALTER TABLE postings DROP COLUMN IF EXISTS ihl_workflow_run_id;
ALTER TABLE postings DROP COLUMN IF EXISTS fetched_at;

-- Drop posting_position_uri (redundant - external_url has full URL)
ALTER TABLE postings DROP COLUMN IF EXISTS posting_position_uri;

-- Rename source_id to posting_source_id for clarity
-- First check if column exists and hasn't been renamed yet
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'postings' AND column_name = 'source_id') THEN
        ALTER TABLE postings RENAME COLUMN source_id TO posting_source_id;
    END IF;
END $$;

COMMIT;
