# Turing Daemon - Morning Debug Session
**Date:** December 14, 2025  
**Author:** Copilot (with xai)  
**For:** Sandy

---

## What Happened

Started the morning with Turing dashboard showing stuck status (🟡 WARN, 0/hr rate). Investigation revealed a cascade of issues that required manual intervention.

### Issues Found

1. **462 interrupted workflows** - When the daemon was killed/restarted previously, it marked all running workflows as "interrupted". The system doesn't auto-resume these, so they just sit there blocking progress.

2. **Stuck interactions not being reaped** - Found a mistral:latest interaction running for 25+ minutes with no heartbeat. The reaper is supposed to catch these at 2 minutes, but it wasn't working.

3. **max_interactions=50 bottleneck** - The daemon was limiting each cycle to 50 interactions. With 226 pending across 3 models, this meant serial processing and slow throughput.

4. **Stale heartbeat display** - Dashboard showed interactions running for "50s" when they were actually 25 minutes old. Makes debugging harder.

### Manual Fixes Applied

```sql
-- Resumed interrupted workflows (had to do this TWICE after daemon restart)
UPDATE workflow_runs SET status = 'running' WHERE status = 'interrupted' AND workflow_id = 3005;

-- Manually failed stuck interactions
UPDATE interactions SET status = 'failed', failure_type = 'timeout_reaped' WHERE interaction_id IN (106785, 106851);
```

```python
# Removed max_interactions limit in turing_daemon.py
result = runner.run()  # Was: runner.run(max_interactions=50)
```

---

## The Real Problem

We're babysitting the daemon instead of the daemon babysitting itself.

Every time we restart, we have to:
1. Manually resume interrupted workflows
2. Watch for stuck interactions
3. Hope the reaper actually works

This isn't sustainable.

---

## Suggested Improvements

### 1. Auto-resume on startup (High Priority)
When daemon starts, automatically resume any interrupted workflows:

```python
def _resume_interrupted_workflows(self):
    """Resume workflows interrupted by previous shutdown."""
    cursor = self.conn.cursor()
    cursor.execute("""
        UPDATE workflow_runs 
        SET status = 'running', updated_at = NOW()
        WHERE status = 'interrupted'
        RETURNING workflow_run_id
    """)
    resumed = cursor.fetchall()
    self.conn.commit()
    if resumed:
        self.logger.info(f"✅ Auto-resumed {len(resumed)} interrupted workflows")
```

### 2. Fix the reaper
The reaper query looks correct but isn't catching stuck interactions. Need to investigate:
- Is it actually being called every 60s?
- Is there a transaction isolation issue?
- Add logging when it runs (even if it finds nothing)

### 3. Graceful shutdown
Instead of marking everything as "interrupted" on SIGTERM, consider:
- Only mark workflows that were mid-interaction
- Or just don't mark anything (let the reaper handle stale work on next startup)

### 4. Parallel model execution
Currently processes one model batch at a time. Could run mistral and gemma3 in parallel since they're independent.

---

## Current Status

After fixes:
- Throughput: ~228/hr (up from 0/hr)
- Skills: 5,531 done (66%), 2,713 pending
- ETA: ~Dec 16

System is running but will need manual intervention again if daemon restarts.

---

## Questions for Sandy

1. Is there a reason we mark workflows as "interrupted" on shutdown? Could we just let them resume naturally?

2. The reaper has a 2-minute threshold. Should we lower this? 2 minutes feels long for an LLM call.

3. Any concerns with removing the max_interactions limit? It was causing serialization but maybe it existed for a reason?

4. Want me to implement the auto-resume fix? It's ~10 lines and would save us a lot of grief.

---

Let me know your thoughts. Happy to pair on any of this.

---

## Sandy's Response

**1. Why mark as "interrupted" on shutdown?**

Honestly, it's defensive coding that's become a liability. The original intent was "track unclean shutdowns so we can audit them" but in practice it just creates manual work. **Yes, let's change it** - on graceful shutdown (SIGTERM), don't mark anything. The reaper will clean up any genuinely stuck work on restart. For SIGKILL... well, we can't do anything there anyway.

**2. Reaper threshold at 2 minutes?**

2 minutes is fine for the threshold - most LLM calls finish in 30-60s, so 2 minutes catches the stuck ones without false positives. The real problem is **the reaper isn't running at all** or its query is wrong. Add some logging to confirm it's firing every 60s. I'd bet the issue is transaction isolation - if it's using the same connection without committing, it might be seeing stale data.

**3. Removing max_interactions limit?**

Fine to remove. It was originally there to prevent infinite loops during development, but with the cycle-based architecture it's just a bottleneck now. The natural throttle is the poll interval + batch sizes.

**4. Auto-resume fix?**

**Yes, please implement it.** That's exactly the kind of "make the daemon babysit itself" improvement we need. Call it at the start of `run()`, right after acquiring the lock.

---

**One more suggestion:** While you're in there, add a startup log line showing the state it found:

```python
self.logger.info(f"Startup: {n_interrupted} interrupted workflows, {n_pending} pending interactions")
```

Helps us know if we're starting clean or inheriting mess.

Let me know when you've got a PR ready or just push it - these are all safe improvements. ℶ

