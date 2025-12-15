#!/bin/bash
# Check Recipe 1114 structure

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RECIPE 1114 STRUCTURE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

psql -h localhost -U base_admin -d base_yoga << 'SQL'
\pset border 2

-- Recipe info
SELECT recipe_id, recipe_name, recipe_description
FROM recipes WHERE recipe_id = 1114;

\echo ''
\echo '📍 SESSIONS:'
SELECT 
    rs.execution_order,
    s.session_name,
    a.actor_id,
    c.canonical_code
FROM recipe_sessions rs
JOIN sessions s ON rs.session_id = s.session_id
JOIN actors a ON s.actor_id = a.actor_id
JOIN canonicals c ON s.canonical_code = c.canonical_code
WHERE rs.recipe_id = 1114
ORDER BY rs.execution_order;

\echo ''
\echo '📝 SESSION 1 INSTRUCTION:'
SELECT 
    i.step_number,
    i.step_description,
    LEFT(i.prompt_template, 200) as prompt_preview
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name = (
    SELECT s2.session_name 
    FROM recipe_sessions rs 
    JOIN sessions s2 ON rs.session_id = s2.session_id 
    WHERE rs.recipe_id = 1114 AND rs.execution_order = 1
)
ORDER BY i.step_number;

SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
