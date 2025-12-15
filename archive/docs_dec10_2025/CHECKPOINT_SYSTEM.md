# Turing Checkpoint System

**Version:** 1.0  
**Last Updated:** November 17, 2025  
**Purpose:** Complete guide to checkpoint recovery, crash resilience, and state queries

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Overview

The checkpoint system provides **crash recovery** and **reliable state access** for Turing workflows.

### Key Features

- **Crash Recovery**: Resume workflow from last saved checkpoint after system failure
- **State Persistence**: All PostingState serialized to `posting_state_checkpoints` table
- **Checkpoint Queries**: Access conversation outputs reliably across wave boundaries
- **Audit Trail**: Complete history of posting's journey through workflow

---

## Checkpoint Storage

### Database Table: `posting_state_checkpoints`

**Schema**:
```sql
CREATE TABLE posting_state_checkpoints (
    checkpoint_id SERIAL PRIMARY KEY,
    posting_id INTEGER NOT NULL,
    workflow_run_id INTEGER,
    conversation_id INTEGER,
    execution_order INTEGER,
    state_snapshot JSONB NOT NULL,  -- Full PostingState serialized
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_checkpoints_posting ON posting_state_checkpoints(posting_id);
CREATE INDEX idx_checkpoints_workflow_run ON posting_state_checkpoints(workflow_run_id);
CREATE INDEX idx_checkpoints_outputs ON posting_state_checkpoints USING GIN((state_snapshot->'outputs'));
```

### state_snapshot JSONB Structure

```json
{
  "posting_id": 123,
  "job_description": "Software Engineer position...",
  "current_conversation_id": 3335,
  "outputs": {
    "3335": "Extracted summary: ...",
    "3336": "Grade: 8/10",
    "3337": "Improved summary: ..."
  },
  "conversation_outputs": {
    "conversation_1_output": "First conversation result",
    "conversation_2_output": "Second conversation result"
  },
  "execution_sequence": [1, 2, 3, 3335, 3336, 3337],
  "is_terminal": false,
  "workflow_run_id": 4567,
  "conversation_run_ids": {
    "(123, 3335)": 8901,
    "(123, 3336)": 8902
  }
}
```

---

## Checkpoint Creation

### When Checkpoints Are Saved

Checkpoints are saved **after each posting completes a conversation**:

```python
def _process_wave(self, conversation_id: int, postings: List[PostingState]):
    """Process wave with checkpoint saves"""
    
    for posting in postings:
        # Execute conversation
        output = actor_router.execute_instruction(...)
        posting.outputs[conversation_id] = output
        
        # Evaluate branching
        posting.next_conversation_id = evaluate_branches(...)
        
        # SAVE CHECKPOINT (completes in ~8ms)
        save_checkpoint(
            posting=posting,
            wave_number=wave_num,
            conversation_id=conversation_id,
            execution_order=exec_order,
            conversation_name=conv_name
        )
```

### Performance

From `checkpoint_manager.py`:

```python
def save_checkpoint(posting: PostingState, wave_number: int, 
                    conversation_id: int, execution_order: int,
                    conversation_name: str) -> None:
    """Save checkpoint for crash recovery - completes in ~8ms"""
    
    conn = get_connection()  # ~0.5ms (from pool)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posting_state_checkpoints (
                posting_id, workflow_run_id, conversation_id, 
                execution_order, state_snapshot
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            posting.posting_id,
            posting.workflow_run_id,
            conversation_id,
            execution_order,
            json.dumps(posting.to_dict())  # ~7ms total
        ))
        conn.commit()
    finally:
        return_connection(conn)  # Back to pool
```

**Total Time**: ~8ms per checkpoint (so fast GPU never waits)

---

## Crash Recovery

### Resume from Checkpoints

When workflow crashes, resume from last saved state:

```python
def resume_from_checkpoints(workflow_run_id: int) -> List[PostingState]:
    """Resume workflow from last saved checkpoints"""
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Get latest checkpoint for each posting
        cursor.execute("""
            SELECT DISTINCT ON (posting_id)
                posting_id,
                state_snapshot,
                created_at
            FROM posting_state_checkpoints
            WHERE workflow_run_id = %s
            ORDER BY posting_id, created_at DESC
        """, (workflow_run_id,))
        
        postings = []
        for row in cursor.fetchall():
            posting = PostingState.from_dict(row['state_snapshot'])
            postings.append(posting)
        
        return postings
    finally:
        return_connection(conn)
```

### Usage

