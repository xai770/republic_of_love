-- Migration 054: Replace taxonomy_gopher with simple_skill_mapper
-- =================================================================
-- Date: 2025-11-04
-- Purpose: Replace the slow, unreliable taxonomy_gopher with simple_skill_mapper
--          that uses hybrid fuzzy matching + LLM approach
--
-- Background:
--   - taxonomy_gopher uses 15-turn interactive conversation (slow, times out)
--   - Only mapped 2 skills out of 22 extracted skills
--   - Our LLMs (qwen2.5:7b, gemma3:1b) recommended hybrid approach
--   - New simple_skill_mapper: fuzzy matching (fast) + LLM for ambiguous (accurate)
--
-- Changes:
--   1. Create new actor: simple_skill_mapper (actor_id=50)
--   2. Update conversation 3354 to use new actor
--   3. Keep taxonomy_gopher disabled for reference

-- =====================================================================
-- 1. Create simple_skill_mapper actor
-- =====================================================================

INSERT INTO actors (
    actor_id,
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    enabled,
    created_at,
    updated_at,
    url
) VALUES (
    50,
    'simple_skill_mapper',
    'script',
    'python_script',
    'tools/simple_skill_mapper.py',
    TRUE,
    NOW(),
    NOW(),
    'local://simple_skill_mapper'
) ON CONFLICT (actor_id) DO UPDATE SET
    actor_name = EXCLUDED.actor_name,
    execution_path = EXCLUDED.execution_path,
    enabled = TRUE,
    updated_at = NOW();

-- =====================================================================
-- 2. Update conversation 3354 (r2_map_to_taxonomy) to use new actor
-- =====================================================================

UPDATE conversations
SET 
    actor_id = 50,
    updated_at = NOW()
WHERE conversation_id = 3354
  AND conversation_name = 'r2_map_to_taxonomy';

-- =====================================================================
-- 3. Disable old taxonomy_gopher (keep for reference)
-- =====================================================================

UPDATE actors
SET 
    enabled = FALSE,
    updated_at = NOW()
WHERE actor_id = 47
  AND actor_name = 'taxonomy_gopher';

-- =====================================================================
-- Verification queries
-- =====================================================================

-- Check actors
SELECT 
    actor_id,
    actor_name,
    actor_type,
    execution_path,
    enabled
FROM actors
WHERE actor_id IN (47, 50)
ORDER BY actor_id;

-- Check conversation routing
SELECT 
    c.conversation_id,
    c.conversation_name,
    c.actor_id,
    a.actor_name,
    a.enabled as actor_enabled
FROM conversations c
JOIN actors a ON c.actor_id = a.actor_id
WHERE c.conversation_id = 3354;

-- =====================================================================
-- Rollback (if needed)
-- =====================================================================

-- To rollback:
-- UPDATE conversations SET actor_id = 47 WHERE conversation_id = 3354;
-- UPDATE actors SET enabled = TRUE WHERE actor_id = 47;
-- UPDATE actors SET enabled = FALSE WHERE actor_id = 50;
