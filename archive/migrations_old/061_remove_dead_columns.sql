-- Migration 061: Remove dead/useless columns from postings table
-- Date: 2025-11-07
-- Reason: Table health analysis showed 10 columns with no useful data
--         These columns are either 100% NULL, always the same value, or <2% filled

BEGIN;

-- Drop columns that are 100% NULL
ALTER TABLE postings
  DROP COLUMN IF EXISTS complexity_score,           -- 100% NULL
  DROP COLUMN IF EXISTS posting_source_id,          -- 100% NULL
  DROP COLUMN IF EXISTS last_checked_at;            -- 100% NULL

-- Drop columns with always the same value
ALTER TABLE postings
  DROP COLUMN IF EXISTS employment_benefits,        -- Always [] (empty array)
  DROP COLUMN IF EXISTS location_remote_options,    -- Always False
  DROP COLUMN IF EXISTS metadata_status,            -- Always "fetched"
  DROP COLUMN IF EXISTS posting_hiring_year,        -- Always "2025"
  DROP COLUMN IF EXISTS status_reason;              -- Always same message

-- Drop columns that are nearly empty (<2% filled)
ALTER TABLE postings
  DROP COLUMN IF EXISTS employment_salary_range,    -- 98.8% empty
  DROP COLUMN IF EXISTS status_checked_at;          -- 98.4% empty

COMMENT ON TABLE postings IS 
'Job postings table - cleaned up 2025-11-07. Removed 10 dead columns. All data preserved in source_metadata JSONB.';

COMMIT;

-- Verification queries (run after migration):
-- 1. Check columns were dropped
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'postings' ORDER BY ordinal_position;

-- 2. Verify we still have the important columns
-- SELECT COUNT(*) FROM postings WHERE source_metadata IS NOT NULL;

-- 3. Check table size reduction
-- SELECT pg_size_pretty(pg_total_relation_size('postings')) as table_size;
