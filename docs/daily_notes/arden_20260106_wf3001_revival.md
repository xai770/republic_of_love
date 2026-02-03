# Arden Daily Note — January 6, 2026

**Session:** 07:43 - ongoing
**Focus:** WF3001 revival, architecture review, brainstorming next steps

---

## Summary

WF2020 (SECT Decomposer) passed RAQ and is running at scale 5. While it processes, we investigated why `extracted_summary` stopped populating. **Root cause found and fixed.**

---

## Completed ✅

### 1. WF3001 Revival
**Problem:** `extracted_summary` stopped being populated on Jan 1, 2026.

**Investigation:**
- Postings from Jan 1+ have `extracted_summary = NULL`
- Postings from Dec 31 and earlier have summaries
- WF3001 had `input_config = NULL` — daemon didn't know what to queue
- Last WF3001 runs were Dec 12, 2025 (manually triggered)

**Fix Applied:**
```sql
UPDATE workflows SET input_config = '{
  "subject_mappings": {
    "posting": {
      "table": "postings",
      "variables": {
        "posting_id": "posting_id",
        "job_title": "job_title",
        "job_description": "job_description"
      },
      "key_column": "posting_id"
    }
  }
}'::jsonb WHERE workflow_id = 3001;
```

**Backlog Queued:**
```sql
INSERT INTO queue (workflow_id, subject_type, subject_id, status, reason, priority)
SELECT 3001, 'posting', posting_id, 'pending', 'BACKLOG_20260106', 50
FROM postings 
WHERE extracted_summary IS NULL 
  AND job_description IS NOT NULL 
  AND enabled = true;
-- 50 postings queued
```

**Status:** WF3001 running (scale_limit=1), will process 50 backlogged postings.

---

## In Progress 🔄

### 2. WF2020 Production Run
- **Status:** Running at scale 10
- **Progress:** ~87% done (3313/3810 postings)
- **ETA:** ~8 hours (slower due to WF3001 sharing GPU)
- **Rate:** 1.0 postings/minute

### 3. WF3001 Processing
- **Status:** Running (scale_limit=1)
- **Queued:** 48 postings
- **Processing:** 2

---

## Issues Found & Fixed 🔧

### Daemon Stuck on posting_validator (09:20)
**Symptom:** GPU at 0%, daemon shows 5 processing, nothing progressing

**Investigation:**
- 5 WF2020 runs showed `status=running` but all interactions completed
- 1 WF3001 run had `posting_validator` hanging (makes HTTP requests to check URLs)
- Daemon blocked waiting for slow HTTP, couldn't advance WF2020 runs

**Fix:** Restart daemon, clean up stuck items
```bash
pkill -f turing_daemon
./scripts/q.sh "UPDATE workflow_runs SET status='failed' WHERE status='running'"
./scripts/q.sh "UPDATE interactions SET status='failed' WHERE status='running'"
nohup python3 scripts/turing_daemon.py > temp/daemon.log 2>&1 &
```

**Root Cause:** Reaper gap
- Interactions: reaped after `timeout_seconds` (default 300s)
- Workflow runs: reaped only if no `seed_interaction_id` for 5min OR running > 1hr
- Gap: runs with completed interactions but not marked done wait 1 hour

**TODO:** Add reaper check for "all interactions done but run still 'running'"

---

## TODO 📋

### Easy Stuff

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | ✅ Fix WF3001 input_config | Done | Was NULL, now has subject_mappings |
| 2 | ✅ Queue backlog postings | Done | 50 postings queued |
| 3 | ⬜ Integrate WF2020 into WF3001 | Not started | Replace conversations 14 & 15 |
| 4 | ⬜ RAQ test WF3001 after integration | Not started | After #3 |
| 5 | ⬜ Auto-queue new postings | Not started | Interrogator or cron should queue |

