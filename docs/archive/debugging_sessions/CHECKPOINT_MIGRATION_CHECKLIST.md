# Checkpoint Query Pattern - Migration Checklist

**Purpose:** Quick reference for migrating actors from template substitution to checkpoint queries

---

## Pre-Migration Audit

Run this query to find actors that need migration:

```sql
SELECT 
    actor_id,
    actor_name,
    actor_type,
    enabled
FROM actors
WHERE (script_code LIKE '%{session_%' OR script_code LIKE '%{conversation_%')
  AND enabled = true
ORDER BY actor_id;
```

---

## Migration Steps

### Step 1: Add Import

```python
from core.checkpoint_utils import get_conversation_output
```

### Step 2: Replace Template Variable Usage

**Before:**
```python
# Relies on wave_batch_processor to substitute {conversation_3341_output}
# in prompt_template before sending to script
```

**After:**
```python
import os
posting_id = int(os.environ['POSTING_ID'])

# Explicitly get the data
formatted_summary = get_conversation_output(posting_id, '3341')
```

### Step 3: Update Actor Script

Example migration for a typical actor:

```python
#!/usr/bin/env python3
"""
Actor: save_final_output
Migrated to checkpoint query pattern: 2025-11-17
"""

import os
import sys
from core.database import get_connection, return_connection
from core.checkpoint_utils import get_conversation_output

def main():
    # Get posting_id from environment
    posting_id = int(os.environ['POSTING_ID'])
    
    # CHECKPOINT QUERY: Get data from previous conversations
    summary = get_conversation_output(posting_id, '3341')
    requirements = get_conversation_output(posting_id, '3338', allow_missing=True)
    
    # Process the data
    save_to_database(posting_id, summary, requirements)
    
    # Return success
    print("[SUCCESS]")

if __name__ == '__main__':
    main()
```

### Step 4: Test

```bash
# Test with single posting
python3 -m core.wave_batch_processor --workflow WORKFLOW_ID --posting-ids TEST_POSTING_ID

# Check logs for errors
tail -f /tmp/workflow_WORKFLOW_ID.log

# Verify checkpoint data exists
psql ... -c "
SELECT state_snapshot->'outputs'->'3341' 
FROM posting_state_checkpoints 
WHERE posting_id = TEST_POSTING_ID 
ORDER BY created_at DESC LIMIT 1;
"
```

### Step 5: Update Database

```sql
-- Update the actor script in database
UPDATE actors
SET script_code = '[YOUR MIGRATED SCRIPT]',
    updated_at = NOW()
WHERE actor_id = [ACTOR_ID];
```

---

## Common Patterns

### Pattern: Simple replacement

**Before:** `{conversation_3341_output}` in template  
**After:** `get_conversation_output(posting_id, '3341')`

### Pattern: Multiple outputs

**Before:**
```
Summary: {conversation_3341_output}
Requirements: {conversation_3338_output}
```

**After:**
```python
from core.checkpoint_utils import get_multiple_outputs

outputs = get_multiple_outputs(posting_id, ['3341', '3338'])
summary = outputs['3341']
requirements = outputs['3338']
```

### Pattern: Optional data

**Before:** No good way to handle missing data  
**After:**
```python
optional_data = get_conversation_output(posting_id, '3340', allow_missing=True)
if optional_data:
    process(optional_data)
else:
    use_fallback()
```

---

## Verification Checklist

- [ ] Removed all `{conversation_X}` and `{session_X}` from script_code
- [ ] Added import for `checkpoint_utils`
- [ ] Added code to get posting_id from environment
- [ ] Added checkpoint queries for all needed data
- [ ] Tested with real posting data
- [ ] Verified output matches expected format
- [ ] Updated actor in database
- [ ] Documented conversation IDs used in actor comments

---

## Status: Workflow 3001

- ✅ Actor 77 (summary_saver) - Migrated 2025-11-15
- ✅ All workflow 3001 actors using checkpoint queries
- ✅ 122 postings regenerated successfully
- ✅ Zero template substitution bugs

---

## For Future Workflows

**Recommendation:** Start with checkpoint queries from day 1. Don't use template substitution.

**Standard actor template:**

```python
#!/usr/bin/env python3
import os
from core.checkpoint_utils import get_conversation_output

def main():
    posting_id = int(os.environ['POSTING_ID'])
    
    # Get data from checkpoints
    data = get_conversation_output(posting_id, 'CONVERSATION_ID')
    
    # Process
    result = process(data)
    
    # Output
    print(result)

if __name__ == '__main__':
    main()
```

**See:** `docs/CHECKPOINT_QUERY_PATTERN.md` for full documentation
