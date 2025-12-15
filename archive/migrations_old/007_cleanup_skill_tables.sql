-- Migration 007: Cleanup skill tables (drop old TEXT columns)
-- Date: 2025-10-30
-- Purpose: Drop denormalized TEXT columns from skill_hierarchy and skill_relationships
-- Impact: 340 + 0 rows (no FKs depend on these TEXT columns anymore)
-- Risk: LOW - Already migrated to integer FKs in migration 005

BEGIN;

-- ============================================================================
-- STEP 1: Drop old TEXT columns from skill_hierarchy
-- ============================================================================

-- These were kept for transition period, now safe to drop
ALTER TABLE skill_hierarchy
  DROP COLUMN IF EXISTS skill_name CASCADE,
  DROP COLUMN IF EXISTS parent_skill_name CASCADE;

COMMENT ON TABLE skill_hierarchy IS 
'Parent-child relationships between skills (340 edges). Fully integer-based after migration 007.
Uses skill_id and parent_skill_id as composite PK, both FK to skill_aliases.';

-- ============================================================================
-- STEP 2: Drop old TEXT columns from skill_relationships
-- ============================================================================

ALTER TABLE skill_relationships
  DROP COLUMN IF EXISTS subject_skill_name CASCADE,
  DROP COLUMN IF EXISTS object_skill_name CASCADE;

-- ============================================================================
-- STEP 3: Drop old TEXT column from skill_occurrences
-- ============================================================================

ALTER TABLE skill_occurrences
  DROP COLUMN IF EXISTS skill_name CASCADE;

COMMENT ON TABLE skill_occurrences IS 
'Tracks where skills appear in postings/profiles (404 rows). Uses skill_id FK to skill_aliases.';

-- ============================================================================
-- STEP 4: Set NOT NULL on skill_relationships integer FKs
-- ============================================================================

-- Make sure integer FKs are required (table is empty so safe)
ALTER TABLE skill_relationships
  ALTER COLUMN subject_skill_id SET NOT NULL,
  ALTER COLUMN object_skill_id SET NOT NULL;

-- ============================================================================
-- STEP 5: Add composite PK to skill_relationships
-- ============================================================================

ALTER TABLE skill_relationships
  DROP CONSTRAINT IF EXISTS skill_relationships_pkey;

ALTER TABLE skill_relationships
  ADD PRIMARY KEY (subject_skill_id, relationship_type, object_skill_id);

COMMENT ON TABLE skill_relationships IS 
'Semantic relationships between skills (0 rows currently). Fully integer-based.
Composite PK: (subject_skill_id, relationship_type, object_skill_id).';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
BEGIN
  -- Verify skill_hierarchy has no TEXT columns (except created_by, notes)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'skill_hierarchy' 
      AND column_name IN ('skill', 'parent_skill', 'skill_name', 'parent_skill_name')
  ) THEN
    RAISE EXCEPTION 'skill_hierarchy still has old TEXT columns!';
  END IF;

  -- Verify skill_relationships has no TEXT skill columns
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'skill_relationships' 
      AND column_name IN ('subject_skill', 'object_skill', 'subject_skill_name', 'object_skill_name')
  ) THEN
    RAISE EXCEPTION 'skill_relationships still has old TEXT columns!';
  END IF;

  RAISE NOTICE '✓ Migration 007 complete';
  RAISE NOTICE '  - skill_hierarchy cleaned (340 relationships)';
  RAISE NOTICE '  - skill_relationships cleaned (0 relationships)';
  RAISE NOTICE '  - skill_occurrences cleaned (404 occurrences)';
  RAISE NOTICE '  - All skill tables now fully integer-based';
END $$;

COMMIT;
