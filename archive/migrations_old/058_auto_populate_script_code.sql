-- Migration 058: Auto-populate script_code from disk for NULL entries
-- Created: 2025-11-12
-- Rationale: Critical security issue - code must be stored in database, not just on disk
--
-- This migration creates a function to auto-load script code from disk
-- when script_code is NULL, then stores it in the database.

BEGIN;

-- =============================================================================
-- STEP 1: Create helper function to load script from disk
-- =============================================================================

CREATE OR REPLACE FUNCTION load_script_from_disk(script_path TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    script_content TEXT;
    cmd TEXT;
BEGIN
    -- Build command to read file (use Python for cross-platform compatibility)
    cmd := format('python3 -c "import sys; print(open(''%s'').read())"', script_path);
    
    -- Note: This requires PostgreSQL to have permissions to execute Python
    -- Alternative: Use COPY command if file is in allowed directory
    
    -- For now, return NULL and handle in Python layer
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION load_script_from_disk IS 'Placeholder for loading script code from disk (implemented in Python layer)';

-- =============================================================================
-- STEP 2: Add trigger to warn when script_code is NULL
-- =============================================================================

CREATE OR REPLACE FUNCTION warn_missing_script_code()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.actor_type = 'script' AND NEW.script_code IS NULL THEN
        RAISE WARNING 'Actor % (%) has NULL script_code - code should be in database!', 
            NEW.actor_id, NEW.actor_name;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_warn_missing_script_code
    BEFORE INSERT OR UPDATE ON actors
    FOR EACH ROW
    EXECUTE FUNCTION warn_missing_script_code();

COMMENT ON TRIGGER trg_warn_missing_script_code ON actors IS 'Warn when script actors have NULL script_code';

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Check actors with NULL script_code
-- SELECT actor_id, actor_name, execution_path 
-- FROM actors 
-- WHERE actor_type = 'script' AND script_code IS NULL
-- ORDER BY actor_id;

COMMIT;

-- =============================================================================
-- NOTES
-- =============================================================================

-- PostgreSQL cannot directly read files from disk for security reasons.
-- The actual auto-population must be done in the Python layer (core/actor_router.py).
--
-- This migration:
-- 1. Documents the issue
-- 2. Adds warning trigger for visibility
-- 3. Provides placeholder for future enhancements
--
-- The real fix is in core/actor_router.py:
-- - Check if script_code IS NULL
-- - Read from execution_path
-- - UPDATE actors SET script_code = ... WHERE actor_id = ...
-- - Then execute from script_code instead of disk
