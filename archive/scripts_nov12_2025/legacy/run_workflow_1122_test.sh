#!/bin/bash
# Quick script to run workflow 1122 and report results

cd /home/xai/Documents/ty_learn

echo "Starting Workflow 1122..."
python3 runners/workflow_1122_runner.py --profile-id 1 > /tmp/w1122_final.log 2>&1

EXIT_CODE=$?

echo ""
echo "Workflow completed with exit code: $EXIT_CODE"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCESS! Checking database..."
    python3 << 'EOF'
from core.database import get_connection
import psycopg2.extras

conn = get_connection()
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cursor.execute('''
    SELECT COUNT(*) as count 
    FROM profile_skills 
    WHERE profile_id = 1
''')
count = cursor.fetchone()['count']
print(f"\n🎉 Skills saved: {count}\n")

if count > 0:
    cursor.execute('''
        SELECT sa.skill_name, ps.proficiency_level, ps.years_experience
        FROM profile_skills ps
        JOIN skill_aliases sa ON ps.skill_id = sa.skill_id
        WHERE ps.profile_id = 1
        ORDER BY ps.profile_skill_id
        LIMIT 10
    ''')
    print("Top 10 skills:")
    for row in cursor.fetchall():
        years = f" ({row['years_experience']} years)" if row['years_experience'] else ""
        print(f"  • {row['skill_name']}: {row['proficiency_level']}{years}")
conn.close()
EOF
else
    echo "❌ Workflow failed. Check /tmp/w1122_final.log"
    tail -50 /tmp/w1122_final.log
fi
