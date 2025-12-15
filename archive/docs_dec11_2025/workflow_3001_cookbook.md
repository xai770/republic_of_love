# Workflow 3001 Cookbook

**Last Updated:** December 3, 2025  
**Author:** Sandy  
**Purpose:** Complete operational guide for the Deutsche Bank job processing pipeline

> **📁 Path Note:** `ty_wave` and `ty_learn` refer to the same workspace. There are symlinks:
> `~/Documents/ty_wave` → `~/Documents/ty_learn`. Use either path interchangeably.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Starting a Batch](#starting-a-batch)
3. [Monitoring Progress](#monitoring-progress)
4. [Stopping & Restarting](#stopping--restarting)
5. [Troubleshooting](#troubleshooting)
6. [Architecture Deep Dive](#architecture-deep-dive)
7. [Database Queries](#database-queries)

---

## Quick Reference

```bash
# Start a batch (background)
nohup python3 scripts/test/run_workflow_3001.py --fetch --max-jobs 200 > logs/run.log 2>&1 &

# Monitor (live refresh)
python3 tools/_workflow_flowchart.py

# Monitor (one-shot)
python3 tools/_workflow_flowchart.py --once

# Quick DB query
./scripts/q.sh "SELECT COUNT(*) FROM postings WHERE ihl_score IS NOT NULL"

# Check if runner is alive
ps aux | grep run_workflow
```

---

## Starting a Batch

### Basic Start (Fetch + Process)

```bash
cd /home/xai/Documents/ty_wave
nohup python3 scripts/test/run_workflow_3001.py --fetch --max-jobs 200 > logs/run_200.log 2>&1 &
```

**What happens:**
1. Fetches up to 200 **NEW** jobs from Deutsche Bank API (skips existing)
2. Validates each posting (checks job_description exists)
3. Creates pending interactions for each workflow step
4. Processes all pending interactions across the pipeline

### Process Existing Postings Only (No Fetch)

```bash
python3 scripts/test/run_workflow_3001.py
```

This will process any postings that have pending interactions but no new fetching.

### Process a Single Posting

```bash
python3 scripts/test/run_workflow_3001.py --posting-id 10441
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--fetch` | off | Fetch new jobs from API |
| `--max-jobs N` | 50 | Max NEW jobs to fetch (ignores existing) |
| `--max-iterations N` | 5000 | Max processing loops |
| `--posting-id N` | none | Process single posting |

---

## Monitoring Progress

### Flowchart Dashboard (Recommended)

```bash
python3 tools/_workflow_flowchart.py
```

Shows:
- Step-by-step progress with completion percentages
- **Avg column**: Average processing time per step (actual execution, not queue wait)
- **ETA column**: Estimated time to complete remaining work per step
- **Phosphor bar**: Activity history (bright=recent, dim=older) showing last 20 min
- Status breakdown: ✅completed 🔄running ⏳pending ❌failed
- Overall ETA based on recent throughput

Options:
- `--once`: Run once and exit
- `--interval 30`: Refresh every 30 seconds (default: 60)

### Check Runner Process

```bash
ps aux | grep run_workflow
```

### Check Log File

```bash
tail -f logs/run_200.log
```

---

## Stopping & Restarting

### ⚠️ IMPORTANT: Safe Shutdown

The runner handles `Ctrl+C` (SIGINT) and `kill` (SIGTERM) gracefully:

1. Marks workflow_run status as `'interrupted'`
2. Commits current transaction
3. Does NOT corrupt data

**What to do:**
```bash
# Option 1: If running in foreground
Ctrl+C

# Option 2: If running in background
kill $(pgrep -f run_workflow_3001)
```

### After Restart: Clean Up Stale States

When you restart the system, some interactions might be stuck in `'running'` status (they were mid-execution when shutdown happened).

**Fix before restarting:**

```bash
./scripts/q.sh "
-- Reset stuck 'running' interactions to 'pending'
UPDATE interactions 
SET status = 'pending', updated_at = NOW()
WHERE status = 'running';
"
```

**Fix stale workflow_runs:**

```bash
./scripts/q.sh "
-- Reset interrupted/running workflow_runs so they can be resumed
UPDATE workflow_runs 
SET status = 'running', updated_at = NOW()
WHERE status IN ('interrupted', 'running')
  AND workflow_id = 3001;
"
```

### Restart the Workflow

After cleanup, just start a new run:

```bash
nohup python3 scripts/test/run_workflow_3001.py --fetch --max-jobs 200 > logs/run.log 2>&1 &
```

It will:
1. Pick up all pending interactions from previous runs
2. Continue processing where it left off
3. Fetch new jobs if `--fetch` is specified

---

## Troubleshooting

### Problem: "No pending interactions" but postings aren't complete

**Check for stuck interactions:**
```bash
./scripts/q.sh "
SELECT status, COUNT(*) 
FROM interactions 
WHERE conversation_id IN (
    SELECT conversation_id FROM workflow_conversations WHERE workflow_id = 3001
)
GROUP BY status;
"
```

If you see `running` count > 0, reset them:
```bash
./scripts/q.sh "UPDATE interactions SET status = 'pending' WHERE status = 'running';"
```

### Problem: Fetcher says "0 new jobs" but API has more

**Cause:** The fetcher scans from offset 0. If early jobs are all existing, it might not reach new ones at higher offsets.

**Fix (already applied Dec 3):** The fetcher now continues until it finds `max_jobs` NEW insertions, regardless of how many existing ones it skips.

**Verify:** Check the debug log:
```bash
tail -50 /tmp/db_job_fetcher_debug.txt
```

### Problem: High fail rate on grading steps

**Check which step is failing:**
```bash
./scripts/q.sh "
SELECT c.conversation_name, i.status, COUNT(*)
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE c.workflow_id = 3001
GROUP BY c.conversation_name, i.status
HAVING i.status = 'failed'
ORDER BY COUNT(*) DESC;
"
```

### Problem: Postings stuck at "pending" status forever

**Check if they have interactions:**
```bash
./scripts/q.sh "
SELECT p.posting_id, p.posting_name, COUNT(i.interaction_id) as interactions
FROM postings p
LEFT JOIN interactions i ON p.posting_id = i.posting_id
WHERE p.extracted_summary IS NULL
GROUP BY p.posting_id, p.posting_name
ORDER BY interactions
LIMIT 10;
"
```

If interactions = 0, the fan-out didn't create them. Re-run with:
```bash
python3 scripts/test/run_workflow_3001.py --posting-id <posting_id>
```

---

## Architecture Deep Dive

### Workflow Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE 1: FETCH & VALIDATE                                     │
├─────────────────────────────────────────────────────────────────┤
│ 1. Fetch Jobs (db_job_fetcher)                                  │
│    └─→ Calls Deutsche Bank Workday API                          │
│    └─→ Inserts new postings, updates last_seen_at for existing │
│                                                                  │
│ 2. Validate Job Description (check_description)                 │
│    └─→ Checks job_description NOT NULL and length >= 100       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE 2: SUMMARY GENERATION                                   │
├─────────────────────────────────────────────────────────────────┤
│ 3. Extract (qwen2.5:7b) ─→ Create initial summary               │
│ 4. Grade (mistral:latest) ─→ Independent review                 │
│ 5. Grade (qwen2.5:7b) ─→ Second review                          │
│      │                                                           │
│      ├─→ PASS ─→ 9. Format Standardization                      │
│      └─→ FAIL ─→ 6. Improve ─→ 7. Regrade                       │
│                       │                                          │
│                       ├─→ PASS ─→ 9. Format Standardization     │
│                       └─→ FAIL ─→ 8. Create Ticket              │
│                                                                  │
│ 10. Save Summary (summary_saver)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE 3: SKILLS EXTRACTION                                    │
├─────────────────────────────────────────────────────────────────┤
│ 11. Extract Skills (qwen2.5:7b)                                 │
│ 12. Save Skills (postingskill_save)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE 4: IHL SCORING                                          │
├─────────────────────────────────────────────────────────────────┤
│ 13. Analyst (qwen2.5:7b) ─→ Find red flags                      │
│ 14. Skeptic (mistral:latest) ─→ Challenge analysis              │
│ 15. HR Expert (qwen2.5:7b) ─→ Final verdict                     │
│ 16. Save IHL Score (ihl_score_saver)                            │
└─────────────────────────────────────────────────────────────────┘
```

### Model Configuration

| Role | Model | Notes |
|------|-------|-------|
| Writer | qwen2.5:7b | Extraction, improvement, formatting |
| Grader 1 | mistral:latest | Independent grading |
| Grader 2 | qwen2.5:7b | Second grading (same as writer) |

**Known issue:** Qwen grades its own work. Consider adding a third model for true independence.

### Key Tables

| Table | Purpose |
|-------|---------|
| `postings` | Job data (description, summary, skills, IHL score) |
| `interactions` | Individual LLM/script executions |
| `workflow_runs` | Execution state, heartbeat, progress |
| `conversations` | Step definitions (prompts, actors) |
| `workflow_conversations` | Step ordering, branching logic |

---

## Database Queries

### Current Progress
```sql
SELECT 
    COUNT(*) as total,
    COUNT(extracted_summary) as has_summary,
    COUNT(skill_keywords) as has_skills,
    COUNT(ihl_score) as has_ihl
FROM postings WHERE source = 'deutsche_bank';
```

### Interactions by Status
```sql
SELECT status, COUNT(*) 
FROM interactions 
WHERE conversation_id IN (
    SELECT conversation_id FROM workflow_conversations WHERE workflow_id = 3001
)
GROUP BY status;
```

### Failed Postings
```sql
SELECT p.posting_id, p.posting_name, c.conversation_name
FROM postings p
JOIN interactions i ON p.posting_id = i.posting_id
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.status = 'failed'
ORDER BY p.posting_id;
```

### IHL Score Distribution
```sql
SELECT ihl_score, COUNT(*) 
FROM postings 
WHERE ihl_score IS NOT NULL 
GROUP BY ihl_score 
ORDER BY ihl_score;
```

### Recent Activity (last hour)
```sql
SELECT 
    c.conversation_name,
    COUNT(*) FILTER (WHERE i.status = 'completed') as completed,
    COUNT(*) FILTER (WHERE i.status = 'pending') as pending
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.updated_at > NOW() - INTERVAL '1 hour'
GROUP BY c.conversation_name
ORDER BY completed DESC;
```

---

## Restart Checklist

Before restarting after a system shutdown:

- [ ] Reset stuck `running` interactions to `pending`
- [ ] Check workflow_runs status (reset `interrupted` to `running` if needed)
- [ ] Start new workflow run with `nohup ... &`
- [ ] Verify it's picking up pending work with `--once` dashboard check
- [ ] Monitor with flowchart dashboard

---

*Happy processing! 🚀*
