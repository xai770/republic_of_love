# Event Invalidation System Design

**Date:** November 21, 2025  
**Author:** Sandy (Claude Sonnet 4.5)  
**Reviewer:** Arden (Claude Sonnet 4.5)  
**Status:** Production (Workflow 3001)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Philosophy

> **Events are immutable historical facts. You can't change what happened, but you can change how you interpret it.**

Event sourcing demands that events never be deleted - they are the source of truth. But what happens when events represent **invalid executions** - steps that ran without required input data?

**Answer:** Mark them as invalid, preserve the historical record, exclude from metrics.

---

## The Problem

**Scenario:** Workflow bug causes 2,034 postings to execute steps 11-21 without required grading data from steps 4-10.

**Question:** What do we do with the 5,750 `execution_events` records?

**Bad Solutions:**
- ❌ **Delete events** - Violates event sourcing immutability, loses audit trail
- ❌ **Ignore them** - Monitor shows false 100% completion, misleading metrics
- ❌ **Rebuild projection only** - Events still exist, problem returns on next rebuild

**Good Solution:**
- ✅ **Mark events as invalid** - Preserve history, update interpretation, fix metrics

---

## Schema Pattern

### Columns

```sql
ALTER TABLE execution_events 
ADD COLUMN invalidated BOOLEAN DEFAULT FALSE,
ADD COLUMN invalidation_reason TEXT;
```

**Field Definitions:**

- **`invalidated`** (BOOLEAN, DEFAULT FALSE)
  - `FALSE` or `NULL`: Event is valid, include in metrics/monitoring
  - `TRUE`: Event is invalid, exclude from metrics but preserve for audit

- **`invalidation_reason`** (TEXT, NULLABLE)
  - Human-readable explanation of why event was invalidated
  - Include: what went wrong, why it happened, when it was discovered
  - Example: `"Executed without required input data - postings skipped steps 4-10 due to idempotency_check bug"`

### Index

```sql
CREATE INDEX idx_execution_events_invalidated 
ON execution_events(invalidated) 
WHERE invalidated = FALSE;
```

**Purpose:** Optimize queries that filter for valid events only (most common case)

### Comments

```sql
COMMENT ON COLUMN execution_events.invalidated IS 
'TRUE if this event execution was invalid (e.g., missing required input data). Invalid events are kept for completeness but excluded from monitoring/metrics.';

COMMENT ON COLUMN execution_events.invalidation_reason IS 
'Human-readable explanation of why this event was invalidated';
```

---

## When to Invalidate vs Delete

### Invalidate When:

✅ **Execution was technically successful but logically invalid**
- Step executed without required input data
- Step executed in wrong order (skipped dependencies)
- Step executed with stale/corrupted data
- Step executed during known bug period

✅ **You need audit trail of what happened**
- Forensics: "What went wrong and when?"
- Compliance: "Can we prove these steps were re-run correctly?"
- Learning: "What patterns led to this failure?"

✅ **Events might inform future decisions**
- Performance analysis (even failed attempts have timing data)
- Error pattern detection
- System behavior analysis

### Delete When:

❌ **Test data in production** (use separate test database instead)  
❌ **PII/sensitive data that must be purged** (but mark deletion in metadata)  
❌ **Duplicate events from idempotency failure** (only if truly identical)

**General Rule:** Invalidate first, delete never (or only after extended retention period with approval).

---

## Implementation Pattern

### 1. Identify Invalid Events

```sql
-- Find events to invalidate
SELECT 
    event_id,
    aggregate_id,
    event_type,
    event_data->>'conversation_id' as conversation_id
FROM execution_events
WHERE event_type IN ('conversation_completed', 'script_execution_completed')
  AND aggregate_type = 'posting'
  AND (event_data->>'conversation_id')::int IN (9185, 3350, 9186)  -- Steps 11, 12, 16
  AND aggregate_id IN (
      SELECT posting_id::text 
      FROM posting_state_projection 
      WHERE current_step = 4  -- Postings that were reset
  )
  AND invalidated IS NULL;  -- Not already invalidated
```

