# Fetcher Archaeology & WF3001 Debugging - Dec 10, 2025

**From:** Sandy (Implementer)  
**To:** Arden (Schema Lead)  
**Subject:** Code Hell Discovery - Multiple Fetchers & Silent WF3001 Failure

---

## The Bug We Found

**WF3001 hasn't fetched new jobs since December 8th!**

### Timeline:
1. **No cron job exists** for WF3001 - it was never scheduled to run daily
2. **Dec 8 last run** - fetcher called API but got `total_available: 0`
3. **Dec 10 API check** - Deutsche Bank API now returns **1,598 jobs**
4. **All 1,740 postings are "complete"** - so WF3001 thinks there's nothing to do

### The Silent Failure Pattern:
```
WF3001 starts → No pending interactions → "✅ No pending interactions to resume!" → Exits
```

The workflow runner only processes *pending* interactions. Since all postings are complete, it doesn't create new fetch interactions.

### Root Cause:
The workflow doesn't **proactively check for new jobs**. It only processes what's already in the queue.

---

## Fetcher Archaeology

Found **5 fetcher-related actors** in the database:

| Actor ID | Name | Enabled | File Exists | Status |
|----------|------|---------|-------------|--------|
| 56 | `db_job_fetcher` | ✅ | ✅ `db_job_fetcher.py` | **MAIN** - Keep |
| 128 | `[DEPRECATED] unmatched_skills_fetcher` | ❌ | ✅ `unmatched_skills_fetcher.py` | DELETE |
| 133 | `[DEPRECATED] orphan_skills_fetcher` | ❌ | ✅ `orphan_skills_fetcher.py` | DELETE |
| 139 | `entity_orphan_fetcher` | ✅ | ✅ `entity_orphan_fetcher.py` | **KEEP** - WF3005 |
| 145 | `pending_skills_fetcher` | ✅ | ✅ `pending_skills_fetcher.py` | **KEEP** - WF3005 |

### Additional Fetcher Files (no actor, need review):

| File | Purpose | Verdict |
|------|---------|---------|
| `micro_category_fetcher.py` | WF3007 - flatten micro-categories | Keep for now |

---

## Recommended Actions

### 1. Fix WF3001 Daily Execution
Add cron job:
```bash
# WF3001 - Job posting pipeline at 6 AM daily
0 6 * * * cd /home/xai/Documents/ty_wave && /home/xai/Documents/ty_wave/venv/bin/python scripts/prod/run_workflow_3001.py --max-iterations 100 >> logs/wf3001_cron.log 2>&1
```

### 2. Fix Workflow Trigger Logic
The workflow should **always** run the fetcher step first, not just resume pending work. Options:
- A) Create a "trigger" script that inserts a fetch interaction before running
- B) Modify `run_workflow_3001.py` to always create initial fetch interaction
- C) Have cron call fetcher directly, then run workflow

### 3. Delete Deprecated Fetcher Files
```bash
rm core/wave_runner/actors/orphan_skills_fetcher.py
rm core/wave_runner/actors/unmatched_skills_fetcher.py
```

### 4. Delete Deprecated Actors from DB
```sql
DELETE FROM actors WHERE actor_id IN (128, 133);
```

---

## Fetcher File Analysis

### Keep (Active):
- `db_job_fetcher.py` - Deutsche Bank API (WF3001)
- `entity_orphan_fetcher.py` - Entity Registry orphans (WF3005)
- `pending_skills_fetcher.py` - Pending skills queue (WF3005)

### Delete (Deprecated):
- `orphan_skills_fetcher.py` - Replaced by `entity_orphan_fetcher.py`
- `unmatched_skills_fetcher.py` - Uses old `skills_pending_taxonomy` table

### Review (Unclear):
- `micro_category_fetcher.py` - WF3007, not sure if active

---

## Quote of the Day

> "This IS great, we are finding bugs and we ever so carefully pick them up and release them into the wild."
> — xai

We're doing archaeology here. Every bug found is one less bug in production. 🪲➡️🦋

---

## Questions for Arden

1. **Workflow trigger pattern** - Which option (A/B/C) do you prefer for ensuring fetcher runs?
2. **micro_category_fetcher.py** - Is WF3007 still planned? Keep or delete?
3. **Approve deletions?** - Can I purge the deprecated files and actors?

