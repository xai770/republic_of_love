# Skill Taxonomy RAQ Session - 2026-01-07

## Objective
RAQ test the Skill Taxonomy conversation (formerly WF2010) using pull architecture.

## 🎉 MAJOR BREAKTHROUGH: Pull/Batcher Architecture

### Problem Solved
The pull_daemon was calling WaveRunner.run() which processes ALL pending interactions globally, breaking subject-scoped execution needed for pull workflows.

### Solution: Separation of Concerns
Created `scripts/batcher.py` - a dedicated process for executing pending interactions:

1. **Pull Daemon** (`core/pull_daemon.py`)
   - Finds work via conversation's `work_query`
   - Creates seed interactions (status='pending')
   - Does NOT execute anything!

2. **Batcher** (`scripts/batcher.py`)
   - Polls pending interactions globally
   - Groups by model (GPU stays loaded - Directive 15)
   - Executes each interaction
   - Calls `create_child_interactions()` which follows the instruction_steps tree

### Verified Results
For skill 11943 ("People leadership experience"):
```
1110029 (create) → 1110030 (classify_a) + 1110031 (classify_b)  ← PARALLEL!
                         ↓ wait_for_group
                   1110032 (compare)
                         ↓
                   1110033 (victor)
```

- Classifier A picked folder 39060
- Classifier B picked folder 40025
- **DISAGREEMENT = SUCCESS** (they didn't see each other's output!)

### Usage
```bash
# Create seed interactions
python3 core/pull_daemon.py --workflow 2010 --limit 10

# Process them (runs continuously)
python3 scripts/batcher.py --workflow 2010

# Or run once for testing
python3 scripts/batcher.py --workflow 2010 --run-once
```

---

## Pre-RAQ Investigation

### Current State (before RAQ run)
```
[2026-01-07 13:03:11] WF2010: Q:0p/0r→1044✓ | Rate:5/hr | ETA:done | Oversized:0 | NR:1 | Err:2
```

### Issues to Investigate

#### 1. Three Failed Interactions (last 24h)
- **Status**: 🔴 NEEDS INVESTIGATION

| interaction_id | conversation | error | entity_id | skill |
|----------------|--------------|-------|-----------|-------|
| 1108230 | classify_a | Timeout (external reaper) | 33738 | human_resources |
| 1108192 | classify_b | (empty - mystery) | 24284 | technology |
| 1108181 | compare | Timeout (external reaper) | 30185 | discretion |

- **Pattern**: 2 timeouts, 1 mystery empty error
- **Root Cause**: wf2010_c6_compare had 30s timeout - too short when classifiers disagree
- **Fix**: `UPDATE conversations SET timeout_seconds = 120 WHERE conversation_name = 'wf2010_c6_compare'`

**Skills Re-queued** (pending_ids 21266, 21267, 21268):
- technology (entity 24284)
- discretion (entity 30185) 
- human_resources (entity 33738)

#### 2. One Skill in _NeedsReview
- **Status**: 🟡 LOW PRIORITY (expected escape hatch usage)
- **Finding**: 
- **Root Cause**: 

---

## Session Changes Made

### 1. Model-First Batching (Directive 15 Fix)
**File**: `core/pull_daemon.py`
**Change**: `_get_pull_conversations()` now orders by `requires_model NULLS LAST` before `poll_priority`
**Why**: GPU utilization - keep one model loaded until all its work is exhausted

### 2. Conversation Name Resolver  
**File**: `scripts/raq.py`
**Change**: Accept camelCase names instead of cryptic IDs
**Why**: `raq start SkillTaxonomy` >> `raq start 9351`

---

## RAQ Test Plan

### Command
```bash
raq start SkillTaxonomy --count 100 --runs 3
```

### Pre-flight Checklist
- [ ] Investigate 2 errors first
- [ ] Backup current state: `raq backup SkillTaxonomy`
- [ ] Verify pending skills exist: `SELECT COUNT(*) FROM entities_pending WHERE entity_type='skill' AND status='pending'`
- [ ] Monitor running: `tail -f logs/wf2010_qa_watch.log`

### Expected Outcome
- 100 skills processed × 3 runs
- Compare for 100% consistency
- Any disagreement = investigation target

---

## RAQ Run Log

**Batch**: RAQ_20260107_130755

### Run 1
- **Started**: 2026-01-07 13:07:55
- **Completed**: 
- **Errors**: 
- **Notes**: 

### Run 2
- **Started**: 
- **Completed**: 
- **Errors**: 
- **Notes**: 

### Run 3
- **Started**: 
- **Completed**: 
- **Errors**: 
- **Notes**: 

### Comparison
- **Match Rate**: 
- **Mismatches**: 

---

## Gold Nuggets (Investigation Findings)

### Nugget 1: Classify Timeouts Still Too Tight
- **Discovery**: classify_b timed out at 335s (limit was 300s) for "Credit Limit Management"
- **Root Cause**: Complex skills need more LLM thinking time
- **Fix Applied**: `UPDATE conversations SET timeout_seconds = 600 WHERE conversation_name LIKE 'wf2010_c3%_classify_%'`
- **Lesson**: 10 minutes is safer for classification steps

### Nugget 2: "Stuck - no heartbeat" Mystery
- **Discovery**: classify_a failed with empty error_message but `output = {"error": "Stuck - no heartbeat"}`
- **Root Cause**: Same as above - long skill names ("Building, maintaining and continually implementing tests...") take longer
- **Fix Applied**: Same timeout bump
- **Lesson**: Error message sometimes in output, not error_message column

