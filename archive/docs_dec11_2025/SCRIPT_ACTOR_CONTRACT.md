# Script Actor Contract

**Version:** 1.0  
**Date:** 2025-12-08  
**Author:** Sandy (discovered), Arden (documented)

---

## Overview

Script actors are Python scripts executed via subprocess by the WaveRunner.
They are **NOT** imported as modules - they run as standalone processes.

---

## Execution Model

```
WaveRunner
    ↓
ScriptExecutor.execute()
    ↓
subprocess.run(['python3', script_file_path], stdin=JSON, capture_output=True)
    ↓
Script reads stdin, processes, writes stdout
    ↓
ScriptExecutor parses stdout as JSON
    ↓
WaveRunner continues with result
```

---

## Input Contract

Scripts receive a JSON object on **stdin** with:

```json
{
  "interaction_id": 78817,
  "posting_id": null,
  "workflow_run_id": 5986,
  "param1": "value1",
  "param2": "value2"
}
```

The exact fields depend on:
1. What the workflow step's `input` contains
2. What the runner automatically adds (`interaction_id`, `posting_id`, `workflow_run_id`)

**Read it like this:**
```python
import sys
import json

input_data = {}
if not sys.stdin.isatty():
    input_data = json.load(sys.stdin)
```

---

## Output Contract

Scripts **MUST** write a JSON object to **stdout**:

```json
{
  "status": "success",
  "data": {...},
  "message": "Optional human-readable message"
}
```

**Or on error:**
```json
{
  "status": "error",
  "error": "Description of what went wrong"
}
```

**Write it like this:**
```python
import json

result = {"status": "success", "data": {...}}
print(json.dumps(result))
```

⚠️ **WARNING:** Any non-JSON output to stdout will cause the runner to fail!
Use `sys.stderr` for debug output.

---

## Database Access

Scripts create their **OWN** database connection using environment variables:

```python
import os
import psycopg2
from pathlib import Path

# Load .env file manually (or use python-dotenv)
env_file = Path(__file__).parent.parent.parent.parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ.setdefault(k, v)

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', 5432),
    dbname=os.getenv('DB_NAME', 'turing'),
    user=os.getenv('DB_USER', 'base_admin'),
    password=os.getenv('DB_PASSWORD', '')
)
```

**Why own connection?** Scripts run in a subprocess - they cannot share the parent's connection.

---

## Template: Script Actor Boilerplate

```python
#!/usr/bin/env python3
"""
[ACTOR NAME] - [WORKFLOW] Step [N]

[Brief description of what this actor does]

Author: [Name]
Date: [Date]
"""

import json
import sys
import os
import psycopg2
import psycopg2.extras
from pathlib import Path


def execute(input_data: dict, conn) -> dict:
    """
    Main execution logic.
    
    Args:
        input_data: JSON from stdin (interaction context)
        conn: Database connection
        
    Returns:
        dict with status and result data
    """
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Your logic here
        result = {"key": "value"}
        
        return {
            "status": "success",
            "data": result,
            "message": "Processed successfully"
        }
        
    except Exception as e:
        conn.rollback()
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Load environment from .env file
    env_file = Path(__file__).parent.parent.parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)
    
    # Read input from stdin
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            pass
    
    # Create database connection
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    
    try:
        result = execute(input_data, conn)
        print(json.dumps(result))
    finally:
        conn.close()
```

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Forgetting `if __name__ == "__main__"` | Script doesn't run via subprocess | Add the block |
| Printing debug output to stdout | JSON parse error | Use `sys.stderr.write()` for debug |
| Hardcoding DB credentials | Works locally, fails in prod | Use environment variables |
| Not handling `stdin.isatty()` | Script hangs waiting for input | Check before reading |
| Returning non-JSON | WaveRunner fails to parse | Always `print(json.dumps(result))` |
| Forgetting `conn.rollback()` on error | Transaction left open | Always rollback in exception handler |

---

## Testing Script Actors

```bash
# Test with sample input
echo '{"interaction_id": 1, "posting_id": null}' | \
  python3 core/wave_runner/actors/my_script.py

# Verify JSON output is valid
echo '{}' | python3 core/wave_runner/actors/my_script.py | jq .

# Test with actual workflow input
echo '{"interaction_id": 78817, "workflow_run_id": 5986}' | \
  python3 core/wave_runner/actors/entity_orphan_fetcher.py | jq .
```

---

## Database Column: `actors.script_file_path`

Scripts are located via the `script_file_path` column in the `actors` table:

```sql
SELECT actor_id, actor_name, script_file_path
FROM actors
WHERE actor_type = 'script'
  AND script_file_path IS NOT NULL;
```

⚠️ **Note:** The `execution_path` column is **DEPRECATED**. Use `script_file_path`.

---

## Related Files

- `core/wave_runner/executors.py` - `ScriptExecutor` class
- `core/wave_runner/runner.py` - `_execute_script()` method
- `core/wave_runner/script_sync.py` - Syncs scripts from filesystem to DB

---

## History

| Date | Change | Author |
|------|--------|--------|
| 2025-12-08 | Created after debugging WF3005 | Sandy |
| 2025-12-08 | Reviewed and approved | Arden |
