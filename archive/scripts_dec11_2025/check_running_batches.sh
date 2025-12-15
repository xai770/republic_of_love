#!/bin/bash
# Check for running WaveRunner processes
# Usage: ./check_running_batches.sh [--force]
#
# By default, shows what's running. Use --force to kill.

set -e

FORCE=false
if [[ "$1" == "--force" ]]; then
    FORCE=true
fi

echo "========================================"
echo "WaveRunner Process Check"
echo "========================================"

# Find Python processes in ty_wave directory
PIDS=$(ps aux | grep -E "python.*ty_wave|python3.*ty_wave" | grep -v grep | grep -v "check_running" | awk '{print $2}')

if [[ -z "$PIDS" ]]; then
    echo "✅ No WaveRunner processes found"
else
    echo "Found WaveRunner processes:"
    echo ""
    for PID in $PIDS; do
        echo "PID $PID:"
        ps -p $PID -o pid,ppid,etime,cmd --no-headers 2>/dev/null || echo "  (process ended)"
        echo ""
    done
    
    if [[ "$FORCE" == "true" ]]; then
        echo "Killing processes..."
        for PID in $PIDS; do
            kill $PID 2>/dev/null && echo "  Killed $PID" || echo "  $PID already dead"
        done
        echo "✅ Processes killed"
    else
        echo "Use --force to kill these processes"
    fi
fi

# Check PID files
echo ""
echo "========================================"
echo "PID Files"
echo "========================================"

for pidfile in /tmp/workflow_*.pid; do
    if [[ -f "$pidfile" ]]; then
        PID=$(cat "$pidfile")
        if ps -p $PID > /dev/null 2>&1; then
            echo "🔄 $pidfile: PID $PID (running)"
        else
            echo "💀 $pidfile: PID $PID (dead - stale file)"
            if [[ "$FORCE" == "true" ]]; then
                rm "$pidfile"
                echo "   Removed stale PID file"
            fi
        fi
    fi
done

if ! ls /tmp/workflow_*.pid 1> /dev/null 2>&1; then
    echo "✅ No PID files found"
fi

# Check Ollama
echo ""
echo "========================================"
echo "Ollama Status"
echo "========================================"

curl -s http://localhost:11434/api/ps | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])
if models:
    for m in models:
        print(f\"  {m['name']}: {m['size_vram']//1024//1024}MB VRAM\")
else:
    print('  No models loaded')
" 2>/dev/null || echo "  Ollama not running"

echo ""
echo "========================================"
echo "GPU Status"
echo "========================================"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "  nvidia-smi not available"