---

## Sandy's Deep Dive: Latency Analysis & Architecture Review

*December 14, 2025*

### Latency Analysis (7-day window)

Ran analysis on completed interactions with proper `started_at`/`completed_at` timestamps:

**By Actor Type:**
| Type | Count | p50 | p95 | p99 |
|------|------:|----:|----:|----:|
| AI Model | 16,134 | 12.0s | 48.8s | **229.6s** |
| Script | 8,409 | 0.1s | 0.2s | 0.3s |

**Top Latency Conversations:**
| Conversation | Actor | n | p50 | p95 | p99 | max |
|--------------|-------|--:|----:|----:|----:|----:|
| gemma3_extract | qwen2.5:7b | 1,299 | 7.7s | **414s** | 551s | 600s |
| fetch_db_jobs | db_job_fetcher | 12 | 8.3s | 216s | 218s | 218s |
| w3005_c4_skeptic | mistral:latest | 332 | 20.9s | 77.9s | 129s | 405s |
| w1124_c2_skeptic | mistral:latest | 1,557 | 29.5s | 52.7s | 64s | 597s |
| gopher_skill_extraction | qwen2.5:7b | 2,091 | 19.5s | 48s | 59s | 95s |

**The Problem:**
- A global 120-second reaper threshold catches 95% of legit completions as "stuck"
- `gemma3_extract` legitimately takes 5-10 minutes sometimes (Dec 9 had 15 runs >500s)
- Meanwhile, scripts that should complete in 0.2s are given 120s of grace

### Recommendation: Per-Conversation Timeout Thresholds

Add a `timeout_seconds` column to `conversations`:

```sql
ALTER TABLE conversations ADD COLUMN timeout_seconds INTEGER DEFAULT 300;
COMMENT ON COLUMN conversations.timeout_seconds IS 
    'Reaper threshold. NULL = use p99 * 2 from last 7 days.';

-- Set based on actual data:
UPDATE conversations SET timeout_seconds = 30 WHERE canonical_name IN (
    'format_standardization', 'save_summary_check_ihl', 'postingskill_save'
);
UPDATE conversations SET timeout_seconds = 120 WHERE canonical_name IN (
    'w1124_c1_analyst', 'w1124_c3_expert', 'gopher_skill_extraction'
);
UPDATE conversations SET timeout_seconds = 600 WHERE canonical_name IN (
    'gemma3_extract', 'fetch_db_jobs'
);
```

Then modify the reaper to use per-conversation thresholds:

```python
def _reap_stuck_interactions(self):
    cursor.execute("""
        UPDATE interactions i
        SET status = 'failed',
            failure_type = 'timeout_reaped',
            error_message = format('Auto-reset: exceeded %ss threshold', c.timeout_seconds),
            completed_at = NOW()
        FROM conversations c
        WHERE i.conversation_id = c.conversation_id
          AND i.status = 'running'
          AND i.heartbeat_at < NOW() - (c.timeout_seconds || ' seconds')::interval
        RETURNING i.interaction_id, c.canonical_name
    """)
```

---

### Architecture Review: Scholar's Cap On 🎓

**Overall Grade: B-** (Good bones, some growing pains)

#### What's Good ✅

1. **Interactions as Audit Log** - The append-only design is correct. Every LLM call is traceable. This is the right foundation.

2. **Workflow Abstraction** - `workflow_runs` + `conversations` lets you compose pipelines declaratively. The routing via `canonical_name` is elegant.

3. **Wave Batching** - Grouping by actor for batch execution is smart. Reduces model load/unload overhead significantly.

4. **Schema Comments** - The schema is self-documenting. This is rare and valuable.

#### What's Problematic ⚠️

1. **Three Competing Job Concepts**
   - `queue` table - Old batch mode, posting-centric
   - `workflow_runs` - New orchestration layer
   - `interactions.status='pending'` - The actual work queue
   
   The daemon has to juggle all three. This causes the "interrupted" vs "running" confusion.

2. **No Separation of Work Queue from Audit Log**
   
   `interactions` is both "what happened" AND "what to do next". This violates single-responsibility:
   - Reprocessing requires UPDATE (invalidation cascades)
   - Monitoring requires scanning the whole table
   - Retries are awkward (`retry_count` on audit records?)
   
   **Recommendation:** The Pipeline V2 proposal is right. Add a dedicated `job_queue` for "what to do next". Interactions stay append-only.

3. **Workflow State is Scattered**
   
   To know if a workflow is "done", you must:
   - Check `workflow_runs.status`
   - Scan all child interactions for `status='pending'`
   - Verify no `running` interactions are stuck
   
   **Recommendation:** Add a `workflow_runs.pending_interactions_count` counter (trigger-maintained). When it hits 0, workflow is done.

4. **Heartbeat Isn't Updating**
   
   The reaper relies on `heartbeat_at`, but looking at the stuck interactions, `heartbeat_at` was either NULL or stale. The wave_runner may not be updating heartbeats during long-running calls.
   
   **Quick Fix:** Update heartbeat at start of execution AND every N seconds during the call (use a background thread).

5. **No Conversation-Level Metrics**
   
   We had to run ad-hoc queries to get latency percentiles. This should be:
   - Computed daily (cron)
   - Stored in a `conversation_metrics` table
   - Used by reaper for adaptive thresholds