### 2. Mark Events as Invalid

```sql
UPDATE execution_events
SET invalidated = TRUE,
    invalidation_reason = 'Executed without required input data - postings skipped steps 4-10 (grading workflow) due to idempotency_check bug. Discovered during clean model refactoring on 2025-11-21.'
WHERE event_id IN (
    -- IDs from query above
);
```

### 3. Verify Invalidation

```sql
-- Check invalidation summary
SELECT 
    invalidated,
    COUNT(*) as event_count,
    COUNT(DISTINCT aggregate_id) as posting_count
FROM execution_events
WHERE invalidated = TRUE
GROUP BY invalidated;

-- Expected: ~5,750 events for ~2,034 postings
```

---

## Monitor Filtering Pattern

### Query Pattern

**Before (shows invalid events):**
```sql
SELECT 
    conversation_id,
    COUNT(DISTINCT aggregate_id) as completed_postings
FROM execution_events
WHERE event_type = 'conversation_completed'
  AND event_timestamp > NOW() - INTERVAL '24 hours'
GROUP BY conversation_id;
```

**After (excludes invalid events):**
```sql
SELECT 
    conversation_id,
    COUNT(DISTINCT aggregate_id) as completed_postings
FROM execution_events
WHERE event_type = 'conversation_completed'
  AND event_timestamp > NOW() - INTERVAL '24 hours'
  AND COALESCE(invalidated, FALSE) = FALSE  -- ← Add this filter
GROUP BY conversation_id;
```

### Application Code

```python
# In monitor_workflow.py or similar
def get_step_progress(workflow_id, hours=24):
    query = """
        SELECT 
            wc.execution_order,
            c.conversation_name,
            COUNT(DISTINCT CASE 
                WHEN e.event_timestamp > NOW() - INTERVAL %s hours
                AND COALESCE(e.invalidated, FALSE) = FALSE  -- Exclude invalid
                THEN e.aggregate_id 
            END) as completed_count
        FROM workflow_conversations wc
        JOIN conversations c ON wc.conversation_id = c.conversation_id
        LEFT JOIN execution_events e ON e.aggregate_type = 'posting'
        WHERE wc.workflow_id = %s
        GROUP BY wc.execution_order, c.conversation_name
        ORDER BY wc.execution_order
    """
    return execute_query(query, (hours, workflow_id))
```

**Key Pattern:** `COALESCE(e.invalidated, FALSE) = FALSE`
- Handles NULL (valid) and FALSE (explicitly valid)
- Only excludes TRUE (explicitly invalid)

---

## Audit and Forensics Uses

### 1. Incident Timeline

```sql
-- What happened during the incident?
SELECT 
    event_timestamp,
    aggregate_id as posting_id,
    event_data->>'conversation_id' as conversation_id,
    c.canonical_name,
    invalidated,
    invalidation_reason
FROM execution_events e
LEFT JOIN conversations c ON (e.event_data->>'conversation_id')::int = c.conversation_id
WHERE event_timestamp BETWEEN '2025-11-20' AND '2025-11-21'
  AND aggregate_id IN (SELECT posting_id::text FROM posting_state_projection WHERE current_step = 4)
ORDER BY event_timestamp;
```

### 2. Impact Analysis

```sql
-- How many postings were affected?
SELECT 
    COUNT(DISTINCT aggregate_id) as affected_postings,
    COUNT(*) as invalid_events,
    MIN(event_timestamp) as first_invalid,
    MAX(event_timestamp) as last_invalid
FROM execution_events
WHERE invalidated = TRUE;
```

### 3. Pattern Detection

```sql
-- Which conversations had invalid executions?
SELECT 
    event_data->>'conversation_id' as conversation_id,
    c.canonical_name,
    COUNT(*) as invalid_count,
    COUNT(DISTINCT aggregate_id) as affected_postings
FROM execution_events e
LEFT JOIN conversations c ON (e.event_data->>'conversation_id')::int = c.conversation_id
WHERE invalidated = TRUE
GROUP BY event_data->>'conversation_id', c.canonical_name
ORDER BY invalid_count DESC;
```

