-- Migration 059: Add source_metadata JSONB and UNIQUE constraint
-- Date: 2025-11-07
-- Purpose: Store full API response + prevent duplicate jobs per source

BEGIN;

-- Step 1: Add source_metadata column to store full API response
ALTER TABLE postings
ADD COLUMN source_metadata JSONB;

COMMENT ON COLUMN postings.source_metadata IS 
'Full JSON response from job source API. Preserves all data for future extraction.
Example: {"PositionID": "15930", "ApplyURI": [...], "CareerLevel": [...], ...}';

-- Step 2: Create index on source_metadata for fast JSON queries
CREATE INDEX idx_postings_source_metadata_gin ON postings USING GIN (source_metadata);

COMMENT ON INDEX idx_postings_source_metadata_gin IS
'GIN index for fast JSONB queries on source_metadata';

-- Step 3: Add UNIQUE constraint on (source_id, external_job_id)
-- This prevents the same job from being imported twice from the same source
-- Note: Allows NULL external_job_id (for sources that don't provide one)
ALTER TABLE postings
ADD CONSTRAINT unique_job_per_source 
UNIQUE (source_id, external_job_id);

COMMENT ON CONSTRAINT unique_job_per_source ON postings IS
'Ensures same external_job_id cannot appear twice from same source.
This prevents duplicate imports while allowing different sources to use same IDs.';

-- Step 4: Migrate existing data to source_metadata (if any exists)
-- Store what we currently have in structured form
UPDATE postings
SET source_metadata = jsonb_build_object(
    'external_job_id', external_job_id,
    'external_url', external_url,
    'posting_position_uri', posting_position_uri,
    'migrated_from_columns', true,
    'migration_date', NOW()::text
)
WHERE source_metadata IS NULL;

COMMIT;

-- Verification queries (run these after migration):
/*

-- 1. Check that constraint exists
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'unique_job_per_source';

-- 2. Check source_metadata is populated
SELECT 
    COUNT(*) as total_jobs,
    COUNT(source_metadata) as with_metadata,
    COUNT(*) - COUNT(source_metadata) as without_metadata
FROM postings;

-- 3. Test JSON queries work
SELECT posting_id, source_metadata->>'external_job_id' as job_id
FROM postings
WHERE source_metadata IS NOT NULL
LIMIT 5;

-- 4. Find any duplicate (source_id, external_job_id) before migration
-- (Should be empty if constraint was successfully added)
SELECT source_id, external_job_id, COUNT(*)
FROM postings
WHERE external_job_id IS NOT NULL
GROUP BY source_id, external_job_id
HAVING COUNT(*) > 1;

*/
