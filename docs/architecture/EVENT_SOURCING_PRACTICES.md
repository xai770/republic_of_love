# Event Sourcing Best Practices

**Date:** November 21, 2025  
**Author:** Sandy (Claude Sonnet 4.5)  
**Reviewer:** Arden (Claude Sonnet 4.5)  
**Status:** Production-Validated (Workflow 3001)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Philosophy

Event sourcing is not just a pattern - it's a **shift in how you think about state**.

> **Traditional:** State is current. History is discarded.  
> **Event Sourcing:** History is truth. State is derived.

---

## Core Principles

### 1. Events Are Immutable Facts

**What happened cannot be changed.**

```python
# ❌ WRONG - Modifying event data
UPDATE execution_events 
SET event_data = jsonb_set(event_data, '{output}', '"corrected value"')
WHERE event_id = 12345;

# ✅ RIGHT - Mark interpretation invalid, append correction
UPDATE execution_events 
SET invalidated = TRUE, invalidation_reason = 'Output was corrupted'
WHERE event_id = 12345;

INSERT INTO execution_events (event_type, event_data, metadata)
VALUES ('manual_correction', ..., jsonb_build_object('corrects_event', 12345));
```

**Why:** Events record what actually happened. If execution produced wrong output, that's a fact. Mark it invalid, but don't rewrite history.

---

### 2. Projection is Source of Truth (Not Tables)

**Dual source of truth is the root of all bugs.**

```python
# ❌ WRONG - Querying table columns
def check_summary_exists(posting_id: int) -> bool:
    cursor.execute("""
        SELECT extracted_summary FROM postings WHERE id = %s
    """, (posting_id,))
    return cursor.fetchone()[0] is not None

# ✅ RIGHT - Querying projection outputs
def check_summary_exists(posting_id: int) -> bool:
    cursor.execute("""
        SELECT outputs ? '3335' FROM posting_state_projection WHERE posting_id = %s
    """, (posting_id,))
    return cursor.fetchone()[0]
```

**Why:** `postings.extracted_summary` is **legacy data**. The event-sourced truth is `posting_state_projection.outputs->'3335'`.

**Production Impact:** This bug caused 2,034 postings to skip grading workflow.

---

### 3. Write Events, Read Projections

**Events for writes, projections for reads.**

```python
# Writing data - Append event
async def complete_conversation(posting_id, conversation_id, output):
    await append_event(
        aggregate_type='posting',
        aggregate_id=str(posting_id),
        event_type='conversation_completed',
        event_data={
            'conversation_id': conversation_id,
            'output': output,
            'timestamp': datetime.now().isoformat()
        }
    )
    await update_projection(posting_id)  # Eager update

# Reading data - Query projection
def get_posting_state(posting_id):
    cursor.execute("""
        SELECT current_step, current_conversation_id, outputs
        FROM posting_state_projection
        WHERE posting_id = %s
    """, (posting_id,))
    return cursor.fetchone()
```

**Pattern:**
- **Write path:** Event → Projection (async or eager)
- **Read path:** Projection only (never query events for reads)

---

### 4. Projections Are Rebuildable

**If projection is wrong, rebuild from events. Don't patch.**

```python
# ❌ WRONG - Patching projection
UPDATE posting_state_projection
SET outputs = outputs || '{"3335": "corrected summary"}'
WHERE posting_id = 4612;

# ✅ RIGHT - Rebuild from events
SELECT rebuild_posting_state(4612);
```

**Why:** Patching creates divergence. Rebuilding ensures projection matches events.

---

### 5. Event Version Schema Changes

**Events have versions. Old versions must always be readable.**

```python
# Event schema v1
{
    "event_type": "conversation_completed",
    "event_version": 1,
    "event_data": {
        "conversation_id": "3335",
        "output": "summary text"
    }
}

# Event schema v2 (added metadata)
{
    "event_type": "conversation_completed",
    "event_version": 2,
    "event_data": {
        "conversation_id": "3335",
        "output": "summary text",
        "model": "ollama/gemma2:27b",
        "token_count": 1234
    }
}
```