```bash
# Check for incomplete workflow runs
SELECT workflow_run_id, started_at, status
FROM workflow_runs
WHERE status = 'RUNNING'
  AND started_at < NOW() - INTERVAL '1 hour';

# Resume from checkpoint
python3 -m core.wave_batch_processor --workflow 3001 --resume-from 4567
```

**What Happens**:
1. Load PostingState for all postings from checkpoints
2. Each posting resumes from its `current_conversation_id`
3. Already-completed work is skipped (idempotency)
4. Workflow continues until all postings reach TERMINAL

---

## The Template Substitution Bug (November 2025)

### Critical Production Bug

**Discovery**: 122 job posting summaries contained hallucinations instead of proper analysis:
- Template placeholders: `"{session_9_output}"`
- Meta-commentary: "based on session_4_output"
- Instruction leakage: "Craft a summary..."

### Root Cause Timeline

Here's the exact sequence of events showing WHERE and WHEN the failure occurred:

```
WAVE 1 (Execution Order 2) - Step: Extract Summary
├─ Time: 10:00:00
├─ Posting 123: Execute conversation 3341 (extract_summary)
│  └─ Actor processes job description → output: "Summary: Python dev role..."
├─ posting.outputs[3341] = "Summary: Python dev role..."
├─ Save checkpoint to database:
│  └─ state_snapshot.outputs.3341 = "Summary: Python dev role..."  ✅ SAVED
├─ Posting marked complete for this wave
└─ PostingState object remains in memory (for now)

───────────────────────────────────────────────────────────────────
⏱️  3-5 MINUTE GAP - Processing other postings at execution_order 2
───────────────────────────────────────────────────────────────────

WAVE 2 (Execution Order 3) - Step: Grade Summary  
├─ Time: 10:04:30 (4.5 minutes later)
├─ System reloads active postings from database
│  └─ Query: SELECT * FROM posting_state_checkpoints WHERE posting_id = 123
├─ ❌ BUG: PostingState.from_checkpoint() doesn't restore outputs dict!
│  ├─ state_snapshot loaded from JSONB ✅
│  ├─ posting.current_conversation_id = 3342 ✅
│  ├─ posting.execution_sequence restored ✅
│  └─ posting.outputs = {} ❌ EMPTY! Should have {3341: "Summary: ..."}
├─ Conversation 3342 (grade_summary) template contains:
│  └─ "Please grade this summary: {conversation_3341_output}"
├─ Template substitution attempts posting.outputs[3341]
│  └─ KeyError! Dict is empty → falls back to literal string
├─ LLM receives prompt:
│  └─ "Please grade this summary: {conversation_3341_output}"  ❌ LITERAL!
└─ LLM hallucinates what {conversation_3341_output} "should" be
   └─ Output: "Grade: 7/10 based on the provided summary about Python..."
       (But no summary was actually provided!)
```

### Why This Happened

1. **Wave Processing**: Postings processed in batches, creating multi-minute gaps
2. **Memory Reset**: Between waves, PostingState objects discarded and reloaded
3. **Incomplete Deserialization**: `PostingState.from_checkpoint()` loaded JSONB but didn't parse `outputs` nested dict
4. **Template Dependency**: Conversation prompts assumed `posting.outputs` would be populated
5. **Silent Failure**: No error raised—template substitution just used literal string
6. **LLM Cooperation**: Instead of refusing, LLMs generated plausible-sounding content

### Impact

- **122 postings affected** (hallucinated summaries/grades)
- **Detection**: Pattern-based QA script (`qa_check_hallucinations.py`)
- **Fix**: Checkpoint Query Pattern (query database instead of trusting in-memory dict)

**Documentation**: See `docs/TEMPLATE_SUBSTITUTION_BUG.md` for complete technical analysis

---

## Checkpoint Query Pattern (Standard Solution)

### Philosophy

Query workflow state **directly from checkpoints** instead of relying on fragile in-memory template substitution.

### Why Checkpoints?

- `posting_state_checkpoints` is source of truth for workflow state
- JSONB storage: `state_snapshot->'outputs'->'CONVERSATION_ID'` contains all conversation outputs
- Survives crashes, wave boundaries, process restarts
- No dependency on in-memory state propagation

### OLD PATTERN (BROKEN)

Relies on template substitution from posting.outputs dict:

```python
# In actor script_code:
summary_text = "{conversation_3341_output}"  # FAILS across waves!
```

**Problem**: `posting.outputs` dict not reliably restored from checkpoints across wave boundaries.