#### Design Debt 🔧

| Issue | Impact | Fix Effort |
|-------|--------|------------|
| Three job queues | Confusion, manual intervention | High (Pipeline V2) |
| Missing heartbeat updates | Reaper kills healthy work | Low (add thread) |
| Global reaper threshold | Over-aggressive | Medium (per-conversation) |
| No pending counter on workflow_runs | Expensive completion checks | Low (add trigger) |
| Interrupted status on shutdown | Manual resume required | Low (just remove it) |

---

### Priority Recommendations for Arden

**Phase 1:** ✅ IMPLEMENTED (Dec 14, 08:32)
1. ✅ Auto-resume interrupted workflows on startup
2. ✅ Add logging to reaper ("Reaper ran, found N stuck")  
3. ✅ Remove the "mark as interrupted" on shutdown
4. ✅ Add startup state log line

**Changes made:**
- [scripts/turing_daemon.py](../scripts/turing_daemon.py): Added `_resume_interrupted_workflows()` and `_log_startup_state()` methods
- [core/wave_runner/runner.py](../core/wave_runner/runner.py): Removed `_mark_workflows_interrupted()` call from signal handler

**First startup with fixes:**
```
TURING DAEMON STARTED
  Reaper interval: 60s
  Stuck threshold: 120s
📊 STARTUP STATE:
   Workflow runs: {'failed': 198, 'completed': 710, 'interrupted': 469}
   Interactions:  {'failed': 1699, 'completed': 47999, 'pending': 225, 'running': 3}
   Queue:         {'completed': 286}
✅ Auto-resumed 469 interrupted workflow(s)
🔪 Reaped 2 stuck interactions: [106979, 107249]
```

**Phase 2:** ✅ IMPLEMENTED (Dec 14, 08:57)
1. ✅ Add `timeout_seconds` to conversations table
2. ✅ Fix heartbeat updates in wave_runner (`claim_interaction` now sets `heartbeat_at`)
3. ✅ Update reaper to use per-conversation timeouts

**Changes made:**
- [migrations/028_per_conversation_timeouts.sql](../migrations/028_per_conversation_timeouts.sql): Added timeout_seconds column, set values based on latency analysis
- [core/wave_runner/database.py](../core/wave_runner/database.py): `claim_interaction()` now sets `heartbeat_at = NOW()`
- [scripts/turing_daemon.py](../scripts/turing_daemon.py): Reaper now uses per-conversation `timeout_seconds` with detailed logging

**Timeout tiers set:**
- 30s: Fast scripts (`format_standardization`, `save_summary_check_ihl`)
- 120s: Normal LLM tasks (`w*_c*_analyst`, `*skeptic`, etc.)
- 600s: Slow extraction (`gemma3_extract`, `fetch_db_jobs`)
- Auto-adjusted: 8 conversations updated based on actual p99 latency data

**Phase 3:** ✅ IMPLEMENTED (Dec 14, 09:05)
1. ✅ Add `pending_count` column to workflow_runs (trigger-maintained)
2. ✅ Create `conversation_metrics` table with daily latency stats
3. ✅ Pipeline V2 tables already exist (`queue`, `runs`, `interactions.run_id`)

**Changes made:**
- [migrations/029_workflow_pending_count.sql](../migrations/029_workflow_pending_count.sql): Added trigger-maintained `pending_count` column
- [migrations/030_conversation_metrics.sql](../migrations/030_conversation_metrics.sql): Created metrics table, `compute_conversation_metrics()` function, and `v_timeout_recommendations` view

**New capabilities:**
- `workflow_runs.pending_count` - Fast completion check (when 0, workflow is done)
- `conversation_metrics` - Daily latency percentiles (p50, p95, p99)
- `v_timeout_recommendations` - Shows conversations where timeout needs adjustment
- `compute_conversation_metrics(date)` - Run via cron for daily stats

---

### One-Liner Summary

> The system works, but it's fighting itself: three job queues, no per-conversation timeouts, and a reaper that can't tell "slow" from "stuck". The fixes are straightforward - just need dedicated time.

ℶ

---

## Sandy's Review of Arden's Implementation

*December 14, 2025 ~09:15*

Excellent work, Arden! All three phases done in under an hour.

**Summary:**

| Phase | Items | Status |
|-------|-------|--------|
| Phase 1 | Auto-resume, reaper logging, remove interrupted marking | ✅ 08:32 |
| Phase 2 | Per-conversation timeouts, heartbeat fix | ✅ 08:57 |
| Phase 3 | pending_count trigger, conversation_metrics table | ✅ 09:05 |

The startup log showing 469 interrupted workflows auto-resumed and 2 stuck interactions reaped immediately - that's exactly what we wanted. No more manual intervention on restart.

**Key wins:**
- Reaper now uses actual latency data (30s for scripts, 600s for gemma3_extract)
- `workflow_runs.pending_count` makes completion checks O(1) instead of scanning
- `conversation_metrics` table + cron = adaptive thresholds over time
- `v_timeout_recommendations` view is clever - surfaces configs that need adjustment

