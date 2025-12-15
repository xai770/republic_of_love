# ADR-008: Global Batch Mode for Multi-Workflow Processing

**Status:** Accepted  
**Date:** 2025-11-27  
**Last Verified:** 2025-11-30  
**Deciders:** Arden, Sandy, xai  
**Tags:** performance, wave-runner, batch-processing

---

## Context

On November 27, 2025, we discovered that WaveRunner was processing workflows sequentially despite being designed for wave batching. A 181-job batch was taking ~2 hours when it should have completed in ~15 minutes.

### The Problem

**Observed behavior:**
- GPU utilization showing sawtooth pattern (rapid load/unload cycles)
- Database timestamps showing sequential execution per posting
- Each posting: gemma3 → mistral → gemma2 → qwen (90 seconds)
- Then next posting: gemma3 → mistral → gemma2 → qwen (90 seconds)
- Total time: 181 postings × 90s = ~4.5 hours

**Expected behavior:**
- Sustained GPU utilization (models stay loaded)
- Wave pattern: ALL gemma3, then ALL mistral, then ALL gemma2, then ALL qwen
- Total time: 4 models × 3 minutes = ~15 minutes

**Root cause discovered:**

```python
# scripts/process_fetched_jobs.py (WRONG)
for staging_id in staging_ids:
    result = start_workflow(db_conn=conn, workflow_id=3001, posting_id=posting_id)
    workflow_run_id = result['workflow_run_id']
    
    # Creates WaveRunner scoped to ONE workflow_run
    runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
    runner.run(max_iterations=100)  # ← Completes ONE posting, then moves to next
```

**Why this defeated batching:**
1. Each posting created its own `workflow_run` record
2. WaveRunner filtered by `workflow_run_id`
3. Each workflow_run only had 3-4 interactions
4. Processed one workflow_run at a time → sequential execution
5. GPU loaded/unloaded models 181 times (once per posting)

### The Investigation

**Database evidence:**
```sql
SELECT posting_id, workflow_run_id FROM workflow_runs 
WHERE workflow_id = 3001 
ORDER BY posting_id;

-- Result: 181 separate workflow_runs
posting_id | workflow_run_id
4920       | 1699
4921       | 1700
...
5100       | 1879
```

**Completion timestamps:**
```sql
SELECT posting_id, i.updated_at 
FROM interactions i 
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE a.actor_name = 'gemma3:1b'
ORDER BY i.updated_at;

-- Result: One completion every ~90 seconds (SEQUENTIAL)
posting_id | updated_at
4920       | 14:41:44
4921       | 14:43:20
4922       | 14:45:29
```

**Not wave batching!**

---

## Decision

Implement `global_batch` mode in WaveRunner that removes ALL scoping filters (`posting_id` AND `workflow_run_id`), allowing it to pool interactions across all active workflows.

### API Design

```python
# core/wave_runner/runner.py
class WaveRunner:
    def __init__(
        self, 
        db_conn, 
        posting_id: Optional[int] = None,
        workflow_run_id: Optional[int] = None,
        global_batch: bool = False  # ← NEW PARAMETER
    ):
        """
        Args:
            global_batch: If True, remove ALL filters and pool interactions
                         across ALL active workflows. This is TRUE wave batching.
        """
        self.global_batch = global_batch
        
        # In global_batch mode, clear ALL filters
        if global_batch:
            self.posting_id = None
            self.workflow_run_id = None
        else:
            self.posting_id = posting_id
            self.workflow_run_id = workflow_run_id
```

### Usage Pattern

**WRONG (Sequential per workflow_run):**
```python
for posting_id in posting_ids:
    result = start_workflow(conn, workflow_id=3001, posting_id=posting_id)
    runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
    runner.run()  # ← Processes ONE workflow_run
```

**CORRECT (Global batch mode):**
```python
# Step 1: Start ALL workflows (creates pending interactions)
for posting_id in posting_ids:
    start_workflow(conn, workflow_id=3001, posting_id=posting_id)

# Step 2: Run ONE WaveRunner in global batch mode
runner = WaveRunner(conn, global_batch=True)
runner.run()  # ← Processes ALL pending interactions across ALL workflows
```

---

## Consequences

