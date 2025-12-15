#!/bin/bash
# Monitor Recipe 1114 batch progress

export PGPASSWORD='base_yoga_secure_2025'

echo "🔍 Monitoring Recipe 1114 Batch Progress"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

while true; do
    clear
    echo "🌙 Recipe 1114 Overnight Batch - Progress Monitor"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏰ Current Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Database stats
    psql -h localhost -U base_admin -d base_yoga <<SQL
SELECT 
    '📊 Summary Statistics:' as section;
SELECT 
    '   Total Jobs: ' || COUNT(*) as stat
FROM postings
UNION ALL
SELECT 
    '   ✅ With Summaries: ' || COUNT(*) || ' (' || ROUND(100.0 * COUNT(*) / 71, 1) || '%)'
FROM postings WHERE extracted_summary IS NOT NULL
UNION ALL
SELECT 
    '   ⏳ Remaining: ' || COUNT(*)
FROM postings WHERE extracted_summary IS NULL;

SELECT '';
SELECT '📈 Recent Activity (last 5 summaries):' as section;
SELECT 
    '   ' || job_id || ': ' || LENGTH(extracted_summary) || ' chars at ' || 
    TO_CHAR(summary_extracted_at, 'HH24:MI:SS')
FROM postings 
WHERE extracted_summary IS NOT NULL
ORDER BY summary_extracted_at DESC NULLS LAST
LIMIT 5;
SQL
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Refreshing in 30 seconds... (Ctrl+C to stop)"
    sleep 30
done
