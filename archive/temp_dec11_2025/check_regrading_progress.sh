#!/bin/bash
# Quick progress checker for Session 3 regrading

DB="data/llmcore.db"

echo "=== REGRADING PROGRESS ==="
echo ""

# Count Session 3 completion
echo "📊 Session 3 Status:"
sqlite3 $DB "
SELECT status, COUNT(*) as count
FROM session_runs
WHERE session_number = 3
GROUP BY status
ORDER BY status
"

echo ""
echo "⏱️  Recent Activity (last 5 completions):"
sqlite3 $DB "
SELECT 
    recipe_run_id,
    session_number,
    status,
    strftime('%H:%M:%S', timestamp) as time
FROM session_runs
WHERE session_number = 3
ORDER BY session_run_id DESC
LIMIT 5
"

echo ""
echo "🎯 Overall Recipe Run Status:"
sqlite3 $DB "
SELECT status, COUNT(*) as count
FROM recipe_runs
WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE name LIKE '%og_generate_and_grade_joke%')
GROUP BY status
ORDER BY status
"

echo ""
echo "💡 To watch live: tail -f temp/regrading_output.log"
