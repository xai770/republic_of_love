# Workflow Run Cookbook

> Systematic procedures for running workflows with reproducibility and traceability.

---

## Philosophy

**Every workflow run is an experiment.**

- **Hypothesis**: "Running workflow X will process Y items"
- **Method**: Documented procedure
- **Results**: Logged and analyzed
- **Reproducible**: Same inputs → Same outputs

---

## Pre-Flight Checklist

Before running ANY workflow:

### 1. State Snapshot

```bash
# Save current state
./scripts/q.sh "SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL) as summaries,
    COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as skills,
    COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as ihl
FROM postings" > /tmp/state_before.txt

cat /tmp/state_before.txt
```

### 2. Pending Work Estimate

```bash
# What WILL be processed?
./scripts/q.sh "SELECT 
    'pending_summary' as stage, COUNT(*) FROM postings 
    WHERE extracted_summary IS NULL AND job_description IS NOT NULL
UNION ALL SELECT 
    'pending_skills', COUNT(*) FROM postings 
    WHERE skill_keywords IS NULL AND extracted_summary IS NOT NULL
UNION ALL SELECT 
    'pending_ihl', COUNT(*) FROM postings 
    WHERE ihl_score IS NULL AND skill_keywords IS NOT NULL"
```

### 3. Interaction Queue Check

```bash
# Any stuck interactions?
./scripts/q.sh "SELECT status, COUNT(*) FROM interactions 
    WHERE created_at > NOW() - INTERVAL '24 hours' 
    GROUP BY status ORDER BY count DESC"
```

### 4. Model Availability

```bash
# Which models are loaded?
curl -s http://localhost:11434/api/ps | jq '.models[].name'

# Which models does WF3001 need?
./scripts/q.sh "SELECT DISTINCT a.actor_name 
    FROM workflow_conversations wc 
    JOIN conversations c ON wc.conversation_id = c.conversation_id
    JOIN actors a ON c.actor_id = a.actor_id 
    WHERE wc.workflow_id = 3001
    ORDER BY a.actor_name"
```

---

## Running a Workflow

### Standard Method: Use the Wrapper Script

```bash
# ✅ RECOMMENDED - background with logging
./scripts/run_workflow.sh 3001

# Also valid - direct CLI with more options
./tools/run_workflow.py 3001
./tools/run_workflow.py 3001 --mode single_posting --posting-id 4920
```

**Both methods provide:**
- Audit trail (logged to Workflow Orchestrator conversation 9198)
- PID locking (prevents duplicate runs)
- State snapshots (before/after comparison)

**Why `run_workflow.sh`?**
- Runs with `nohup` (survives if your session ends)
- Background execution (doesn't block terminal)
- Automatic log file creation

### What Happens When You Run

```bash
$ ./scripts/run_workflow.sh 3001

🚀 Starting workflow 3001 in background...
📝 Log file: logs/workflow_3001_20251210_143522.log
✅ Started! PID: 12345

Monitor with:
  tail -f logs/workflow_3001_20251210_143522.log
  ./scripts/status.sh

Stop with:
  kill 12345
```

### Monitor Progress

```bash
# Quick status check
./scripts/status.sh

# Live dashboard (recommended!)
python3 tools/live_dashboard.py --once

# Watch log file
tail -f logs/workflow_3001_*.log  # Most recent

# Check if running
ps -p $(cat /tmp/workflow_3001.pid 2>/dev/null) >/dev/null 2>&1 && echo "RUNNING" || echo "STOPPED"
```

---

## Post-Run Analysis

### 1. State Comparison

```bash
# Save after state
./scripts/q.sh "SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL) as summaries,
    COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as skills,
    COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as ihl
FROM postings" > /tmp/state_after.txt

# Compare
echo "=== BEFORE ===" && cat /tmp/state_before.txt
echo "=== AFTER ===" && cat /tmp/state_after.txt
```

### 2. Interaction Summary

```bash
# What interactions were processed?
./scripts/q.sh "SELECT 
    c.conversation_name,
    COUNT(*) as processed,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_sec
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.created_at > NOW() - INTERVAL '1 hour'
GROUP BY c.conversation_name
ORDER BY processed DESC"
```

### 3. Error Check

```bash
# Any failures?
./scripts/q.sh "SELECT 
    output->>'error' as error_type,
    COUNT(*)
FROM interactions 
WHERE status = 'failed' 
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY output->>'error'"
```

---

## Troubleshooting

### Runner Died Unexpectedly

```bash
# Check last log entries
tail -100 logs/workflow_*.log | grep -i "error\|exception\|failed"

# Check system resources
free -h
df -h /home

# Restart with fresh state
python3 tools/run_workflow.py 3001
```

### Interactions Stuck in Pending

```bash
# Find stuck interactions
./scripts/q.sh "SELECT 
    conversation_id, 
    COUNT(*),
    MIN(created_at) as oldest
FROM interactions 
WHERE status = 'pending'
GROUP BY conversation_id"

# Option 1: Reset to pending
./scripts/q.sh "UPDATE interactions SET status = 'pending' 
    WHERE status = 'processing' 
    AND updated_at < NOW() - INTERVAL '30 minutes'"

# Option 2: Delete orphans (careful!)
./scripts/q.sh "DELETE FROM interactions 
    WHERE status = 'pending' 
    AND workflow_run_id IS NULL"
```

### Wrong Model Processing

```bash
# Check which actor handles which conversation in WF3001
./scripts/q.sh "SELECT 
    wc.execution_order,
    c.conversation_name,
    a.actor_name
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE wc.workflow_id = 3001
ORDER BY wc.execution_order"
```

---

## Run Log Template

Create this after every run:

```markdown
# Workflow Run: 3001
**Date**: YYYY-MM-DD HH:MM
**Duration**: X hours
**Operator**: Name

## Before
- Total: X
- Summaries: X  
- Skills: X
- IHL: X

## Expected
- Process ~X summaries
- Process ~X skills
- Process ~X IHL

## After
- Total: X (+N)
- Summaries: X (+N)
- Skills: X (+N)
- IHL: X (+N)

## Interactions
- Created: X
- Completed: X
- Failed: X

## Issues
- None / List issues

## Notes
- Any observations
```

---

## Audit Trail (Implemented)

Every workflow execution is logged to **Workflow Orchestrator** (conversation 9198):

```sql
-- Query execution history
SELECT 
    interaction_id,
    created_at,
    input->>'workflow_id' as workflow,
    input->'state_before'->>'postings_total' as before_total,
    output->'state_after'->>'postings_total' as after_total,
    output->'delta' as changes
FROM interactions 
WHERE conversation_id = 9198
ORDER BY created_at DESC
LIMIT 10;
```

This provides:
- **Traceability**: "What ran on Dec 2?"
- **Analysis**: Compare runs over time
- **Debugging**: State before/after, duration, errors

---

*Last updated: 2025-12-10*
