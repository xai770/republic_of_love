-- Migration 009: Standardize schema_documentation
-- Date: 2025-10-30
-- Purpose: Add documentation_id INTEGER PK to replace composite (table_name, column_name)
-- Impact: 4 rows, no FKs
-- Risk: LOW - Utility table, no dependencies

BEGIN;

-- ============================================================================
-- STEP 1: Add new integer column
-- ============================================================================

ALTER TABLE schema_documentation 
  ADD COLUMN documentation_id INTEGER;

CREATE SEQUENCE schema_documentation_documentation_id_seq;

UPDATE schema_documentation 
SET documentation_id = nextval('schema_documentation_documentation_id_seq');

ALTER TABLE schema_documentation 
  ALTER COLUMN documentation_id SET DEFAULT nextval('schema_documentation_documentation_id_seq');

-- ============================================================================
-- STEP 2: Set new PRIMARY KEY
-- ============================================================================

ALTER TABLE schema_documentation
  DROP CONSTRAINT IF EXISTS schema_documentation_pkey;

ALTER TABLE schema_documentation
  ADD PRIMARY KEY (documentation_id);

-- Keep composite unique constraint for lookup
ALTER TABLE schema_documentation
  ADD CONSTRAINT schema_documentation_table_column_unique 
  UNIQUE (table_name, column_name);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE schema_documentation IS 
'Schema metadata and documentation (4 entries). Standardized 2025-10-30.
Pattern: documentation_id (INTEGER PK) + (table_name, column_name) UNIQUE composite key.';

COMMENT ON COLUMN schema_documentation.documentation_id IS 
'Surrogate key - stable integer identifier';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  doc_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO doc_count FROM schema_documentation WHERE documentation_id IS NULL;
  IF doc_count > 0 THEN
    RAISE EXCEPTION 'Found % documentation rows without documentation_id', doc_count;
  END IF;

  RAISE NOTICE '✓ Migration 009 complete';
  RAISE NOTICE '  - % documentation entries migrated', (SELECT COUNT(*) FROM schema_documentation);
END $$;

COMMIT;