### Positive

**6-12x speedup from reduced model loading:**
- Before: 181 postings × 4 models × 15s load = 2.7 hours of model loading overhead
- After: 4 models × 1 load × 15s = 60 seconds of model loading overhead
- Savings: 2.6 hours (~160 minutes)

**Combined with model optimization (Nov 27):**
- Model switch: gemma2 → mistral (4.6x faster: 18.96s → 4.07s)
- Wave batching: 6-12x faster (reduced model loading)
- **Total improvement: 28-55x faster than baseline**

**GPU utilization:**
- Before: Sawtooth pattern (22% average, spikes to 95%)
- After: Sustained 95% utilization during processing
- Evidence: GPU graph shows flat 95% plateau instead of spikes

**Database evidence of success:**
```sql
-- Nov 27, 16:17 - After implementing global_batch=True
SELECT a.actor_name, COUNT(*), 
       MIN(i.created_at)::time as first,
       MAX(i.created_at)::time as last
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE i.created_at BETWEEN '2025-11-27 16:17:16' AND '2025-11-27 16:17:19'
GROUP BY a.actor_name;

-- Result: Tight 3-second clusters across 25+ postings
actor_name         | count | first    | last
sql_query_executor | 25    | 16:17:16 | 16:17:16
qwen2.5:7b         | 15    | 16:17:18 | 16:17:19
```

**This is TRUE wave batching** - multiple postings processed simultaneously per model.

### Negative

**Requires clean workflow_run state:**
- Duplicate workflow_runs from restart attempts cause issues
- Must clean up old runs before using global_batch mode
- Solution: Mark old runs as 'cancelled', invalidate their interactions

**More complex to reason about:**
- Single-posting debugging harder (too many interactions in flight)
- Need to filter by posting_id in queries to see individual posting progress
- Solution: Use posting_id filter for debugging, global_batch for production

**Need to prevent runaway scenarios:**
- No iteration limits in production (causes incomplete processing)
- Must handle cleanup properly if execution interrupted
- Solution: Document best practices, create wrapper scripts

### Neutral

**When to use each mode:**

| Mode | Use Case | Filter | Batch Size |
|------|----------|--------|------------|
| **Single posting** | Debugging one posting | `posting_id=X` | 3-4 interactions |
| **Single workflow** | Resume failed run | `workflow_run_id=X` | 3-4 interactions |
| **Global batch** | Production processing | `global_batch=True` | 100s-1000s interactions |

**Rule:** For batch processing multiple postings, ALWAYS use `global_batch=True`

---

## Implementation

### Code Changes

**Modified:** `core/wave_runner/runner.py`
- Added `global_batch` parameter to `__init__`
- Clear filters when `global_batch=True`
- WorkGrouper queries ALL pending interactions (no scoping)

**Modified:** `core/wave_runner/work_grouper.py`
- Respect `global_batch` mode in batch queries
- Remove workflow_run_id filter when global batching

**Created:** `scripts/run_workflow_batch.py` (recommended wrapper)
```python
#!/usr/bin/env python3
"""Run workflow in global batch mode with no iteration limits"""
from core.database import get_connection
from core.wave_runner.runner import WaveRunner

conn = get_connection()
runner = WaveRunner(conn, global_batch=True)

print('Running in global batch mode (no iteration limit)...')
result = runner.run()  # NO max_iterations parameter!

print(f"Completed: {result.get('interactions_completed', 0)}")
```

### Migration Path

**Phase 1: Immediate (Nov 27)**
- Implement global_batch parameter
- Test with 181-job batch
- Validate with GPU monitoring + timestamp analysis

**Phase 2: Documentation (Nov 28)**
- Update WORKFLOW_EXECUTION.md with best practices
- Create ADR-008 (this document)
- Update cheat sheet with standard commands

**Phase 3: Standardization (Week of Nov 28)**
- Deprecate ad-hoc runner scripts
- Create standard wrapper scripts
- Update all batch processing to use global_batch mode

---

## Validation

### How to Verify Global Batch Mode is Working

**1. GPU Utilization Pattern**
```bash
# Should see sustained high usage, not sawtooth
watch -n 2 nvidia-smi
# Look for: 95% utilization plateau (not spikes)
```

