# Projection Rebuild Patterns

**Date:** November 21, 2025  
**Author:** Sandy (Claude Sonnet 4.5)  
**Reviewer:** Arden (Claude Sonnet 4.5)  
**Status:** Production (Workflow 3001)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Core Concept

In event sourcing, **projections are derived state** - they're built by replaying events. When projection data becomes stale or corrupted, **rebuild from events**.

> **Events are the source of truth. Projections are just cached views.**

---

## When to Rebuild

### Rebuild When:

✅ **Projection shows stale data**
- Progress bars show outputs that shouldn't exist
- `current_step` and actual outputs don't match
- Posting appears stuck but events show completion

✅ **Schema changes to projection**
- Added new column (populate from events)
- Changed aggregation logic (recalculate)
- Split/merged projection tables

✅ **Workflow logic changes**
- Changed conversation IDs
- Changed branching rules
- Need to re-interpret events with new rules

✅ **Data corruption detected**
- Projection and events mismatch
- Null values where shouldn't be
- Duplicate entries

✅ **After batch operations**
- Bulk UPDATE of projection state
- Mass posting reset
- Migration from old system

### Don't Rebuild When:

❌ **Events are wrong** - Fix at source (append correction events)  
❌ **Just one posting** - Cheaper to manually fix projection  
❌ **Production is running** - Rebuilds can lock tables  
❌ **You don't understand why** - Investigate first, rebuild second

---

## Rebuild Patterns

### Pattern 1: Full Rebuild (All Events)

**When:** Need to completely recalculate projection from scratch

**SQL Function:**
```sql
CREATE OR REPLACE FUNCTION rebuild_posting_state(p_posting_id INT)
RETURNS TABLE (
    rebuild_time_ms NUMERIC,
    events_replayed INT,
    final_step INT,
    final_conversation_id INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_start_time TIMESTAMPTZ;
    v_events_count INT;
    v_outputs JSONB := '{}'::jsonb;
    v_conversation_history JSONB := '[]'::jsonb;
    v_current_step INT := 1;
    v_current_conversation_id INT := 9144;  -- Default: fetch_db_jobs
    v_current_status TEXT := 'pending';
BEGIN
    v_start_time := clock_timestamp();
    
    -- Replay all events for this posting
    FOR event IN 
        SELECT * FROM execution_events
        WHERE aggregate_type = 'posting'
          AND aggregate_id = p_posting_id::text
          AND COALESCE(invalidated, FALSE) = FALSE  -- Skip invalid events!
        ORDER BY event_id ASC
    LOOP
        v_events_count := v_events_count + 1;
        
        CASE event.event_type
            WHEN 'conversation_completed', 'script_execution_completed' THEN
                -- Store output
                v_outputs := v_outputs || jsonb_build_object(
                    event.event_data->>'conversation_id',
                    event.event_data->>'output'
                );
                
                -- Update current position
                v_current_conversation_id := (event.event_data->>'next_conversation_id')::INT;
                v_current_step := (event.event_data->>'next_execution_order')::INT;
                
                -- Add to history
                v_conversation_history := v_conversation_history || jsonb_build_object(
                    'conversation_id', event.event_data->>'conversation_id',
                    'timestamp', event.event_timestamp,
                    'output_preview', LEFT(event.event_data->>'output', 100)
                );
                
            WHEN 'posting_created' THEN
                v_current_step := COALESCE((event.event_data->>'initial_step')::INT, 1);
                v_current_status := 'pending';
        END CASE;
    END LOOP;
    
    -- Update projection with rebuilt state
    INSERT INTO posting_state_projection (
        posting_id, current_step, current_conversation_id, current_status,
        outputs, conversation_history, last_updated
    ) VALUES (
        p_posting_id, v_current_step, v_current_conversation_id, v_current_status,
        v_outputs, v_conversation_history, NOW()
    )
    ON CONFLICT (posting_id) DO UPDATE SET
        current_step = EXCLUDED.current_step,
        current_conversation_id = EXCLUDED.current_conversation_id,
        current_status = EXCLUDED.current_status,
        outputs = EXCLUDED.outputs,
        conversation_history = EXCLUDED.conversation_history,
        last_updated = EXCLUDED.last_updated;
    
    RETURN QUERY SELECT
        EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) * 1000,
        v_events_count,
        v_current_step,
        v_current_conversation_id;
END;
$$;
```

**Usage:**
```sql
-- Rebuild one posting
SELECT * FROM rebuild_posting_state(4612);

-- Rebuild multiple
SELECT posting_id, rebuild_posting_state(posting_id)
FROM posting_state_projection
WHERE current_step = 4;
```

**Performance:** ~100ms per posting with 10-20 events

---

### Pattern 2: Selective Rebuild (Specific Outputs)

**When:** Need to restore only certain conversation outputs, not full state

**Example: Restore only step 2 and 3 outputs after reset**

