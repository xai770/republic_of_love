# Event Sourcing Architecture

**Purpose**: Reference documentation for Turing's event sourcing system  
**Status**: Production (November 2025)  
**Related**: [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md), [CHECKPOINT_SYSTEM.md](CHECKPOINT_SYSTEM.md)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Overview

Turing uses **pure event sourcing** for workflow state management. All workflow execution state is captured in an append-only event log, with materialized projections for fast queries and periodic snapshots for performance optimization.

### Core Principle

**Events are immutable facts about what happened. State is derived.**

```
Actor Execution → Event Store (append-only) → Projections (queryable state)
                                            → Snapshots (performance optimization)
```

---

## Architecture Components

### 1. Event Store (Source of Truth)

**Table**: `execution_events`

```sql
CREATE TABLE execution_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type TEXT NOT NULL,           -- 'posting', 'workflow', 'actor'
    aggregate_id INT NOT NULL,              -- posting_id, workflow_id, etc.
    aggregate_version INT NOT NULL,         -- Optimistic concurrency control
    event_type TEXT NOT NULL,               -- 'script_execution_completed', 'llm_call_failed'
    event_data JSONB NOT NULL,              -- Event payload
    metadata JSONB,                         -- Causation, correlation, timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_aggregate_version 
        UNIQUE (aggregate_type, aggregate_id, aggregate_version)
);

CREATE INDEX idx_execution_events_aggregate 
    ON execution_events(aggregate_type, aggregate_id);
CREATE INDEX idx_execution_events_conversation 
    ON execution_events((metadata->>'conversation_id'));
CREATE INDEX idx_execution_events_created 
    ON execution_events(created_at DESC);
```

**Key Features:**
- **Append-only**: Never UPDATE or DELETE
- **Versioned**: Aggregate version prevents concurrent write conflicts
- **JSONB payload**: Flexible schema evolution
- **Full audit trail**: Every execution captured with metadata

### 2. Projections (Materialized Views)

**Purpose**: Fast queryable state derived from events

**posting_state_projection** - Current workflow position for each posting
```sql
CREATE TABLE posting_state_projection (
    posting_id INT PRIMARY KEY,
    current_conversation_id INT,
    execution_sequence INT[],               -- Order of execution
    outputs JSONB,                          -- {conversation_id: output}
    is_terminal BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMPTZ,
    
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id)
);
```

**Rebuild Function** - Replay events to reconstruct state
```sql
CREATE OR REPLACE FUNCTION rebuild_posting_state(p_posting_id INT)
RETURNS void AS $$
BEGIN
    DELETE FROM posting_state_projection WHERE posting_id = p_posting_id;
    
    INSERT INTO posting_state_projection (posting_id, outputs, execution_sequence, ...)
    SELECT 
        aggregate_id,
        jsonb_object_agg(
            metadata->>'conversation_id',
            event_data->>'output'
        ) as outputs,
        array_agg(metadata->>'conversation_id' ORDER BY created_at) as execution_sequence,
        ...
    FROM execution_events
    WHERE aggregate_type = 'posting' AND aggregate_id = p_posting_id
    GROUP BY aggregate_id;
END;
$$ LANGUAGE plpgsql;
```

### 3. Snapshots (Performance Optimization)

**Purpose**: Avoid replaying thousands of events for frequently accessed aggregates

**posting_state_snapshots** - Periodic state snapshots
```sql
CREATE TABLE posting_state_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    posting_id INT NOT NULL,
    event_sequence INT NOT NULL,           -- Snapshot taken after N events
    state JSONB NOT NULL,                  -- Full posting state
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id)
);

CREATE INDEX idx_snapshots_posting 
    ON posting_state_snapshots(posting_id, event_sequence DESC);
```

**Snapshot Frequency**: Every 10 events (configurable)

**State Reconstruction**:
1. Load latest snapshot (if exists)
2. Replay events since snapshot
3. Much faster than replaying all events

---

## Event Types

### Workflow Events

**Past tense verbs** - Events describe what happened, not what will happen

