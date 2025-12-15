-- Migration 006: Standardize canonicals table
-- Date: 2025-10-30
-- Purpose: Add canonical_id INTEGER PK, rename canonical_code → canonical_name
-- Impact: 62 rows, 1 FK (sessions.canonical_code)
-- Risk: LOW - Single FK reference

BEGIN;

-- ============================================================================
-- STEP 1: Add new integer column
-- ============================================================================

ALTER TABLE canonicals 
  ADD COLUMN canonical_id INTEGER;

CREATE SEQUENCE canonicals_canonical_id_seq;

UPDATE canonicals 
SET canonical_id = nextval('canonicals_canonical_id_seq');

ALTER TABLE canonicals 
  ALTER COLUMN canonical_id SET DEFAULT nextval('canonicals_canonical_id_seq');

-- ============================================================================
-- STEP 2: Update sessions FK
-- ============================================================================

ALTER TABLE sessions
  ADD COLUMN canonical_id INTEGER;

UPDATE sessions s
SET canonical_id = (
  SELECT c.canonical_id
  FROM canonicals c
  WHERE c.canonical_code = s.canonical_code
);

DO $$
DECLARE
  unmatched INTEGER;
BEGIN
  SELECT COUNT(*) INTO unmatched FROM sessions WHERE canonical_id IS NULL AND canonical_code IS NOT NULL;
  IF unmatched > 0 THEN
    RAISE WARNING 'Found % sessions with unmatched canonical_code', unmatched;
  END IF;
END $$;

-- ============================================================================
-- STEP 3: Drop old FK constraint
-- ============================================================================

ALTER TABLE sessions
  DROP CONSTRAINT IF EXISTS sessions_canonical_code_fkey;

-- ============================================================================
-- STEP 4: Rename canonical_code → canonical_name
-- ============================================================================

ALTER TABLE canonicals
  RENAME COLUMN canonical_code TO canonical_name;

ALTER TABLE sessions
  RENAME COLUMN canonical_code TO canonical_name;

-- ============================================================================
-- STEP 5: Set new PRIMARY KEY on canonicals
-- ============================================================================

ALTER TABLE canonicals
  DROP CONSTRAINT canonicals_pkey;

ALTER TABLE canonicals
  ADD PRIMARY KEY (canonical_id);

ALTER TABLE canonicals
  ADD CONSTRAINT canonicals_canonical_name_unique UNIQUE (canonical_name);

ALTER TABLE canonicals
  ALTER COLUMN canonical_name SET NOT NULL;

-- ============================================================================
-- STEP 6: Create new FK from sessions
-- ============================================================================

ALTER TABLE sessions
  ADD CONSTRAINT sessions_canonical_id_fkey
  FOREIGN KEY (canonical_id)
  REFERENCES canonicals(canonical_id)
  ON UPDATE CASCADE ON DELETE SET NULL;

-- ============================================================================
-- STEP 7: Update facet_id FK (it's TEXT, will be fixed in migration 007)
-- ============================================================================

-- NOTE: canonicals.facet_id still references facets.facet_id (TEXT)
-- Will be updated when facets table is standardized

COMMENT ON TABLE canonicals IS 
'Canonical skill/capability definitions (62 entries). Standardized 2025-10-30.
Pattern: canonical_id (INTEGER PK) + canonical_name (TEXT UNIQUE).';

COMMENT ON COLUMN canonicals.canonical_name IS 
'Natural key - unique canonical code (e.g., PYTHON_PROGRAMMING)';

-- ============================================================================
-- STEP 8: Update history trigger for sessions
-- ============================================================================

-- Trigger references canonical_code, needs to use canonical_name now
CREATE OR REPLACE FUNCTION archive_sessions()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO sessions_history (
        session_id, canonical_code, session_name, session_description,
        actor_id, context_strategy, max_instruction_runs, enabled,
        created_at, updated_at, change_reason
    ) VALUES (
        OLD.session_id, OLD.canonical_name, OLD.session_name, OLD.session_description,
        OLD.actor_id, OLD.context_strategy, OLD.max_instruction_runs, OLD.enabled,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: sessions_history.canonical_code column name kept for now (history table)
COMMENT ON FUNCTION archive_sessions() IS 
'Updated 2025-10-30: Uses canonical_name from sessions (renamed from canonical_code)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  canonical_count INTEGER;
  session_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO canonical_count FROM canonicals WHERE canonical_id IS NULL;
  IF canonical_count > 0 THEN
    RAISE EXCEPTION 'Found % canonicals without canonical_id', canonical_count;
  END IF;

  SELECT COUNT(*) INTO session_count FROM sessions WHERE canonical_id IS NULL AND canonical_name IS NOT NULL;
  IF session_count > 0 THEN
    RAISE WARNING 'Found % sessions with unmatched canonical', session_count;
  END IF;

  RAISE NOTICE '✓ Migration 006 complete';
  RAISE NOTICE '  - % canonicals migrated', (SELECT COUNT(*) FROM canonicals);
  RAISE NOTICE '  - % sessions updated', (SELECT COUNT(*) FROM sessions WHERE canonical_id IS NOT NULL);
END $$;

COMMIT;
