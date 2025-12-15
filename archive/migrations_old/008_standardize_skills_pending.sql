-- Migration 008: Standardize skills_pending_taxonomy
-- Date: 2025-10-30
-- Purpose: Add pending_skill_id INTEGER PK, rename raw_skill → raw_skill_name
-- Impact: 1090 rows, no FKs
-- Risk: LOW - No dependencies

BEGIN;

-- ============================================================================
-- STEP 1: Add new integer column
-- ============================================================================

ALTER TABLE skills_pending_taxonomy 
  ADD COLUMN pending_skill_id INTEGER;

CREATE SEQUENCE skills_pending_taxonomy_pending_skill_id_seq;

UPDATE skills_pending_taxonomy 
SET pending_skill_id = nextval('skills_pending_taxonomy_pending_skill_id_seq');

ALTER TABLE skills_pending_taxonomy 
  ALTER COLUMN pending_skill_id SET DEFAULT nextval('skills_pending_taxonomy_pending_skill_id_seq');

-- ============================================================================
-- STEP 2: Rename raw_skill → raw_skill_name
-- ============================================================================

ALTER TABLE skills_pending_taxonomy
  RENAME COLUMN raw_skill TO raw_skill_name;

-- ============================================================================
-- STEP 3: Set new PRIMARY KEY
-- ============================================================================

ALTER TABLE skills_pending_taxonomy
  DROP CONSTRAINT IF EXISTS skills_pending_taxonomy_pkey;

ALTER TABLE skills_pending_taxonomy
  ADD PRIMARY KEY (pending_skill_id);

ALTER TABLE skills_pending_taxonomy
  ADD CONSTRAINT skills_pending_taxonomy_raw_skill_name_unique UNIQUE (raw_skill_name);

ALTER TABLE skills_pending_taxonomy
  ALTER COLUMN raw_skill_name SET NOT NULL;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE skills_pending_taxonomy IS 
'Skills awaiting taxonomy classification (1090 entries). Standardized 2025-10-30.
Pattern: pending_skill_id (INTEGER PK) + raw_skill_name (TEXT UNIQUE).';

COMMENT ON COLUMN skills_pending_taxonomy.pending_skill_id IS 
'Surrogate key - stable integer identifier';

COMMENT ON COLUMN skills_pending_taxonomy.raw_skill_name IS 
'Natural key - raw skill text extracted from postings (unique)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  skill_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO skill_count FROM skills_pending_taxonomy WHERE pending_skill_id IS NULL;
  IF skill_count > 0 THEN
    RAISE EXCEPTION 'Found % pending skills without pending_skill_id', skill_count;
  END IF;

  RAISE NOTICE '✓ Migration 008 complete';
  RAISE NOTICE '  - % pending skills migrated', (SELECT COUNT(*) FROM skills_pending_taxonomy);
END $$;

COMMIT;