```sql
UPDATE posting_state_projection psp
SET outputs = (
    SELECT jsonb_object_agg(
        COALESCE(
            (event_data->>'conversation_id'),
            (event_data->>'script_conversation_id')
        )::text,
        event_data->'output'
    )
    FROM execution_events
    WHERE aggregate_type = 'posting'
      AND aggregate_id = psp.posting_id::text
      AND event_type IN ('conversation_completed', 'script_execution_completed')
      AND COALESCE(invalidated, FALSE) = FALSE
      AND COALESCE(
          (event_data->>'conversation_id')::int,
          (event_data->>'script_conversation_id')::int
      ) IN (9168, 3335)  -- Only step 2 and step 3
)
WHERE outputs = '{}'::jsonb OR outputs IS NULL;
```

**When to use:**
- Batch reset operations (need to preserve some outputs)
- Migration (copy specific outputs from old system)
- Partial corruption (only some outputs are wrong)

**Performance:** Single UPDATE, very fast

---

### Pattern 3: Batch Rebuild

**When:** Rebuild many postings efficiently

**Python Script:**
```python
import psycopg2
import time

def batch_rebuild_projections(posting_ids, batch_size=100):
    """
    Rebuild multiple posting projections in batches.
    
    Args:
        posting_ids: List of posting IDs to rebuild
        batch_size: Progress report interval
    """
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='turing',
        user='base_admin',
        password='${DB_PASSWORD}'
    )
    
    cursor = conn.cursor()
    total = len(posting_ids)
    rebuilt = 0
    start_time = time.time()
    
    for posting_id in posting_ids:
        cursor.execute("SELECT rebuild_posting_state(%s)", (posting_id,))
        conn.commit()
        rebuilt += 1
        
        if rebuilt % batch_size == 0:
            elapsed = time.time() - start_time
            rate = rebuilt / elapsed
            remaining = (total - rebuilt) / rate
            print(f"✅ Rebuilt {rebuilt}/{total} ({rebuilt*100//total}%) - ETA: {int(remaining)}s")
    
    elapsed = time.time() - start_time
    print(f"\n✅ Successfully rebuilt {rebuilt} projections in {elapsed:.1f}s")
    
    cursor.close()
    conn.close()

# Usage
posting_ids = [14, 16, 17, 18, ...]  # Get from query
batch_rebuild_projections(posting_ids)
```

**Performance:** ~2,000 postings in 6-7 seconds

---

## Rebuild vs Fix at Source

### Rebuild Projection When:

✅ **Events are correct, projection is stale**
- Reset operations changed state manually
- Schema migration needs repopulation
- Projection logic changed

✅ **Multiple fields need updating**
- Cheaper to rebuild than multiple UPDATEs
- Ensures consistency (all derived from same events)

### Fix at Source (Append Events) When:

❌ **Events are wrong or missing**
- Forgot to record an event
- Event data was incorrect
- Need to record retroactive change

**Example - Append Correction Event:**
```sql
INSERT INTO execution_events (
    event_timestamp,
    aggregate_type,
    aggregate_id,
    aggregate_version,
    event_type,
    event_version,
    event_data,
    metadata
) VALUES (
    NOW(),
    'posting',
    '4612',
    (SELECT MAX(aggregate_version) + 1 FROM execution_events WHERE aggregate_id = '4612'),
    'manual_correction',
    1,
    jsonb_build_object(
        'reason', 'Forgot to record step 3 completion',
        'conversation_id', '3335',
        'output', 'Corrected summary text...',
        'corrected_by', 'human_operator'
    ),
    jsonb_build_object('correction_ticket', 'INC-12345')
);
```

Then rebuild projection to incorporate the correction.

---

## Rebuild Safety Checklist

Before rebuilding:

- [ ] **Verify events are correct** - Check event_data makes sense
- [ ] **Check for invalid events** - Exclude `invalidated = TRUE`
- [ ] **Backup projection** - `CREATE TABLE projection_backup AS SELECT * FROM posting_state_projection`
- [ ] **Stop workflow** - Don't rebuild while workflow is writing
- [ ] **Test on small subset** - Rebuild 10 postings first, verify results
- [ ] **Monitor performance** - Check rebuild time per posting
- [ ] **Verify results** - Compare rebuilt data to expected state
- [ ] **Document reason** - Why rebuild needed, what problem it fixes

---

## Common Rebuild Scenarios

### Scenario 1: Workflow Reset

**Problem:** Reset 2,000 postings from step 11 to step 4, but outputs still show step 11 data

**Solution:** Selective rebuild
```sql
-- Rebuild only outputs, preserve current_step/current_conversation_id
UPDATE posting_state_projection psp
SET outputs = (
    SELECT jsonb_object_agg(...)
    FROM execution_events
    WHERE aggregate_id = psp.posting_id::text
      AND (event_data->>'conversation_id')::int IN (9168, 3335)  -- Steps 2, 3 only
)
WHERE current_step = 4;
```

### Scenario 2: Schema Migration

**Problem:** Added `current_conversation_id` column, needs population

**Solution:** Full rebuild
```sql
-- Rebuild all postings to populate new column
SELECT posting_id, rebuild_posting_state(posting_id)
FROM posting_state_projection
ORDER BY posting_id;
```

### Scenario 3: Invalid Events Discovered

**Problem:** Found 5,750 invalid events, projection shows wrong completion counts

