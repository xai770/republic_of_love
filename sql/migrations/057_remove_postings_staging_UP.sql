-- Migration: 057_remove_postings_staging_UP.sql
-- Description: Remove postings_staging table - fetcher writes directly to postings
-- Date: 2024-12-02
-- 
-- RATIONALE:
-- postings_staging was a middle-man that added complexity without clear value.
-- The fetcher now writes directly to postings with posting_status='pending'.
-- Validation just changes status to 'active'.
-- We still have full audit trail via interactions table.

-- ============================================================================
-- PART 1: Backup staging data (just in case)
-- ============================================================================

CREATE TABLE IF NOT EXISTS postings_staging_backup AS 
SELECT * FROM postings_staging;

-- ============================================================================
-- PART 2: Drop foreign key constraints referencing postings_staging
-- ============================================================================

-- Check for any FKs pointing to staging
DO $$
DECLARE
    fk_record RECORD;
BEGIN
    FOR fk_record IN 
        SELECT tc.constraint_name, tc.table_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND ccu.table_name = 'postings_staging'
    LOOP
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', 
                      fk_record.table_name, fk_record.constraint_name);
        RAISE NOTICE 'Dropped FK: % on %', fk_record.constraint_name, fk_record.table_name;
    END LOOP;
END $$;

-- ============================================================================
-- PART 3: Drop the staging table
-- ============================================================================

DROP TABLE IF EXISTS postings_staging CASCADE;

-- ============================================================================
-- PART 4: Update postings table - ensure we have needed columns
-- ============================================================================

-- Add source column if not exists (to track 'deutsche_bank' etc)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'postings' AND column_name = 'source') THEN
        ALTER TABLE postings ADD COLUMN source VARCHAR(100);
    END IF;
END $$;

-- Ensure posting_status has correct values
-- pending = just fetched, needs validation
-- active = validated, being processed  
-- complete = has summary + skills + IHL
-- filled = job no longer available
ALTER TABLE postings DROP CONSTRAINT IF EXISTS postings_status_check;
ALTER TABLE postings ADD CONSTRAINT postings_status_check 
    CHECK (posting_status IN ('pending', 'active', 'complete', 'filled', 'invalid'));

-- ============================================================================
-- PART 5: Verify
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'postings_staging') THEN
        RAISE NOTICE '✅ postings_staging table dropped successfully';
    ELSE
        RAISE EXCEPTION '❌ postings_staging table still exists';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'postings_staging_backup') THEN
        RAISE NOTICE '✅ Backup created: postings_staging_backup';
    END IF;
END $$;