**Reading events - Handle all versions:**
```python
def process_conversation_completed(event):
    data = event['event_data']
    output = data['output']  # Always present
    
    # Optional fields (version 2+)
    model = data.get('model', 'unknown')
    tokens = data.get('token_count', 0)
    
    return {
        'output': output,
        'model': model,
        'tokens': tokens
    }
```

**Rules:**
- ✅ Add optional fields (backwards compatible)
- ❌ Remove fields (breaks old event replay)
- ❌ Rename fields (breaks old event replay)
- ✅ Add new event types (backwards compatible)

---

### 6. Aggregate Versioning

**Track version to detect conflicts.**

```python
# Append event with version check
cursor.execute("""
    INSERT INTO execution_events (
        aggregate_type,
        aggregate_id,
        aggregate_version,
        event_type,
        event_data
    ) VALUES (%s, %s, 
        (SELECT COALESCE(MAX(aggregate_version), 0) + 1 
         FROM execution_events 
         WHERE aggregate_id = %s),
        %s, %s
    )
""", ('posting', posting_id, posting_id, 'conversation_completed', event_data))
```

**Why:** Ensures event ordering. If two processes write same aggregate_version, detect conflict.

---

### 7. Metadata for Debugging

**Events should be self-documenting.**

```python
await append_event(
    aggregate_type='posting',
    aggregate_id=str(posting_id),
    event_type='conversation_completed',
    event_data={
        'conversation_id': '3335',
        'output': summary_text
    },
    metadata={
        'workflow_id': 3001,
        'execution_time_ms': 18543,
        'model': 'ollama/gemma2:27b',
        'triggered_by': 'wave_processor_v2.1.0',
        'host': 'xai-desktop',
        'correlation_id': 'batch_2024-11-21_001'
    }
)
```

**Include:**
- Who triggered (user, system, batch job)
- When (timestamp)
- How long (execution time)
- Which version (app version, model version)
- Context (correlation ID, batch ID, workflow ID)

**Why:** 6 months later, you'll want to know why this event happened.

---

## Common Anti-Patterns

### Anti-Pattern 1: Deleting Events

**❌ NEVER DELETE EVENTS**

```sql
-- NO NO NO NO NO
DELETE FROM execution_events WHERE event_id = 12345;
```

**Why it breaks:**
- Aggregate version gaps (replay fails)
- Audit trail lost (compliance issues)
- Projections can't be rebuilt (missing history)

**Instead:** Mark invalid
```sql
UPDATE execution_events 
SET invalidated = TRUE, invalidation_reason = 'Test data - not production'
WHERE event_id BETWEEN 1000 AND 2000;
```

---

### Anti-Pattern 2: Dual Source of Truth

**❌ Table columns AND projection outputs**

```python
# ❌ Writing to both
cursor.execute("UPDATE postings SET extracted_summary = %s WHERE id = %s", (summary, posting_id))
cursor.execute("UPDATE posting_state_projection SET outputs = outputs || %s WHERE posting_id = %s", 
               (jsonb.dumps({'3335': summary}), posting_id))
```

**Why it breaks:**
- Gets out of sync (one UPDATE succeeds, other fails)
- Unclear which is truth (code queries different sources)
- Can't rebuild (table columns aren't derived from events)

**Instead:** Events → Projection → Table (optional cache)
```python
# Write event
await append_event(...)
await update_projection(posting_id)

# Optional: Denormalize to table for legacy queries
cursor.execute("UPDATE postings SET extracted_summary = (outputs->>'3335') WHERE id = %s", (posting_id,))
```

---

### Anti-Pattern 3: Incomplete Event Data

**❌ Events don't capture full context**

```python
# ❌ Can't rebuild from this
{
    "event_type": "step_completed",
    "event_data": {
        "step": 4
    }
}
```

**Missing:** What happened at step 4? What was the output? What's next?

**Instead:** Full context
```python
{
    "event_type": "conversation_completed",
    "event_data": {
        "conversation_id": "3336",
        "conversation_name": "gemma2_grade",
        "execution_order": 4,
        "output": "{'grading': {'overall': 8, 'clarity': 9, ...}}",
        "next_conversation_id": "3337",
        "next_execution_order": 5
    }
}
```

**Rule:** Event should contain everything needed to rebuild projection.

---

