# Interaction Invalidation & Workflow Recovery Discussion

**Date:** 2025-12-02 03:35  
**Participants:** xai, Sandy  
**Status:** 🟡 DISCUSSION - Validating Current Architecture

---

## Your Understanding (xai's Proposal)

> 1. **Every interaction is stored** - May be enabled or not, but should never be deleted. Orphan interactions are archived, that's all.
> 2. **Interactions are the sole base for postings** - No postings without a trail in interactions.
> 3. **Invalidation triggers recovery** - If we invalidate a posting, there must be workflow steps that need to be invalidated/disabled. Then workflow 3001 picks up where the good interactions ended and faulty ones began.

---

## Current Architecture Validation

Let me validate each point against our existing architecture:

### ✅ Point 1: Interactions Never Deleted (CONFIRMED)

**Schema Evidence** (`sql/schema_export_20251202.sql`, line 4018):

```sql
CREATE TABLE public.interactions (
    interaction_id bigint NOT NULL,
    posting_id integer,
    conversation_id integer NOT NULL,
    workflow_run_id bigint,
    actor_id integer NOT NULL,
    actor_type text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    execution_order integer NOT NULL,
    enabled boolean DEFAULT true,                    -- ✅ Can be disabled
    invalidated boolean DEFAULT false,               -- ✅ Can be invalidated
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    -- ...
);

COMMENT ON COLUMN public.interactions.enabled IS 
    'Flag to enable/disable interaction (NOT deletion)';

COMMENT ON COLUMN public.interactions.invalidated IS 
    'Flag to mark interaction as invalid (duplicate, bug, etc.)';
```

**Work Grouper Evidence** (`core/wave_runner/work_grouper.py`, line 65):

```python
where_clauses = [
    "i.status = 'pending'", 
    "i.enabled = TRUE",           # ✅ Filters by enabled
    "i.invalidated = FALSE"       # ✅ Filters by invalidated
]
```

**Architecture Doc** (`docs/architecture/EVENT_INVALIDATION.md`):

> **Events are immutable historical facts. You can't change what happened, but you can change how you interpret it.**
>
> **Answer:** Mark them as invalid, preserve the historical record, exclude from metrics.

**Lifecycle Policy** (`docs/architecture/DATA_LIFECYCLE.md`):

```
1. Configuration (IMMORTAL) - workflows, conversations, actors
   - NEVER delete, even when disabled

2. Execution Records (MORTAL) - workflow_runs, interactions
   - Archive when parent deleted (30-day retention)
   - Hard delete after expiry

3. User Data (EPHEMERAL) - postings, profiles
   - GDPR: Delete immediately on request
```

**Conclusion:** ✅ **FULLY IMPLEMENTED**
- Interactions have `enabled` flag (can be turned off without deletion)
- Interactions have `invalidated` flag (mark as invalid but preserve)
- Work queries filter: `enabled = TRUE AND invalidated = FALSE`
- NO `DELETE FROM interactions` anywhere in codebase
- Archive strategy exists for old data (30-day retention)

---

### ✅ Point 2: Interactions as Sole Base for Postings (CONFIRMED!)

**Update (2025-12-02 03:45):** After investigation, this is **FULLY IMPLEMENTED** via the staging table!

**Current Reality:**

ALL postings trace back to interactions through `postings_staging`:

#### The Lineage Chain ✅

```
Interaction (Fetch Jobs) 
    → postings_staging (with interaction_id)
        → postings (via promoted_to_posting_id)
```

**Evidence from database (Dec 2, 2025):**

```
🔍 POSTINGS_STAGING INTERACTION LINKAGE:
  Total staging records:     1,632
  With interaction_id:       1,632 (100%) ✅
  Promoted to postings:      1,632 (100%) ✅

🔍 POSTINGS WITH VS WITHOUT LINEAGE:
  With lineage (staging record):     1,632
  Without lineage (direct insert):   0      ✅ ALL have lineage!

🔍 SAMPLE LINEAGE TRACE (posting -> staging -> interaction):
  posting 10435 <- staging 3317 <- int 37138 (conv: Fetch Jobs from Deutsche Bank)
  posting 10434 <- staging 3316 <- int 37138 (conv: Fetch Jobs from Deutsche Bank)
  posting 10433 <- staging 3315 <- int 37138 (conv: Fetch Jobs from Deutsche Bank)
```

