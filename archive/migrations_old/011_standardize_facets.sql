-- Migration 011: Standardize facets table
-- Date: 2025-10-30
-- Purpose: Convert facet_id from TEXT to INTEGER, add facet_name
-- Impact: 74 rows, 2 FKs (canonicals.facet_id, facets.parent_id self-ref)
-- Risk: MEDIUM - Referenced by canonicals, has self-referencing hierarchy

BEGIN;

-- ============================================================================
-- STEP 0: Update canonicals trigger to use facet_id (still TEXT at this point)
-- ============================================================================

-- Temporarily use facet_id (TEXT) until we rename it later
CREATE OR REPLACE FUNCTION archive_canonicals()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO canonicals_history (
        canonical_code, facet_id, capability_description, prompt, response,
        review_notes, enabled, created_at, updated_at, change_reason
    ) VALUES (
        OLD.canonical_name, OLD.facet_id, OLD.capability_description, OLD.prompt, OLD.response,
        OLD.review_notes, OLD.enabled, OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 1: Add new integer column to facets
-- ============================================================================

ALTER TABLE facets 
  ADD COLUMN facet_id_new INTEGER,
  ADD COLUMN parent_id_new INTEGER;

CREATE SEQUENCE facets_facet_id_seq;

UPDATE facets 
SET facet_id_new = nextval('facets_facet_id_seq');

ALTER TABLE facets 
  ALTER COLUMN facet_id_new SET DEFAULT nextval('facets_facet_id_seq');

-- ============================================================================
-- STEP 2: Populate parent_id_new (self-reference)
-- ============================================================================

UPDATE facets f
SET parent_id_new = (
  SELECT parent.facet_id_new
  FROM facets parent
  WHERE parent.facet_id = f.parent_id
)
WHERE f.parent_id IS NOT NULL;

-- ============================================================================
-- STEP 3: Update canonicals.facet_id FK
-- ============================================================================

ALTER TABLE canonicals
  ADD COLUMN facet_id_new INTEGER;

UPDATE canonicals c
SET facet_id_new = (
  SELECT f.facet_id_new
  FROM facets f
  WHERE f.facet_id = c.facet_id
);

-- ============================================================================
-- STEP 4: Drop old FK constraints
-- ============================================================================

ALTER TABLE canonicals
  DROP CONSTRAINT IF EXISTS canonicals_facet_id_fkey;

ALTER TABLE facets
  DROP CONSTRAINT IF EXISTS facets_parent_id_fkey;

-- ============================================================================
-- STEP 5: Rename columns
-- ============================================================================

-- In facets
ALTER TABLE facets
  RENAME COLUMN facet_id TO facet_name;

ALTER TABLE facets
  RENAME COLUMN facet_id_new TO facet_id;

ALTER TABLE facets
  RENAME COLUMN parent_id TO parent_facet_name;

ALTER TABLE facets
  RENAME COLUMN parent_id_new TO parent_id;

-- In canonicals
ALTER TABLE canonicals
  RENAME COLUMN facet_id TO facet_name;

ALTER TABLE canonicals
  RENAME COLUMN facet_id_new TO facet_id;

-- ============================================================================
-- STEP 6: Set new PRIMARY KEY on facets
-- ============================================================================

ALTER TABLE facets
  DROP CONSTRAINT facets_pkey;

ALTER TABLE facets
  ADD PRIMARY KEY (facet_id);

ALTER TABLE facets
  ADD CONSTRAINT facets_facet_name_unique UNIQUE (facet_name);

ALTER TABLE facets
  ALTER COLUMN facet_name SET NOT NULL;

-- ============================================================================
-- STEP 7: Create new FKs
-- ============================================================================

-- Self-referencing FK for hierarchy
ALTER TABLE facets
  ADD CONSTRAINT facets_parent_id_fkey
  FOREIGN KEY (parent_id)
  REFERENCES facets(facet_id)
  ON UPDATE CASCADE ON DELETE SET NULL;

-- FK from canonicals
ALTER TABLE canonicals
  ALTER COLUMN facet_id SET NOT NULL;

ALTER TABLE canonicals
  ADD CONSTRAINT canonicals_facet_id_fkey
  FOREIGN KEY (facet_id)
  REFERENCES facets(facet_id)
  ON UPDATE CASCADE ON DELETE RESTRICT;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE facets IS 
'Hierarchical facet taxonomy (74 entries). Standardized 2025-10-30.
Pattern: facet_id (INTEGER PK) + facet_name (TEXT UNIQUE).
Self-referencing: parent_id → facet_id.';

COMMENT ON COLUMN facets.facet_id IS 
'Surrogate key - stable integer identifier for joins';

COMMENT ON COLUMN facets.facet_name IS 
'Natural key - unique facet name (e.g., TECHNICAL_SKILLS)';

COMMENT ON COLUMN facets.parent_id IS 
'Self-referencing FK to parent facet (NULL for root facets)';

-- ============================================================================
-- STEP 8: Update ALL triggers to use new column names
-- ============================================================================

-- Now that rename is complete, update triggers to final form
CREATE OR REPLACE FUNCTION archive_canonicals()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO canonicals_history (
        canonical_code, facet_id, capability_description, prompt, response,
        review_notes, enabled, created_at, updated_at, change_reason
    ) VALUES (
        OLD.canonical_name, OLD.facet_name, OLD.capability_description, OLD.prompt, OLD.response,
        OLD.review_notes, OLD.enabled, OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Facets trigger (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'archive_facets') THEN
        CREATE OR REPLACE FUNCTION archive_facets()
        RETURNS TRIGGER AS $func$
        BEGIN
            INSERT INTO facets_history (
                facet_id, facet_label, parent_id, facet_order,
                enabled, created_at, updated_at, change_reason
            ) VALUES (
                OLD.facet_name, OLD.facet_label, OLD.parent_facet_name, OLD.facet_order,
                OLD.enabled, OLD.created_at, OLD.updated_at, 'Updated via trigger'
            );
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;
        
        RAISE NOTICE 'Updated archive_facets() trigger';
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  facet_count INTEGER;
  canonical_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO facet_count FROM facets WHERE facet_id IS NULL;
  IF facet_count > 0 THEN
    RAISE EXCEPTION 'Found % facets without facet_id', facet_count;
  END IF;

  SELECT COUNT(*) INTO canonical_count FROM canonicals WHERE facet_id IS NULL;
  IF canonical_count > 0 THEN
    RAISE EXCEPTION 'Found % canonicals without facet_id', canonical_count;
  END IF;

  RAISE NOTICE '✓ Migration 011 complete';
  RAISE NOTICE '  - % facets migrated', (SELECT COUNT(*) FROM facets);
  RAISE NOTICE '  - % facets with parents', (SELECT COUNT(*) FROM facets WHERE parent_id IS NOT NULL);
  RAISE NOTICE '  - % canonicals updated', (SELECT COUNT(*) FROM canonicals);
END $$;

COMMIT;