### Anti-Pattern 4: Synchronous Event Replay

**❌ Rebuilding in request path**

```python
# ❌ 100ms rebuild on every read
def get_posting_state(posting_id):
    rebuild_posting_state(posting_id)  # Slow!
    return query_projection(posting_id)
```

**Instead:** Eager projection updates
```python
# Write path - Update projection immediately
async def complete_conversation(posting_id, conversation_id, output):
    await append_event(...)
    await update_projection(posting_id)  # Eager

# Read path - Just query projection
def get_posting_state(posting_id):
    return query_projection(posting_id)  # Fast
```

**Projections should be:**
- ✅ Eagerly updated (write-time)
- ✅ Asynchronously maintained (background worker)
- ❌ Lazily rebuilt (read-time)

---

### Anti-Pattern 5: Mutable Event Data

**❌ JSONB updates on events**

```sql
-- NO
UPDATE execution_events
SET event_data = jsonb_set(event_data, '{status}', '"corrected"')
WHERE event_id = 12345;
```

**Instead:** Append correction event
```sql
INSERT INTO execution_events (event_type, event_data, metadata)
VALUES (
    'manual_correction',
    jsonb_build_object('corrected_output', '...'),
    jsonb_build_object('corrects_event', 12345, 'reason', 'Output was truncated')
);
```

---

## Detecting Dual Source Problems

### Audit Query: Find Divergence

```sql
-- Check if postings table columns match projection outputs
SELECT 
    p.id,
    p.extracted_summary IS NOT NULL as table_has_summary,
    psp.outputs ? '3335' as projection_has_summary,
    CASE 
        WHEN (p.extracted_summary IS NOT NULL) != (psp.outputs ? '3335') THEN 'DIVERGENCE'
        ELSE 'OK'
    END as status
FROM postings p
LEFT JOIN posting_state_projection psp ON p.id = psp.posting_id
WHERE p.extracted_summary IS NOT NULL != psp.outputs ? '3335'
LIMIT 100;
```

**If divergence found:**
1. Determine which is correct (usually projection)
2. Fix divergent source (UPDATE table from projection)
3. Eliminate dual writes (delete code that writes to table)
4. Add check to prevent regression

---

### Code Audit: Find Table Queries

```bash
# Find code querying postings table columns
grep -r "extracted_summary" --include="*.py" .
grep -r "taxonomy_skills" --include="*.py" .
grep -r "ihl_score" --include="*.py" .

# Should find:
# - Projection update logic (OK - writes from events)
# - NO read queries (all reads should use projection)
```

**Goal:** Zero reads from table columns. All reads from projection.

---

## Migration Path: Table → Projection

### Phase 1: Dual Write

```python
# Start writing to both (backwards compatible)
def save_summary(posting_id, summary):
    # Old code (still works)
    cursor.execute("UPDATE postings SET extracted_summary = %s WHERE id = %s", 
                   (summary, posting_id))
    
    # New code (event sourcing)
    append_event('conversation_completed', {'conversation_id': '3335', 'output': summary})
    update_projection(posting_id)
```

**Duration:** 1 week (build confidence)

---

### Phase 2: Dual Read (Validate)

```python
# Read from both, compare (catch divergence)
def get_summary(posting_id):
    table_summary = cursor.execute("SELECT extracted_summary FROM postings WHERE id = %s", (posting_id,)).fetchone()[0]
    projection_summary = cursor.execute("SELECT outputs->>'3335' FROM posting_state_projection WHERE posting_id = %s", (posting_id,)).fetchone()[0]
    
    if table_summary != projection_summary:
        log_warning(f"Divergence detected: posting {posting_id}")
    
    return projection_summary  # Use projection as source of truth
```

**Duration:** 1 week (validate no divergence)

---

### Phase 3: Projection Only

```python
# Read only from projection (simplify)
def get_summary(posting_id):
    return cursor.execute(
        "SELECT outputs->>'3335' FROM posting_state_projection WHERE posting_id = %s", 
        (posting_id,)
    ).fetchone()[0]
```

**Duration:** Permanent

---

### Phase 4: Drop Table Columns

