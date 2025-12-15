-- Migration 055: Update simple_skill_mapper instruction prompt
-- ================================================================
-- Date: 2025-11-04
-- Purpose: Update instruction 3351 prompt_template for simple_skill_mapper
--
-- Background:
--   - Migration 054 replaced taxonomy_gopher with simple_skill_mapper
--   - But instruction 3351 prompt_template still has OLD taxonomy_gopher format
--   - OLD format: "Map these raw skills... {session_2_output} {taxonomy} ... Return JSON array"
--   - simple_skill_mapper expects JUST the skills JSON array as input
--   - Mapper handles taxonomy loading and matching internally
--
-- Problem:
--   - Current prompt passes formatted text with {taxonomy} placeholder
--   - Mapper can't parse this, so it fails or returns garbage
--   - Workflow runs but saves ALL 316 taxonomy skills instead of matched subset
--
-- Solution:
--   - Change prompt_template to pass ONLY {session_2_output} (the extracted skills JSON)
--   - Remove {taxonomy} placeholder and all instruction text
--   - Mapper will receive clean JSON input it expects

-- =====================================================================
-- Update instruction 3351 prompt template
-- =====================================================================

UPDATE instructions
SET 
    prompt_template = '{session_2_output}',
    updated_at = NOW()
WHERE instruction_id = 3351
  AND instruction_name = 'Map extracted skills to taxonomy';

-- =====================================================================
-- Verification query
-- =====================================================================

SELECT 
    instruction_id,
    instruction_name,
    delegate_actor_id,
    prompt_template,
    LENGTH(prompt_template) as prompt_length
FROM instructions
WHERE instruction_id = 3351;

-- Expected output:
--   instruction_id: 3351
--   instruction_name: Map extracted skills to taxonomy
--   delegate_actor_id: 50
--   prompt_template: {session_2_output}
--   prompt_length: 19

-- =====================================================================
-- Rollback (if needed)
-- =====================================================================

-- To restore old prompt:
-- UPDATE instructions SET prompt_template = 
-- 'Map these raw skills to our canonical taxonomy.
-- 
-- RAW SKILLS EXTRACTED:
-- {session_2_output}
-- 
-- {taxonomy}
-- 
-- TASK:
-- 1. For each raw skill extracted, find the closest matching taxonomy skill
-- 2. If the skill is in German, translate to English first
-- 3. Return ONLY skills that match the taxonomy (don''t add new ones)
-- 4. Use exact taxonomy names (underscores, capitalization)
-- 5. If no good match exists, skip that skill
-- 
-- Return a JSON array of matched taxonomy skills:
-- ["SQL", "Python", "Leadership", "Communication"]
-- 
-- Return ONLY the JSON array, no other text.'
-- WHERE instruction_id = 3351;
