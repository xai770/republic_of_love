-- Migration 028: Drop unused skill tables
-- Date: 2025-10-31
-- Purpose: Remove skill_inference_rules and skill_extraction_log tables
--          Not used by current active workflows (Recipes 1114, 1121, 1122)

-- These tables are dropped because:
-- 1. skill_inference_rules: Only 2 sample entries, never used in production
-- 2. skill_extraction_log: Used only by hybrid_skill_extraction.py (obsolete script)
-- 3. Current recipes (1114, 1121, 1122) use by_recipe_runner.py for all skill extraction
-- 4. No active production code references these tables

BEGIN;

-- Step 1: Drop skill_extraction_log table
DROP TABLE IF EXISTS skill_extraction_log CASCADE;

-- Step 2: Drop skill_extraction_log sequence
DROP SEQUENCE IF EXISTS skill_extraction_log_log_id_seq CASCADE;

-- Step 3: Drop skill_inference_rules table
DROP TABLE IF EXISTS skill_inference_rules CASCADE;

-- Step 4: Drop skill_inference_rules sequence
DROP SEQUENCE IF EXISTS skill_inference_rules_rule_id_seq CASCADE;

-- Note: Current skill extraction handled by:
-- - Recipe 1114: Job posting extraction (qwen2.5:7b + taxonomy mapping)
-- - Recipe 1121: Job skills extraction with importance/proficiency
-- - Recipe 1122: Profile skill extraction
-- All executed via by_recipe_runner.py

COMMIT;

-- Verification: Tables should no longer exist
-- \dt skill_extraction_log
-- \dt skill_inference_rules
