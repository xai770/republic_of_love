# Workflow Debugging Cookbook

**Last Updated:** December 7, 2025  
**Authors:** Sandy (Claude Sonnet 4.5) & Arden (Claude Sonnet 4.5)  
**Status:** Production-Validated

A practical guide for debugging workflow issues without losing work.

**Recent Update (Dec 7):** Template variables now auto-extracted - see `WORKFLOW_EXECUTION.md` § Dynamic Template Variable Extraction.

**Related Documentation:**
- `EVENT_INVALIDATION.md` - How to mark invalid events
- `PROJECTION_REBUILD.md` - How to rebuild projections from events
- `EVENT_SOURCING_PRACTICES.md` - Event sourcing best practices
- `IDEMPOTENCY_BUG_POSTMORTEM.md` - Real-world debugging case study
- `WORKFLOW_EXECUTION.md` - Traceability system (Nov 25)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Table of Contents

1. [Debugging Philosophy](#debugging-philosophy)
2. [Incremental Testing Pattern](#incremental-testing-pattern-nov-25) ⭐ **NEW**
3. [Trace Report Analysis](#trace-report-analysis-nov-25) ⭐ **NEW**
4. [Common Issues & Solutions](#common-issues--solutions)
5. [Reset Strategies](#reset-strategies)
6. [Data Inspection Recipes](#data-inspection-recipes)
7. [Branching Issues](#branching-issues)
8. [Performance Debugging](#performance-debugging)

---

## Debugging Philosophy

### The Golden Rule: Preserve Completed Work

**Event sourcing gives us superpowers:**
- Events are append-only history
- Projection outputs cache expensive LLM results
- We can "rewind" by deleting recent events WITHOUT losing previous work

**Before any reset, ask:**
1. What step has the bug?
2. What work can we preserve?
3. Can we restart from step N instead of step 1?

---

## Incremental Testing Pattern (Nov 25)

### The CRAWL → WALK → RUN Approach

**When to use:** Complex workflows fail or behave unexpectedly, and you don't know which step is broken.

**The Problem:**
- Running full workflow (15 steps) takes 3 minutes
- Failure at step 12 means 2:45 wasted time
- Can't isolate root cause without breaking down execution

**The Solution:** Test incrementally, starting with smallest units.

### CRAWL: Test Individual Conversations

Test each conversation in isolation to verify it works independently.

```bash
# Test Extract conversation alone
python3 tests/test_single_conversation.py 3335

# Test each grader alone
python3 tests/test_single_conversation.py 3336
python3 tests/test_single_conversation.py 3337

# Test improvement session
python3 tests/test_single_conversation.py 3338
```

**What this proves:**
- ✅ Conversation prompt template is valid
- ✅ Actor executes successfully
- ✅ Output format is correct
- ✅ Database writes work

**What it doesn't prove:**
- ❌ Data flows between conversations (tested in WALK)
- ❌ Branching logic works (tested in WALK)
- ❌ Full pipeline completes (tested in RUN)

### WALK: Test Conversation Chains

Test 2-3 conversations in sequence to verify data flow and branching.

```bash
# Test Extract → Grade chain (3 steps)
python3 tests/test_conversation_chain.py 3335 3

# Test Improvement → Format chain (2 steps)
python3 tests/test_conversation_chain.py 3338 2

# Test specific branch
python3 tests/test_conversation_chain.py 9144 5  # Job Fetcher → Extract → Grades
```

**What this proves:**
- ✅ Parent outputs flow to child inputs
- ✅ Template variables substitute correctly
- ✅ Branching conditions evaluate properly
- ✅ Child interactions created correctly

**Common failures found in WALK:**
- Variable name mismatches (`{session_3_output}` vs `{conversation_3335_output}`)
- Empty parent outputs (parent conversation failed silently)
- Wrong branching condition (grade passes but goes to improvement)

### RUN: Test Full Workflow

Only after CRAWL and WALK pass, test the complete pipeline.

```bash
# Full workflow
python3 -m core.wave_runner.runner --workflow 3001 --posting-id 176 --trace

# Batch processing
python3 -m core.wave_runner.runner --workflow 3001 --limit 10 --trace
```

**What this proves:**
- ✅ All 15 conversations execute
- ✅ Complete data flow works
- ✅ Terminal conditions reached
- ✅ Database state correct

### Example: Debugging Workflow 3001 (Nov 25)

**Symptoms:** Graders fail with [FAIL] on empty summary

**CRAWL Testing:**
```bash
# Test Extract
$ python3 tests/test_single_conversation.py 3335
✅ SUCCESS - Created summary (3,489ms)

# Test first grader
$ python3 tests/test_single_conversation.py 3336
✅ SUCCESS - But graded empty summary? 🤔
```

**Discovery:** Extract works alone, but grader gets empty input when chained!

**WALK Testing:**
```bash
# Test chain
$ python3 tests/test_conversation_chain.py 3335 2
[FAIL] Summary is empty
```

**Trace report shows:**
```
--- start summary ---

--- end summary ---
```

**Root cause:** Template uses `{session_3_output}` but should use `{conversation_3335_output}`.

**Time saved:** Found bug in 2 minutes with traces vs 30 minutes blind debugging.

---

## Trace Report Analysis (Nov 25)

### What Are Trace Reports?

Markdown files in `/reports/trace_*.md` that capture complete execution details:

```markdown
### Prompt Template
{variations_param_1}

### Actual Input (Substituted)
[full 3,771-char job description]

### Actual Output
[AI response]
```

### Enabling Trace Reports

```python
# In test scripts
runner = WorkflowRunner(
    workflow_id=3001,
    posting_id=176,
    trace=True  # ← Enable detailed traces
)
```

```bash
# Or via command line
python3 -m core.wave_runner.runner --workflow 3001 --trace
```

### Reading Trace Reports

**File naming:**
- `trace_conv_3335_run_112.md` - Single conversation test
- `trace_chain_run_123.md` - Conversation chain test  
- `trace_workflow_3001_run_45.md` - Full workflow test

**Key sections to check:**

**1. Prompt Template** - What's in the database
```
Extract skills from: {variations_param_1}
```

**2. Actual Input (Substituted)** - What was sent to AI
```
Extract skills from: Job Description: CA Intern at Deutsche Bank...
[3,771 characters]
```

**3. Actual Output** - What AI produced
```json
{
  "skills": ["risk management", "capital adequacy", "ICAAP"],
  ...
}
```

**4. Parent Interactions** - Data flow
```
Parent: Interaction 230 (Extract)
Output passed to child: {...}
```

### Common Debugging Patterns

**Empty Variable Substitution:**
```
--- start summary ---

--- end summary ---
```
**Diagnosis:** Variable name mismatch or parent output missing.

**Fix:** Check `{conversation_XXXX_output}` naming, verify parent executed.

**Wrong Data in Prompt:**
```
Job Title: undefined
Location: null
```
**Diagnosis:** Variable mapping points to wrong field.

**Fix:** Check `executors.py` variable mapping matches database columns.

**AI Hallucination:**
```
**Company:** Google
(Actual job is from Deutsche Bank)
```
**Diagnosis:** Prompt doesn't contain company name, AI guessed.

**Fix:** Add `{company_name}` variable to template.

### Trace Report Metrics

Each interaction shows:
- **Duration:** How long it took (helps identify slow steps)
- **Status:** completed/failed (helps find crash points)
- **Metadata:** Model used, tokens, latency

**Performance analysis:**
```
Interaction 1: 3.5s  (Extract - gemma3:1b)
Interaction 2: 13s   (Grade - gemma2:latest) ← Slow!
Interaction 3: 9.4s  (Grade - qwen2.5:7b)
```

**Optimization:** Replace gemma2 with faster model or reduce prompt size.

---

## Common Issues & Solutions

### Issue 1: Workflow Stuck at One Step

**Symptoms:**
```
Step 2: 2089 completed (100%)
Step 3: 0 completed (0%)
```
```

**Diagnosis:**
```bash
# Check if process is running
ps aux | grep wave_processor

# Check recent log activity
tail -50 logs/workflow_3001_*.log | grep "posting_completed"

# Check projection state
PGPASSWORD=base_yoga_secure_2025 psql -h localhost -U base_admin -d turing -c \
"SELECT current_step, current_status, COUNT(*) FROM posting_state_projection GROUP BY current_step, current_status;"
```

**Common Causes:**
1. Process died → Restart it
2. All postings marked as TERMINAL → Check why
3. Branching logic broken → Check branch conditions
4. Entry point routing issue → Verify workflow loader

**Solution:**
- If process died: Just restart workflow
- If branching broken: Fix branch logic, do SMART reset from problem step
- If all TERMINAL: Check events to see why they're marked terminal

---

### Issue 1a: Multiple Child Interactions Created (Nov 25, 2025)

**Symptoms:**
Trace report shows conversation created multiple children when only one expected

**Example:**
```markdown
## Interaction 5: session_c_qwen25_grade
Output: [PASS]

Child Interactions Created:
- Interaction 397 (Format) ✅
- Interaction 398 (Ticket) ❌ Why?
```

**Root cause:** Wildcard catch-all rule (`*`) matches even when higher priority rules match

**Known bug:** Runner doesn't stop after first match at highest priority level (evaluates ALL priorities)

**Diagnosis:**
```sql
-- Find conversations with wildcard rules
SELECT
    c.conversation_id,
    c.conversation_name,
    COUNT(CASE WHEN is.priority > 0 THEN 1 END) as specific_rules,
    COUNT(CASE WHEN is.priority = 0 AND is.branching_condition = '*' THEN 1 END) as wildcard_rules
FROM conversations c
JOIN instruction_steps is ON c.conversation_id = is.conversation_id
WHERE c.workflow_id = 3001
GROUP BY c.conversation_id, c.conversation_name
HAVING COUNT(CASE WHEN is.priority = 0 AND is.branching_condition = '*' THEN 1 END) > 0;
```

**Quick Fix:**
```sql
-- Delete conflicting wildcard rule
DELETE FROM instruction_steps
WHERE conversation_id = 3337
  AND branching_condition = '*'
  AND priority = 0;
```

**Prevention:**
- ✅ Avoid wildcard rules when specific conditions exist
- ✅ Use high priority (99) for wildcards if needed
- ✅ Check trace reports for unexpected children
- ✅ Monitor for unnecessary LLM calls (cost indicator)

**Impact:** Mostly harmless (creates extra interaction) but wastes time/money on unnecessary LLM calls

**Proper fix:** Update `runner.py` to stop after first match (pending implementation)

---

### Issue 2: Wrong Branch Taken

**Symptoms:**
```
Step 5: 2089 completed → All went to step 8 (should have split between 6 and 9)
```

**Root Cause Examples:**
- LLM output doesn't exactly match branch condition
- Branch priority wrong
- Default `*` branch catching everything

**Diagnosis:**
```sql
-- Check what the actual output was for step 5
SELECT posting_id, 
       event_data->>'output' as actual_output,
       SUBSTRING(event_data->>'output', 1, 50) as output_preview
FROM execution_events 
WHERE event_data->>'conversation_id' = '3337'  -- Step 5 conversation ID
LIMIT 10;

-- Check branch conditions
SELECT branch_condition, next_conversation_id, branch_priority 
FROM instruction_steps 
WHERE instruction_id = (
    SELECT instruction_id FROM instructions WHERE conversation_id = 3337 LIMIT 1
) 
ORDER BY branch_priority DESC;
```

**Example Fix:**
```python
# If condition is [PASS] but LLM outputs "[PASS]\n\nThe summary is good..."
# The exact match fails!

# Fix: Check if output STARTS WITH the condition
if condition.startswith('[') and condition.endswith(']'):
    output_stripped = output.strip()
    if output_stripped.startswith(condition):
        return next_conv_id  # Match!
```

**Recovery:**
```sql
-- DON'T DELETE EVENTS - Mark them invalid instead!
UPDATE execution_events
SET invalidated = TRUE,
    invalidation_reason = 'Wrong branch taken - all went to step 8 instead of 6/9 split'
WHERE (event_data->>'execution_order')::INT >= 5;

-- Reset to step 5, preserve outputs from steps 1-4
UPDATE posting_state_projection 
SET current_step = 5, 
    current_status = 'pending',
    current_conversation_id = (SELECT conversation_id FROM conversations WHERE canonical_name = 'step5')
WHERE posting_id IN (SELECT posting_id FROM postings WHERE enabled = TRUE);
```

---

### Issue 3: Monitor Shows Wrong Numbers (Invalid Events)

**Symptoms:**
Monitor shows 100% completion for steps 11-21, but postings are actually at step 4.

**Cause:**
Historical invalid events not filtered. Monitor counts ALL events, including ones from failed/invalid executions.

**Solution: Use Event Invalidation** ✅

```sql
-- 1. Mark invalid events
UPDATE execution_events 
SET invalidated = TRUE, 
    invalidation_reason = 'Executed without required data - idempotency bug'
WHERE (event_data->>'execution_order')::INT >= 11
  AND (event_data->>'conversation_id')::INT IN (3341, 3342, ...);  -- Problem steps

-- 2. Update monitor queries to filter invalid events
SELECT COUNT(*) 
FROM execution_events 
WHERE event_data->>'execution_order' = '5'
  AND COALESCE(invalidated, FALSE) = FALSE;  -- ← Add this filter!
```

**Why NOT delete events:**
- ❌ Breaks aggregate versioning
- ❌ Loses audit trail
- ❌ Can't investigate what went wrong
- ✅ Mark invalid, keep history

See `EVENT_INVALIDATION.md` for complete pattern.

---

### Issue 4: Step Keeps Failing

**Symptoms:**
```
circuit_breaker_opened for actor gemma3:1b
```

**Diagnosis:**
```bash
# Find the errors before circuit breaker opened
grep -B 20 "circuit_breaker_opened" logs/workflow_3001_*.log | grep -E "error|exception|failed"

# Check specific posting that failed
grep "posting_id\": 123" logs/workflow_3001_*.log | grep -E "error|failed|exception"
```

**Common Causes:**
1. Ollama timeout (increase timeout)
2. Model not loaded (check `ollama list`)
3. Bad prompt format (check template variables)
4. Rate limiting (check actor configuration)

**Recovery:**
```sql
-- Check which postings failed
SELECT posting_id, failure_count, current_step 
FROM posting_state_projection 
WHERE failure_count > 0;

-- Reset failed postings to retry
UPDATE posting_state_projection 
SET current_status = 'pending', failure_count = 0 
WHERE posting_id = 123;
```

---

## Reset Strategies

### Strategy 1: Event Invalidation + Projection Rebuild (RECOMMENDED) ⭐

**When to use:**
- Invalid executions happened (wrong data, bug, test run)
- Want to preserve audit trail
- Need to re-run specific steps

**Steps:**
```sql
-- 1. Mark events as invalid (DON'T DELETE!)
UPDATE execution_events 
SET invalidated = TRUE,
    invalidation_reason = 'Idempotency bug - executed steps 11-21 without grading data'
WHERE aggregate_type = 'posting'
  AND (event_data->>'execution_order')::INT >= 11
  AND aggregate_id::INT IN (SELECT posting_id FROM posting_state_projection WHERE current_step >= 11);
-- Example: 5,750 events marked invalid

-- 2. Reset postings to correct step
UPDATE posting_state_projection
SET current_step = 4,  -- Back to grading
    current_conversation_id = 3336,  -- gemma2_grade
    current_status = 'pending'
WHERE current_step >= 11;
-- Example: 2,034 postings reset

-- 3. Optionally: Selective rebuild to restore specific outputs
UPDATE posting_state_projection psp
SET outputs = (
    SELECT jsonb_object_agg(
        (event_data->>'conversation_id')::text,
        event_data->'output'
    )
    FROM execution_events
    WHERE aggregate_id = psp.posting_id::text
      AND COALESCE(invalidated, FALSE) = FALSE  -- Exclude invalid events!
      AND (event_data->>'conversation_id')::INT IN (9168, 3335)  -- Steps 2, 3 only
)
WHERE outputs IS NULL OR outputs = '{}'::jsonb;

-- 4. Restart workflow
```

**What you preserve:**
- ✅ Complete audit trail (events marked invalid, not deleted)
- ✅ Legitimate work (steps 2-3 outputs restored)
- ✅ Monitor accuracy (invalid events filtered)
- ✅ Forensic capability (can analyze what went wrong)

**See also:** `EVENT_INVALIDATION.md`, `PROJECTION_REBUILD.md`

---

### Strategy 2: Full Projection Rebuild

**When to use:**
- Projection data corrupted or stale
- Schema migration
- Want to recalculate everything from events

**Steps:**
```sql
-- Use rebuild_posting_state() function
SELECT posting_id, rebuild_posting_state(posting_id)
FROM posting_state_projection
WHERE workflow_id = 3001;

-- Or batch rebuild with Python script
-- See tools/rebuild_projections.py
```

**Important:**
- Rebuilds replay ALL non-invalid events
- Make sure invalid events are marked BEFORE rebuilding
- Test on small subset first

**See:** `PROJECTION_REBUILD.md` for complete patterns

---

### Strategy 3: Nuclear Reset (Last Resort)

**When to use:**
- Complete workflow redesign
- Testing from scratch
- All data is test data

**Steps:**
```sql
-- ⚠️ WARNING: Deletes EVERYTHING
TRUNCATE TABLE execution_events CASCADE;

UPDATE posting_state_projection 
SET current_step = 2,
    current_status = 'pending',
    outputs = '{}'::jsonb,
    conversation_history = '[]'::jsonb
WHERE posting_id IN (SELECT posting_id FROM postings WHERE enabled = TRUE);
```

**Only use when:**
- Running in development/test environment
- All events are test data
- You don't need audit trail

---

## Data Inspection Recipes

### Recipe 1: Check What Outputs We Have

```sql
-- See which steps completed for sample postings
SELECT posting_id, 
       current_step,
       jsonb_object_keys(outputs) as completed_conversation_ids
FROM posting_state_projection 
WHERE posting_id IN (2, 3, 4, 5)
ORDER BY posting_id;

-- Count completions by step
SELECT 
    COUNT(CASE WHEN outputs ? '3335' THEN 1 END) as step3_done,
    COUNT(CASE WHEN outputs ? '3336' THEN 1 END) as step4_done,
    COUNT(CASE WHEN outputs ? '3337' THEN 1 END) as step5_done
FROM posting_state_projection;
```

### Recipe 2: Inspect Actual Outputs

```sql
-- See first 200 chars of step 3 output for posting 2
SELECT posting_id,
       SUBSTRING(outputs->>'3335', 1, 200) as step3_summary_preview
FROM posting_state_projection 
WHERE posting_id = 2;

-- See full output
SELECT outputs->'3335' as full_summary
FROM posting_state_projection 
WHERE posting_id = 2;
```

### Recipe 3: Check Event History

```sql
-- See all events for a posting
SELECT event_id,
       event_type,
       event_data->>'conversation_name' as step_name,
       event_data->>'execution_order' as step_num,
       SUBSTRING(event_data->>'output', 1, 100) as output_preview,
       event_timestamp
FROM execution_events 
WHERE aggregate_id = '2'
ORDER BY event_id;

-- Count events by type
SELECT event_type, COUNT(*) 
FROM execution_events 
GROUP BY event_type;

-- Events in last hour
SELECT COUNT(*), event_data->>'conversation_name' as step
FROM execution_events 
WHERE event_timestamp > NOW() - INTERVAL '1 hour'
GROUP BY step;
```

### Recipe 4: Find Where Workflow Got Stuck

```sql
-- Distribution of current steps
SELECT current_step, current_status, COUNT(*) 
FROM posting_state_projection 
GROUP BY current_step, current_status 
ORDER BY current_step;

-- Postings that haven't moved in 30 minutes
SELECT posting_id, current_step, current_status, last_updated
FROM posting_state_projection 
WHERE last_updated < NOW() - INTERVAL '30 minutes'
  AND current_status NOT IN ('TERMINAL', 'completed')
LIMIT 20;
```

---

## Branching Issues

### Debug Branch Matching

**Check branch configuration:**
```sql
SELECT c.canonical_name,
       ist.branch_condition,
       ist.next_conversation_id,
       c2.canonical_name as next_step_name,
       ist.branch_priority
FROM instruction_steps ist
JOIN instructions i ON ist.instruction_id = i.instruction_id
JOIN conversations c ON i.conversation_id = c.conversation_id
LEFT JOIN conversations c2 ON ist.next_conversation_id = c2.conversation_id
WHERE c.conversation_id = 3337  -- Step 5
ORDER BY ist.branch_priority DESC;
```

**Check actual outputs vs expected:**
```sql
-- What did the LLM actually output?
SELECT 
    posting_id,
    SUBSTRING(event_data->>'output', 1, 50) as output_start,
    event_data->>'output' ~ '^\[PASS\]' as starts_with_pass,
    event_data->>'output' ~ '^\[FAIL\]' as starts_with_fail
FROM execution_events 
WHERE event_data->>'conversation_id' = '3337'
LIMIT 10;
```

**Common branch matching bugs:**

1. **Exact match fails:**
   ```
   Condition: [PASS]
   Output: [PASS]\n\nThe summary is good...
   Match: FALSE ❌ (output has extra text)
   ```
   Fix: Use `startswith()` for bracket conditions

2. **Priority wrong:**
   ```
   [*] priority 100  ← Catches everything first!
   [PASS] priority 10
   ```
   Fix: Give specific conditions higher priority

3. **Regex not anchored:**
   ```
   Condition: /PASS/
   Output: "This will PASS the test"
   Match: TRUE ✓ (but shouldn't!)
   ```
   Fix: Anchor regex `^[PASS]`

---

## Performance Debugging

### Monitor Active Processing

```bash
# Real-time log following
tail -f logs/workflow_3001_*.log | grep -E "posting_completed|wave_progress"

# Count completions per minute
watch -n 10 'grep "posting_completed" logs/workflow_3001_*.log | tail -60 | wc -l'

# Average time per posting
grep "avg_time_sec" logs/workflow_3001_*.log | tail -1
```

### Check LLM Performance

```sql
-- Average tokens and duration by conversation
SELECT 
    event_data->>'conversation_name' as step,
    COUNT(*) as executions,
    AVG((event_data->>'tokens')::INT) as avg_tokens,
    AVG((event_data->>'duration_ms')::INT) as avg_duration_ms
FROM execution_events 
WHERE event_type = 'llm_call_completed'
GROUP BY step
ORDER BY avg_duration_ms DESC;
```

### Find Slow Postings

```sql
-- Which postings take longest at step 5?
SELECT 
    aggregate_id as posting_id,
    (event_data->>'duration_ms')::INT as duration_ms,
    SUBSTRING(event_data->>'output', 1, 100) as output_preview
FROM execution_events 
WHERE event_data->>'conversation_id' = '3337'
ORDER BY (event_data->>'duration_ms')::INT DESC
LIMIT 10;
```

---

## Quick Reference Commands

```bash
# Start workflow
cd /home/xai/Documents/ty_wave && source venv/bin/activate
python3 -m core.wave_processor.cli --workflow 3001

# Stop workflow
pkill -f "wave_processor.*3001"

# Monitor progress
python3 tools/monitor_workflow.py --workflow 3001 --mode snapshot

# Check process
ps aux | grep wave_processor | grep -v grep

# Recent activity
tail -100 logs/workflow_3001_*.log | grep "posting_completed"

# Current state
PGPASSWORD=base_yoga_secure_2025 psql -h localhost -U base_admin -d turing -c \
"SELECT current_step, current_status, COUNT(*) FROM posting_state_projection GROUP BY current_step, current_status;"
```

---

## Real-World Case Study: Idempotency Bug

**See:** `IDEMPOTENCY_BUG_POSTMORTEM.md` for complete analysis

**Problem:** 2,034 postings skipped grading workflow (steps 4-10) and jumped to step 11+

**Root Cause:** `tools/idempotency_check.py` queried wrong source of truth:
- ❌ Queried `postings.extracted_summary` (legacy table column)
- ✅ Should query `posting_state_projection.outputs ? '3335'` (event-sourced projection)

**Impact:**
- 2,034 postings misrouted
- 5,750 invalid events created
- GPU idle (workflow thought work complete)
- Monitor showed 100% completion (false positive)

**Recovery:**
1. Reset 2,034 postings to step 4
2. Mark 5,750 events as invalid
3. Selective rebuild (restore step 3 outputs only)
4. Update monitor to filter invalid events
5. Restart workflow

**Time Cost:** 7 hours debugging + ~22 hours re-processing

**Prevention:**
- Fix idempotency_check.py to query projection
- Add integration tests (steps 1-21 end-to-end)
- Document "projection is source of truth"

**See full post-mortem for lessons learned and prevention strategy.**

---

## Key Debugging Principles

**1. Events Are Immutable**
- ❌ Never DELETE events (breaks audit trail, aggregate versioning)
- ✅ Mark events as invalid (`invalidated = TRUE`)
- ✅ Filter invalid events in queries (`COALESCE(invalidated, FALSE) = FALSE`)

**2. Projection Is Source of Truth**
- ❌ Don't query table columns (`postings.extracted_summary`)
- ✅ Query projection outputs (`posting_state_projection.outputs ? '3335'`)
- ✅ Dual source of truth causes bugs

**3. Preserve Work**
- ✅ Selective rebuild (restore specific conversation outputs)
- ✅ Event invalidation (mark bad, keep good)
- ❌ Nuclear reset (only in test environments)

**4. Understand Event Sourcing**
- Events = What actually happened (immutable history)
- Projection = Current state (derived from events, rebuildable)
- Monitor = Interpretation of events (must filter invalid)

**5. When in Doubt**
- Read `EVENT_SOURCING_PRACTICES.md`
- Check execution_events table (what really happened?)
- Verify projection matches events
- Mark invalid, don't delete

---

## Common Anti-Patterns

❌ **Deleting events** → Breaks audit trail  
✅ **Mark events invalid** → Preserves history

❌ **Querying table columns** → Dual source of truth  
✅ **Query projection outputs** → Single source

❌ **Patching projection manually** → Diverges from events  
✅ **Rebuild from events** → Ensures consistency

❌ **Nuclear reset in production** → Loses valuable work  
✅ **Selective invalidation** → Preserves good data

❌ **Ignoring monitor discrepancies** → Hides bugs  
✅ **Investigate root cause** → Prevents recurrence

---

## Quick Reference: Event Invalidation

```sql
-- Mark invalid events
UPDATE execution_events 
SET invalidated = TRUE,
    invalidation_reason = 'Brief explanation of why invalid'
WHERE <criteria>;

-- Query valid events only
SELECT * FROM execution_events 
WHERE COALESCE(invalidated, FALSE) = FALSE;

-- Count invalid events
SELECT COUNT(*), invalidation_reason
FROM execution_events 
WHERE invalidated = TRUE
GROUP BY invalidation_reason;

-- Audit trail
SELECT event_id, event_type, event_timestamp, 
       event_data->>'conversation_id' as conv,
       invalidated, invalidation_reason
FROM execution_events 
WHERE aggregate_id = '4612'
ORDER BY event_id;
```

See `EVENT_INVALIDATION.md` for complete pattern.

---

**End of Cookbook**

Remember: **Events are sacred. Interpretation can change.** When debugging, mark events as invalid - don't rewrite history. 🎯

### Current Architecture Gaps

**What We Have:**
- `execution_events` - Immutable event log (source of truth)
- `posting_state_projection` - Current state + outputs cache (JSONB)
- `posting_state_snapshots` - Performance optimization snapshots
- `posting_processing_status` - Boolean milestone flags

**The Problem:**
- Smart resets require manual SQL (`DELETE WHERE execution_order >= N`)
- No way to compare "before fix" vs "after fix" results
- Monitor shows cumulative events from all runs (no run isolation)
- Lost 355 summaries in nuclear reset - could have been preserved
- No checkpoint system for risky changes

### Proposed Solutions

#### Enhancement 1: Workflow Run Tracking (Lightweight) ⭐

**Purpose:** Tag events and state by workflow run for filtering and isolation.

```sql
-- Track distinct workflow runs
CREATE TABLE workflow_runs (
    run_id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status TEXT,  -- 'running', 'completed', 'failed', 'superseded'
    start_step INTEGER,
    end_step INTEGER,
    notes TEXT
);

-- Tag events with run_id
ALTER TABLE execution_events 
ADD COLUMN workflow_run_id INTEGER REFERENCES workflow_runs(run_id);

-- Tag projection with last run_id
ALTER TABLE posting_state_projection 
ADD COLUMN last_workflow_run_id INTEGER REFERENCES workflow_runs(run_id);
```

**Benefits:**
- Monitor queries filter by run: `WHERE workflow_run_id = 5` (current run only!)
- Mark old runs as 'superseded' instead of deleting events
- Historical analysis: "How long did run 3 take vs run 5?"
- Lightweight - just integer tags

**Example Usage:**
```sql
-- Start new run
INSERT INTO workflow_runs (workflow_id, status, start_step, notes)
VALUES (3001, 'running', 2, 'Testing branch fix')
RETURNING run_id;  -- Returns: 5

-- Update executor to tag events
-- event_data JSON now includes: workflow_run_id = 5

-- Monitor current run only
SELECT COUNT(*) 
FROM execution_events 
WHERE workflow_run_id = 5 
  AND event_data->>'execution_order' = '5';

-- Mark old run as superseded
UPDATE workflow_runs 
SET status = 'superseded', notes = 'Branch logic was broken'
WHERE run_id = 4;
```

---

#### Enhancement 2: Smart Checkpoints (Medium Weight) ⭐⭐

**Purpose:** Snapshot outputs before risky changes for easy rollback.

```sql
-- Checkpoint system for preservation
CREATE TABLE posting_state_checkpoints (
    checkpoint_id SERIAL PRIMARY KEY,
    posting_id INTEGER NOT NULL,
    checkpoint_name TEXT,  -- 'before_step5_fix', 'end_of_extraction'
    checkpoint_step INTEGER,
    outputs JSONB,  -- Snapshot of outputs at this point
    conversation_history JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    workflow_run_id INTEGER,
    notes TEXT,
    
    INDEX idx_checkpoint_name (checkpoint_name),
    INDEX idx_checkpoint_posting (posting_id, checkpoint_name)
);

-- Helper function to create checkpoint for all postings
CREATE FUNCTION create_workflow_checkpoint(
    p_name TEXT,
    p_notes TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    checkpoint_count INTEGER;
BEGIN
    INSERT INTO posting_state_checkpoints 
        (posting_id, checkpoint_name, checkpoint_step, outputs, conversation_history, notes)
    SELECT 
        posting_id,
        p_name,
        current_step,
        outputs,
        conversation_history,
        p_notes
    FROM posting_state_projection;
    
    GET DIAGNOSTICS checkpoint_count = ROW_COUNT;
    RETURN checkpoint_count;
END;
$$ LANGUAGE plpgsql;

-- Helper function to restore from checkpoint
CREATE FUNCTION restore_from_checkpoint(
    p_checkpoint_name TEXT
) RETURNS INTEGER AS $$
DECLARE
    restored_count INTEGER;
BEGIN
    UPDATE posting_state_projection p
    SET outputs = c.outputs,
        current_step = c.checkpoint_step,
        conversation_history = c.conversation_history,
        current_status = 'pending'
    FROM posting_state_checkpoints c
    WHERE p.posting_id = c.posting_id 
      AND c.checkpoint_name = p_checkpoint_name;
    
    GET DIAGNOSTICS restored_count = ROW_COUNT;
    RETURN restored_count;
END;
$$ LANGUAGE plpgsql;
```

**Benefits:**
- Safe experimentation: checkpoint → test → rollback if needed
- Compare results: keep both checkpoint and new outputs
- Named snapshots: descriptive names instead of "outputs from 2 hours ago"
- Protects against accidental data loss

**Example Usage:**
```sql
-- Before fixing branch logic
SELECT create_workflow_checkpoint(
    'before_branch_fix',
    'Saved outputs from steps 2-4 before testing new branch matching'
);
-- Returns: 2089 (checkpointed 2089 postings)

-- Run workflow with fix... oops, outputs worse!

-- Restore previous state
SELECT restore_from_checkpoint('before_branch_fix');
-- Returns: 2089 (restored 2089 postings)

-- List checkpoints
SELECT checkpoint_name, 
       checkpoint_step, 
       COUNT(*) as posting_count,
       MIN(created_at) as created_at,
       notes
FROM posting_state_checkpoints
GROUP BY checkpoint_name, checkpoint_step, notes
ORDER BY created_at DESC;
```

**Advanced: Automatic Checkpoints on Major Steps**

```sql
-- Auto-checkpoint when completing extraction phase
CREATE TRIGGER auto_checkpoint_after_extraction
AFTER UPDATE ON posting_state_projection
FOR EACH ROW
WHEN (OLD.current_step < 5 AND NEW.current_step >= 5)
EXECUTE FUNCTION create_auto_checkpoint('extraction_complete');
```

---

#### Enhancement 3: Projection History (Heavy Weight)

**Purpose:** Automatic audit trail of all projection changes.

```sql
CREATE TABLE posting_state_projection_history (
    history_id BIGSERIAL PRIMARY KEY,
    posting_id INTEGER NOT NULL,
    workflow_run_id INTEGER,
    snapshot_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Snapshot of projection state
    current_step INTEGER,
    current_status TEXT,
    outputs JSONB,
    conversation_history JSONB,
    total_tokens INTEGER,
    total_duration_ms INTEGER,
    
    -- Metadata
    changed_by TEXT,  -- 'workflow_3001', 'manual_reset', etc.
    change_type TEXT,  -- 'step_completed', 'reset', 'checkpoint'
    notes TEXT
);

-- Trigger to auto-record changes
CREATE OR REPLACE FUNCTION record_projection_history()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO posting_state_projection_history 
        (posting_id, current_step, current_status, outputs, conversation_history,
         total_tokens, total_duration_ms, changed_by, change_type)
    VALUES 
        (NEW.posting_id, NEW.current_step, NEW.current_status, NEW.outputs,
         NEW.conversation_history, NEW.total_tokens, NEW.total_duration_ms,
         current_user, 'auto_snapshot');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only trigger on significant changes (not every update)
CREATE TRIGGER track_projection_history
AFTER UPDATE ON posting_state_projection
FOR EACH ROW
WHEN (OLD.current_step != NEW.current_step OR 
      OLD.outputs != NEW.outputs)
EXECUTE FUNCTION record_projection_history();
```

**Benefits:**
- Complete audit trail of all changes
- Time-travel queries: "What was posting 123's state at 3pm?"
- Forensics: "When did we lose the summaries?"

**Cons:**
- Storage overhead (JSONB grows fast)
- Write amplification (trigger on every update)
- Maybe overkill - events already provide history

---

#### Enhancement 4: Replace posting_processing_status with View

**Current Problem:** `posting_processing_status` is derived data maintained separately.

**Solution:** Make it a view over projection.outputs

```sql
-- Drop the table (after confirming we don't need the extra fields)
DROP TABLE posting_processing_status;

-- Replace with view
CREATE VIEW posting_processing_status AS
SELECT 
    posting_id,
    
    -- Extract boolean flags from outputs JSONB
    (outputs ? '3335') as summary_extracted,  -- Step 3 conversation_id
    CASE WHEN outputs ? '3335' 
         THEN (SELECT event_timestamp FROM execution_events 
               WHERE aggregate_id::INT = posting_id 
                 AND event_data->>'conversation_id' = '3335' 
               ORDER BY event_id DESC LIMIT 1)
         ELSE NULL 
    END as summary_extracted_at,
    
    (outputs ? '3348') as skills_extracted,  -- Skills step conversation_id
    CASE WHEN outputs ? '3348'
         THEN (SELECT event_timestamp FROM execution_events 
               WHERE aggregate_id::INT = posting_id 
                 AND event_data->>'conversation_id' = '3348' 
               ORDER BY event_id DESC LIMIT 1)
         ELSE NULL 
    END as skills_extracted_at,
    
    (outputs ? '3352') as ihl_analyzed,  -- IHL step conversation_id
    CASE WHEN outputs ? '3352'
         THEN (SELECT event_timestamp FROM execution_events 
               WHERE aggregate_id::INT = posting_id 
                 AND event_data->>'conversation_id' = '3352' 
               ORDER BY event_id DESC LIMIT 1)
         ELSE NULL 
    END as ihl_analyzed_at,
    
    -- Computed completeness
    (outputs ? '3335' AND outputs ? '3348' AND outputs ? '3352') as processing_complete,
    
    -- Latest activity
    (SELECT MAX(event_timestamp) FROM execution_events 
     WHERE aggregate_id::INT = posting_id) as last_processed_at

FROM posting_state_projection;
```

**Benefits:**
- Always in sync (no separate updates needed)
- One source of truth (projection.outputs)
- No data duplication

**Cons:**
- Slightly slower queries (view computation)
- Can't store workflow_run_id per stage (but could add to outputs)

---

### Recommended Implementation Order

**Phase 1: Quick Wins (Do This Week)**
1. ✅ Add `workflow_runs` table
2. ✅ Tag new events with `workflow_run_id`
3. ✅ Update monitor to filter by run
4. ✅ Add `last_workflow_run_id` to projection

**Phase 2: Safety Net (Do Before Next Major Workflow)**
1. ✅ Add `posting_state_checkpoints` table
2. ✅ Add helper functions (create/restore checkpoint)
3. ✅ Document checkpoint workflow in cheat sheet
4. ✅ Test checkpoint/restore cycle

**Phase 3: Cleanup (When We Have Time)**
1. ⏸️ Evaluate if we need `posting_processing_status` table
2. ⏸️ Consider replacing with view
3. ⏸️ Consider projection_history (only if needed for auditing)

---

### Discussion Questions for Arden

1. **Workflow Run Tracking:** Worth the small overhead to tag events by run? Would clean up monitor queries significantly.

2. **Checkpoint System:** Would you use manual checkpoints before risky changes? Or prefer automatic checkpoints at major milestones (end of extraction, end of grading, etc.)?

3. **posting_processing_status:** Keep as table or convert to view? Currently it's derived data that needs manual maintenance.

4. **Projection History:** Do we need full audit trail? Or is event log + occasional checkpoints enough?

5. **Storage Concerns:** JSONB compresses well, but 2089 postings × 21 steps × outputs could grow. Set retention policy? (Keep checkpoints for 30 days, delete older ones?)

6. **Integration:** Should checkpoint creation be integrated into wave_processor CLI? (`--checkpoint-before` and `--checkpoint-after` flags?)

---

---

**End of Cookbook - Outdated Sections Removed (Nov 21, 2025)**

The sections below (Future Enhancements, Status Report) were removed as they're now outdated. The actual implementations and patterns are documented in:
- `EVENT_INVALIDATION.md` - Event invalidation pattern (implemented)
- `PROJECTION_REBUILD.md` - Projection rebuild patterns (implemented)
- `IDEMPOTENCY_BUG_POSTMORTEM.md` - Real production case study

---
