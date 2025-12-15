# Idempotency & Pre-flight Checks Pattern

## Problem
Running expensive LLM operations on data that's already been processed:
- Re-extracting summaries that already exist
- Re-running fetcher when it ran 2 hours ago (rate limit: 24h)
- Re-extracting skills that are already in database

## Solution: Two-Layer Check Pattern

### Layer 1: Entry Filter (Wave Processor)
```python
# In _get_pending_postings()
WHERE extracted_summary IS NULL  # Only load unprocessed postings
```
✅ Already implemented - prevents loading finished postings into pipeline

### Layer 2: Pre-flight Checks (Per Conversation)
Add check actors BEFORE expensive operations:

```
Workflow Structure:
┌──────────────────────────────────────────┐
│ 1. check_fetch_needed (script actor)    │
│    → [SKIP_FETCH] → gemma3_extract       │
│    → [RUN_FETCH] → db_job_fetcher        │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│ 2. db_job_fetcher (if needed)            │
│    → [SUCCESS] → gemma3_extract          │
│    → [RATE_LIMITED] → gemma3_extract     │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│ 3. check_posting_status (script actor)   │
│    check_fields: ['extracted_summary']   │
│    → [COMPLETE] → TERMINAL (skip!)       │
│    → [INCOMPLETE] → gemma3_extract       │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│ 4. gemma3_extract (only if needed)       │
│    → [SUCCESS] → gemma2_grade            │
└──────────────────────────────────────────┘
```

## Implementation Scripts

### 1. tools/check_fetch_needed.py
**Purpose:** Check if fetcher ran in last 24 hours
**Input:** `{"user_id": 1}`
**Output:** 
```json
{
  "status": "SKIP_FETCH",
  "last_run": "2025-11-13T10:15:00",
  "hours_since": 12.5,
  "hours_remaining": 11.5,
  "branch": "[SKIP_FETCH]"
}
```

### 2. tools/check_posting_status.py
**Purpose:** Check if specific fields already exist
**Input:** 
```json
{
  "posting_id": 858,
  "check_fields": ["extracted_summary", "taxonomy_skills"]
}
```
**Output:**
```json
{
  "posting_id": 858,
  "extracted_summary": {"exists": true, "value_preview": "**Role:** Senior..."},
  "taxonomy_skills": {"exists": false},
  "all_complete": false,
  "branch": "[INCOMPLETE]"
}
```

## Migration Pattern

To add pre-flight checks to existing workflow:

```sql
-- 1. Create check actor
INSERT INTO actors (actor_name, actor_type, canonical_name, execution_path, execution_config)
VALUES (
    'Check Fetch Needed',
    'script',
    'check_fetch_needed',
    'tools/check_fetch_needed.py',
    '{"rate_limit_hours": 0}'::jsonb  -- No rate limit on check itself
) RETURNING actor_id;  -- e.g., 67

-- 2. Create check conversation
INSERT INTO conversations (conversation_name, canonical_name, actor_id)
VALUES (
    'Pre-flight: Check Fetch Status',
    'preflight_check_fetch',
    67
) RETURNING conversation_id;  -- e.g., 9200

-- 3. Add to workflow (execution_order = 1, before fetcher)
INSERT INTO workflow_conversations (workflow_id, conversation_id, execution_order)
VALUES (3001, 9200, 1);

-- 4. Bump execution_order of all subsequent conversations
UPDATE workflow_conversations
SET execution_order = execution_order + 1
WHERE workflow_id = 3001 AND execution_order >= 1;

-- 5. Create instruction with branching
INSERT INTO instructions (instruction_name, conversation_id, step_number, prompt_template)
VALUES (
    'Check if fetch needed',
    9200,
    1,
    '{"user_id": 1}'  -- JSON input for script
) RETURNING instruction_id;  -- e.g., 3400

-- 6. Add branch conditions
INSERT INTO instruction_steps (instruction_id, instruction_step_name, branch_condition, next_conversation_id, branch_priority)
VALUES
    (3400, 'Skip fetch if recent', '[SKIP_FETCH]', 3327, 100),  -- → gemma3_extract
    (3400, 'Run fetch if stale', '[RUN_FETCH]', 3326, 90);       -- → db_job_fetcher
```

## Benefits

### Performance
- **Fetcher:** Save ~1,871 rate limit checks (1 check vs 1,871 checks)
- **Extraction:** Skip postings that already have summaries
- **Skills:** Skip postings that already have taxonomy skills

### Cost
- Avoid re-running expensive LLM operations ($$ savings)
- Avoid API rate limits from redundant requests

### Reliability
- Idempotent operations = safe to re-run workflows
- Crash recovery: restart workflow, only processes missing data

## Usage

### Test Check Scripts
```bash
# Test fetch check
echo '{"user_id": 1}' | python3 tools/check_fetch_needed.py

# Test posting status check
echo '{"posting_id": 858, "check_fields": ["extracted_summary"]}' | \
  python3 tools/check_posting_status.py
```

### Add to Workflow
See migration pattern above. Key steps:
1. Create check actor
2. Create check conversation
3. Insert at appropriate execution_order
4. Add branching logic
5. Test with limit=1

## Best Practices

### When to Add Checks
✅ Before expensive operations (LLM calls, API requests)
✅ Before operations that might fail (API rate limits)
✅ Before operations that modify data (prevent duplicates)

### When NOT to Add Checks
❌ Before cheap operations (<100ms, like simple queries)
❌ Before operations that must always run (final save step)
❌ When entry filter already handles it (loading postings WHERE field IS NULL)

### Check Granularity
- **Wave-level checks:** Rate limits, API availability (check once per wave)
- **Posting-level checks:** Data existence, field population (check per posting)

## Wave Processor Integration

The wave processor now has wave-level rate limit optimization (committed):
```python
# Check rate limit ONCE at start of wave, not for every posting
if rate_limit_hours and last_run < 24h_ago:
    print(f"⏭ Wave-level RATE LIMIT: skipping all {len(postings)} postings")
    # Route all postings via [RATE_LIMITED] branch
    for posting in postings:
        posting.outputs[conversation_id] = '[RATE_LIMITED]'
        posting.current_conversation_id = next_conversation_id
    return len(postings)
```

This eliminates 1,871 redundant rate limit checks when fetcher ran recently.

## Next Steps

1. ✅ Create check scripts (done)
2. ⏳ Add to workflow 3001 via migration
3. ⏳ Test with --limit 1
4. ⏳ Deploy to production
5. ⏳ Monitor performance gains