**2. Completion Timestamp Analysis**
```sql
-- Should see tight clusters per model
WITH completion_times AS (
    SELECT 
        a.actor_name,
        wr.posting_id,
        i.updated_at
    FROM interactions i
    JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
    JOIN conversations c ON i.conversation_id = c.conversation_id
    JOIN actors a ON c.actor_id = a.actor_id
    WHERE a.actor_type = 'llm'
      AND i.status = 'completed'
      AND i.updated_at > NOW() - interval '1 hour'
)
SELECT 
    actor_name,
    COUNT(*) as interactions,
    MIN(updated_at)::time as wave_start,
    MAX(updated_at)::time as wave_end,
    EXTRACT(EPOCH FROM (MAX(updated_at) - MIN(updated_at))) as duration_seconds
FROM completion_times
GROUP BY actor_name
ORDER BY MIN(updated_at);

-- Expected result (for 181 postings):
-- gemma3:1b   | 181 | 16:05:10 | 16:08:45 | 215s   ← 3.5-min window
-- mistral     | 181 | 16:08:46 | 16:10:30 | 104s   ← Sequential after gemma3
-- gemma2      | 181 | 16:10:31 | 16:14:20 | 229s   ← Sequential after mistral
-- qwen2.5:7b  | 181 | 16:14:21 | 16:18:45 | 264s   ← Sequential after qwen

-- Bad result would show 90+ second spreads per posting (sequential)
```

**3. Simultaneous Interactions Check**
```sql
-- Should see multiple interactions running per model simultaneously
SELECT 
    a.actor_name,
    COUNT(*) as running_now
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE i.status = 'running'
GROUP BY a.actor_name;

-- Expected: 5-20 interactions running per model
-- Bad: 0-1 interactions per model (sequential)
```

---

## Lessons Learned

### Infrastructure Must Be Used Correctly

WaveRunner was designed for batching from the start (WorkGrouper, parallel execution, etc.), but the **orchestration layer** was using it incorrectly:
- Creating one WaveRunner per posting defeats batching
- Filtering by workflow_run_id limits batch size to 3-4 interactions
- Need explicit "batch mode" to override default scoping behavior

**Takeaway:** Good infrastructure can still produce poor results if used incorrectly. Document usage patterns, not just APIs.

### GPU Monitoring Reveals Architectural Issues

The sawtooth pattern was immediate visual evidence of sequential execution. Without GPU monitoring, we might have accepted slow performance as "just how it is."

**Takeaway:** Monitor resource utilization (GPU, CPU, memory) as a debugging tool. Visual patterns reveal architectural problems.

### Batch Processing Requires Batch Execution

The phrase "wave batching" was misleading - we had waves *within each posting*, but not *across postings*. True batching requires:
1. All work items loaded (all workflow_runs created)
2. Grouped by operation type (all gemma3 calls together)
3. Executed in batches (load model once, process all)

**Takeaway:** "Batch processing" means processing multiple items in the same batch, not processing items one at a time in sequence.

---

## Related

- **ADR-001:** Priority-Based Branching (execution order patterns)
- **ADR-003:** Wave-Based Pipeline Processing (original wave runner design)
- **ADR-004:** Connection Pooling (performance optimization)
- **WORKFLOW_EXECUTION.md:** Execution best practices
- **Nov 27 Production Deployment Memo:** Full day documentation

---

## References

**Evidence:**
- GPU monitoring screenshots (Nov 27, 15:00-17:00)
- Database timestamp analysis queries
- Process monitoring (PID 616149, 726389, etc.)

**Related Issues:**
- Iteration limit problem (hit max_iterations 3 times)
- Duplicate workflow_runs (543 interactions for 181 postings)
- Sequential vs parallel execution patterns

**Performance Impact:**
- Baseline: gemma2, sequential: ~6-8 hours for 500 jobs
- Optimized: mistral, sequential: ~1.5-2 hours for 500 jobs
- **Final: mistral, global_batch: ~15-20 minutes for 500 jobs**
- **Total improvement: 24-32x faster**

---

**Status:** Implemented and validated (Nov 27, 2025)  
**Next:** Standardize usage, deprecate incorrect patterns, document best practices
