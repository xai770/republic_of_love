-- Migration: Add beruf column to postings
-- Date: 2026-02-03
-- Author: Arden
-- Rationale: AA API provides official occupation category. Needed for dashboard filtering.
--            Currently in JSONB, but dashboard queries need column for speed + indexing.

-- Step 1: Add column
ALTER TABLE postings ADD COLUMN IF NOT EXISTS beruf TEXT;

-- Step 2: Add index for filtering
CREATE INDEX IF NOT EXISTS idx_postings_beruf ON postings(beruf) WHERE beruf IS NOT NULL;

-- Step 3: Backfill from existing JSONB data
UPDATE postings
SET beruf = source_metadata->'raw_api_response'->>'beruf'
WHERE source = 'arbeitsagentur'
  AND source_metadata->'raw_api_response'->>'beruf' IS NOT NULL
  AND beruf IS NULL;

-- Step 4: Add comment for documentation
COMMENT ON COLUMN postings.beruf IS 'Official AA occupation category (e.g., Arzt/Ärztin). From API beruf field. Added 2026-02-03.';

-- Verification query (run after migration):
-- SELECT beruf, COUNT(*) FROM postings WHERE beruf IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 20;
