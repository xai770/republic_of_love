-- Migration 026: Drop schema_documentation table
-- Date: 2025-10-31
-- Purpose: Remove redundant schema_documentation table
--          PostgreSQL's native COMMENT system is superior and already in use

-- This migration drops schema_documentation because:
-- 1. PostgreSQL has native COMMENT ON TABLE/COLUMN system (standard, backed up, tool-supported)
-- 2. Duplicate documentation systems are error-prone and hard to maintain
-- 3. schema_documentation is already outdated (4 entries reference old table names)
-- 4. All recent migrations (016-025) use native COMMENT extensively
-- 5. Native comments are queryable via obj_description() and col_description()

BEGIN;

-- Step 1: Drop the table
DROP TABLE IF EXISTS schema_documentation CASCADE;

-- Step 2: Drop the sequence
DROP SEQUENCE IF EXISTS schema_documentation_documentation_id_seq CASCADE;

-- Note: All documentation now lives in PostgreSQL's native COMMENT system
-- To view comments:
--   Table comment:  SELECT obj_description('table_name'::regclass, 'pg_class');
--   Column comment: SELECT col_description('table_name'::regclass, column_ordinal_position);
--   Or use: \d+ table_name in psql

COMMIT;

-- Verification: Table should no longer exist
-- \dt schema_documentation