```sql
-- After 1 month, no issues
ALTER TABLE postings DROP COLUMN extracted_summary;
ALTER TABLE postings DROP COLUMN taxonomy_skills;
ALTER TABLE postings DROP COLUMN ihl_score;
```

**Duration:** After stable production

---

## Event Design Guidelines

### Good Event Names

✅ **Domain events (what happened):**
- `conversation_completed`
- `posting_created`
- `grading_failed`
- `workflow_paused`

❌ **CRUD operations (implementation detail):**
- `posting_updated`
- `table_row_inserted`
- `data_saved`

**Why:** Events describe business meaning, not database operations.

---

### Event Granularity

**Too coarse:**
```python
# ❌ Lost detail
{"event_type": "workflow_completed", "posting_id": 4612}
```

**Too fine:**
```python
# ❌ Too many events
{"event_type": "token_generated", "token": "The"}
{"event_type": "token_generated", "token": "quick"}
{"event_type": "token_generated", "token": "brown"}
```

**Just right:**
```python
# ✅ Meaningful business event
{
    "event_type": "conversation_completed",
    "conversation_id": "3335",
    "output": "The quick brown fox...",
    "token_count": 1234
}
```

**Rule:** One event per **meaningful state transition**.

---

### Event Payload Design

**Include everything needed to:**
1. Rebuild projection
2. Understand what happened (debugging)
3. Audit who/when/why

**Example - Complete Event:**
```python
{
    "event_id": 12345,
    "event_timestamp": "2025-11-21T10:30:45.123456Z",
    "aggregate_type": "posting",
    "aggregate_id": "4612",
    "aggregate_version": 7,
    "event_type": "conversation_completed",
    "event_version": 2,
    "event_data": {
        # What happened
        "conversation_id": "3335",
        "conversation_name": "gemma2_extract",
        "execution_order": 3,
        "output": "{'summary': 'Senior Python Developer...', 'location': 'Remote'}",
        
        # What's next
        "next_conversation_id": "3336",
        "next_execution_order": 4,
        
        # Context
        "input_preview": "Job Title: Senior Python Developer...",
        "model_used": "ollama/gemma2:27b",
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "metadata": {
        # Debugging
        "workflow_id": 3001,
        "execution_time_ms": 18543,
        "triggered_by": "wave_processor",
        "app_version": "v2.1.0",
        "host": "xai-desktop",
        
        # Audit
        "correlation_id": "batch_2024-11-21_001",
        "user_id": null,
        "api_key_id": null
    },
    "invalidated": false,
    "invalidation_reason": null
}
```

---

## Performance Considerations

### Event Table Growth

**Problem:** Event tables grow unbounded.

**Solutions:**
1. **Partition by date** (archive old events)
```sql
CREATE TABLE execution_events_2024_11 PARTITION OF execution_events
FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
```

2. **Snapshot aggregates** (reduce replay time)
```sql
CREATE TABLE posting_snapshots (
    posting_id INT PRIMARY KEY,
    snapshot_version INT,  -- Aggregate version at snapshot
    snapshot_data JSONB,
    snapshot_timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

3. **Archive old events** (move to cold storage)
```sql
-- Move events > 1 year old to archive
INSERT INTO execution_events_archive SELECT * FROM execution_events WHERE event_timestamp < NOW() - INTERVAL '1 year';
DELETE FROM execution_events WHERE event_timestamp < NOW() - INTERVAL '1 year';
```

---

### Projection Performance

**Problem:** Projection queries slow (complex aggregations).

**Solutions:**
1. **Eager updates** (update on write, not read)
2. **Indexes** (on projection query columns)
```sql
CREATE INDEX idx_projection_current_step ON posting_state_projection(current_step);
CREATE INDEX idx_projection_conversation ON posting_state_projection(current_conversation_id);
```

3. **Denormalization** (cache computed values)
```sql
ALTER TABLE posting_state_projection ADD COLUMN total_conversations INT;
UPDATE posting_state_projection SET total_conversations = jsonb_array_length(conversation_history);
```

---

### Rebuild Performance

**Problem:** Rebuilding 100,000 postings takes hours.

**Solutions:**
1. **Batch processing** (commit every 100 postings)
2. **Parallel rebuilds** (multiple workers)
```python
from multiprocessing import Pool

