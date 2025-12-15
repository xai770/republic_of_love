# Workflow 3001: Empty DB → Fully Enriched Postings

## Execution Plan

**Goal:** Start from empty database, end with postings that have summaries, skills, and IHL scores.

**Date:** December 2, 2025

---

## Phase 0: Schema Changes (Before Running)

### 0.1 Remove `postings_staging` table
Fetcher will write directly to `postings` with `posting_status='pending'`.

```sql
-- Backup first
CREATE TABLE postings_staging_backup AS SELECT * FROM postings_staging;
-- Then drop
DROP TABLE postings_staging CASCADE;
```

### 0.2 Update `db_job_fetcher.py`
- Change from: INSERT INTO postings_staging
- Change to: INSERT INTO postings (posting_status='pending')

### 0.3 Update Validator (9193)
- Change from: Promote staging → postings
- Change to: UPDATE postings SET posting_status='active' WHERE posting_status='pending'

---

## Phase 1: Single Posting Test (n=1)

**Purpose:** Verify entire pipeline works end-to-end.

### Command
```bash
python3 examples/run_workflow_3001.py --max-jobs 1
```

### Expected `_workflow_flowchart.py` Output
```
WORKFLOW 3001: Complete Job Processing Pipeline
═══════════════════════════════════════════════════════════════════════

📊 POSTING TOTALS: 1 total | 1 active | 0 summaries | 0 skills | 0 IHL

STEP  CONVERSATION                           ACTOR                  STATUS
───────────────────────────────────────────────────────────────────────
1/16  ⚙️  Fetch Jobs from Deutsche Bank API   db_job_fetcher         ✅ 1 completed
2/16  ⚙️  Validate Job Description            sql_query_executor     ✅ 1 completed
3/16  🤖 session_a_llama32_extract           llama3.2:latest        🔄 1 running
4/16  🤖 session_b_mistral_grade             mistral:latest         ⏳ 0 pending
...
```

### Success Criteria
```sql
SELECT posting_id, posting_status, 
       extracted_summary IS NOT NULL as has_summary,
       skill_keywords IS NOT NULL as has_skills,
       ihl_score IS NOT NULL as has_ihl
FROM postings;

-- Expected:
-- posting_id | posting_status | has_summary | has_skills | has_ihl
-- -----------+----------------+-------------+------------+---------
--        1   | complete       | t           | t          | t
```

---

## Phase 2: Small Batch Test (n=5)

**Purpose:** Verify parallel processing works, no race conditions.

### Command
```bash
python3 examples/run_workflow_3001.py --max-jobs 5
```

### Expected `_workflow_flowchart.py` Output
```
📊 POSTING TOTALS: 5 total | 5 active | 0 summaries | 0 skills | 0 IHL

STEP  CONVERSATION                           ACTOR                  STATUS
───────────────────────────────────────────────────────────────────────
1/16  ⚙️  Fetch Jobs from Deutsche Bank API   db_job_fetcher         ✅ 1 completed
2/16  ⚙️  Validate Job Description            sql_query_executor     ✅ 5 completed
3/16  🤖 session_a_llama32_extract           llama3.2:latest        🔄 2 running, 3 pending
...
```

### Success Criteria
- All 5 postings reach `posting_status='complete'`
- No duplicate interactions (auto-skip working)
- `interactions_history` empty (nothing deleted)

---

## Phase 3: Medium Batch (n=20)

**Purpose:** Full API batch (DB API limit is 20).

### Command
```bash
python3 examples/run_workflow_3001.py --max-jobs 20
```

### Expected Timing
- Fetch: ~5 seconds
- Validate: ~2 seconds (SQL check)
- Summary pipeline: ~20 postings × ~2 min = ~40 minutes
- Skills: ~20 postings × ~30s = ~10 minutes
- IHL: ~20 postings × ~90s = ~30 minutes
- **Total: ~80 minutes**

### Expected Progress (mid-run)
```
┌─────────────────────────────────────────────────────────────────────┐
│ WORKFLOW 3001 LIVE DASHBOARD                    Refresh: 30s       │
├─────────────────────────────────────────────────────────────────────┤
│ Workflow Runs: 1 running                                            │
│ Recent Activity (5m): 12 completions                                │
├─────────────────────────────────────────────────────────────────────┤
│ Progress by Step:                                                   │
│   Fetch:    [████████████████████████████████] 100%  (1/1)         │
│   Validate: [████████████████████████████████] 100%  (20/20)       │
│   Summary:  [████████████░░░░░░░░░░░░░░░░░░░░]  35%  (7/20)        │
│   Skills:   [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0%  (0/20)        │
│   IHL:      [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   0%  (0/20)        │
├─────────────────────────────────────────────────────────────────────┤
│ ETA: ~55 minutes remaining                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Success Criteria
- All 20 postings have summary + skills + IHL
- Can query: `SELECT * FROM postings WHERE ihl_score IS NOT NULL`

---

## Phase 4: Production Run (n=500)

**Purpose:** Process all available jobs.

### Prerequisites
- Phases 1-3 completed successfully
- Ollama models loaded and responsive
- Sufficient disk space for interactions table

### Command
```bash
# Run in batches of 20 (API limit)
for i in {1..25}; do
  echo "=== Batch $i/25 ==="
  python3 examples/run_workflow_3001.py --max-jobs 20
  sleep 60  # Rate limit between batches
