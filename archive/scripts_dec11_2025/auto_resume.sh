#!/bin/bash
# Auto-resume interrupted workflows
# Add to crontab: */5 * * * * /home/xai/Documents/ty_wave/scripts/auto_resume.sh >> /home/xai/Documents/ty_wave/logs/auto_resume.log 2>&1

cd /home/xai/Documents/ty_wave

# Source environment
source venv/bin/activate
source .env

# Check for dead workflows
DEAD_COUNT=$(python3 scripts/resume_workflows.py --quiet 2>&1 | grep -c "needing attention" || echo "0")

if [ "$DEAD_COUNT" != "0" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Found dead workflows, resuming..."
    python3 scripts/resume_workflows.py --resume
    
    # Check if a runner is already running
    RUNNER_PID=$(pgrep -f "run_batch_cleanup.py" | head -1)
    
    if [ -z "$RUNNER_PID" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting batch runner..."
        nohup python3 -u scripts/run_batch_cleanup.py >> logs/batch.log 2>&1 &
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Runner started with PID $!"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Runner already running (PID: $RUNNER_PID)"
    fi
else
    # Uncomment below for verbose logging
    # echo "$(date '+%Y-%m-%d %H:%M:%S') - All workflows healthy"
    :
fi
