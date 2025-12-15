-- Migration 039b: Add Missing fetch_run_id Column
-- =================================================
-- Patch for Migration 039 - add fetch_run_id to postings table
-- This column was defined in 039 but apparently not applied

-- Check if migration 039 was recorded but column missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'postings' AND column_name = 'fetch_run_id'
    ) THEN
        -- Add the column
        ALTER TABLE postings 
        ADD COLUMN fetch_run_id INTEGER REFERENCES job_fetch_runs(fetch_run_id);
        
        CREATE INDEX idx_postings_fetch_run ON postings(fetch_run_id);
        
        RAISE NOTICE '✅ Added fetch_run_id column to postings table';
    ELSE
        RAISE NOTICE 'ℹ️  fetch_run_id column already exists';
    END IF;
END $$;

-- Record this patch migration
SELECT record_migration(
    '039b',
    'Add Missing fetch_run_id Column',
    'SUCCESS',
    NULL,
    NULL,
    'Patch for Migration 039 - ensures fetch_run_id exists'
);

COMMIT;

-- Summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Migration 039b: Add Missing fetch_run_id Column - COMPLETE';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Added:';
    RAISE NOTICE '  - postings.fetch_run_id (INTEGER, FK to job_fetch_runs)';
    RAISE NOTICE '  - Index: idx_postings_fetch_run';
    RAISE NOTICE '';
    RAISE NOTICE 'Purpose: Complete Migration 039 integration';
    RAISE NOTICE '=================================================================';
END $$;
