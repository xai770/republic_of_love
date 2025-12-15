#!/bin/bash
# Real-time system monitoring for Workflow 3001
# Shows: Ollama processes, GPU usage, Database connections, Running workflows

echo "=========================================="
echo "SYSTEM MONITOR - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

echo ""
echo "🎮 GPU STATUS:"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits | \
    awk -F',' '{printf "  GPU %s: %s - Util: %s%%, Memory: %sMB/%sMB (%.1f%%)\n", $1, $2, $3, $4, $5, ($4/$5)*100}'
else
    echo "  nvidia-smi not available"
fi

echo ""
echo "🤖 OLLAMA PROCESSES:"
ps aux | grep ollama | grep -v grep | awk '{printf "  PID %s: CPU: %s%%, MEM: %s%%, CMD: %s\n", $2, $3, $4, substr($0, index($0,$11))}'
if [ -z "$(ps aux | grep ollama | grep -v grep)" ]; then
    echo "  No Ollama processes running"
fi

echo ""
echo "🐘 OLLAMA MODELS LOADED:"
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('models'):
        for model in data['models']:
            print(f\"  - {model['name']} (size: {model.get('size', 0) / 1024 / 1024 / 1024:.1f}GB)\")
    else:
        print('  No models currently loaded')
except:
    print('  Unable to query Ollama API')
"

echo ""
echo "🗄️  DATABASE CONNECTIONS:"
./scripts/q.sh "
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active,
    SUM(CASE WHEN state = 'idle' THEN 1 ELSE 0 END) as idle
FROM pg_stat_activity
WHERE datname = 'turing';
" | tail -n +3 | awk '{printf "  Total: %s, Active: %s, Idle: %s\n", $1, $3, $5}'

echo ""
echo "⚙️  ACTIVE WORKFLOWS (last 5 minutes):"
./scripts/q.sh "
SELECT 
    wr.workflow_run_id,
    wr.posting_id,
    wr.status,
    EXTRACT(EPOCH FROM (NOW() - wr.started_at))::int as running_seconds,
    COUNT(i.interaction_id) as interactions
FROM workflow_runs wr
LEFT JOIN interactions i ON i.workflow_run_id = wr.workflow_run_id
WHERE wr.started_at > NOW() - interval '5 minutes'
GROUP BY wr.workflow_run_id, wr.posting_id, wr.status, wr.started_at
ORDER BY wr.started_at DESC;
" | tail -n +3

echo ""
echo "🔄 RUNNING INTERACTIONS:"
./scripts/q.sh "
SELECT 
    i.interaction_id,
    c.conversation_name,
    a.actor_name,
    EXTRACT(EPOCH FROM (NOW() - i.started_at))::int as running_seconds
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON i.actor_id = a.actor_id
WHERE i.status = 'running'
ORDER BY i.started_at;
" | tail -n +3

echo ""
echo "💾 SYSTEM MEMORY:"
free -h | grep Mem | awk '{printf "  Total: %s, Used: %s, Free: %s, Available: %s\n", $2, $3, $4, $7}'

echo ""
echo "=========================================="
echo "Press Ctrl+C to stop monitoring"
echo "=========================================="