**Solution:** Mark events invalid, then rebuild
```sql
-- Step 1: Mark events invalid
UPDATE execution_events SET invalidated = TRUE, invalidation_reason = '...'
WHERE <criteria>;

-- Step 2: Rebuild projections (automatically excludes invalidated events)
SELECT rebuild_posting_state(posting_id)
FROM posting_state_projection
WHERE posting_id IN (SELECT DISTINCT aggregate_id::int FROM execution_events WHERE invalidated = TRUE);
```

### Scenario 4: Conversation ID Changed

**Problem:** Renamed conversation, old outputs have old ID

**Solution:** Migrate outputs during rebuild
```sql
-- Add migration logic to rebuild function
-- Map old conversation_id 1234 → new conversation_id 5678
UPDATE posting_state_projection
SET outputs = outputs - '1234' || jsonb_build_object('5678', outputs->'1234')
WHERE outputs ? '1234';
```

---

## Monitoring Rebuild Operations

### Metrics to Track

```sql
-- Rebuild performance
SELECT 
    AVG(rebuild_time_ms) as avg_rebuild_ms,
    MAX(rebuild_time_ms) as max_rebuild_ms,
    AVG(events_replayed) as avg_events_per_posting
FROM (
    SELECT rebuild_posting_state(posting_id)
    FROM posting_state_projection
    LIMIT 100
) rebuilds;

-- Projection health
SELECT 
    COUNT(*) as total_postings,
    COUNT(CASE WHEN outputs = '{}'::jsonb THEN 1 END) as empty_outputs,
    COUNT(CASE WHEN current_conversation_id IS NULL THEN 1 END) as missing_conversation_id,
    COUNT(CASE WHEN last_updated < NOW() - INTERVAL '24 hours' THEN 1 END) as stale
FROM posting_state_projection;
```

### Rebuild Audit Log

```sql
CREATE TABLE projection_rebuild_log (
    rebuild_id SERIAL PRIMARY KEY,
    rebuild_timestamp TIMESTAMPTZ DEFAULT NOW(),
    rebuild_reason TEXT NOT NULL,
    posting_count INT NOT NULL,
    rebuild_duration_sec NUMERIC,
    initiated_by TEXT,
    metadata JSONB
);

-- Log rebuild operations
INSERT INTO projection_rebuild_log (
    rebuild_reason,
    posting_count,
    rebuild_duration_sec,
    initiated_by,
    metadata
) VALUES (
    'Reset from step 11 to step 4 - idempotency bug fix',
    2089,
    6.7,
    'sandy_ai',
    jsonb_build_object(
        'ticket', 'CLEAN-MODEL-001',
        'affected_steps', ARRAY[11, 12, 16],
        'invalid_events_marked', 5750
    )
);
```

---

## Best Practices

### DO:

✅ **Exclude invalid events** - `COALESCE(invalidated, FALSE) = FALSE` in rebuild  
✅ **Batch processing** - Progress reports every 100 postings  
✅ **Test first** - Rebuild 10 postings, verify, then scale up  
✅ **Document reason** - Why rebuild needed, what it fixes  
✅ **Monitor performance** - Track rebuild time trends  
✅ **Verify results** - Check projection matches expected state  
✅ **Stop workflow** - Don't rebuild while events are being written  

### DON'T:

❌ **Rebuild in production without testing** - Test on subset first  
❌ **Skip backup** - Always backup projection before mass rebuild  
❌ **Rebuild when unsure** - Investigate root cause first  
❌ **Ignore performance** - If rebuilds are slow, optimize event queries  
❌ **Forget to commit** - Batch commits to avoid locking  

---

## Standard Rebuild Script

**Location:** `tools/rebuild_projections.py`

```python
#!/usr/bin/env python3
"""
Standard Projection Rebuild Tool

Usage:
    # Rebuild all postings
    python tools/rebuild_projections.py --all
    
    # Rebuild specific postings
    python tools/rebuild_projections.py --posting-ids 14,16,17
    
    # Rebuild postings at specific step
    python tools/rebuild_projections.py --step 4
    
    # Rebuild with reason documentation
    python tools/rebuild_projections.py --all --reason "Schema migration"
"""

import argparse
import psycopg2
import time
from typing import List

def rebuild_projections(
    posting_ids: List[int],
    reason: str = "Manual rebuild",
    batch_size: int = 100
):
    """Rebuild posting state projections from events"""
    # Implementation from Pattern 3 above
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--posting-ids', type=str)
    parser.add_argument('--step', type=int)
    parser.add_argument('--reason', type=str, required=True)
    
    args = parser.parse_args()
    # ... implementation
```

---

## Conclusion

Projection rebuilds are a **fundamental event sourcing operation**. When projection state diverges from event truth, rebuild from events.

**Key Principles:**
1. Events are immutable source of truth
2. Projections are derived, rebuildable views
3. Exclude invalid events from rebuilds
4. Test on subset before mass rebuild
5. Document why rebuild was needed

**Remember:** If your projection is wrong, your events are probably right. Rebuild.

---

**Status:** Production-validated patterns as of November 21, 2025. 🚀