done
```

Or create a batch runner script.

### Expected Timing
- 500 postings ÷ 20 per batch = 25 batches
- ~80 minutes per batch
- **Total: ~33 hours** (with rate limiting)

### Monitoring
```bash
# Terminal 1: Workflow monitor
python3 tools/_show_3001.py

# Terminal 2: Check status periodically
watch -n 60 './scripts/q.sh "SELECT posting_status, COUNT(*) FROM postings GROUP BY 1"'
```

---

## Verification Queries

### After Each Phase
```sql
-- Overall progress
SELECT 
    COUNT(*) as total_postings,
    COUNT(extracted_summary) as has_summary,
    COUNT(skill_keywords) as has_skills,
    COUNT(ihl_score) as has_ihl,
    COUNT(*) FILTER (WHERE posting_status = 'complete') as fully_complete
FROM postings;

-- Interactions audit
SELECT 
    c.conversation_name,
    COUNT(*) as interactions,
    COUNT(*) FILTER (WHERE i.status = 'completed') as completed,
    COUNT(*) FILTER (WHERE i.status = 'failed') as failed
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
GROUP BY c.conversation_name
ORDER BY COUNT(*) DESC;

-- Check for orphaned/skipped
SELECT COUNT(*) as skipped FROM interactions WHERE status = 'skipped';

-- IHL distribution
SELECT ihl_category, COUNT(*) 
FROM postings 
WHERE ihl_score IS NOT NULL
GROUP BY ihl_category;
```

---

## Rollback Plan

If something goes wrong:

```sql
-- Check what happened
SELECT status, COUNT(*) FROM interactions GROUP BY status;
SELECT status, COUNT(*) FROM workflow_runs GROUP BY status;

-- Mark failed workflow as aborted
UPDATE workflow_runs SET status = 'aborted' WHERE status = 'running';

-- Reset stuck interactions
UPDATE interactions SET status = 'failed' WHERE status = 'running';

-- If needed, restore staging from backup
-- CREATE TABLE postings_staging AS SELECT * FROM postings_staging_backup;
```

---

## Checklist

- [ ] Phase 0: Schema changes applied
- [ ] Phase 0: db_job_fetcher.py updated
- [ ] Phase 0: Validator updated
- [ ] Phase 1: Single posting test passed
- [ ] Phase 2: 5 postings test passed
- [ ] Phase 3: 20 postings test passed
- [ ] Phase 4: 500 postings complete
- [ ] Verification queries all pass

---

## Arden's Comments (Dec 2, 2025)

**Overall:** This is a solid execution plan. The phased approach (1 → 5 → 20 → 500) is exactly right. Some additions:

### On Phase 0: Removing `postings_staging` ⚠️

I'm **cautious** about removing staging entirely. The staging table serves as a buffer:
- Bad data stays in staging until validated
- Production `postings` table stays clean
- Easy rollback if fetcher has bugs

**Alternative approach:**
Instead of removing staging, keep the two-table pattern but make the validator smarter:
```sql
-- Validator promotes valid rows
INSERT INTO postings SELECT * FROM postings_staging WHERE validated = true;
DELETE FROM postings_staging WHERE validated = true;
```

**If we DO remove staging:** Make sure `posting_status` has proper constraints and the fetcher can't accidentally create invalid postings.

### On Timing Estimates 📊

Your estimates look reasonable, but remember:
- **llama3.2:latest** for extraction is ~4s per posting (from Dec 1 benchmark)
- **qwen2.5:7b** for formatting is ~3s per posting
- **IHL three-model chain** is the slowest (~90s total agreed)

For 20 postings:
- Summary pipeline: 20 × 2 min = 40 min ✓ (includes grading + possible improvement loops)
- Skills: 20 × 30s = 10 min ✓
- IHL: 20 × 90s = 30 min ✓

Looks correct!

### On Phase 4: Batch Loop ⚠️

The bash loop approach works but has issues:
```bash
for i in {1..25}; do
  python3 examples/run_workflow_3001.py --max-jobs 20
  sleep 60
done
```

**Problems:**
1. If one batch fails, loop continues to next batch
2. No progress tracking between batches
3. 60s sleep is arbitrary - should wait for previous batch to complete

**Better approach:** Use our existing `run_workflow_safe.py` with global_batch mode:
```bash
# Start all workflow runs
python3 scripts/start_workflows_for_postings.py --limit 500

# Then run ONE global batch processor
python3 scripts/run_workflow_safe.py 3001
```

The runner will process all pending interactions in waves, much more efficient than 25 separate batches.

### Additional Verification Query 📋

Add this to catch model degeneration (from Dec 1 findings):

```sql
-- Check for degenerate outputs (repeated patterns)
SELECT posting_id, LEFT(extracted_summary, 100) as summary_start
FROM postings
WHERE extracted_summary IS NOT NULL
  AND extracted_summary ~ '(\w+\s+){3,}\1{5,}'  -- Repeated word patterns
LIMIT 10;
```

### Missing: Smoke Test Integration 🧪

We have `tests/test_workflow_3001_smoke.py` now. Add to checklist:

```
- [ ] Phase 1: Run smoke test first: `python3 tests/test_workflow_3001_smoke.py --posting-id <id>`
```

---

*— Arden*