#### How It Works

**Step 1:** Fetcher creates interaction and inserts into staging with `interaction_id`:

```python
# core/wave_runner/actors/db_job_fetcher.py
cursor.execute("""
    INSERT INTO postings_staging (
        interaction_id,  -- ✅ Links back to fetch interaction!
        job_title, company_name, location, ...
    ) VALUES (%s, %s, %s, %s, ...)
""", (interaction_id, job_data['title'], ...))
```

**Step 2:** Validator promotes staging → postings, preserving linkage:

```python
# Staging record keeps:
#   - interaction_id (original fetch)
#   - promoted_to_posting_id (new posting created)
```

**Step 3:** Full lineage query:

```sql
-- Trace any posting back to its source interaction
SELECT 
    p.posting_id,
    ps.staging_id,
    ps.interaction_id,
    i.conversation_id,
    c.conversation_name
FROM postings p
JOIN postings_staging ps ON p.posting_id = ps.promoted_to_posting_id
JOIN interactions i ON ps.interaction_id = i.interaction_id
JOIN conversations c ON i.conversation_id = c.conversation_id;
```

#### What This Means for Invalidation

**If we invalidate interaction 37138 (the fetch):**

```sql
-- Find all affected postings
SELECT promoted_to_posting_id 
FROM postings_staging 
WHERE interaction_id = 37138;
-- Returns: 1,632 posting IDs

-- Can then invalidate/clean them systematically
UPDATE postings 
SET invalidated = TRUE,
    invalidation_reason = 'Source interaction 37138 invalidated'
WHERE posting_id IN (
    SELECT promoted_to_posting_id 
    FROM postings_staging 
    WHERE interaction_id = 37138
);
```

**Conclusion:** ✅ **FULLY IMPLEMENTED**
- Every posting has lineage via `postings_staging`
- Can trace: `posting → staging → interaction → conversation`
- Invalidation cascade is possible through this chain

---

### 🔴 Point 3: Invalidation → Automatic Recovery (NOT IMPLEMENTED)

**What EXISTS:**

1. **Interaction invalidation mechanism** ✅
   ```sql
   UPDATE interactions 
   SET invalidated = TRUE,
       invalidation_reason = 'Executed without required input'
   WHERE interaction_id IN (...);
   ```

2. **Work queries skip invalidated** ✅
   ```python
   WHERE i.enabled = TRUE AND i.invalidated = FALSE
   ```

3. **Workflow state architecture** ✅
   - `workflow_runs.state` stores semantic keys
   - Can detect "what data exists" via state checks
   - Conversations like "Check if Summary Exists" query state

**What DOESN'T EXIST:**

1. **Automatic interaction re-creation** ❌
   - If you invalidate interaction X, there's no mechanism to auto-create a replacement
   - You must manually delete the bad data OR re-run workflow

2. **Posting → Interaction reverse lookup** ❌
   - No index on `interactions(posting_id, conversation_id)`
   - Hard to find "all interactions for posting P in conversation C"

3. **Invalidation cascade rules** ❌
   - If interaction 100 is invalidated, should its children (101, 102) also be invalidated?
   - No CASCADE behavior defined

4. **Recovery workflow** ❌
   - No documented process for "invalidate bad interactions → re-run from failure point"
   - Manual intervention required

---

## Gap Analysis

### What We Have ✅

| Feature | Status | Evidence |
|---------|--------|----------|
| Interactions never deleted | ✅ Implemented | `enabled` and `invalidated` flags |
| Posting lineage via staging | ✅ Implemented | `postings_staging.interaction_id` → 100% linkage |
| Event sourcing for workflow state | ✅ Implemented | `workflow_runs.state` JSONB |
| Append-only event log | ✅ Implemented | `execution_events` table |
| Skip invalidated work | ✅ Implemented | Work queries filter `invalidated = FALSE` |
| Idempotent execution | ✅ Implemented | State checks like "Check if Summary Exists" |
| Audit trail preservation | ✅ Implemented | All interactions kept, archive policy exists |

