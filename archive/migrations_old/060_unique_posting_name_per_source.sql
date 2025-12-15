-- Migration 060: Make posting_name unique per source
-- Date: 2025-11-07
-- Reason: External job IDs are unreliable - same job posted 407 times with different IDs
--         Use posting_name (job title) as the true unique identifier per source

BEGIN;

-- Step 1: Remove the old constraint that only checked external_job_id
ALTER TABLE postings DROP CONSTRAINT IF EXISTS unique_job_per_source;
ALTER TABLE postings DROP CONSTRAINT IF EXISTS idx_postings_external_unique;

-- Step 2: For existing duplicates, keep the earliest posting and mark others as duplicates
-- First, add a column to track duplicates if it doesn't exist
ALTER TABLE postings ADD COLUMN IF NOT EXISTS duplicate_of_posting_id INTEGER;

COMMENT ON COLUMN postings.duplicate_of_posting_id IS 
'If not NULL, this posting is a duplicate of the referenced posting_id';

-- Step 4: Before applying constraint, we need to handle existing duplicates
-- Option A: Delete duplicates (keep earliest)
-- Option B: Mark duplicates (safe, reversible)

-- Let's mark duplicates first (safer approach)
WITH ranked AS (
    SELECT 
        posting_id,
        source_id,
        posting_name,
        ROW_NUMBER() OVER (
            PARTITION BY source_id, posting_name 
            ORDER BY first_seen_at NULLS LAST, posting_id
        ) as rn
    FROM postings
    WHERE posting_name IS NOT NULL
)
UPDATE postings p
SET duplicate_of_posting_id = (
    SELECT r_master.posting_id 
    FROM ranked r_master
    WHERE r_master.source_id = p.source_id
      AND r_master.posting_name = p.posting_name
      AND r_master.rn = 1
)
FROM ranked r
WHERE p.posting_id = r.posting_id
  AND r.rn > 1;

-- Step 3: Now delete the duplicate records (keep only the earliest)
-- Comment: This will reduce 407 Bankkaufmann postings to 1
DELETE FROM postings
WHERE duplicate_of_posting_id IS NOT NULL;

-- Step 4: Clean up the temporary column
ALTER TABLE postings DROP COLUMN duplicate_of_posting_id;

-- Step 5: Verify no duplicates remain
DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count
    FROM (
        SELECT source_id, posting_name, COUNT(*) as cnt
        FROM postings
        WHERE posting_name IS NOT NULL
        GROUP BY source_id, posting_name
        HAVING COUNT(*) > 1
    ) dupes;
    
    IF duplicate_count > 0 THEN
        RAISE EXCEPTION 'Still have % duplicate posting names!', duplicate_count;
    ELSE
        RAISE NOTICE 'Success! No duplicate posting names remain.';
    END IF;
END $$;

-- Step 6: Add new constraint on (source_id, posting_name)
-- This prevents duplicate job titles from the same source
ALTER TABLE postings 
ADD CONSTRAINT unique_posting_name_per_source 
UNIQUE (source_id, posting_name);

COMMENT ON CONSTRAINT unique_posting_name_per_source ON postings IS 
'Ensures each job title appears only once per source. External job IDs are unreliable.';

COMMIT;

-- Verification queries (run after migration):
-- 1. Check constraint exists
-- SELECT conname, contype FROM pg_constraint WHERE conname = 'unique_posting_name_per_source';

-- 2. Count postings before/after
-- SELECT source_id, COUNT(*) FROM postings GROUP BY source_id;

-- 3. Verify Bankkaufmann job count (should be 1 now, was 407)
-- SELECT COUNT(*) FROM postings WHERE posting_name LIKE '%Bankkaufmann%';
