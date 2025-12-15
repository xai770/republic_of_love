#!/bin/bash
# Quick status check for Recipe 1121 progress

export PGPASSWORD='base_yoga_secure_2025'

echo "🔍 Recipe 1121 Progress Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏰ $(date '+%H:%M:%S')"
echo ""

psql -h localhost -U base_admin -d base_yoga -t -A <<SQL
SELECT 'Jobs with skills: ' || COUNT(*) || '/71 (' || ROUND(100.0 * COUNT(*) / 71, 1) || '%)'
FROM postings 
WHERE skill_keywords::text != '[]' AND skill_keywords IS NOT NULL;

SELECT 'Total skills extracted: ' || COALESCE(SUM(json_array_length(skill_keywords::json)), 0)
FROM postings
WHERE skill_keywords::text != '[]';

SELECT 'Remaining jobs: ' || COUNT(*) 
FROM postings
WHERE skill_keywords::text = '[]' OR skill_keywords IS NULL;
SQL

echo ""
echo "Latest 3 jobs processed:"
psql -h localhost -U base_admin -d base_yoga -t -A -c "
SELECT '  ' || job_id || ': ' || json_array_length(skill_keywords::json) || ' skills'
FROM postings
WHERE skill_keywords::text != '[]'
ORDER BY COALESCE((skill_keywords::json)->>'timestamp', '1970-01-01')::timestamp DESC
LIMIT 3;
" 2>/dev/null || echo "  (checking...)"