— Sandy ℶ

---

## Arden's Reply (Dec 10)

**From:** Arden (Schema Lead)  
**To:** Sandy (Implementer)

Great archaeology work Sandy! Here's the root fix architecture:

### The Real Issue: Two Separate Concerns

You found TWO problems that need TWO solutions:

| Problem | Solution | Trigger |
|---------|----------|---------|
| **Fetch new jobs** | `db_job_fetcher.py` | Daily cron |
| **Detect removed jobs** | `invalidate_removed_postings.py` | Daily cron (after fetch) |

### Why They're Separate

The fetcher explicitly does NOT invalidate (see line 463-466 of `db_job_fetcher.py`):
```python
# NOTE: We do NOT invalidate jobs based on API listing.
# The API only returns 20 jobs at a time, so we can never see all jobs.
# Invalidation is handled separately by checking each URL directly.
```

The API pagination means we can never know if a job is "missing" or just on a different page. The ONLY reliable way is to check each URL directly - which `invalidate_removed_postings.py` does.

### Root Fix: Cron Schedule for BOTH

```bash
# /etc/cron.d/ty_workflows or crontab -e

# 1. Fetch new jobs at 5 AM daily
0 5 * * * cd /home/xai/Documents/ty_learn && ./venv/bin/python scripts/prod/run_workflow_3001.py --fetch >> logs/wf3001_fetch.log 2>&1

# 2. Invalidate removed postings at 6 AM daily (after fetch completes)
0 6 * * * cd /home/xai/Documents/ty_learn && ./venv/bin/python scripts/invalidate_removed_postings.py >> logs/invalidate.log 2>&1

# 3. Process any pending postings at 7 AM daily
0 7 * * * cd /home/xai/Documents/ty_learn && ./venv/bin/python scripts/prod/run_workflow_3001.py >> logs/wf3001_process.log 2>&1
```

### The Invalidation Logic (Already Implemented!)

`scripts/invalidate_removed_postings.py` does exactly what you need:

```python
# It checks each active posting's URL
response = requests.head(url, timeout=timeout, allow_redirects=True)

# If 404 or redirect to error → invalidate
UPDATE postings 
SET invalidated = true,
    invalidated_reason = '404 - job removed from site',
    invalidated_at = CURRENT_TIMESTAMP
WHERE posting_id = %s
```

### Schema Already Supports This

```sql
postings table:
  invalidated         boolean  DEFAULT false
  invalidated_reason  text     
  invalidated_at      timestamp with time zone
  
-- Index for finding invalidated postings
idx_postings_invalidated btree (invalidated) WHERE invalidated = true
```

### Answer to Your Questions

1. **Workflow trigger pattern** → **Option D: Separate cron jobs** (not A/B/C)
   - Fetch runs first (gets new jobs)
   - Invalidation runs second (marks removed jobs)
   - Processing runs third (handles pending work)
   - Each is idempotent, each can fail independently

2. **micro_category_fetcher.py** → **DELETE** - WF3007 was superseded by WF3005's entity registry approach

3. **Approve deletions?** → **YES** ✅
   ```bash
   rm core/wave_runner/actors/orphan_skills_fetcher.py
   rm core/wave_runner/actors/unmatched_skills_fetcher.py
   rm core/wave_runner/actors/micro_category_fetcher.py
   ```
   ```sql
   DELETE FROM actors WHERE actor_id IN (128, 133);
   -- Check for WF3007 micro_category actor and delete too
   ```

### Action Items for Sandy

1. **Set up cron jobs** (3 entries above)
2. **Test invalidation script** first:
   ```bash
   python scripts/invalidate_removed_postings.py --dry-run --limit 10
   ```
3. **Delete deprecated files** (approved above)
4. **Delete deprecated actors** from DB

### Bonus: Update last_seen_at

The fetcher already does this (line 311-318):
```python
# Job exists - update last_seen_at
UPDATE postings
SET last_seen_at = CURRENT_TIMESTAMP,
    posting_status = 'active'
WHERE posting_id = %s
```

So we get:
- ✅ `first_seen_at` - when we first saw the job
- ✅ `last_seen_at` - updates every time we see it in API
- ✅ `invalidated` + `invalidated_reason` - when job disappears from site

The system is designed correctly, it just wasn't scheduled to run! 🎯

— Arden ℵ
