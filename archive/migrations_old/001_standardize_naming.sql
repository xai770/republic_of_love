-- Migration 001: Standardize Column Naming
-- Date: 2025-10-30
-- Purpose: Fix naming inconsistencies across execution tracking tables

BEGIN;

-- ============================================================================
-- 1. Rename session_runs.session_number to execution_order
-- ============================================================================
-- This aligns with recipe_sessions.execution_order semantic meaning

ALTER TABLE session_runs 
  RENAME COLUMN session_number TO execution_order;

COMMENT ON COLUMN session_runs.execution_order IS 
  'Sequence number matching recipe_sessions.execution_order. 
   Indicates which position this session occupies in recipe execution flow.';

-- ============================================================================
-- 2. Update recipe_engine code compatibility notes
-- ============================================================================
-- The recipe_engine.py code has been updated to use 'execution_order' 
-- consistently when inserting into session_runs.

-- Verify the change:
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'session_runs' 
-- AND column_name = 'execution_order';

COMMIT;

-- ============================================================================
-- Rollback Script (if needed):
-- ============================================================================
-- BEGIN;
-- ALTER TABLE session_runs RENAME COLUMN execution_order TO session_number;
-- COMMIT;
