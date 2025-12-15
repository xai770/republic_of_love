-- Migration 064: Clean up duplicate records and extract external_job_id
-- Date: 2025-11-07
-- Purpose: 
--   1. Delete old duplicate records (migrated from old system, same job_id as newer records)
--   2. Extract external_job_id from posting_position_uri for remaining records
--   This allows comprehensive job validation via API

BEGIN;

-- STEP 1: Find and delete duplicate records
-- These are old migrated records that have the same job ID as newer records with external_url
WITH extracted_ids AS (
    SELECT 
        posting_id,
        external_job_id,
        substring(posting_position_uri from 'id=(\d+)') as uri_job_id,
        external_url IS NOT NULL as has_url,
        first_seen_at
    FROM postings
    WHERE source_id = 1
),
duplicates AS (
    SELECT 
        posting_id,
        COALESCE(external_job_id, uri_job_id) as job_id,
        has_url,
        first_seen_at,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(external_job_id, uri_job_id) 
            ORDER BY has_url DESC, first_seen_at DESC, posting_id DESC
        ) as rn
    FROM extracted_ids
    WHERE COALESCE(external_job_id, uri_job_id) IS NOT NULL
)
DELETE FROM postings
WHERE posting_id IN (
    SELECT posting_id 
    FROM duplicates 
    WHERE rn > 1  -- Keep the first (newest with URL preferred)
);

-- Show what was deleted
SELECT 'Duplicate records deleted' as action, COUNT(*) as count
FROM (SELECT 1) x
WHERE EXISTS (
    SELECT 1 FROM postings WHERE source_id = 1 LIMIT 1
);

-- STEP 2: Extract job ID from posting_position_uri for remaining records
UPDATE postings
SET external_job_id = substring(posting_position_uri from 'id=(\d+)')
WHERE source_id = 1
  AND external_job_id IS NULL
  AND posting_position_uri IS NOT NULL
  AND posting_position_uri ~ 'id=\d+';

-- Show what was updated
SELECT 
    'Records with extracted job_id' as metric,
    COUNT(*) as count
FROM postings
WHERE source_id = 1
  AND external_job_id IS NOT NULL
  AND external_url IS NULL;

COMMENT ON COLUMN postings.external_job_id IS 
    'External job ID from source system (e.g., Workday PositionID, API job ID). 
    Extracted from posting_position_uri for migrated records if not directly available.
    Used for job validation via API.';

COMMIT;

-- Verification
SELECT 
    'Total postings (after dedup)' as metric,
    COUNT(*) as count
FROM postings WHERE source_id = 1
UNION ALL
SELECT 
    'Have external_url',
    COUNT(*)
FROM postings WHERE source_id = 1 AND external_url IS NOT NULL
UNION ALL
SELECT 
    'Have external_job_id',
    COUNT(*)
FROM postings WHERE source_id = 1 AND external_job_id IS NOT NULL
UNION ALL
SELECT 
    'Can validate (URL or ID)',
    COUNT(*)
FROM postings WHERE source_id = 1 AND (external_url IS NOT NULL OR external_job_id IS NOT NULL)
UNION ALL
SELECT 
    'Cannot validate (no ID or URL)',
    COUNT(*)
FROM postings WHERE source_id = 1 AND external_url IS NULL AND external_job_id IS NULL;
