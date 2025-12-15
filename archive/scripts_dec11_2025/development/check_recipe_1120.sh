#!/bin/bash
# Check Recipe 1120 SkillBridge status

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏗️ RECIPE 1120: SkillBridge Skills Extraction"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

psql -h localhost -U base_admin -d base_yoga << 'SQL'
\pset border 2
\pset format wrapped

SELECT 
    r.recipe_id, 
    r.recipe_name, 
    rs.execution_order, 
    s.session_name, 
    a.actor_id,
    rs.execute_condition,
    rs.on_success_action
FROM recipes r 
JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id 
JOIN sessions s ON rs.session_id = s.session_id 
JOIN actors a ON s.actor_id = a.actor_id 
WHERE r.recipe_id = 1120 
ORDER BY rs.execution_order;

SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
