-- Migration 012: Standardize postings table
-- Date: 2025-10-30
-- Purpose: Convert job_id from TEXT to INTEGER PK, add posting_name
-- Impact: 76 rows, 3 FKs (job_skills, production_runs.posting_id, profile_job_matches)
-- Risk: HIGH - Core table for job postings

BEGIN;

-- ============================================================================
-- STEP 1: Add new integer column to postings
-- ============================================================================

ALTER TABLE postings 
  ADD COLUMN posting_id INTEGER;

CREATE SEQUENCE postings_posting_id_seq;

UPDATE postings 
SET posting_id = nextval('postings_posting_id_seq');

ALTER TABLE postings 
  ALTER COLUMN posting_id SET DEFAULT nextval('postings_posting_id_seq');

-- ============================================================================
-- STEP 2: Update job_skills FK
-- ============================================================================

ALTER TABLE job_skills
  ADD COLUMN posting_id INTEGER;

UPDATE job_skills js
SET posting_id = (
  SELECT p.posting_id
  FROM postings p
  WHERE p.job_id = js.job_id
);

-- ============================================================================
-- STEP 3: Update production_runs.posting_id FK
-- ============================================================================

-- Note: production_runs.posting_id references postings.job_id
ALTER TABLE production_runs
  ADD COLUMN posting_id_new INTEGER;

UPDATE production_runs pr
SET posting_id_new = (
  SELECT p.posting_id
  FROM postings p
  WHERE p.job_id = pr.posting_id
)
WHERE pr.posting_id IS NOT NULL;

-- ============================================================================
-- STEP 4: Update profile_job_matches FK
-- ============================================================================

ALTER TABLE profile_job_matches
  ADD COLUMN posting_id INTEGER;

UPDATE profile_job_matches pjm
SET posting_id = (
  SELECT p.posting_id
  FROM postings p
  WHERE p.job_id = pjm.job_id
);

-- ============================================================================
-- STEP 5: Drop old FK constraints
-- ============================================================================

ALTER TABLE job_skills
  DROP CONSTRAINT IF EXISTS job_skills_job_id_fkey;

ALTER TABLE production_runs
  DROP CONSTRAINT IF EXISTS production_runs_posting_id_fkey;

ALTER TABLE profile_job_matches
  DROP CONSTRAINT IF EXISTS profile_job_matches_job_id_fkey;

-- ============================================================================
-- STEP 6: Rename columns
-- ============================================================================

-- In postings: job_id (TEXT) → posting_name
ALTER TABLE postings
  RENAME COLUMN job_id TO posting_name;

-- In job_skills: job_id → posting_name
ALTER TABLE job_skills
  RENAME COLUMN job_id TO posting_name;

-- In production_runs: posting_id (TEXT) → posting_name, posting_id_new → posting_id
ALTER TABLE production_runs
  RENAME COLUMN posting_id TO posting_name;

ALTER TABLE production_runs
  RENAME COLUMN posting_id_new TO posting_id;

-- In profile_job_matches: job_id → posting_name
ALTER TABLE profile_job_matches
  RENAME COLUMN job_id TO posting_name;

-- ============================================================================
-- STEP 7: Set new PRIMARY KEY on postings
-- ============================================================================

ALTER TABLE postings
  DROP CONSTRAINT postings_pkey;

ALTER TABLE postings
  ADD PRIMARY KEY (posting_id);

-- Note: posting_name is NOT unique (can have duplicates like 'TEST_ORACLE_DBA_001')
-- So we don't add UNIQUE constraint
ALTER TABLE postings
  ALTER COLUMN posting_name SET NOT NULL;

-- ============================================================================
-- STEP 8: Set NOT NULL and create new FKs
-- ============================================================================

ALTER TABLE job_skills
  ALTER COLUMN posting_id SET NOT NULL;

ALTER TABLE job_skills
  ADD CONSTRAINT job_skills_posting_id_fkey
  FOREIGN KEY (posting_id)
  REFERENCES postings(posting_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE production_runs
  ADD CONSTRAINT production_runs_posting_id_fkey
  FOREIGN KEY (posting_id)
  REFERENCES postings(posting_id)
  ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE profile_job_matches
  ALTER COLUMN posting_id SET NOT NULL;

ALTER TABLE profile_job_matches
  ADD CONSTRAINT profile_job_matches_posting_id_fkey
  FOREIGN KEY (posting_id)
  REFERENCES postings(posting_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE postings IS 
'Job postings (76 entries). Standardized 2025-10-30.
Pattern: posting_id (INTEGER PK) + posting_name (TEXT, not unique).
Note: posting_name can have duplicates (e.g., test data like TEST_ORACLE_DBA_001).';

COMMENT ON COLUMN postings.posting_id IS 
'Surrogate key - stable integer identifier for joins';

COMMENT ON COLUMN postings.posting_name IS 
'Job identifier from source system (can be duplicate for test data)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  posting_count INTEGER;
  job_skill_count INTEGER;
  match_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO posting_count FROM postings WHERE posting_id IS NULL;
  IF posting_count > 0 THEN
    RAISE EXCEPTION 'Found % postings without posting_id', posting_count;
  END IF;

  SELECT COUNT(*) INTO job_skill_count FROM job_skills WHERE posting_id IS NULL;
  IF job_skill_count > 0 THEN
    RAISE EXCEPTION 'Found % job_skills without posting_id', job_skill_count;
  END IF;

  SELECT COUNT(*) INTO match_count FROM profile_job_matches WHERE posting_id IS NULL;
  IF match_count > 0 THEN
    RAISE EXCEPTION 'Found % profile_job_matches without posting_id', match_count;
  END IF;

  RAISE NOTICE '✓ Migration 012 complete';
  RAISE NOTICE '  - % postings migrated', (SELECT COUNT(*) FROM postings);
  RAISE NOTICE '  - % job_skills updated', (SELECT COUNT(*) FROM job_skills);
  RAISE NOTICE '  - % production_runs updated', (SELECT COUNT(*) FROM production_runs WHERE posting_id IS NOT NULL);
  RAISE NOTICE '  - % profile_job_matches updated', (SELECT COUNT(*) FROM profile_job_matches);
END $$;

COMMIT;
