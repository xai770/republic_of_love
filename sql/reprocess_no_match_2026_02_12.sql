-- Reprocessing migration: 2026-02-12
-- Context: Commits 685677e (three-tier owl_lookup) and 9b7e6dc (clean_job_title fixes)
--
-- These 15,651 rows were classified as no_match with the old buggy clean_job_title
-- (missing *in stripping, separator variants, salary/date suffixes) and the old
-- owl_lookup (rejected all ambiguous names).
--
-- Resetting berufenet_verified to NULL puts them back in the Phase 1 queue,
-- where the new code will:
--   1. Clean titles properly (10 regex fixes)
--   2. Accept ambiguous OWL names via three-tier logic
--
-- Run AFTER the current turing_fetch batch finishes (check: no berufenet_U.py in ps).
-- Safe to run while turing_fetch.sh is looping — it will pick up the reset rows
-- in the next batch.
--
-- Expected: ~15,651 rows reset

BEGIN;

-- Preview count
SELECT COUNT(*) AS rows_to_reset
FROM postings
WHERE berufenet_id IS NULL
  AND berufenet_verified = 'no_match'
  AND job_title IS NOT NULL;

-- Reset
UPDATE postings
SET berufenet_verified = NULL
WHERE berufenet_id IS NULL
  AND berufenet_verified = 'no_match'
  AND job_title IS NOT NULL;

COMMIT;
