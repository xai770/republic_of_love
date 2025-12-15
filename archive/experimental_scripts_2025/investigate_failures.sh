#!/bin/bash
# Investigate Recipe 1120 failures

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 INVESTIGATING RECIPE 1120 FAILURES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

psql -h localhost -U base_admin -d base_yoga << 'SQL'
\pset border 2

-- Failed runs overview
\echo ''
\echo '📋 FAILED RECIPE RUNS:'
SELECT 
    rr.recipe_run_id,
    rr.variation_id,
    rr.batch_id,
    rr.status,
    rr.error_details,
    v.test_data->>'param_1' as input
FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
WHERE rr.recipe_id = 1120 AND rr.status = 'FAILED'
ORDER BY rr.recipe_run_id;

-- Check session_runs for failed runs
\echo ''
\echo '🔍 SESSION DETAILS FOR FAILED RUNS:'
SELECT 
    sr.session_run_id,
    sr.recipe_run_id,
    sr.session_number,
    s.session_name,
    sr.status,
    sr.error_details
FROM session_runs sr
JOIN sessions s ON sr.session_id = s.session_id
WHERE sr.recipe_run_id IN (6, 8, 9)
ORDER BY sr.recipe_run_id, sr.session_number;

-- Check instruction_runs for those failed sessions
\echo ''
\echo '📝 INSTRUCTION DETAILS:'
SELECT 
    ir.instruction_run_id,
    sr.recipe_run_id,
    sr.session_number,
    ir.step_number,
    LEFT(ir.prompt_rendered, 200) as prompt_preview,
    ir.status,
    ir.error_details
FROM instruction_runs ir
JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
WHERE sr.recipe_run_id IN (6, 8, 9)
ORDER BY sr.recipe_run_id, sr.session_number, ir.step_number;

SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