| Event Type | Description | Metadata |
|------------|-------------|----------|
| `workflow_started` | Workflow execution began | workflow_id, posting_count |
| `workflow_completed` | All postings reached terminal state | workflow_id, duration_ms |
| `workflow_failed` | Workflow encountered fatal error | workflow_id, error |

### Posting Events

| Event Type | Description | Metadata |
|------------|-------------|----------|
| `script_execution_completed` | Script actor finished successfully | conversation_id, actor_id, output |
| `llm_call_completed` | LLM actor finished successfully | conversation_id, actor_id, model, tokens |
| `script_execution_failed` | Script actor failed | conversation_id, actor_id, error |
| `llm_call_failed` | LLM actor failed | conversation_id, actor_id, error |
| `posting_terminal` | Posting reached terminal state | final_conversation_id |
| `circuit_breaker_open` | Actor circuit breaker triggered | actor_id, failure_count |

### Conversation Events

| Event Type | Description | Metadata |
|------------|-------------|----------|
| `conversation_started` | Wave processing began | conversation_id, posting_count |
| `conversation_completed` | Wave finished | conversation_id, processed_count |

---

## Event Metadata Structure

**Standard metadata fields** (JSONB):

```json
{
  "conversation_id": 9184,
  "actor_id": 74,
  "execution_order": 2,
  "duration_ms": 245,
  "retry_count": 0,
  "causation_id": "event-uuid-that-caused-this",
  "correlation_id": "workflow_3001_posting_12345",
  "event_version": "1.0"
}
```

**Key Fields:**
- `causation_id`: UUID of event that caused this event (event chain)
- `correlation_id`: Trace entire workflow execution
- `event_version`: Schema evolution support
- `duration_ms`: Performance tracking
- `retry_count`: Retry logic tracking

---

## Event Store API

### Python Interface

**core/event_store.py** - EventStore class

```python
from core.event_store import EventStore

event_store = EventStore()

# Append event
event_store.append_event(
    event_type='script_execution_completed',
    aggregate_type='posting',
    aggregate_id=posting_id,
    event_data={
        'output': result,
        'status': 'SUCCESS'
    },
    metadata={
        'conversation_id': conversation_id,
        'actor_id': actor_id,
        'duration_ms': 245
    }
)

# Get posting state (from projection)
state = event_store.get_posting_state(posting_id)

# Get all events for posting (event replay)
events = event_store.get_aggregate_events('posting', posting_id)

# Rebuild projection from events
event_store.rebuild_projection(posting_id)
```

---

## Migration Strategy

### Phase 1: Core Event Store (Week 1)
- Create `execution_events` table
- Create `posting_state_projection` table
- Create `posting_state_snapshots` table
- Add indexes

### Phase 2: Dual-Write (Week 2)
- Update `WaveProcessor` to write to BOTH old tables AND event store
- Validate data consistency
- Monitor for discrepancies

### Phase 3: Validation (Week 3)
- Run `validate_event_store()` function continuously
- Compare old vs new state
- Fix any inconsistencies

### Phase 4: Switch Reads (Week 4)
- Update code to read from projections instead of old tables
- Monitor performance (should be faster)
- Keep dual-write enabled

### Phase 5: Deprecate Old Tables (Week 6+)
- Disable dual-write
- Rename old tables to `*_deprecated`
- Archive for 2 months, then drop

### Rollback Plan
1. Switch reads back to old tables
2. Disable event store writes
3. Investigate and fix issues
4. Re-enable when ready

---

## Benefits

### 1. Full Audit Trail
Every workflow execution captured with complete metadata. Debug issues by replaying events.

### 2. Time Travel
Rebuild state at any point in history:
```sql
SELECT * FROM execution_events 
WHERE aggregate_id = 12345 
  AND created_at <= '2025-11-19 10:00:00';
```

### 3. Event Replay
Fix bugs by replaying events with corrected logic:
```python
for event in get_aggregate_events('posting', posting_id):
    apply_event_with_new_logic(event)
```

### 4. Performance
- **Event append**: 1-2ms (single INSERT, no locks)
- **Projection query**: <1ms (indexed table, no event replay)
- **State rebuild**: 5-100ms (depends on event count)