### NEW PATTERN (RELIABLE)

Query checkpoints directly:

```python
def get_formatted_summary_from_checkpoint(posting_id: int) -> str:
    cursor.execute("""
        SELECT state_snapshot->'outputs'->'3341'
        FROM posting_state_checkpoints
        WHERE posting_id = %s 
          AND state_snapshot->'outputs' ? '3341'
        ORDER BY created_at DESC 
        LIMIT 1
    """, (posting_id,))
    return cursor.fetchone()[0]
```

---

## Checkpoint Utils Module

### Helper Functions

From `core/checkpoint_utils.py`:

```python
from core.checkpoint_utils import (
    get_conversation_output,
    get_multiple_outputs,
    checkpoint_exists,
    get_all_outputs
)
```

### get_conversation_output()

Retrieve single conversation output:

```python
def get_conversation_output(
    posting_id: int, 
    conversation_id: int,
    allow_missing: bool = False
) -> Optional[str]:
    """
    Get output from specific conversation for a posting
    
    Args:
        posting_id: Posting ID
        conversation_id: Conversation ID
        allow_missing: If True, return None if not found. If False, raise error.
    
    Returns:
        str: Conversation output, or None if allow_missing=True and not found
    
    Raises:
        ValueError: If output not found and allow_missing=False
    """
```

**Usage**:
```python
# Strict mode (raises error if missing)
summary = get_conversation_output(posting_id=123, conversation_id=3341)

# Lenient mode (returns None if missing)
summary = get_conversation_output(posting_id=123, conversation_id=3341, allow_missing=True)
if summary is None:
    # Handle missing case
```

### get_multiple_outputs()

Retrieve multiple conversation outputs at once:

```python
def get_multiple_outputs(
    posting_id: int,
    conversation_ids: List[int]
) -> Dict[int, str]:
    """
    Get outputs from multiple conversations for a posting
    
    Args:
        posting_id: Posting ID
        conversation_ids: List of conversation IDs
    
    Returns:
        Dict[int, str]: conversation_id → output mapping
    """
```

**Usage**:
```python
outputs = get_multiple_outputs(
    posting_id=123,
    conversation_ids=[3341, 3342, 3343]
)

summary = outputs.get(3341)
grade = outputs.get(3342)
improved = outputs.get(3343)
```

### checkpoint_exists()

Check if checkpoint exists before querying:

```python
def checkpoint_exists(
    posting_id: int, 
    conversation_id: int
) -> bool:
    """
    Check if checkpoint exists for posting/conversation
    
    Returns:
        bool: True if checkpoint with this output exists
    """
```

**Usage**:
```python
if checkpoint_exists(posting_id=123, conversation_id=3341):
    summary = get_conversation_output(123, 3341)
else:
    # Generate summary or handle missing case
    pass
```

### get_all_outputs()

Get all conversation outputs for a posting:

```python
def get_all_outputs(posting_id: int) -> Dict[int, str]:
    """
    Get all conversation outputs for a posting
    
    Returns:
        Dict[int, str]: conversation_id → output mapping
    """
```

**Usage**:
```python
all_outputs = get_all_outputs(posting_id=123)

for conv_id, output in all_outputs.items():
    print(f"Conversation {conv_id}: {len(output)} chars")
```

---

## Migration from Template Substitution

### Migration Checklist

See `docs/CHECKPOINT_MIGRATION_CHECKLIST.md` for complete guide.

**Quick Steps**:

1. **Identify actors using template substitution**:
   ```sql
   SELECT actor_id, actor_name, script_code
   FROM actors
   WHERE script_code LIKE '%{conversation_%'
      OR script_code LIKE '%{session_%';
   ```

2. **Update script to use checkpoint queries**:
   ```python
   # OLD:
   summary = "{conversation_3341_output}"
   
   # NEW:
   from core.checkpoint_utils import get_conversation_output
   summary = get_conversation_output(posting_id, 3341)
   ```

3. **Deploy updated actor code**:
   ```bash
   python3 tools/update_actor_code.py --actor-id 77
   ```

4. **Test with sample postings**:
   ```bash
   python3 tools/test_actor.py --actor-id 77 --posting-id 123
   ```

5. **Clear bad data and re-run workflow**:
   ```sql
   UPDATE postings SET extracted_summary = NULL WHERE posting_id IN (...);
   ```

---

## Checkpoint Queries

### Query Latest State

```sql
-- Get latest checkpoint for posting
SELECT state_snapshot
FROM posting_state_checkpoints
WHERE posting_id = 123
ORDER BY created_at DESC
LIMIT 1;
```