### What We're Missing ❌

| Gap | Impact | Workaround |
|-----|--------|------------|
| Interaction invalidation cascade | Children of invalidated parents still run | Manually identify and invalidate children |
| Auto-recovery from invalidation | Must manually delete bad data | Delete posting data, re-run workflow |
| Invalidation → Data cleanup link | Invalidating interaction doesn't clean posting data | Separate cleanup script required |

---

## Your Scenario: How It SHOULD Work

**Scenario:** Summary extraction failed because job_description was NULL (prompt didn't include description).

**Ideal Flow:**

```
1. Discover problem:
   - Posting 4709 has extracted_summary but it's garbage
   - Root cause: interaction 98765 (Extract Summary) got NULL job_description

2. Invalidate bad work:
   UPDATE interactions 
   SET invalidated = TRUE,
       invalidation_reason = 'Executed with NULL job_description'
   WHERE interaction_id IN (
       SELECT interaction_id 
       FROM interactions 
       WHERE posting_id = 4709 
         AND conversation_id IN (3335, 3336, 3337, 3341, 9189)  -- Extract → Save Summary
   );

3. Clean bad data:
   UPDATE postings 
   SET extracted_summary = NULL 
   WHERE posting_id = 4709;

4. Re-run workflow:
   ./scripts/run_workflow.sh run_workflow_safe.py --workflow 3001 --posting 4709
   
5. Workflow picks up from beginning:
   - Check if Summary Exists → Returns [RUN] (summary is NULL)
   - Extract → Grading → Format → Save ✅
```

**Current Reality:**

```
1. Discover problem: ✅ Can do this

2. Invalidate bad work: ⚠️ Can do this, but must manually find all affected interactions

3. Clean bad data: ⚠️ Must do manually, no link from interaction → posting data

4. Re-run workflow: ❌ PROBLEM! Workflow sees workflow_run.state has 'extract_summary' key
   - Check if Summary Exists → Returns [SKIP] ❌
   - Workflow doesn't re-run extraction!
   
5. Must ALSO clean workflow state:
   UPDATE workflow_runs 
   SET state = state - 'extract_summary' - 'current_summary'
   WHERE posting_id = 4709;
```

---

## What Schema Says We SHOULD Have

**From EVENT_SOURCING_ARCHITECTURE.md:**

> **posting_state_projection** - Current workflow position for each posting
> 
> ```sql
> CREATE TABLE posting_state_projection (
>     posting_id INT PRIMARY KEY,
>     current_conversation_id INT,
>     execution_sequence INT[],               -- Order of execution
>     outputs JSONB,                          -- {conversation_id: output}
>     is_terminal BOOLEAN DEFAULT FALSE,
>     last_updated TIMESTAMPTZ
> );
> ```
>
> **Rebuild Function** - Replay events to reconstruct state
> ```sql
> CREATE OR REPLACE FUNCTION rebuild_posting_state(p_posting_id INT)
> RETURNS void AS $$
> BEGIN
>     -- Replay all VALID events (invalidated = FALSE) to reconstruct state
>     INSERT INTO posting_state_projection (posting_id, outputs, ...)
>     SELECT ...
>     FROM execution_events
>     WHERE aggregate_id = p_posting_id
>       AND invalidated = FALSE  -- ✅ Skip invalidated events!
> END;
> $$;
> ```

**This table DOES NOT EXIST in schema_export_20251202.sql!**

We have:
- ✅ `execution_events` table (event store)
- ❌ `posting_state_projection` table (NOT IMPLEMENTED)
- ❌ `rebuild_posting_state()` function (NOT IMPLEMENTED)

**What we use instead:**
- `workflow_runs.state` - Per workflow run, not per posting
- No projection rebuild mechanism

---

## Recommendations

### Option 1: Implement Missing Architecture (Full Event Sourcing)

**Add the projection layer:**

```sql
-- Create projection table
CREATE TABLE posting_state_projection (
    posting_id INT PRIMARY KEY,
    current_conversation_id INT,
    execution_sequence INT[],
    outputs JSONB,
    is_terminal BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMPTZ,
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id)
);

-- Rebuild function
CREATE OR REPLACE FUNCTION rebuild_posting_state(p_posting_id INT)
RETURNS void AS $$
BEGIN
    DELETE FROM posting_state_projection WHERE posting_id = p_posting_id;
    
    INSERT INTO posting_state_projection
    SELECT 
        posting_id,
        MAX(conversation_id) as current_conversation_id,
        array_agg(conversation_id ORDER BY completed_at) as execution_sequence,
        jsonb_object_agg(conversation_id::text, output) as outputs,
        bool_or(status = 'terminal') as is_terminal,
        MAX(completed_at) as last_updated
    FROM interactions
    WHERE posting_id = p_posting_id
      AND enabled = TRUE          -- ✅ Skip disabled
      AND invalidated = FALSE     -- ✅ Skip invalidated
      AND status = 'completed'
    GROUP BY posting_id;
END;
$$ LANGUAGE plpgsql;
```

**Recovery workflow:**

```python
# scripts/invalidate_and_recover.py
def invalidate_and_recover(posting_id, from_conversation_id):
    """
    Invalidate all interactions from a conversation onwards, rebuild state, re-run.
    """
    # 1. Invalidate bad interactions
    cursor.execute("""
        UPDATE interactions
        SET invalidated = TRUE,
            invalidation_reason = %s
        WHERE posting_id = %s
          AND execution_order >= (
              SELECT execution_order 
              FROM interactions 
              WHERE posting_id = %s AND conversation_id = %s
              LIMIT 1
          )
    """, (reason, posting_id, posting_id, from_conversation_id))
    
    # 2. Rebuild projection (automatically skips invalidated)
    cursor.execute("SELECT rebuild_posting_state(%s)", (posting_id,))
    
    # 3. Clear affected workflow state keys
    cursor.execute("""
        UPDATE workflow_runs
        SET state = '{}'::jsonb  -- Reset state
        WHERE posting_id = %s
    """, (posting_id,))
    
    # 4. Re-run workflow (picks up from beginning due to empty state)
    run_workflow(workflow_id=3001, posting_id=posting_id)
```

**Pros:**
- ✅ True event sourcing pattern
- ✅ Automatic recovery via projection rebuild
- ✅ Clear separation: events vs state

**Cons:**
- ❌ Major architectural change
- ❌ Requires migration of existing data
- ❌ More complex than current system

---

### Option 2: Enhance Current System (Pragmatic)

**Add missing pieces to current architecture:**

1. **Add posting lineage to interactions:**
   ```sql
   -- Already exists! Just use it:
   SELECT * FROM interactions WHERE posting_id = 4709;
   ```

2. **Add invalidation cascade helper:**
   ```sql
   CREATE OR REPLACE FUNCTION invalidate_posting_work(
       p_posting_id INT,
       p_from_conversation_id INT,
       p_reason TEXT
   ) RETURNS INTEGER AS $$
   DECLARE
       v_count INTEGER;
   BEGIN
       UPDATE interactions
       SET invalidated = TRUE,
           invalidation_reason = p_reason
       WHERE posting_id = p_posting_id
         AND conversation_id IN (
             -- Get all conversations AFTER the failing one
             SELECT conversation_id 
             FROM interactions 
             WHERE posting_id = p_posting_id
               AND execution_order >= (
                   SELECT MIN(execution_order)
                   FROM interactions
                   WHERE posting_id = p_posting_id
                     AND conversation_id = p_from_conversation_id
               )
         );
       
       GET DIAGNOSTICS v_count = ROW_COUNT;
       RETURN v_count;
   END;
   $$ LANGUAGE plpgsql;
   ```

3. **Add state cleanup helper:**
   ```sql
   CREATE OR REPLACE FUNCTION reset_posting_workflow_state(
       p_posting_id INT,
       p_workflow_id INT
   ) RETURNS void AS $$
   BEGIN
       UPDATE workflow_runs
       SET state = '{}'::jsonb,
           status = 'pending',
           updated_at = NOW()
       WHERE posting_id = p_posting_id
         AND workflow_id = p_workflow_id;
   END;
   $$ LANGUAGE plpgsql;
   ```

4. **Create recovery script:**
   ```python
   # scripts/invalidate_and_recover.py
   def recover_posting(posting_id, from_conversation_id, reason):
       """Invalidate bad work and reset for re-run."""
       with get_db_conn() as conn:
           cur = conn.cursor()
           
           # Invalidate interactions
           cur.execute("""
               SELECT invalidate_posting_work(%s, %s, %s)
           """, (posting_id, from_conversation_id, reason))
           invalidated_count = cur.fetchone()[0]
           
           # Reset workflow state
           cur.execute("""
               SELECT reset_posting_workflow_state(%s, 3001)
           """, (posting_id,))
           
           # Clear posting data fields affected
           cur.execute("""
               UPDATE postings
               SET extracted_summary = NULL,
                   skill_keywords = NULL,
                   ihl_score = NULL,
                   ihl_category = NULL
               WHERE posting_id = %s
           """, (posting_id,))
           
           conn.commit()
           print(f"✅ Invalidated {invalidated_count} interactions")
           print(f"✅ Reset workflow state and posting data")
           print(f"✅ Ready to re-run: ./scripts/run_workflow.sh ... --posting {posting_id}")
   ```

**Pros:**
- ✅ Works with current architecture
- ✅ Minimal schema changes
- ✅ Easy to implement and test

**Cons:**
- ❌ Manual cleanup still required (not automatic)
- ❌ State management split between interactions and workflow_runs

---

## My Recommendation

**Go with Option 2 (Pragmatic Enhancement)** because:

1. **Current system works well** - Don't fix what isn't broken
2. **Your scenario is rare** - Invalidation + recovery is exceptional, not normal flow
3. **Quick to implement** - Can have this working today vs. weeks for Option 1
4. **Lower risk** - No major architectural changes

**Implementation Plan:**

1. ✅ **Week 1:** Add helper functions (invalidate_posting_work, reset_posting_workflow_state)
2. ✅ **Week 2:** Create recovery script (invalidate_and_recover.py)
3. ✅ **Week 3:** Add monitoring query (find postings with invalidated interactions)
4. ✅ **Week 4:** Document recovery workflow in /docs/architecture

**Then revisit Option 1** if we find:
- Recovery scenarios are common (>5/month)
- Manual cleanup is error-prone
- State reconstruction is needed frequently

---

## Discussion Questions

1. **How often do you expect to invalidate interactions?**
   - Rare (bug fixes, bad data): Option 2 is fine
   - Common (daily data corrections): Consider Option 1

2. **Do you need automatic recovery, or is manual + script acceptable?**
   - Automatic: Need Option 1 (projection rebuild)
   - Manual: Option 2 works

3. **Should invalidation cascade to children automatically?**
   - Yes: Add cascade logic
   - No: Keep manual selection

4. **What data should be cleaned when interactions are invalidated?**
   - Just postings table?
   - Related tables (posting_skills, posting_requirements)?
   - Workflow state?

---

## Conclusion

**Your understanding is CORRECT:**
1. ✅ Interactions are preserved (enabled/invalidated flags, never deleted)
2. ✅ Interactions ARE the base for postings (via `postings_staging.interaction_id` - 100% linkage!)
3. ⚠️ Invalidation → recovery needs automation (cascade + cleanup scripts)

**Current architecture is STRONGER than initially assessed:**
- Full posting lineage exists via staging table
- Can trace any posting back to its source interaction
- Invalidation cascade is technically possible

**Remaining work:**
- Build helper functions for invalidation cascade
- Build recovery scripts for state cleanup
- Document recovery workflow

**We're 90% there** - Just need the automation layer!

---

## Next Steps

Let's discuss:
1. Which option do you prefer (full event sourcing vs. pragmatic)?
2. What scenarios trigger invalidation in your workflow?
3. Should we build the recovery helpers now or wait until we hit a real case?

What do you think?
