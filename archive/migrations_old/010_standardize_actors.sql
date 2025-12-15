-- Migration 010: Standardize actors table
-- Date: 2025-10-30
-- Purpose: Convert actor_id from TEXT to INTEGER PK, add actor_name
-- Impact: 47 rows, 3 FKs (sessions.actor_id, instructions.delegate_actor_id, human_tasks.assigned_actor_id)
-- Risk: HIGH - Core table used by recipe engine

BEGIN;

-- ============================================================================
-- STEP 1: Add new integer column to actors
-- ============================================================================

ALTER TABLE actors 
  ADD COLUMN actor_id_new INTEGER;

CREATE SEQUENCE actors_actor_id_seq;

UPDATE actors 
SET actor_id_new = nextval('actors_actor_id_seq');

ALTER TABLE actors 
  ALTER COLUMN actor_id_new SET DEFAULT nextval('actors_actor_id_seq');

-- ============================================================================
-- STEP 2: Update sessions FK
-- ============================================================================

ALTER TABLE sessions
  ADD COLUMN actor_id_new INTEGER;

UPDATE sessions s
SET actor_id_new = (
  SELECT a.actor_id_new
  FROM actors a
  WHERE a.actor_id = s.actor_id
);

-- ============================================================================
-- STEP 3: Update instructions.delegate_actor_id FK
-- ============================================================================

ALTER TABLE instructions
  ADD COLUMN delegate_actor_id_new INTEGER;

UPDATE instructions i
SET delegate_actor_id_new = (
  SELECT a.actor_id_new
  FROM actors a
  WHERE a.actor_id = i.delegate_actor_id
)
WHERE i.delegate_actor_id IS NOT NULL;

-- ============================================================================
-- STEP 4: Update human_tasks.actor_id FK
-- ============================================================================

ALTER TABLE human_tasks
  ADD COLUMN actor_id_new INTEGER;

UPDATE human_tasks ht
SET actor_id_new = (
  SELECT a.actor_id_new
  FROM actors a
  WHERE a.actor_id = ht.actor_id
)
WHERE ht.actor_id IS NOT NULL;

-- ============================================================================
-- STEP 5: Drop old FK constraints
-- ============================================================================

ALTER TABLE sessions
  DROP CONSTRAINT IF EXISTS sessions_actor_id_fkey;

ALTER TABLE instructions
  DROP CONSTRAINT IF EXISTS instructions_delegate_actor_id_fkey;

ALTER TABLE human_tasks
  DROP CONSTRAINT IF EXISTS human_tasks_actor_id_fkey;

-- ============================================================================
-- STEP 6: Rename columns
-- ============================================================================

-- In actors: actor_id (TEXT) → actor_name, actor_id_new → actor_id
ALTER TABLE actors
  RENAME COLUMN actor_id TO actor_name;

ALTER TABLE actors
  RENAME COLUMN actor_id_new TO actor_id;

-- In sessions
ALTER TABLE sessions
  RENAME COLUMN actor_id TO actor_name;

ALTER TABLE sessions
  RENAME COLUMN actor_id_new TO actor_id;

-- In instructions
ALTER TABLE instructions
  RENAME COLUMN delegate_actor_id TO delegate_actor_name;

ALTER TABLE instructions
  RENAME COLUMN delegate_actor_id_new TO delegate_actor_id;

-- In human_tasks
ALTER TABLE human_tasks
  RENAME COLUMN actor_id TO actor_name;

ALTER TABLE human_tasks
  RENAME COLUMN actor_id_new TO actor_id;

-- ============================================================================
-- STEP 7: Set new PRIMARY KEY on actors
-- ============================================================================

ALTER TABLE actors
  DROP CONSTRAINT actors_pkey;

ALTER TABLE actors
  ADD PRIMARY KEY (actor_id);

ALTER TABLE actors
  ADD CONSTRAINT actors_actor_name_unique UNIQUE (actor_name);

ALTER TABLE actors
  ALTER COLUMN actor_name SET NOT NULL;

-- ============================================================================
-- STEP 8: Set NOT NULL and create new FKs
-- ============================================================================

ALTER TABLE sessions
  ALTER COLUMN actor_id SET NOT NULL;

ALTER TABLE sessions
  ADD CONSTRAINT sessions_actor_id_fkey
  FOREIGN KEY (actor_id)
  REFERENCES actors(actor_id)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE instructions
  ADD CONSTRAINT instructions_delegate_actor_id_fkey
  FOREIGN KEY (delegate_actor_id)
  REFERENCES actors(actor_id)
  ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE human_tasks
  ALTER COLUMN actor_id SET NOT NULL;

ALTER TABLE human_tasks
  ADD CONSTRAINT human_tasks_actor_id_fkey
  FOREIGN KEY (actor_id)
  REFERENCES actors(actor_id)
  ON UPDATE CASCADE ON DELETE RESTRICT;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE actors IS 
'Execution agents: LLMs, scripts, humans (47 entries). Standardized 2025-10-30.
Pattern: actor_id (INTEGER PK) + actor_name (TEXT UNIQUE).
Types: ollama_api, python_script, bash_script, http_api.';

COMMENT ON COLUMN actors.actor_id IS 
'Surrogate key - stable integer identifier for joins';

COMMENT ON COLUMN actors.actor_name IS 
'Natural key - unique actor name (e.g., qwen2.5:7b, taxonomy_gopher)';

-- ============================================================================
-- STEP 9: Update history trigger for sessions (references actor_id)
-- ============================================================================

-- Trigger might reference actor_id, update if needed
-- Check if trigger exists and update
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'sessions_before_update') THEN
        -- Recreate trigger function to use new column names
        CREATE OR REPLACE FUNCTION archive_sessions()
        RETURNS TRIGGER AS $func$
        BEGIN
            INSERT INTO sessions_history (
                session_id, canonical_code, session_name, session_description,
                actor_id, context_strategy, max_instruction_runs, enabled,
                created_at, updated_at, change_reason
            ) VALUES (
                OLD.session_id, OLD.canonical_name, OLD.session_name, OLD.session_description,
                OLD.actor_name, OLD.context_strategy, OLD.max_instruction_runs, OLD.enabled,
                OLD.created_at, OLD.updated_at, 'Updated via trigger'
            );
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;
        
        RAISE NOTICE 'Updated archive_sessions() trigger to use actor_name';
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  actor_count INTEGER;
  session_count INTEGER;
  instruction_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO actor_count FROM actors WHERE actor_id IS NULL;
  IF actor_count > 0 THEN
    RAISE EXCEPTION 'Found % actors without actor_id', actor_count;
  END IF;

  SELECT COUNT(*) INTO session_count FROM sessions WHERE actor_id IS NULL;
  IF session_count > 0 THEN
    RAISE EXCEPTION 'Found % sessions without actor_id', session_count;
  END IF;

  RAISE NOTICE '✓ Migration 010 complete';
  RAISE NOTICE '  - % actors migrated', (SELECT COUNT(*) FROM actors);
  RAISE NOTICE '  - % sessions updated', (SELECT COUNT(*) FROM sessions);
  RAISE NOTICE '  - % instructions with delegate updated', (SELECT COUNT(*) FROM instructions WHERE delegate_actor_id IS NOT NULL);
  RAISE NOTICE '  - % human_tasks updated', (SELECT COUNT(*) FROM human_tasks);
END $$;

COMMIT;
