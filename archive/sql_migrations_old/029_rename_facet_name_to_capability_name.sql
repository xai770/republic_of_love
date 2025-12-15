-- Migration 029: Rename facet_name to capability_name in validated_prompts
-- Date: 2025-10-31
-- Purpose: Update column name to match capabilities table rename (formerly facets)
--          Maintains consistency after facets → capabilities rename

-- This migration renames facet_name to capability_name because:
-- 1. Facets were renamed to capabilities in earlier cleanup
-- 2. validated_prompts.facet_name references capabilities table
-- 3. Column name should match the referenced table name
-- 4. Completes the facets → capabilities migration

BEGIN;

-- Step 1: Rename the column
ALTER TABLE validated_prompts RENAME COLUMN facet_name TO capability_name;

-- Step 2: Add column comment
COMMENT ON COLUMN validated_prompts.capability_name IS 'Name of the capability being tested (references capabilities.capability_name). Formerly facet_name.';

-- Step 3: Update table comment to reflect change
COMMENT ON TABLE validated_prompts IS 'Manually-tested prompt-response pairs (scrapbook of validated prompts).
Each entry is a canonical example of a specific capability test case with known-good prompt and expected response.
Used for: regression testing, LLM comparison, capability validation.

Formerly: canonicals → validated_prompts (migration 016).
Updated: facet_name → capability_name (migration 029).

Pattern: validated_prompt_id (INTEGER PK) + validated_prompt_name (TEXT UNIQUE).
Links to capabilities table via capability_id and capability_name.';

COMMIT;

-- Verification queries
-- SELECT validated_prompt_id, validated_prompt_name, capability_name FROM validated_prompts LIMIT 5;
-- \d validated_prompts