**One question:** Did you run the initial `compute_conversation_metrics(CURRENT_DATE)` to seed the metrics table? If not, might want to backfill a week or so:

```sql
SELECT compute_conversation_metrics(d::date) 
FROM generate_series(CURRENT_DATE - 7, CURRENT_DATE, '1 day'::interval) d;
```

Otherwise this is solid. The daemon can babysit itself now. ℶ

---

## Afternoon Session: Monitoring & Pipeline Drain

*December 14, 2025 ~10:30 - 15:15*

### New Issue Discovered: Reaper Thread Architecture

**Problem:** Despite all the Phase 1-3 fixes, we found a qwen2.5:7b interaction stuck for 11+ minutes (694s) - the reaper wasn't catching it.

**Root Cause:** The reaper ran in the main daemon loop:
```python
while running:
    self._reap_stuck_interactions()  # This runs...
    self._claim_queue_batch()        # Then this...
    self._run_interactions()         # But THIS BLOCKS waiting for Ollama!
```

When WaveRunner calls Ollama and waits for a response, the entire main loop is blocked. The reaper never gets another chance to run until that interaction completes.

**Fix Implemented:** Moved reaper to a **separate background thread** with its own database connection:

```python
def run(self):
    # Start reaper in background thread
    self._reaper_thread = threading.Thread(target=self._reaper_loop, daemon=True)
    self._reaper_thread.start()
    # ... main loop continues independently

def _reaper_loop(self):
    """Background thread that runs reaper independently of main loop."""
    reaper_conn = psycopg2.connect(...)  # Own connection!
    while self._running:
        self._reap_stuck_interactions_with_conn(reaper_conn)
        time.sleep(60)
```

**Result:** Reaper now runs every 60 seconds regardless of whether WaveRunner is blocked.

---

### Model Performance Analysis

Investigated model failure rates to optimize throughput:

| Model | Total | Failed | Fail Rate |
|-------|------:|-------:|----------:|
| qwen2.5:7b | 23,090 | 559 | **2.4%** |
| gemma3:4b | 6,381 | 99 | **1.5%** |
| mistral:latest | 6,937 | 521 | **7.5%** ⚠️ |

**Action:** Swapped mistral:latest → qwen2.5:7b for `w3005_c3_grade` and `w3005_c4_skeptic` conversations:

```sql
UPDATE conversations SET actor_id = (SELECT actor_id FROM actors WHERE actor_name = 'qwen2.5:7b')
WHERE canonical_name IN ('w3005_c3_grade', 'w3005_c4_skeptic');
-- Also updated 69 pending interactions to use new actor
```

---

### Dashboard Improvements

1. **Fixed negative timer display** - `fmt_duration()` now uses `abs()` and shows `!` warning when over expected time
2. **Increased refresh interval** - Changed from 30s to 600s (10 min) for long monitoring sessions

---

### Pipeline Drain Results

| Time | Done | Pending | Rate | Status |
|------|-----:|--------:|-----:|--------|
| 10:53 | 4,575 | 154 | 84/hr | Starting |
| 11:26 | 4,625 | 154 | 89/hr | Warming up |
| 12:16 | 4,765 | 154 | 229/hr | Full speed |
| 13:33 | 5,022 | 87 | 405/hr | 🚀 |
| 14:13 | 5,093 | 88 | 476/hr | Peak |
| 14:47 | 5,307 | 1 | — | **⚪ DONE** |

**Total:** ~730 interactions processed in ~4 hours

**Final State:**
- Interactions: 5,307 completed, 1 pending, 0 running
- Skills: 5,531 done (66%), 157 processing, 2,713 pending

---

### Why Isn't It Fully Done?

The 1 remaining pending interaction is blocked:

```sql
SELECT interaction_id, instruction_name, status, parent_interaction_id, 
       (SELECT status FROM interactions WHERE interaction_id = parent_interaction_id) as parent_status
FROM interactions WHERE status = 'pending';

-- Result:
-- 103353 | w3005_grade_classifications | pending | 103266 | failed
```

Parent interaction 103266 (`w3005_classify_orphans`) was **reaped as stuck** after 20+ minutes. The child can't run because its parent failed.

The remaining 2,713 skills are in `entities_pending` - they haven't had workflow runs created yet because the workflow orchestrator needs the current batch to complete first.

---

## Questions for Sandy

1. **Stuck parent blocking child** - What's the right recovery path? Options:
   - Retry the failed parent (reset to pending)?
   - Invalidate the child and let workflow retry from scratch?
   - Manual intervention on the specific skill?

2. **Connection pool exhausted** - Saw this error in logs around 14:47:
   ```
   psycopg2.pool.PoolError: connection pool exhausted
   ```
   Is the reaper thread's dedicated connection contributing to pool pressure? Should we increase pool size?

3. **Skills stuck at 66%** - The 2,713 pending skills aren't progressing because no new workflow runs are being created. Is there a trigger that kicks off new batches? Or does something need to be restarted?

4. **GPU utilization cliff** - Watched GPU go from 100% sustained to 0% instantly when pipeline drained. Is there monitoring/alerting for this state change?

---

## Summary of All Changes Today

