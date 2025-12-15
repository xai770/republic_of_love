-- Migration 005: Standardize skill_aliases (master skill table)
-- Date: 2025-10-30 (revised after schema discovery)
-- Purpose: Add skill_id INTEGER PK to skill_aliases (the master skill table with 896 skills)
-- Impact: skill_hierarchy (347 relationships), skill_occurrences (404 rows), skill_relationships (0 rows)
-- Risk: MEDIUM - Multiple dependent tables, but clear FK structure

-- SCHEMA DISCOVERY: skill_aliases is the MASTER table (not skill_hierarchy!)
-- skill_aliases.skill is UNIQUE and referenced by all other skill_* tables

BEGIN;

-- ============================================================================
-- STEP 0: Fix data quality - remove case-variant duplicates
-- ============================================================================

-- Delete lowercase variants if uppercase exists (keep uppercase as canonical)
DELETE FROM skill_hierarchy sh1
WHERE EXISTS (
  SELECT 1 FROM skill_hierarchy sh2
  WHERE UPPER(sh1.skill) = UPPER(sh2.skill)
    AND UPPER(sh1.parent_skill) = UPPER(sh2.parent_skill)
    AND sh1.skill <> sh2.skill  -- Different case
    AND sh1.skill ~ '[a-z]'      -- sh1 has lowercase
    AND sh2.skill !~ '[a-z]'      -- sh2 is all uppercase
);

DO $$
DECLARE
  deleted_count INTEGER;
BEGIN
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  IF deleted_count > 0 THEN
    RAISE NOTICE 'Cleaned up % duplicate skill_hierarchy rows (case variants)', deleted_count;
  END IF;
END $$;

-- ============================================================================
-- STEP 1: Drop dependent views
-- ============================================================================

DROP VIEW IF EXISTS v_skill_summary CASCADE;
DROP VIEW IF EXISTS v_pending_synonyms CASCADE;

-- ============================================================================
-- STEP 2: Add new integer column to skill_aliases
-- ============================================================================

ALTER TABLE skill_aliases 
  ADD COLUMN skill_id INTEGER;

-- ============================================================================
-- STEP 3: Populate skill_id with unique integers
-- ============================================================================

CREATE SEQUENCE skill_aliases_skill_id_seq;

UPDATE skill_aliases 
SET skill_id = nextval('skill_aliases_skill_id_seq');

ALTER TABLE skill_aliases 
  ALTER COLUMN skill_id SET DEFAULT nextval('skill_aliases_skill_id_seq');

-- ============================================================================
-- STEP 4: Update skill_hierarchy FKs (2 columns: skill, parent_skill)
-- ============================================================================

ALTER TABLE skill_hierarchy
  ADD COLUMN skill_id INTEGER,
  ADD COLUMN parent_skill_id INTEGER;

-- Case-insensitive match for skill
UPDATE skill_hierarchy sh
SET skill_id = (
  SELECT sa.skill_id
  FROM skill_aliases sa
  WHERE UPPER(sa.skill) = UPPER(sh.skill)
  LIMIT 1
);

-- Case-insensitive match for parent_skill
UPDATE skill_hierarchy sh
SET parent_skill_id = (
  SELECT sa.skill_id
  FROM skill_aliases sa
  WHERE UPPER(sa.skill) = UPPER(sh.parent_skill)
  LIMIT 1
);

DO $$
DECLARE
  unmatched_skill INTEGER;
  unmatched_parent INTEGER;
BEGIN
  SELECT COUNT(*) INTO unmatched_skill 
  FROM skill_hierarchy 
  WHERE skill_id IS NULL AND skill IS NOT NULL;
  
  SELECT COUNT(*) INTO unmatched_parent
  FROM skill_hierarchy 
  WHERE parent_skill_id IS NULL AND parent_skill IS NOT NULL;
  
  IF unmatched_skill > 0 THEN
    RAISE WARNING 'Found % skill_hierarchy rows with unmatched skill', unmatched_skill;
  END IF;
  
  IF unmatched_parent > 0 THEN
    RAISE WARNING 'Found % skill_hierarchy rows with unmatched parent_skill', unmatched_parent;
  END IF;
END $$;

-- ============================================================================
-- STEP 5: Update skill_occurrences FK
-- ============================================================================

ALTER TABLE skill_occurrences
  ADD COLUMN skill_id INTEGER;

UPDATE skill_occurrences so
SET skill_id = (
  SELECT sa.skill_id
  FROM skill_aliases sa
  WHERE UPPER(sa.skill) = UPPER(so.skill)
  LIMIT 1
);

DO $$
DECLARE
  unmatched_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO unmatched_count 
  FROM skill_occurrences 
  WHERE skill_id IS NULL AND skill IS NOT NULL;
  
  IF unmatched_count > 0 THEN
    RAISE WARNING 'Found % skill_occurrences with no matching skill_aliases entry', unmatched_count;
  END IF;