### 4. Re-execution Verification

```sql
-- Were invalidated executions re-run successfully?
WITH invalid_executions AS (
    SELECT DISTINCT 
        aggregate_id as posting_id,
        (event_data->>'conversation_id')::int as conversation_id
    FROM execution_events
    WHERE invalidated = TRUE
)
SELECT 
    ie.posting_id,
    ie.conversation_id,
    c.canonical_name,
    CASE 
        WHEN psp.outputs ? ie.conversation_id::text THEN 'Re-executed ✓'
        ELSE 'Missing ✗'
    END as status
FROM invalid_executions ie
LEFT JOIN posting_state_projection psp ON ie.posting_id::int = psp.posting_id
LEFT JOIN conversations c ON ie.conversation_id = c.conversation_id
ORDER BY status, posting_id;
```

---

## Best Practices

### DO:

✅ **Document the reason** - Future you will want to know why events were invalidated  
✅ **Include discovery date** - Helps with timeline reconstruction  
✅ **Reference ticket/issue** - Link to incident report or bug fix  
✅ **Verify before invalidating** - Run SELECT before UPDATE  
✅ **Count affected entities** - Know the scope of invalidation  
✅ **Update monitors immediately** - Don't let invalid events pollute metrics  
✅ **Preserve in backups** - Invalid events are still historical facts  

### DON'T:

❌ **Delete events** - Violates event sourcing principles  
❌ **Invalidate without reason** - Future forensics need context  
❌ **Skip verification** - Might invalidate wrong events  
❌ **Hide from audit** - Invalidated events should be visible in audit queries  
❌ **Forget to update queries** - Add COALESCE(invalidated, FALSE) = FALSE filter  

---

## Migration Checklist

When adding event invalidation to a new event store:

- [ ] Add `invalidated` and `invalidation_reason` columns
- [ ] Create partial index on `invalidated = FALSE`
- [ ] Add column comments
- [ ] Update all monitoring queries to filter invalid events
- [ ] Update dashboard queries
- [ ] Update audit/forensics queries to show invalidation status
- [ ] Document invalidation criteria in team wiki
- [ ] Create incident response playbook (when to invalidate)
- [ ] Add invalidation metrics to observability (count of invalid events)

---

## Related Patterns

- **Event Versioning**: Invalidate old event versions when schema changes
- **Soft Deletes**: Similar pattern for aggregate deletion (mark, don't delete)
- **Temporal Queries**: Query valid events as of specific timestamp
- **Snapshot Rebuilding**: Exclude invalid events when rebuilding projections

---

## Production Example (Workflow 3001)

**Incident:** Idempotency check bug caused 2,034 postings to skip grading workflow

**Events Invalidated:** 5,750 across steps 11, 12, 16, 19, 20, 21

**Invalidation Reason:**
```
Executed without required input data - postings skipped steps 4-10 (grading workflow) 
due to idempotency_check bug. Discovered during clean model refactoring on 2025-11-21.
```

**Impact:** Monitor went from showing false 100% completion to accurate 0% for affected steps

**Result:** 
- Historical record preserved (can audit what happened)
- Metrics corrected (no longer misleading)
- Re-execution validated (all postings re-processed correctly)

---

## Conclusion

Event invalidation respects event sourcing principles while solving a practical problem: **how do we handle invalid executions without deleting history?**

**The answer:** Interpretation over deletion. Mark events as invalid, update how we query them, preserve the audit trail.

This pattern will serve us well for:
- Bug discovery and mitigation
- System evolution (old behavior becomes "invalid")
- Compliance and forensics
- Performance and error analysis

**Remember:** Events are sacred. We interpret, we don't delete.

---

**Status:** Production-validated pattern as of November 21, 2025. 🚀