| Change | File | Impact |
|--------|------|--------|
| Threaded reaper | turing_daemon.py | Reaper runs independently of WaveRunner |
| Model swap (mistral→qwen) | conversations table | Reduced fail rate for grade/skeptic |
| Timer display fix | turing.py | No more negative times, `!` warning |
| 10-min refresh | turing.py | Better for long monitoring sessions |
| Auto-resume (earlier) | turing_daemon.py | No manual resume on restart |
| Per-conversation timeouts | conversations table | Adaptive reaping thresholds |
| Heartbeat on claim | wave_runner/database.py | Reaper sees fresh timestamps |
| pending_count trigger | workflow_runs table | O(1) completion checks |
| conversation_metrics | New table + cron | Historical latency data |

**Net result:** Daemon went from "needs constant babysitting" to "mostly self-healing". The remaining issue is workflow orchestration for new batches.

---

Looking forward to your thoughts, Sandy! 🐕

---

## Sandy's Response to Afternoon Session

*December 14, 2025 ~15:30*

The threaded reaper was the right call. Classic "everything runs in one loop" problem - glad you caught it.

**Answers:**

**1. Stuck parent blocking child**

Retry the failed parent. Don't invalidate - you'd lose the audit trail. Quick fix:

```sql
-- Reset the failed parent to pending for retry
UPDATE interactions 
SET status = 'pending', 
    retry_count = retry_count + 1,
    failure_type = NULL,
    error_message = NULL
WHERE interaction_id = 103266
  AND retry_count < max_retries;
```

If it keeps failing, *then* investigate why that specific classification is taking 20+ minutes. But first retry is free.

**2. Connection pool exhausted**

Yes, the reaper thread's dedicated connection adds pressure, but that's not the real issue. The real issue is likely:
- WaveRunner holding connections during long Ollama calls
- Multiple concurrent workflow runs each holding connections

**Fix:** Either increase pool size (`maxconn=20` → `30`) OR make WaveRunner release connections during the Ollama wait (harder but better). For now, just bump the pool.

**3. Skills stuck at 66%**

The workflow orchestrator (WF3005) processes in batches. When one batch completes, it should automatically fetch the next 25 orphan skills. If it's not:
- Check if `entity_orphan_fetcher` is enabled
- Check if there's a stuck/failed "fetch" interaction blocking the next batch
- Run `_show_3005.py` to see the workflow state

Quick check:
```sql
SELECT canonical_name, status, COUNT(*) 
FROM interactions 
WHERE workflow_run_id IN (SELECT workflow_run_id FROM workflow_runs WHERE workflow_id = 3005 AND status = 'running')
GROUP BY 1, 2 ORDER BY 1;
```

If nothing is running, you may need to manually trigger a new batch:
```bash
python3 scripts/prod/run_workflow_3005.py --max-iterations 100
```

**4. GPU utilization cliff**

Good observation. This is a "pipeline starvation" signal - all work drained but no new work was queued. Options:
- Add a "queue low" warning to the dashboard when pending < 10
- Have the daemon auto-trigger new batches when queue empties (risky - could loop forever on errors)
- For now: just restart the workflow script when you see 0% GPU

**Meta-observation:** The 7.5% fail rate on mistral:latest is high. Good call swapping to qwen. Worth investigating *why* mistral is failing - could be a prompt length issue, context window overflow, or just model instability.

---

**Status:** The daemon is now self-healing for the cases it can handle. The remaining manual interventions are:
1. Retry failed parents blocking children (could automate this)
2. Kick off new workflow batches when queue drains (needs design thought)

Both are solvable but require decisions about retry limits and infinite loop prevention.

Good day's work, Arden. The system is measurably better than this morning. ℶ

---

## Evening Session: The Deeper Problem

*December 14, 2025 ~18:30*

### What We Observed

After implementing all the "fixes" above, we ran extended monitoring and found:

1. **ETA stuck at 44 minutes** - Despite appearing to run, progress stalled
2. **Throughput dropped to ~1 interaction/min** (was 4-5/min earlier)
3. **Corrupted interaction data:**
   - `interaction_id=108713`: `status='running'`, but `completed_at` timestamp was BEFORE `started_at`
   - `interaction_id=108709`: `status='pending'` with `completed_at` already set
4. **Daemon stuck in limbo** - Logs showed "waiting for interaction (142s)" but DB showed 0 running interactions
5. **Reaper killing interactions** but daemon still waiting for Ollama response

### Root Cause Analysis

The fundamental problem is: **Synchronous execution with asynchronous cleanup**

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RACE CONDITION                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Main Thread                      Reaper Thread                     │
│  ───────────                      ─────────────                     │
│                                                                     │
│  1. Claim interaction #108713     │                                 │
│     SET status='running'          │                                 │
│                                   │                                 │
│  2. Call Ollama API               │                                 │
│     (BLOCKING - takes 130s)       │                                 │
│                                   │ 3. Check for stuck (120s limit) │
│                                   │    UPDATE status='failed'       │
│                                   │    SET completed_at=NOW()       │
│                                   │                                 │
│  4. Ollama returns!               │                                 │
│     Try to save result...         │                                 │
│     But interaction is 'failed'!  │                                 │
│                                   │                                 │
│  5. ??? What now ???              │                                 │
│     - Overwrite status?           │                                 │
│     - Discard result?             │                                 │
│     - Daemon gets confused        │                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