END $$;

-- ============================================================================
-- STEP 6: Update skill_relationships FKs (2 columns)
-- ============================================================================

ALTER TABLE skill_relationships
  ADD COLUMN subject_skill_id INTEGER,
  ADD COLUMN object_skill_id INTEGER;

UPDATE skill_relationships sr
SET subject_skill_id = (
  SELECT sa.skill_id
  FROM skill_aliases sa
  WHERE UPPER(sa.skill) = UPPER(sr.subject_skill)
  LIMIT 1
);

UPDATE skill_relationships sr
SET object_skill_id = (
  SELECT sa.skill_id
  FROM skill_aliases sa
  WHERE UPPER(sa.skill) = UPPER(sr.object_skill)
  LIMIT 1
);

DO $$
DECLARE
  unmatched_subject INTEGER;
  unmatched_object INTEGER;
BEGIN
  SELECT COUNT(*) INTO unmatched_subject 
  FROM skill_relationships 
  WHERE subject_skill_id IS NULL AND subject_skill IS NOT NULL;
  
  SELECT COUNT(*) INTO unmatched_object
  FROM skill_relationships 
  WHERE object_skill_id IS NULL AND object_skill IS NOT NULL;
  
  IF unmatched_subject > 0 THEN
    RAISE WARNING 'Found % skill_relationships with unmatched subject_skill', unmatched_subject;
  END IF;
  
  IF unmatched_object > 0 THEN
    RAISE WARNING 'Found % skill_relationships with unmatched object_skill', unmatched_object;
  END IF;
END $$;

-- ============================================================================
-- STEP 7: Drop old TEXT-based foreign keys
-- ============================================================================

ALTER TABLE skill_hierarchy
  DROP CONSTRAINT IF EXISTS skill_hierarchy_skill_fkey,
  DROP CONSTRAINT IF EXISTS skill_hierarchy_parent_skill_fkey;

ALTER TABLE skill_occurrences
  DROP CONSTRAINT IF EXISTS skill_occurrences_skill_fkey;

ALTER TABLE skill_relationships
  DROP CONSTRAINT IF EXISTS skill_relationships_subject_skill_fkey,
  DROP CONSTRAINT IF EXISTS skill_relationships_object_skill_fkey;

-- ============================================================================
-- STEP 8: Rename old columns (keep as denormalized reference for transition)
-- ============================================================================

ALTER TABLE skill_aliases
  RENAME COLUMN skill TO skill_name;

ALTER TABLE skill_hierarchy
  RENAME COLUMN skill TO skill_name;
ALTER TABLE skill_hierarchy
  RENAME COLUMN parent_skill TO parent_skill_name;

ALTER TABLE skill_occurrences
  RENAME COLUMN skill TO skill_name;

ALTER TABLE skill_relationships
  RENAME COLUMN subject_skill TO subject_skill_name;
ALTER TABLE skill_relationships
  RENAME COLUMN object_skill TO object_skill_name;

-- ============================================================================
-- STEP 9: Set new PRIMARY KEY and constraints on skill_aliases
-- ============================================================================

-- Drop old PK
ALTER TABLE skill_aliases
  DROP CONSTRAINT skill_aliases_pkey;

-- Add new PK
ALTER TABLE skill_aliases
  ADD PRIMARY KEY (skill_id);

-- Keep skill_name unique
ALTER TABLE skill_aliases
  ADD CONSTRAINT skill_aliases_skill_name_unique UNIQUE (skill_name);

ALTER TABLE skill_aliases
  ALTER COLUMN skill_name SET NOT NULL;

-- ============================================================================
-- STEP 10: Update skill_hierarchy PK (composite on INTEGER FKs)
-- ============================================================================

-- Drop old composite PK
ALTER TABLE skill_hierarchy
  DROP CONSTRAINT skill_hierarchy_pkey;

-- Add new composite PK on integer FKs
ALTER TABLE skill_hierarchy
  ADD PRIMARY KEY (skill_id, parent_skill_id);

-- Add NOT NULL constraints
ALTER TABLE skill_hierarchy
  ALTER COLUMN skill_id SET NOT NULL;
ALTER TABLE skill_hierarchy
  ALTER COLUMN parent_skill_id SET NOT NULL;

-- ============================================================================
-- STEP 11: Create new INTEGER-based foreign keys
-- ============================================================================