### Hard Stuff (Architecture)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6 | ⬜ Document workflow dev cycle | Not started | Gershon's brainstorm notes |
| 7 | ⬜ Update directives with lessons | Not started | SECT journey, model selection |
| 8 | ⬜ Mermaid flowcharts for all actors | Not started | "Without sketch, can't see design" |

### Completed During Session

| # | Task | Notes |
|---|------|-------|
| 9 | ✅ Replace posting_validator with nightly cron | `scripts/nightly_invalidate_stale.py` |
| 10 | ✅ Disable posting_validator in WF3001 | conversation_id 9247 disabled |
| 11 | ✅ Add cron job for stale invalidation | Runs 3am daily |
| 12 | ✅ Document heartbeat pattern in directives | "Absence Detection via Heartbeat" |

---

## WF3001 ↔ WF2020 Integration Plan

Current WF3001 flow:
```
... → Save Summary → [14] Hybrid Skills Extraction → [15] Save Posting Skills → IHL Analyst → ...
```

After integration:
```
... → Save Summary → [TRIGGER WF2020] → IHL Analyst → ...
```

**Options:**
1. **Sub-workflow call:** WF3001 triggers WF2020 as sub-workflow
2. **Dependency chain:** WF3001 saves summary, queues posting for WF2020, WF2020 completion queues for IHL
3. **Merge:** Copy WF2020 actor into WF3001 as conversation 14

Recommend **Option 3** (merge) — keeps WF3001 self-contained, easier to RAQ test.

---

## Gershon's Architecture Brainstorm

*(Captured from session for later processing)*

### The Story So Far
1. Scripts grew complex → confusion, parallel code paths
2. Documentation helped but has memory limits
3. **Schema = breakthrough** — anchors the code, guardrails + structure
4. **Workflow docs via tool** — `_document_workflow.py` generates MD with mermaid
5. **Workflow dev cycle:**
   - Build thick actor (prompts in instructions, calls in interactions)
   - Use `raq.py` to test
   - Monitor continuously, stop on bugs, fix root cause
   - Write to Sandy if hairy

### 100% Repeatability Recipe
- Local models are smart — talk to them!
- If model doesn't deliver, use `llm_chat` to debug
- Make it easy for models:
  - Don't ask "is this S, E, C, or T?" — extract ALL dimensions
  - Ask for reflection: "I decided A is B because C, D, E"
  - Use Navigator pattern for data access
  - Script actors check output, ask for fixes
  - Tutor-pupil pattern (3 strikes → escalate)
  - Two graders
  - Short prompts = cleaner JSON
  - Be down to earth: "In a job interview, how would you prove this?"
  - Always ask for confidence rating
  - Always give escape hatch: "_NeedsReview_" folder

### Turing Sketch
> "When you look at a design sketch for a plane in the twenties, you can see the elegance. When you look at the finished plane, not so much."

Core abstractions:
- **Instructions:** templates with actors and inputs
- **Interactions:** stored results of instruction runs
- **Instruction steps:** what follows what (branching)
- **Conversations:** instructions in continuous sessions
- **Workflows:** collections of conversations
- **Entities + entity_names:** global taxonomy (skills, users, orgs, geo...)

---

## Questions for Later

1. **Auto-queue mechanism:** Should interrogator queue new postings, or should we have a cron job?
2. **WF2020 as sub-workflow vs merge:** Tradeoffs?
3. **Mermaid in actors:** Store flowchart in actor file or generate from DB?

---

## Commands Reference

```bash
# Monitor all workflows
python3 scripts/turing.py --status

# Live dashboard
python3 scripts/turing.py --watch

# Check WF3001 specifically
./scripts/q.sh "SELECT workflow_id, status, COUNT(*) FROM queue WHERE workflow_id = 3001 GROUP BY 1,2"

# Check summaries being populated
./scripts/q.sh "SELECT first_seen_at::date, COUNT(*), COUNT(extracted_summary) FROM postings GROUP BY 1 ORDER BY 1 DESC LIMIT 10"
```

---

ℵ