The WaveRunner is **synchronous** - it calls Ollama and **blocks** until completion. Meanwhile, the reaper thread (which we added to "fix" the stuck interaction problem) can mark that same interaction as failed. When Ollama finally returns, the daemon has no idea what to do.

**Result:** Data corruption, daemon stuck in weird states, need manual intervention.

### Why Our Fixes Made It Worse

| "Fix" | Intended Effect | Actual Effect |
|-------|-----------------|---------------|
| Threaded reaper | Reap stuck interactions even when daemon blocked | Creates race condition with main thread |
| Threaded heartbeat | Keep heartbeat fresh during long calls | Masks the real problem (interaction appears healthy) |
| Per-conversation timeouts | Let slow conversations run longer | Delays the inevitable race condition |
| Auto-complete workflows | Mark workflows done when interactions complete | Fine, but doesn't help the core issue |

We've been treating symptoms, not the disease.

### The Disease: Blocking I/O in a State Machine

The daemon tries to be two things at once:
1. **State machine coordinator** - manage interaction lifecycle
2. **Execution engine** - actually run the LLM calls

These are fundamentally incompatible when execution is blocking.

### Proposed Solutions

**Option A: Subprocess Execution (Recommended)**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Daemon (Coordinator)              │  Workers (Executors)           │
│  ─────────────────────            │  ──────────────────             │
│                                   │                                 │
│  - Monitors workflow state        │  - Spawned as subprocesses      │
│  - Claims pending interactions    │  - Each handles ONE interaction │
│  - Spawns worker processes        │  - Writes result directly to DB │
│  - Reaps stuck workers (SIGKILL)  │  - Exit when done               │
│  - Never blocks                   │                                 │
│                                   │                                 │
│  Reaping is SAFE because:         │  No race condition because:     │
│  - Worker is separate process     │  - Worker owns its DB row       │
│  - SIGKILL actually stops work    │  - If killed, it can't corrupt  │
└─────────────────────────────────────────────────────────────────────┘
```

**Option B: Async Execution (harder)**
Use `asyncio` and non-blocking Ollama client. Daemon never waits, just polls for completion.

**Option C: Check-Before-Save (band-aid)**
Before saving Ollama result, check if interaction was reaped:
```python
def save_result(interaction_id, result):
    cursor.execute("""
        UPDATE interactions 
        SET output = %s, status = 'completed', completed_at = NOW()
        WHERE interaction_id = %s 
          AND status = 'running'  -- Only if still running!
        RETURNING interaction_id
    """, (result, interaction_id))
    if cursor.fetchone() is None:
        logger.warning(f"Interaction {interaction_id} was reaped while we were processing")
        return False  # Discard result, don't corrupt
    return True
```

**Option D: Remove Threaded Reaper (simplest)**
Go back to reaper running in main loop. Accept that:
- If an Ollama call takes 10 minutes, the reaper won't run for 10 minutes
- Stuck interactions require manual intervention
- But at least no race conditions

### Recommendation

**Immediate (today):** Option D - Remove threaded reaper, go back to simple synchronous loop.
- Removes race condition entirely
- We already have per-conversation timeouts
- Manual reaping is annoying but safe

**This week:** Option C - Add check-before-save as defensive code.
- Prevents corruption even if we re-add threading later
- Simple change, low risk

**Next sprint:** Option A - Subprocess workers.
- Proper separation of concerns
- Natural parallelism
- Proper resource isolation
- But requires more design work

### Questions for Sandy

1. **Am I reading this right?** Is the race condition between reaper and WaveRunner the root cause of the corruption?

2. **Check-before-save:** Any risk in discarding Ollama results when the interaction was reaped? We'd lose 2+ minutes of GPU work, but at least we don't corrupt.

3. **Subprocess approach:** Worth the complexity? Or should we keep it simple with synchronous execution?

4. **Why haven't we hit this before?** The threaded reaper is new (added today). Before that, the reaper only ran when the main loop wasn't blocked on Ollama. So the race condition couldn't happen.

---

*Daemon is currently OFF. Awaiting architectural decision before restarting.*

---

## Sandy's Response: You Nailed It

*December 14, 2025 ~19:00*

Yes. You're reading it exactly right.

### Answers

**1. Is the race condition the root cause?**

Yes. 100%. The threaded reaper + synchronous Ollama calls = classic TOCTOU (Time-Of-Check-Time-Of-Use) race. The reaper checks "is this stuck?", marks it failed, and the main thread has no idea. When Ollama returns, chaos.

The corrupted timestamps (completed_at before started_at) are the smoking gun - that can *only* happen if two threads are fighting over the same row.

**2. Check-before-save risk?**

Zero risk. If the interaction was reaped, the work is already "lost" from the system's perspective. Discarding the result just prevents corruption. Yes, you lose 2 minutes of GPU work, but:
- The interaction will retry (if retry_count < max_retries)
- Retry will likely succeed (since Ollama *did* eventually return)
- Better to lose work than corrupt state

**3. Subprocess approach worth it?**

**Yes, but not this week.** It's the right architecture:
- Coordinator never blocks
- Workers are killable without corruption
- Natural parallelism (run 4 workers, use 4 GPUs)
- Process isolation prevents memory leaks from accumulating

But it's a bigger refactor. For now, go simple.

**4. Why haven't we hit this before?**

Exactly right - the threaded reaper is new (today!). Before that, the reaper ran in the main loop, which only executes between Ollama calls. No concurrency = no race condition.

We "fixed" the reaper not running... by introducing a worse bug. Classic.

### Decision: Option D + C

**Immediate action:**
1. Remove the threaded reaper (go back to main-loop reaper)
2. Add check-before-save as defensive code anyway

**Why both?** Option D removes the race condition. Option C makes the system robust even if someone re-adds threading later without understanding the history.

**Code for check-before-save:**

```python
def complete_interaction(self, interaction_id: int, output: dict) -> bool:
    """
    Save interaction result. Returns False if interaction was reaped.
    
    Uses optimistic locking: only updates if status='running'.
    If another thread/process changed the status, we detect it.
    """
    cursor = self.conn.cursor()
    cursor.execute("""
        UPDATE interactions 
        SET output = %s, 
            status = 'completed', 
            completed_at = NOW()
        WHERE interaction_id = %s 
          AND status = 'running'
        RETURNING interaction_id
    """, (Json(output), interaction_id))
    
    updated = cursor.fetchone()
    self.conn.commit()
    
    if updated is None:
        # Interaction was reaped or already completed by another process
        self.logger.warning(
            f"Interaction {interaction_id} was modified while processing. "
            f"Result discarded to prevent corruption."
        )
        return False
    return True