### Nugget 3: Batch Counters Never Updated
- **Discovery**: `batches.item_count = 0`, `completed_count = 0` even after 50+ skills processed
- **Root Cause**: pull_daemon creates batches but never updates counters
- **Fix Applied**: 
  1. Added `item_count + 1` in `_create_interaction()`
  2. Created DB trigger `trg_update_batch_counts` to increment `completed_count`/`failed_count` on status change
- **Lesson**: RAQ needs accurate batch tracking for comparison

### Nugget 4: Multiple Stale RAQ Batches
- **Discovery**: 3 batches stuck in 'running' status from interrupted runs
- **Fix Applied**: `UPDATE batches SET status = 'stopped' WHERE status = 'running' AND reason LIKE 'RAQ%'`
- **Lesson**: Need cleanup on RAQ restart

### Nugget 5: RAQ Reset Doesn't Clear Completed Interactions
- **Discovery**: Run 2 only processed 9 skills because 3146 already had completed interactions
- **Root Cause**: `do_reset()` cancelled pending/running but left completed interactions intact. Daemon exclusion query filters `status IN ('pending', 'running', 'completed')`
- **Fix Applied**:
  1. `do_reset()` now sets `invalidated = TRUE` on all interactions
  2. Daemon exclusion query now also checks `invalidated = FALSE`
- **Lesson**: RAQ needs full interaction reset between runs for re-processing 

---

## Sandy Handoff - 2026-01-07 17:35

### Where We Are

We discovered the root cause of the 50% A/B disagreement rate: **Classifier B was seeing Classifier A's response!**

The bug: `parent_response` template variable was passing A's output to B because B was created as a child of A (sequential), not as a sibling (parallel).

### What We Fixed

#### 1. Parallel Classifier Architecture
Per [WF2010_skill_keepers_story.md](../WF2010_skill_keepers_story.md), Clara A and Clara B should classify **independently in parallel**.

**workflow_conversations changes:**
```sql
-- Both classifiers depend on create (step 511), both in parallel_group 1
UPDATE workflow_conversations SET depends_on_step_id = 511, parallel_group = 1 WHERE step_id = 525;  -- classify_a
UPDATE workflow_conversations SET depends_on_step_id = 511, parallel_group = 1 WHERE step_id = 526;  -- classify_b
UPDATE workflow_conversations SET wait_for_group = TRUE WHERE step_id = 515;  -- compare waits for both
```

**instruction_steps changes:**
```sql
-- Create branches to BOTH classifiers (same priority = parallel)
INSERT INTO instruction_steps (create → classify_b, priority=1);  -- NEW step 275
-- Disabled: classify_a → classify_b (was causing sequential execution)
-- Added: classify_a → compare (step 276, so compare fires when either completes)
```

#### 2. Subject Propagation Fix
Child interactions weren't inheriting `subject_id`/`subject_type` from parents.

**core/wave_runner/database.py:**
- Added `i.subject_id, i.subject_type` to `get_pending_interactions()` and `get_interaction_by_id()` queries

**core/wave_runner/interaction_creator.py:**
- Added fallback: when `workflow_run_id` is NULL (pull daemon flow), get subject info from parent interaction
- Added fallback: derive `workflow_id` from `workflow_conversations` when no `workflow_run`

#### 3. wait_for_group Without workflow_run_id
The `check_parallel_group_complete()` method was querying by `workflow_run_id`, which is NULL in pull daemon flows.

**Fix:** Added `subject_id`/`subject_type` parameters to correlate parallel interactions when `workflow_run_id` is NULL.

### What's NOT Working Yet

**The compare step never fires!** 

When tested manually, everything works:
```
INFO: Parallel group 1 check: 2/2 complete (ALL COMPLETE)
INFO: wait_for_group: Creating child for conv 9356 with 2 parent IDs: [1110019, 1110020]
Created: [1110021]  ← compare interaction created!
```

But when run via pull_daemon → WaveRunner, both classifiers complete successfully but compare is never created.

### The Suspected Issue: Push vs Pull Architecture Mismatch

The current code has two execution paths:

1. **Push (workflow_runs)**: Daemon creates workflow_run, WaveRunner processes by workflow_run_id
2. **Pull (pull_daemon)**: Daemon creates seed interaction with subject_id, WaveRunner processes... globally?

**The problem:** When WaveRunner is called by pull_daemon's `_execute_conversational()`, it calls `runner.run()` which calls `work_grouper.get_grouped_batches()` with NO filters:
- No `posting_id`
- No `workflow_run_id` 
- No `workflow_id`
- **No `subject_id`!**

So WaveRunner picks up ALL pending interactions globally, not just the ones for the current subject. This might cause timing/ordering issues where the classifiers complete but their child-creation callbacks don't fire in the expected context.

### Next Steps

1. **Verify the hypothesis**: Check if WaveRunner is picking up interactions from other subjects during the run
2. **Potential fix**: Pass `subject_id` context to WaveRunner, add subject-based filtering to `get_grouped_batches()`
3. **Or**: Make pull_daemon wait for ALL descendants of the seed interaction, not just the seed itself
4. **Alternative**: Have the classifiers check if they're "last in parallel group" and create compare if so

### Files Modified This Session
- `core/wave_runner/interaction_creator.py` - parallel group support for null workflow_run_id
- `core/wave_runner/database.py` - subject_id in interaction queries
- `core/pull_daemon.py` - work_query ordering fix (pending_id vs created_at)

### Current Test State
- Subject 11942: Both classifiers completed ✅, compare NOT created ❌
- The classifiers ARE siblings (both parent=create), so parallel structure is correct
- But wait_for_group logic isn't triggering in the daemon context