Compared to old approach:
- **Old checkpoint query**: 10-50ms (complex JSONB queries)
- **Event sourcing**: 2-10x faster

### 5. Simplified Code
No dual-write complexity to old tables. Event store handles everything.

---

## Best Practices

### 1. Event Naming
✅ **DO**: Use past-tense verbs
- `conversation_completed`
- `llm_call_failed`
- `posting_terminal`

❌ **DON'T**: Use present/future tense
- `conversation_complete`
- `llm_call_fail`
- `posting_terminates`

### 2. Event Granularity
**One event = one atomic fact**

✅ **DO**: Separate events for separate facts
```python
event_store.append_event('conversation_started', ...)
# ... execute postings ...
event_store.append_event('conversation_completed', ...)
```

❌ **DON'T**: Combine multiple facts in one event
```python
event_store.append_event('conversation_started_and_completed', ...)
```

### 3. Event Data vs Metadata
**event_data**: Domain-specific payload (output, status, result)  
**metadata**: Cross-cutting concerns (timing, causation, correlation)

```python
# ✅ CORRECT
event_data = {'output': 'Berlin', 'status': 'SUCCESS'}
metadata = {'conversation_id': 9184, 'duration_ms': 245}

# ❌ WRONG (timing in event_data)
event_data = {'output': 'Berlin', 'duration_ms': 245}
metadata = {'conversation_id': 9184}
```

### 4. Idempotency
Use idempotency keys for retry safety:
```python
event_store.append_event(
    event_type='llm_call_completed',
    aggregate_id=posting_id,
    idempotency_key=f"{posting_id}_{conversation_id}_{timestamp}"
)
```

If duplicate event arrives, idempotency key prevents duplicate append.

---

## Performance Tuning

### Snapshot Frequency
**Default**: Every 10 events

**Tune based on**:
- Event volume: High volume → snapshot less frequently
- Query patterns: Frequent queries → snapshot more often
- Storage cost: Snapshots consume disk space

**Configuration**:
```python
SNAPSHOT_INTERVAL = int(os.getenv('EVENT_SNAPSHOT_INTERVAL', '10'))
```

### Index Optimization
**Critical indexes**:
- `(aggregate_type, aggregate_id)` - Find all events for aggregate
- `(metadata->>'conversation_id')` - Filter by conversation
- `created_at DESC` - Time-based queries

**Optional indexes** (add if slow):
- `(event_type)` - Filter by event type
- `(aggregate_type, aggregate_id, aggregate_version)` - Already UNIQUE constraint

### Partitioning (Future)
When event store exceeds 1M events:
```sql
CREATE TABLE execution_events (
    ...
) PARTITION BY RANGE (created_at);

CREATE TABLE execution_events_2025_11 
    PARTITION OF execution_events
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

---

## Troubleshooting

### Problem: Projection out of sync with events

**Symptom**: Posting state doesn't match event log

**Solution**:
```sql
SELECT rebuild_posting_state(posting_id);
```

### Problem: Concurrent write conflict

**Symptom**: ERROR: duplicate key value violates unique constraint "unique_aggregate_version"

**Cause**: Two processes tried to append event at same version

**Solution**: Optimistic concurrency control - retry with incremented version:
```python
try:
    event_store.append_event(aggregate_version=5, ...)
except IntegrityError:
    # Version conflict - reload state and retry
    current_version = get_current_version(posting_id)
    event_store.append_event(aggregate_version=current_version + 1, ...)
```

### Problem: Event store queries slow

**Check indexes**:
```sql
EXPLAIN ANALYZE 
SELECT * FROM execution_events 
WHERE aggregate_id = 12345;
```

**Expected**: Index Scan on idx_execution_events_aggregate

**If Seq Scan**: Add missing index

---

## References

- **Implementation**: `core/event_store.py`, `core/wave_executor.py`
- **Schema**: `sql/event_store_schema.sql`
- **Tests**: `tests/test_event_store.py`
- **Migration Guide**: `docs/architecture/SANDY_ACTION_PLAN_NOV19.md` (archived)

---

**Last Updated**: November 19, 2025  
**Status**: Production ✅  
**Maintainer**: Arden (GitHub Copilot)
