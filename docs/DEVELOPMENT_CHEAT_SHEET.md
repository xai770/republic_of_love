# Turing Development Cheat Sheet

Quick reference for common patterns. Full directives in `docs/Turing_project_directives.md`.

## New Actor Checklist

```bash
cp thick_actors/TEMPLATE_thick_actor.py thick_actors/{table}__{attribute}_{CRUD}.py
```

1. [ ] Update docstring (input/output tables, Mermaid diagram)
2. [ ] Rename class from `YourActorName`
3. [ ] Set `TASK_TYPE_ID` after DB insert
4. [ ] Set `INSTRUCTION_ID` if using prompts from DB
5. [ ] Implement `_preflight()` - validate input, skip bad data
6. [ ] Implement `_do_work()` - core logic
7. [ ] Implement `_qa_check()` - validate output
8. [ ] Implement `_save_result()` - write to DB
9. [ ] Test: `python3 scripts/my_new_actor.py`
10. [ ] Register: `INSERT INTO task_types ...`
11. [ ] Hash: `./tools/turing/turing-hash-scripts --update`
12. [ ] Verify: `turing-harness run my_actor --input '{"posting_id": 123}'`
13. [ ] RAQ test: `turing-raq start my_actor --count 10 --runs 3`

## Key Directives

**Full coding rules (#7-19) are in [thick_actors/TEMPLATE_thick_actor.py](../thick_actors/TEMPLATE_thick_actor.py).**

Quick reminders:
- Use constants (`Status.COMPLETED`), not strings (`'completed'`)
- Use `get_connection()`, not hardcoded credentials  
- LLM: `temperature=0`, seed from `task_types` table
- Three phases: preflight → process → QA
- Naming: `{table}__{attribute}_{CRUD}.py`

## Three-Phase Actor Structure

```python
def process(self):
    # PHASE 1: PREFLIGHT - Is the data any good?
    preflight = self._preflight(subject_id)
    if not preflight['ok']:
        return {'success': False, 'skip_reason': preflight['reason']}
    
    # PHASE 2: PROCESS - Do the work
    result = self._do_work(preflight['data'])
    
    # PHASE 3: QA - Is the output any good?
    qa_result = self._qa_check(input_data, result)
    if not qa_result['passed']:
        # Retry or fail
```

## Constants (USE THESE)

```python
from core.constants import Status, Fields, OwlTypes

# Status values (task_logs.status)
Status.PENDING    # 'pending'
Status.RUNNING    # 'running'  
Status.COMPLETED  # 'completed'
Status.FAILED     # 'failed'

# Field names (output dicts)
Fields.OWL_ID           # 'owl_id'
Fields.TASK_TYPE_ID     # 'task_type_id'
Fields.SUCCESS          # 'success'
Fields.ERROR            # 'error'
Fields.PARENT_OUTPUT    # 'parent_output'
```

## Database Patterns

```python
# Connection
from core.database import get_connection
conn = get_connection()  # Uses .env credentials

# Dict cursor (most common)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT * FROM postings WHERE posting_id = %s", (posting_id,))
row = cur.fetchone()  # Dict: row['posting_id']

# Always commit after writes
cur.execute("UPDATE ...")
conn.commit()

# Always rollback on error
except Exception as e:
    conn.rollback()
    return {'success': False, 'error': str(e)}
```

## Task Type Setup

```sql
-- 1. Create task_type
INSERT INTO task_types (
    task_type_name,
    task_type_description,
    execution_type,
    script_path,
    requires_model,
    work_query,
    input_table,
    input_columns,
    output_table,
    output_columns,
    triggers_when
) VALUES (
    'my_new_actor',
    'Does X to Y when Z',
    'thick',
    'scripts/my_new_actor.py',
    'qwen2.5-coder:7b',
    'SELECT posting_id as subject_id, ''posting'' as subject_type 
     FROM postings WHERE some_column IS NULL LIMIT :batch_size',
    'postings',
    ARRAY['job_description'],
    'postings', 
    ARRAY['some_column'],
    'posting needs X processing'
) RETURNING task_type_id;

-- 2. Update hash
./tools/turing/turing-hash-scripts --update
```

## LLM Calls

```python
# Get settings from task_types (not hardcoded!)
cur.execute(
    "SELECT llm_temperature, llm_seed FROM task_types WHERE task_type_id = %s",
    (task_type_id,)
)
row = cur.fetchone()
temp = float(row['llm_temperature'] or 0)
seed = int(row['llm_seed'] or 42)

# Ollama call
response = requests.post('http://localhost:11434/api/generate', json={
    'model': 'qwen2.5-coder:7b',
    'prompt': prompt,
    'stream': False,
    'options': {
        'temperature': temp,
        'seed': seed,
        'num_predict': 4096,
    }
})
```

## Testing

```bash
# Dry run (no changes)
python3 core/pull_daemon.py --task_type 1234 --dry-run

# Single item
python3 core/pull_daemon.py --task_type 1234 --limit 1

# Check hashes (CI mode)
./tools/turing/turing-hash-scripts --check

# Direct test
python3 scripts/my_new_actor.py
```

## Query Patterns

```sql
-- What reads from postings?
SELECT task_type_name FROM task_types WHERE input_table = 'postings';

-- What writes extracted_summary?
SELECT task_type_name FROM task_types WHERE 'extracted_summary' = ANY(output_columns);

-- Active task types
SELECT task_type_name, input_table, output_table 
FROM task_types WHERE enabled = true AND work_query IS NOT NULL;
```

## DON'Ts

- ❌ Hardcode `'completed'` → use `Status.COMPLETED`
- ❌ Hardcode connection strings → use `get_connection()`
- ❌ Hardcode temperature/seed → read from `task_types`
- ❌ `print()` for logging → return in output dict
- ❌ Catch Exception and continue → rollback and return error
- ❌ Create queue tables → use `work_query` to find work

## Tools Quick Reference (tools/turing/)

```bash
# After ANY code change to actor:
./tools/turing/turing-hash-scripts --update

# Test actor directly (no daemon):
turing-harness run my_actor --input '{"posting_id": 123}'

# RAQ testing (repeatability):
turing-raq start my_actor --count 10 --runs 3
turing-raq status my_actor          # Check progress
turing-raq reset my_actor           # Clear for re-run (auto-backs up)

# Debug failures:
turing-trace --posting 123          # Full execution trace
turing-errors --limit 10            # Recent failures

# Monitor:
turing-status my_actor              # Progress overview
turing-dashboard                    # Live TUI
turing-dashboard -W 30              # Watchdog mode (check every 30s)
turing-dashboard -W 30 -r -c 20     # + auto-restart + circuit breaker (20%)

# Pipeline status:
# Use posting_pipeline_status view to see what stage each posting is at
```

### Tool Contracts

| Tool | What It Reads | What Actor Must Have |
|------|---------------|---------------------|
| `turing-hash-scripts` | `task_types.script_path` | Script at that path |
| `turing-harness` | Class with `process()` | `__init__(db_conn=None)` |
| `turing-raq` | `task_types.raq_config` | `state_tables`, `compare_output_field` |
| `pull_daemon` | `task_types.work_query` | Returns dict, optional `_consistency` |

### RAQ Config Template

```sql
UPDATE task_types SET raq_config = '{
    "state_tables": [
        {"table": "postings", "filter": "posting_id = :subject_id"}
    ],
    "compare_output_field": "output::text"
}'::jsonb WHERE task_type_id = ???;
```

## Pipeline Change Verification Pattern

**After ANY change to pipeline config (task_types priorities, work_queries, actor logic, daemon changes):**

1. Make the change (SQL update, code edit, etc.)
2. Run a catch-up `turing_fetch.sh` immediately to verify:
   ```bash
   nohup bash scripts/turing_fetch.sh >> logs/turing_fetch.log 2>&1 &
   ```
3. Monitor with: `tail -f logs/turing_fetch.log`
4. Compare before/after metrics (embedding count, description count, etc.)

**Do NOT wait for the nightly cron.** Always run a catch-up to confirm the change works end-to-end.

### Daemon Actor Execution Order

The `turing_daemon` (Step 4) runs actors sequentially by `task_types.priority DESC`.
Order matters — actors that produce data must run before actors that consume it.

```
job_description_backfill (60)  →  fetches HTML descriptions from AA/DB
extracted_summary        (50)  →  LLM-summarizes DB corporate wordiness
embedding_generator      (30)  →  embeds match_text (needs descriptions + summaries first!)
owl_pending_auto_triage  (10)  →  LLM picks best berufenet match
external_partner_scrape   (0)  →  scrapes partner job sites
domain_gate_classifier    (0)  →  classifies posting domains
```

To change order: `UPDATE task_types SET priority = <N> WHERE task_type_name = '<name>';`