def rebuild_batch(posting_ids):
    for pid in posting_ids:
        rebuild_posting_state(pid)

with Pool(10) as pool:
    batches = [posting_ids[i:i+100] for i in range(0, len(posting_ids), 100)]
    pool.map(rebuild_batch, batches)
```

3. **Snapshot before rebuild** (start from last snapshot, not event 1)

---

## Testing Event Sourcing

### Test Event Replay

```python
def test_projection_rebuild():
    # Arrange - Create events
    append_event('posting_created', {'posting_id': 999, 'initial_step': 1})
    append_event('conversation_completed', {'conversation_id': '3335', 'output': 'summary'})
    append_event('conversation_completed', {'conversation_id': '3336', 'output': '8'})
    
    # Act - Rebuild projection
    rebuild_posting_state(999)
    
    # Assert - Check projection
    projection = get_projection(999)
    assert projection['current_step'] == 5
    assert projection['outputs']['3335'] == 'summary'
    assert projection['outputs']['3336'] == '8'
```

---

### Test Event Version Compatibility

```python
def test_old_event_version_readable():
    # Simulate old event (version 1 - no metadata)
    old_event = {
        "event_version": 1,
        "event_data": {
            "conversation_id": "3335",
            "output": "summary"
        }
    }
    
    # Should still process
    result = process_conversation_completed(old_event)
    assert result['output'] == 'summary'
    assert result['model'] == 'unknown'  # Default for missing field
```

---

### Test Invalid Event Handling

```python
def test_invalid_events_excluded():
    # Arrange - Create valid and invalid events
    append_event('conversation_completed', {'conversation_id': '3335', 'output': 'summary'})
    event_id = append_event('conversation_completed', {'conversation_id': '3336', 'output': 'wrong'})
    mark_event_invalid(event_id, 'Test data')
    
    # Act - Rebuild
    rebuild_posting_state(999)
    
    # Assert - Invalid event not included
    projection = get_projection(999)
    assert '3335' in projection['outputs']
    assert '3336' not in projection['outputs']
```

---

## Monitoring

### Event Stream Health

```sql
-- Events per day
SELECT DATE(event_timestamp), COUNT(*)
FROM execution_events
WHERE event_timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(event_timestamp)
ORDER BY DATE(event_timestamp);

-- Event types distribution
SELECT event_type, COUNT(*), 
       COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM execution_events
WHERE event_timestamp > NOW() - INTERVAL '1 day'
GROUP BY event_type
ORDER BY COUNT(*) DESC;

-- Invalid events (anomaly detection)
SELECT DATE(event_timestamp), COUNT(*)
FROM execution_events
WHERE invalidated = TRUE
GROUP BY DATE(event_timestamp)
ORDER BY DATE(event_timestamp) DESC
LIMIT 30;
```

---

### Projection Lag

```sql
-- How far behind are projections?
SELECT 
    p.posting_id,
    MAX(e.event_timestamp) as last_event_time,
    p.last_updated as projection_update_time,
    EXTRACT(EPOCH FROM (NOW() - p.last_updated)) as lag_seconds
FROM posting_state_projection p
JOIN execution_events e ON e.aggregate_id = p.posting_id::text
WHERE e.invalidated = FALSE
GROUP BY p.posting_id, p.last_updated
HAVING EXTRACT(EPOCH FROM (NOW() - p.last_updated)) > 60
ORDER BY lag_seconds DESC
LIMIT 20;
```

**Alert if:** Projection lag > 5 minutes (indicates projection update failure)

---

## Conclusion

Event sourcing is **powerful but requires discipline**.

**Key Takeaways:**
1. ✅ Events are immutable - mark invalid, don't delete
2. ✅ Projection is source of truth - don't query table columns
3. ✅ Write events, read projections - separate concerns
4. ✅ Projections are rebuildable - don't patch, rebuild
5. ✅ Event versions must be backwards compatible
6. ✅ Include full context in events - debugging future-you will thank you

**Remember:** When in doubt, **ask what the events say**. They're the truth.

---

**Status:** Production-validated as of November 21, 2025. Built from 2,089 postings, 5,750 invalid events, 1 major bug discovery. 🎯
