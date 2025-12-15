#!/bin/bash
# Quick view of DynaTax job matching results

echo "🎯 DYNATAX JOB MATCHING RESULTS"
echo "================================"
echo ""

sqlite3 data/llmcore.db << 'SQL'
.mode column
.headers on
.width 3 65 8 15

SELECT 
    CAST(rr.recipe_run_id - 1443 AS TEXT) as '#',
    SUBSTR(v.variations_param_2, 1, 65) as 'Job Title',
    CASE 
        WHEN sr.session_output LIKE '%match_score%' 
        THEN CAST(SUBSTR(SUBSTR(sr.session_output, INSTR(sr.session_output, '"match_score":')), 16, 2) AS TEXT) || '/100'
        ELSE '--'
    END as 'Score',
    CASE 
        WHEN sr.session_output LIKE '%match_score%' THEN '✅ Success'
        WHEN sr.session_output LIKE '%Deutsche Post%' THEN '❌ Hallucinated'
        WHEN sr.session_output IS NULL THEN '⚠️  No Output'
        ELSE '�� Corrupted'
    END as 'Status'
FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
LEFT JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id AND sr.session_number = 2
WHERE rr.batch_id = 'gershon_matching_1761219568'
ORDER BY rr.recipe_run_id;
SQL

echo ""
echo "💡 2 successful matches, 8 hallucinations (phi3:latest continuous bug)"
echo "🔧 Next: Fix recipe to use isolated sessions and re-run"
echo ""
echo "📖 Detailed analysis: sqlite3 data/llmcore.db < explore_dynatax.sql"