### Query Specific Conversation Output

```sql
-- Get output from conversation 3341
SELECT state_snapshot->'outputs'->'3341' as summary
FROM posting_state_checkpoints
WHERE posting_id = 123
  AND state_snapshot->'outputs' ? '3341'
ORDER BY created_at DESC
LIMIT 1;
```

### Query Execution Path

```sql
-- See path posting took through workflow
SELECT state_snapshot->'execution_sequence' as path
FROM posting_state_checkpoints
WHERE posting_id = 123
ORDER BY created_at DESC
LIMIT 1;
```

### Query All Postings at Specific Step

```sql
-- Find all postings currently at execution_order 3
SELECT posting_id, state_snapshot->>'current_conversation_id' as conv_id
FROM (
    SELECT DISTINCT ON (posting_id) *
    FROM posting_state_checkpoints
    WHERE workflow_run_id = 4567
    ORDER BY posting_id, created_at DESC
) latest
WHERE execution_order = 3;
```

---

## Benefits

### Crash Recovery

- **Automatic resume**: Workflow continues from last checkpoint
- **No lost work**: All completed conversations preserved
- **No duplicate work**: Idempotency checks prevent re-execution

### Reliable State Access

- ✅ Survives wave boundaries (3+ minute gaps)
- ✅ Survives crashes (state persisted in database)
- ✅ Debugging (can query historical state)
- ✅ Auditability (checkpoint trail shows all intermediate results)
- ✅ No template fragility (direct SQL query, no string substitution)

### Performance

- **Fast saves**: ~8ms per checkpoint (GPU never waits)
- **Connection pooling**: Reuses pooled connections (no overhead)
- **Minimal overhead**: Only PostingState serialization (~7ms)

---

## Common Patterns

### Pattern 1: Idempotency Check via Checkpoints

```python
def check_work_done(posting_id: int, conversation_id: int) -> bool:
    """Check if conversation already executed for posting"""
    return checkpoint_exists(posting_id, conversation_id)
```

### Pattern 2: Multi-Stage Pipeline State

```python
# Get outputs from all extraction stages
outputs = get_multiple_outputs(
    posting_id=123,
    conversation_ids=[3335, 3336, 3337, 3338, 3339]  # Extract → Grade → Improve → Format
)

# Verify all stages complete
if all(outputs.values()):
    final_summary = outputs[3339]  # Formatted summary
else:
    # Incomplete pipeline
    missing = [cid for cid in [3335, 3336, 3337, 3338, 3339] if cid not in outputs]
```

### Pattern 3: Debugging Workflow State

```python
# Trace posting's journey
all_outputs = get_all_outputs(posting_id=123)

print(f"Posting {posting_id} completed {len(all_outputs)} conversations:")
for conv_id, output in all_outputs.items():
    print(f"  Conversation {conv_id}: {len(output)} chars")
```

---

## Comprehensive Guides

- **Root Cause Analysis**: `docs/TEMPLATE_SUBSTITUTION_BUG.md`
- **Migration Guide**: `docs/CHECKPOINT_MIGRATION_CHECKLIST.md`
- **Query Pattern Guide**: `docs/CHECKPOINT_QUERY_PATTERN.md`
- **Hallucination Detection**: `docs/HALLUCINATION_DETECTION_COOKBOOK.md`

---

## See Also

**Related Architecture Docs**:
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - posting_state_checkpoints table: JSONB state_snapshot
- [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md) - Checkpoints saved after each wave conversation
- [ACTOR_SYSTEM.md](ACTOR_SYSTEM.md) - Script actors using checkpoint_utils for state access
- [CONNECTION_POOLING.md](CONNECTION_POOLING.md) - Efficient checkpoint queries with pooled connections
- [CODE_DEPLOYMENT.md](CODE_DEPLOYMENT.md) - Where checkpoint_utils.py lives (core/)

**Key Code Files**:
- `core/checkpoint_manager.py` - save_checkpoint(), load_latest_checkpoint()
- `core/checkpoint_utils.py` - get_conversation_output(), get_multiple_outputs()
- `scripts/qa_check_hallucinations.py` - Hallucination detection patterns

**Root Cause Analysis**:
- `docs/TEMPLATE_SUBSTITUTION_BUG.md` - Complete technical breakdown
- `docs/CHECKPOINT_QUERY_PATTERN.md` - Migration guide from templates to queries

**Main Reference**:
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - Comprehensive system overview