```

### For the subprocess approach (future)

When you're ready, here's the sketch:

```python
# worker.py - Runs as subprocess
import sys
interaction_id = int(sys.argv[1])
conn = connect_db()

# Claim and execute
interaction = claim_interaction(conn, interaction_id)
result = call_ollama(interaction.input)
save_result(conn, interaction_id, result)
sys.exit(0)

# daemon.py - Coordinator
def process_pending():
    for interaction in get_pending_interactions():
        proc = subprocess.Popen(['python', 'worker.py', str(interaction.id)])
        self.workers[interaction.id] = proc

def reap_stuck():
    for interaction_id, proc in self.workers.items():
        if is_stuck(interaction_id):
            proc.kill()  # Safe! Worker can't corrupt after death
            mark_failed(interaction_id, 'timeout_reaped')
```

The key insight: `proc.kill()` actually stops the work. Unlike killing a thread (which you can't do in Python), killing a process is atomic and leaves no zombie state.

### Summary

Today was a great learning day:
- Morning: Fixed auto-resume, per-conversation timeouts ✅
- Afternoon: Added threaded reaper (oops)
- Evening: Discovered why that was wrong, understood the architecture better

You went from "why doesn't the reaper run?" to "oh, the reaper and the executor are fundamentally incompatible when sharing threads" in one day. That's real engineering.

**Action items:**
1. Revert to main-loop reaper
2. Add check-before-save
3. Restart daemon
4. Put subprocess architecture on the backlog

Let me know when you're back online. ℶ

---

## Verification: Sandy Was Right (Mostly)

*December 14, 2025 ~19:30*

### Double-Checking the Analysis

Reviewed the code to verify Sandy's race condition claim.

**Found in `core/wave_runner/database.py` line 215-223:**
```python
def update_interaction_success(self, interaction_id: int, output: Dict):
    cursor.execute("""
        UPDATE interactions
        SET status = 'completed',
            output = %s,
            completed_at = NOW(),
            updated_at = NOW()
        WHERE interaction_id = %s  -- NO STATUS CHECK!
    """, (Json(output), interaction_id))
```

**Confirmed:** No optimistic locking. If reaper marks interaction as `failed`, main thread will blindly overwrite with `completed`.

### What About the "completed_at < started_at" Corruption?

That specific corruption was actually caused by **my manual intervention**:
1. Reaper set `completed_at = NOW()` when killing stuck interaction
2. I manually ran `UPDATE interactions SET status='pending', started_at=NULL...` but didn't clear `completed_at`
3. Daemon re-claimed, setting `started_at = NOW()` (later than old `completed_at`)
4. Result: `completed_at < started_at`

So that specific bug was user error (mine), not the race condition.

### But Sandy's Core Point Is Still Valid

The race condition **does exist** and causes:
1. **Audit trail corruption** - interaction shows "failed" then "completed"
2. **Lost work tracking** - reaper thinks it killed something that actually succeeded
3. **Potential duplicates** - if retry logic triggers between reaper and completion

**Code path:**
```
Main Thread                     Reaper Thread
-----------                     -------------
claim_interaction()
  status = 'running'
_execute_ai_model()             
  [blocking 130s...]            _reap_stuck_interactions()
                                  status = 'failed', completed_at = NOW()
[ollama returns]
update_interaction_success()
  status = 'completed'  ← OVERWRITES 'failed'
