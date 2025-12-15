#!/bin/bash
# Run Recipe 1120 with test posting

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 RUNNING RECIPE 1120: SkillBridge with test_sb_001"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Create production run
echo "📝 Creating production run..."
psql -h localhost -U base_admin -d base_yoga << 'SQL'
INSERT INTO production_runs (
    recipe_id,
    posting_id,
    status,
    total_sessions
)
SELECT
    1120,
    'test_sb_001',
    'PENDING',
    3
WHERE NOT EXISTS (
    SELECT 1 FROM production_runs 
    WHERE recipe_id = 1120 AND posting_id = 'test_sb_001' AND status IN ('PENDING', 'RUNNING')
)
RETURNING production_run_id, recipe_id, posting_id, status;

SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Production run created! Now execute:"
echo "   python3 recipe_run_test_runner_v32.py --max-runs 1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
