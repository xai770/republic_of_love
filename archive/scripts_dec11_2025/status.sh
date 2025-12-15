#!/bin/bash
# Session Start Status - Run this at the beginning of every Arden session
# Shows current state so context can be established quickly

cd /home/xai/Documents/ty_learn

echo "═══════════════════════════════════════════════════════════════"
echo "  TURING STATUS - $(date '+%Y-%m-%d %H:%M')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 1. Posting counts
echo "📊 POSTING STATUS"
echo "─────────────────"
./scripts/q.sh "SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL) as summaries,
    COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as skills,
    COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as ihl
FROM postings" 2>/dev/null | tail -3 | head -1
echo ""

# 2. Pending work
echo "📋 PENDING WORK"
echo "───────────────"
./scripts/q.sh "SELECT 
    COUNT(*) FILTER (WHERE extracted_summary IS NULL AND job_description IS NOT NULL) as need_summary,
    COUNT(*) FILTER (WHERE skill_keywords IS NULL AND extracted_summary IS NOT NULL) as need_skills,
    COUNT(*) FILTER (WHERE ihl_score IS NULL AND skill_keywords IS NOT NULL) as need_ihl
FROM postings" 2>/dev/null | tail -3 | head -1
echo ""

# 3. Running processes
echo "🔄 RUNNING PROCESSES"
echo "────────────────────"
if ls /tmp/workflow_*.pid 2>/dev/null | head -1 > /dev/null; then
    for pidfile in /tmp/workflow_*.pid; do
        pid=$(cat "$pidfile" 2>/dev/null)
        wf=$(basename "$pidfile" .pid | sed 's/workflow_//')
        if ps -p "$pid" > /dev/null 2>&1; then
            started=$(ps -o lstart= -p "$pid" 2>/dev/null)
            echo "  ✅ Workflow $wf running (PID $pid, started: $started)"
        else
            echo "  ⚠️  Workflow $wf PID file exists but process dead (stale: $pidfile)"
        fi
    done
else
    echo "  No workflow PID files found"
fi

# Check for orphaned python processes
orphans=$(pgrep -af "run_workflow|wave_runner" 2>/dev/null | grep -v grep | head -3)
if [ -n "$orphans" ]; then
    echo "  ⚠️  Possible orphaned processes:"
    echo "$orphans" | sed 's/^/    /'
fi
echo ""

# 4. Last workflow execution (from audit log)
echo "📝 LAST WORKFLOW EXECUTION"
echo "──────────────────────────"
./scripts/q.sh "SELECT 
    created_at::timestamp(0) as ran_at,
    input->>'workflow_id' as workflow,
    output->>'status' as status,
    output->'delta'->>'summary' as \"+summary\",
    output->'delta'->>'skills' as \"+skills\",
    output->'delta'->>'ihl' as \"+ihl\"
FROM interactions 
WHERE conversation_id = 9198
ORDER BY created_at DESC 
LIMIT 1" 2>/dev/null | tail -4 | head -2
echo ""

# 5. Recent errors
echo "❌ RECENT ERRORS (last 24h)"
echo "───────────────────────────"
error_count=$(./scripts/q.sh "SELECT COUNT(*) FROM interactions WHERE status = 'failed' AND created_at > NOW() - INTERVAL '24 hours'" 2>/dev/null | tail -3 | head -1 | tr -d ' ')
if [ "$error_count" = "0" ]; then
    echo "  None ✓"
else
    echo "  $error_count failed interactions"
    ./scripts/q.sh "SELECT conversation_id, COUNT(*) as fails FROM interactions WHERE status = 'failed' AND created_at > NOW() - INTERVAL '24 hours' GROUP BY conversation_id ORDER BY fails DESC LIMIT 3" 2>/dev/null | tail -5
fi
echo ""

# 6. Ollama status
echo "🤖 OLLAMA STATUS"
echo "────────────────"
if curl -s http://localhost:11434/api/ps > /dev/null 2>&1; then
    models=$(curl -s http://localhost:11434/api/ps | jq -r '.models[].name' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
    if [ -n "$models" ]; then
        echo "  Loaded: $models"
    else
        echo "  Running, no models loaded"
    fi
else
    echo "  ⚠️  Ollama not responding"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "  Run: python3 tools/check_stale_docs.py   (check doc freshness)"
echo "  Run: python3 tools/run_workflow.py 3001  (start workflow)"
echo "═══════════════════════════════════════════════════════════════"