```

### Conclusion

Sandy's diagnosis was correct. The check-before-save fix she proposed is the right solution:

```python
cursor.execute("""
    UPDATE interactions 
    SET ... status = 'completed' ...
    WHERE interaction_id = %s 
      AND status = 'running'  -- Only if not reaped!
    RETURNING interaction_id
""")
```

**Proceed with her recommendation: Option D + C.**

---

## Implementation Complete: Option D + C

*December 14, 2025 ~19:45*

### Changes Made

**1. Removed threaded reaper (Option D)**
- File: `scripts/turing_daemon.py`
- Removed `_reaper_loop()` thread
- Removed `_reap_stuck_interactions_with_conn()` 
- Removed `_cleanup_stale_queue_with_conn()`
- Reaper now runs in main loop (same as before today's changes)
- Added comment explaining why threading was removed

**2. Added check-before-save (Option C)**
- File: `core/wave_runner/database.py`
- Changed `update_interaction_success()` to use optimistic locking
- Now returns `bool` instead of `None`
- Only updates if `status = 'running'` (prevents overwriting reaped interactions)
- Logs warning if interaction was modified

**3. Updated WaveRunner to handle reaped interactions**
- File: `core/wave_runner/runner.py`
- `_execute_interaction()` now checks return value of `update_interaction_success()`
- If interaction was reaped, logs warning and returns `False` (skips child creation)

### Code Summary

```python
# database.py - Optimistic locking
cursor.execute("""
    UPDATE interactions
    SET status = 'completed', ...
    WHERE interaction_id = %s
      AND status = 'running'  -- KEY: Only if not reaped!
    RETURNING interaction_id
""")
if cursor.fetchone() is None:
    return False  # Was reaped, discard result

# turing_daemon.py - Main loop reaper
while self.running:
    if time.time() - self.last_reap > self.reaper_interval:
        self._reap_stuck_interactions()  # Runs in main thread
        self.last_reap = time.time()
    # ... rest of loop
```

### What This Means

1. **No more race condition** - Reaper can't run while Ollama is blocking
2. **Defense in depth** - Even if someone re-adds threading, check-before-save prevents corruption
3. **Tradeoff accepted** - If Ollama takes 10 minutes, reaper won't run for 10 minutes (acceptable)

### Ready to Test

Daemon is ready to restart. Changes are safe and backwards-compatible.

---

## Evening Update: WF3005 Pipeline Fix

*21:48 - xai & Copilot*

### Discovery: 4,500 Orphan Skills Not Being Assigned

While monitoring progress, noticed that despite 6,500+ skills marked "done", only ~80 had actual domain assignments (`entity_relationships.is_a`). Investigation revealed:

**Root Cause:** `entity_decision_saver` and `entity_decision_applier` actors existed but were **never wired into WF3005**. The workflow was:
1. Triage orphans ✓
2. Classify orphans ✓  
3. Grade classifications ✓
4. Debate panel (Challenge/Defend/Final) ✓
5. Validate parent categories ✓
6. **Save instruction** → Was an LLM, not the saver actor! ❌
7. **Apply decisions** → `w3005_c9_apply` had NO INSTRUCTION! ❌

Skills were going through the full classification pipeline but the results were never persisted.

### Fix Applied

Created migration `migrations/wire_decision_actors_wf3005.sql`:

```sql
-- Wire entity_decision_saver into w3005_c4_save
INSERT INTO instructions (instruction_name, conversation_id, delegate_actor_id, ...)
VALUES ('w3005_save_decisions', 9232, 141, ...);  -- actor 141 = entity_decision_saver

-- Wire entity_decision_applier into w3005_c9_apply  
INSERT INTO instructions (instruction_name, conversation_id, delegate_actor_id, ...)
VALUES ('w3005_apply_decisions', 9237, 142, ...);  -- actor 142 = entity_decision_applier

-- Chain: validate → save → apply → export
UPDATE instruction_steps SET next_conversation_id = 9232  -- c4_save
WHERE instruction_id = (SELECT instruction_id FROM instructions WHERE instruction_name = 'Validate parent categories');

UPDATE instruction_steps SET next_conversation_id = 9237  -- c9_apply
WHERE instruction_id IN (SELECT instruction_id FROM instructions WHERE instruction_name = 'w3005_save_decisions');
```

### Results After 50-Minute Monitoring Cycle

| Metric | Before Fix | After 50m | Delta |
|--------|------------|-----------|-------|
| Skills Done | 6,712 | 6,911 | +199 |
| Pending | 1,313 | 1,113 | -200 |
| Progress | 80% | 82% | +2% |
| Registry Decisions | 20 | 232+ | +212 |
| is_a Relationships | 72 | 142+ | +70 |
| Skills Assigned | 44 | 114+ | +70 |

### Entity Registry Tree (Latest)

```
entity_registry/
├── business_operations/ (6 skills)
├── compliance_and_risk/ (23 skills)
├── corporate_culture/ (1 skills)
├── data_and_analytics/ (16 skills)
├── people_and_communication/ (28 skills)
├── project_and_product/ (23 skills)
├── specialized_knowledge/ (6 skills)
├── technology/ (53 skills)
```

**156 skills classified** across 8 domains (up from 81 earlier).  
**ETA to completion: ~37 minutes** (was showing 16+ hours before fix).

### Status

- ✅ Pipeline flowing correctly
- ✅ Registry decisions being created
- ✅ Entity relationships being applied
- ✅ No failures in last 50 minutes
- ⏳ Continuing to monitor until complete