ALTER TABLE skill_hierarchy
  ADD CONSTRAINT skill_hierarchy_skill_id_fkey
  FOREIGN KEY (skill_id)
  REFERENCES skill_aliases(skill_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE skill_hierarchy
  ADD CONSTRAINT skill_hierarchy_parent_skill_id_fkey
  FOREIGN KEY (parent_skill_id)
  REFERENCES skill_aliases(skill_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE skill_occurrences
  ADD CONSTRAINT skill_occurrences_skill_id_fkey
  FOREIGN KEY (skill_id)
  REFERENCES skill_aliases(skill_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

-- Allow NULL for now (unmatched occurrences)
-- ALTER TABLE skill_occurrences ALTER COLUMN skill_id SET NOT NULL;

ALTER TABLE skill_relationships
  ADD CONSTRAINT skill_relationships_subject_skill_id_fkey
  FOREIGN KEY (subject_skill_id)
  REFERENCES skill_aliases(skill_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE skill_relationships
  ADD CONSTRAINT skill_relationships_object_skill_id_fkey
  FOREIGN KEY (object_skill_id)
  REFERENCES skill_aliases(skill_id)
  ON UPDATE CASCADE ON DELETE CASCADE;

-- ============================================================================
-- STEP 12: Remove self-referential relationships (data quality fix)
-- ============================================================================

-- Delete rows where skill maps to same ID as its parent (circular reference)
DELETE FROM skill_hierarchy
WHERE skill_id = parent_skill_id;

DO $$
DECLARE
  deleted_count INTEGER;
BEGIN
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  IF deleted_count > 0 THEN
    RAISE NOTICE 'Removed % self-referential skill_hierarchy rows', deleted_count;
  END IF;
END $$;

-- ============================================================================
-- STEP 13: Recreate Check Constraint on skill_hierarchy
-- ============================================================================

ALTER TABLE skill_hierarchy
  DROP CONSTRAINT IF EXISTS skill_hierarchy_check;

ALTER TABLE skill_hierarchy
  ADD CONSTRAINT skill_hierarchy_check CHECK (skill_id <> parent_skill_id);

-- ============================================================================
-- STEP 14: Add helpful comments
-- ============================================================================

COMMENT ON TABLE skill_aliases IS 
'Master list of 896 skills with canonical names and aliases. Standardized 2025-10-30.
Pattern: skill_id (INTEGER PK) + skill_name (TEXT UNIQUE) for AI consistency.';

COMMENT ON COLUMN skill_aliases.skill_id IS 
'Surrogate key - stable integer identifier for joins';

COMMENT ON COLUMN skill_aliases.skill_name IS 
'Natural key - canonical skill name in UPPER_SNAKE_CASE (unique)';

COMMENT ON TABLE skill_hierarchy IS 
'Many-to-many parent-child relationships between skills (347 edges in skill graph).
One skill can belong to multiple domains. Uses integer FKs to skill_aliases.';

COMMENT ON COLUMN skill_hierarchy.skill_name IS 
'Denormalized for human readability - consider dropping after transition period';

COMMENT ON COLUMN skill_hierarchy.parent_skill_name IS 
'Denormalized for human readability - consider dropping after transition period';

-- ============================================================================
-- STEP 15: VERIFICATION QUERIES
-- ============================================================================

DO $$
DECLARE
  skill_count INTEGER;
  hierarchy_count INTEGER;
  null_occurrences INTEGER;
BEGIN
  -- Check all skill_aliases have IDs
  SELECT COUNT(*) INTO skill_count FROM skill_aliases WHERE skill_id IS NULL;
  IF skill_count > 0 THEN
    RAISE EXCEPTION 'Found % skill_aliases without skill_id', skill_count;
  END IF;

  -- Check all skill_hierarchy relationships mapped
  SELECT COUNT(*) INTO hierarchy_count FROM skill_hierarchy 
  WHERE skill_id IS NULL OR parent_skill_id IS NULL;
  IF hierarchy_count > 0 THEN
    RAISE EXCEPTION 'Found % skill_hierarchy rows with NULL FKs', hierarchy_count;
  END IF;

  -- Count NULL skill_ids in occurrences (acceptable for now)
  SELECT COUNT(*) INTO null_occurrences FROM skill_occurrences WHERE skill_id IS NULL;

  RAISE NOTICE '✓ Migration 005 validation passed';
  RAISE NOTICE '  - % skills migrated in skill_aliases', (SELECT COUNT(*) FROM skill_aliases);
  RAISE NOTICE '  - % parent-child relationships in skill_hierarchy', (SELECT COUNT(*) FROM skill_hierarchy);
  RAISE NOTICE '  - % skill_occurrences updated (% orphaned)', 
    (SELECT COUNT(*) FROM skill_occurrences WHERE skill_id IS NOT NULL), null_occurrences;
  RAISE NOTICE '  - % skill_relationships ready', (SELECT COUNT(*) FROM skill_relationships);
  
  IF null_occurrences > 0 THEN
    RAISE NOTICE '';
    RAISE NOTICE 'NOTE: % orphaned skill_occurrences should be cleaned up in follow-up migration', null_occurrences;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- TODO: Recreate views v_skill_summary and v_pending_synonyms
-- (After code is updated to use skill_id)
-- ============================================================================
