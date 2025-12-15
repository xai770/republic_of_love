-- Migration 027: Drop skill_synonyms table
-- Date: 2025-10-31
-- Purpose: Remove unused skill_synonyms table
--          Table was designed but never actively used in workflows

-- This migration drops skill_synonyms because:
-- 1. Only 5 sample entries (K8s, k8, kube, py, Python-Programmierung) - never curated
-- 2. Python code (hybrid_skill_extraction.py) returns empty dict with TODO comment
-- 3. Not referenced by any active workflow or production code
-- 4. Was aspirational feature ("After 3-4 months of curation...") that was never built out
-- 5. If needed later, can recreate from git history

-- Note: skill_aliases table remains - it's the master skill taxonomy (896 entries)

BEGIN;

-- Step 1: Drop the table
DROP TABLE IF EXISTS skill_synonyms CASCADE;

-- Step 2: Drop the sequence
DROP SEQUENCE IF EXISTS skill_synonyms_synonym_id_seq CASCADE;

-- Note: Master skill taxonomy remains in skill_aliases table (896 skills)
-- If synonym mapping is needed in future, can recreate from git history

COMMIT;

-- Verification: Table should no longer exist
-- \dt skill_synonyms
