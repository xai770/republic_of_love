#!/bin/bash
# Keep only self_healing_dual_grader and SkillBridge active

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'
-- Disable all recipes except 1114 and 1120
UPDATE recipes 
SET enabled = false 
WHERE recipe_id NOT IN (1114, 1120);

-- Show active recipes
\echo ''
\echo 'ACTIVE RECIPES:'
SELECT recipe_id, recipe_name, enabled 
FROM recipes 
WHERE enabled = true 
ORDER BY recipe_id;

-- Show disabled count
SELECT COUNT(*) as disabled_count 
FROM recipes 
WHERE enabled = false;

SQL
