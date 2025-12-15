#!/bin/bash
# Championship Round Progress Monitor

echo "=================================================="
echo "🏆 Recipe 1116 - Championship Round Progress"
echo "=================================================="
echo ""

# Check if process is still running
if ps -p 539494 > /dev/null 2>&1; then
    echo "✅ Process Status: RUNNING (PID 539494)"
else
    echo "⏹️  Process Status: COMPLETED or STOPPED"
fi
echo ""

# Count completed runs
echo "📊 Database Stats:"
sqlite3 data/llmcore.db << 'SQL'
SELECT 
    'Total Recipe Runs: ' || COUNT(*) as stat
FROM recipe_runs 
WHERE recipe_id = 1116

UNION ALL

SELECT 
    'Completed: ' || COUNT(*) as stat
FROM recipe_runs 
WHERE recipe_id = 1116 AND status = 'SUCCESS'

UNION ALL

SELECT 
    'Pending: ' || COUNT(*) as stat
FROM recipe_runs 
WHERE recipe_id = 1116 AND status = 'PENDING'

UNION ALL

SELECT 
    'Running: ' || COUNT(*) as stat
FROM recipe_runs 
WHERE recipe_id = 1116 AND status = 'RUNNING'

UNION ALL

SELECT 
    'Failed: ' || COUNT(*) as stat
FROM recipe_runs 
WHERE recipe_id = 1116 AND status = 'FAILED';
SQL

echo ""
echo "📝 Last 5 lines of log:"
tail -5 championship_round.log
echo ""
echo "=================================================="
echo "Run: ./check_championship_progress.sh"
echo "Live monitoring: tail -f championship_round.log"
echo "=================================================="
