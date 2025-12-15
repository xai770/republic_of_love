#!/bin/bash
# View Recipe 1120 execution results

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RECIPE 1120 (SkillBridge) - Execution Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

psql -h localhost -U base_admin -d base_yoga << 'SQL'
\pset border 2
\pset format wrapped

-- Get the latest recipe run
SELECT 
    rr.recipe_run_id,
    rr.recipe_id,
    rr.variation_id,
    rr.status,
    rr.started_at,
    rr.completed_at,
    rr.completed_sessions || '/' || rr.total_sessions as sessions
FROM recipe_runs rr
WHERE rr.recipe_id = 1120
ORDER BY rr.recipe_run_id DESC
LIMIT 1;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '📝 INPUT DATA'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT 
    v.variation_id,
    v.test_data->>'param_1' as input_text
FROM variations v
JOIN recipe_runs rr ON v.variation_id = rr.variation_id
WHERE rr.recipe_id = 1120
ORDER BY rr.recipe_run_id DESC
LIMIT 1;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🔍 SESSION 1: Olmo2 Soft Skills Detection'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT 
    sr.session_run_id,
    s.session_name,
    sr.status,
    sr.started_at,
    EXTRACT(EPOCH FROM (sr.completed_at - sr.started_at)) * 1000 || 'ms' as duration,
    ir.response_received as output
FROM session_runs sr
JOIN sessions s ON sr.session_id = s.session_id
JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE sr.recipe_run_id = (SELECT recipe_run_id FROM recipe_runs WHERE recipe_id = 1120 ORDER BY recipe_run_id DESC LIMIT 1)
  AND sr.session_number = 1
LIMIT 1;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🔍 SESSION 2: Phi3 Technical Skills Extraction'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT 
    sr.session_run_id,
    s.session_name,
    sr.status,
    sr.started_at,
    EXTRACT(EPOCH FROM (sr.completed_at - sr.started_at)) * 1000 || 'ms' as duration,
    ir.response_received as output
FROM session_runs sr
JOIN sessions s ON sr.session_id = s.session_id
JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE sr.recipe_run_id = (SELECT recipe_run_id FROM recipe_runs WHERE recipe_id = 1120 ORDER BY recipe_run_id DESC LIMIT 1)
  AND sr.session_number = 2
LIMIT 1;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🏆 SESSION 3: Llama3.2 Final Taxonomy Assembly'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT 
    sr.session_run_id,
    s.session_name,
    sr.status,
    sr.started_at,
    EXTRACT(EPOCH FROM (sr.completed_at - sr.started_at)) * 1000 || 'ms' as duration,
    ir.response_received as final_taxonomy
FROM session_runs sr
JOIN sessions s ON sr.session_id = s.session_id
JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE sr.recipe_run_id = (SELECT recipe_run_id FROM recipe_runs WHERE recipe_id = 1120 ORDER BY recipe_run_id DESC LIMIT 1)
  AND sr.session_number = 3
LIMIT 1;

SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
