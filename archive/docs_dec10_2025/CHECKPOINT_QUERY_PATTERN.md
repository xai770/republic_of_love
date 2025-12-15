# Checkpoint Query Pattern - Workflow Data Passing

**Status:** RECOMMENDED PATTERN (2025-11-17)  
**Replaces:** Template substitution (`{session_X_output}`, `{conversation_X_output}`)  
**Reason:** More reliable, more flexible, no wave boundary bugs  

---

## What Problem Does This Solve?

In multi-wave workflows, you need to pass data from earlier steps to later steps. For example:
- Step 5 generates a formatted summary
- Step 10 needs to save that summary to the database

**The old way (template substitution)** had a critical bug: data would vanish between waves, causing literal `{conversation_3341_output}` to appear in prompts instead of the actual data.

**The new way (checkpoint queries)** directly fetches data from the `posting_state_checkpoints` table, which is the source of truth for workflow state.

---

## How It Works (Human-Readable Explanation)

### The Big Picture

Think of checkpoints as a **save game file** for each posting as it goes through the workflow:

```
Posting 4650 starts workflow 3001:
├── Step 1: Extract job title → Save checkpoint: {"outputs": {"3335": "Software Engineer"}}
├── Step 2: Extract company → Save checkpoint: {"outputs": {"3335": "...", "3336": "Google Inc"}}
├── Step 3: Extract location → Save checkpoint: {"outputs": {"3335": "...", "3336": "...", "3337": "Mountain View, CA"}}
...
├── Step 9: Format summary → Save checkpoint: {"outputs": {..., "3341": "**Role:** Software Engineer\n**Company:**..."}}
└── Step 10: Save to database → ❓ How do we get Step 9's output?
```

**Old approach (broken):**
```
Step 10 says: "Give me {conversation_3341_output}"
Wave processor says: "Let me check posting.outputs dict... 
                      Uh oh, it's empty because we crossed a wave boundary"
Result: Literal "{conversation_3341_output}" goes into the prompt → BROKEN
```

**New approach (reliable):**
```
Step 10 says: "I need conversation 3341's output. Let me query the checkpoint directly."
  
SELECT state_snapshot->'outputs'->'3341' 
FROM posting_state_checkpoints
WHERE posting_id = 4650
ORDER BY created_at DESC LIMIT 1;

Result: "**Role:** Software Engineer\n**Company:** Google Inc..." → ✓ WORKS
```

### The Storage System

**Where checkpoints live:** `posting_state_checkpoints` table

```sql
posting_state_checkpoints
├── checkpoint_id (unique ID)
├── posting_id (which job posting)
├── workflow_run_id (which run of the workflow)
├── step_name (e.g., "Format Standardization")
├── state_snapshot (JSONB - the actual data) ← THIS IS THE GOLD
└── created_at (timestamp)
```

**What's in state_snapshot:**
```json
{
  "outputs": {
    "3335": "Extract Job Title output goes here",
    "3336": "Extract Company output goes here",
    "3337": "Extract Location output goes here",
    "3338": "Extract Requirements output goes here",
    "3339": "Extract Benefits output goes here",
    "3340": "Enrich Details output goes here",
    "3341": "**Role:** Software Engineer\n**Company:** Google Inc\n..."
  },
  "metadata": {
    "current_step": 9,
    "started_at": "2025-11-17T05:00:00Z"
  }
}
```

The **conversation ID** (like `3341`) is the key. Each conversation in your workflow has a unique ID, and its output gets stored under that key.

---

## Pattern Implementation

### For Python Script Actors

**Example: summary_saver (Actor 77)**

Your actor has two parts:

1. **The Query Function** (reusable helper):
```python
def get_formatted_summary_from_checkpoint(posting_id: int) -> str:
    """
    Get conversation 3341's output from the most recent checkpoint.
    
    This is the CHECKPOINT QUERY PATTERN in action:
    - Query the posting_state_checkpoints table directly
    - Extract the specific conversation output you need
    - No relying on template substitution magic
    
    Args:
        posting_id: ID of the posting we're processing
    
    Returns:
        The formatted summary from Step 9 (conversation 3341)
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # The magic query: Get conversation 3341's output from checkpoint
        cur.execute("""
            SELECT state_snapshot->'outputs'->'3341' as formatted_summary
            FROM posting_state_checkpoints
            WHERE posting_id = %s
              AND state_snapshot->'outputs' ? '3341'  -- ? checks if key exists
            ORDER BY created_at DESC  -- Get the most recent checkpoint
            LIMIT 1
        """, (posting_id,))
        
        result = cur.fetchone()
        
        if result and result[0]:
            summary = result[0]
            # JSONB sometimes returns quoted strings, clean that up
            if isinstance(summary, str) and summary.startswith('"'):
                summary = json.loads(summary)
            return summary
        else:
            raise ValueError(f"No summary found for posting {posting_id}")
    
    finally:
        return_connection(conn)
```

2. **The Main Logic** (uses the query):
```python
def main():
    # Get posting_id from environment or stdin
    posting_id = int(os.environ['POSTING_ID'])
    
    # CHECKPOINT QUERY: Get the data we need
    formatted_summary = get_formatted_summary_from_checkpoint(posting_id)
    
    # Now do whatever you need with it
    save_summary_to_database(posting_id, formatted_summary)
    
    # Return success marker
    print("[SAVED]")
```

**What the prompt_template field contains:**
```
posting_id: {posting_id}
```

That's it! Just passes the posting_id. No complex template substitution needed.

---

### For LLM Conversation Actors

**Example: If you needed to send checkpoint data to an LLM**

```python
def main():
    posting_id = int(os.environ['POSTING_ID'])
    
    # CHECKPOINT QUERY: Get previous conversation outputs
    prior_analysis = get_from_checkpoint(posting_id, '3340')
    formatted_summary = get_from_checkpoint(posting_id, '3341')
    
    # Build your LLM prompt using normal Python f-strings
    llm_prompt = f"""
    You are reviewing a job posting analysis.
    
    Previous detailed analysis:
    {prior_analysis}
    
    Formatted summary:
    {formatted_summary}
    
    Task: Extract the top 5 key requirements and rank them by importance.
    """
    
    # Send to LLM (using whatever LLM call mechanism your system uses)
    response = call_llm_api(llm_prompt, model="gpt-4")
    
    # Return the response
    print(response)
```

**Key difference from old way:**
- OLD: Put `{conversation_3341_output}` in prompt_template, hope it substitutes
- NEW: Fetch data explicitly, build prompt yourself with f-strings

---

## The Generic Query Helper

**Create this once, use it everywhere:**

```python
def get_conversation_output(posting_id: int, conversation_id: str) -> str:
    """
    Generic checkpoint query helper.
    
    Use this in any actor that needs data from a previous conversation.
    
    Args:
        posting_id: The posting being processed
        conversation_id: The conversation ID whose output you want (e.g., '3341')
    
    Returns:
        The output from that conversation
        
    Raises:
        ValueError: If no checkpoint found with that conversation output
    
    Example:
        summary = get_conversation_output(posting_id, '3341')
        requirements = get_conversation_output(posting_id, '3338')
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT state_snapshot->'outputs'->%s
            FROM posting_state_checkpoints
            WHERE posting_id = %s
              AND state_snapshot->'outputs' ? %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (conversation_id, posting_id, conversation_id))
        
        result = cur.fetchone()
        
        if result and result[0]:
            output = result[0]
            # Handle JSONB string quoting
            if isinstance(output, str) and output.startswith('"'):
                output = json.loads(output)
            return output
        else:
            raise ValueError(
                f"No output found for conversation {conversation_id} "
                f"in checkpoints for posting {posting_id}"
            )
    
    finally:
        return_connection(conn)
```

**Put this helper in:** `core/checkpoint_utils.py` or similar shared location.

**Then in your actors:**
```python
from core.checkpoint_utils import get_conversation_output

# One-liner to get any conversation's output:
summary = get_conversation_output(posting_id, '3341')
requirements = get_conversation_output(posting_id, '3338')
benefits = get_conversation_output(posting_id, '3339')
```

---

## Query Anatomy Explained

Let's break down the query piece by piece:

```sql
SELECT state_snapshot->'outputs'->'3341' as formatted_summary
  ↑                      ↑        ↑
  |                      |        └─ Key within outputs object (conversation ID)
  |                      └─ outputs object within state_snapshot
  └─ The JSONB column that stores all workflow state

FROM posting_state_checkpoints
  └─ The table that stores checkpoints

WHERE posting_id = %s
  └─ Filter to the specific posting we're processing

  AND state_snapshot->'outputs' ? '3341'
           ↑                     ↑
           |                     └─ PostgreSQL JSONB "exists" operator
           └─ Only get checkpoints that actually have this conversation output

ORDER BY created_at DESC
  └─ Most recent checkpoint first (in case there are multiple)

LIMIT 1
  └─ We only need the latest one
```

**The `?` operator:** Checks if a JSONB object contains a key. Prevents errors if the key doesn't exist yet.

**The `->` operator:** Extracts a value from JSONB. `state_snapshot->'outputs'` gets the outputs object, then `->>'3341'` gets the specific conversation output.

---

## Advantages Over Template Substitution

| Feature | Template Substitution | Checkpoint Query |
|---------|----------------------|------------------|
| **Reliability** | ❌ Breaks on wave boundaries | ✅ Always works |
| **Debuggability** | ❌ Hard to see what failed | ✅ Can log/print data |
| **Error Handling** | ❌ Silent failures | ✅ Explicit exceptions |
| **Flexibility** | ❌ Simple replacement only | ✅ Can transform/combine data |
| **Type Safety** | ❌ Always strings | ✅ Can parse JSON, validate |
| **Conditionals** | ❌ Not possible | ✅ If/else based on data |
| **Aggregation** | ❌ One at a time | ✅ Query multiple at once |
| **Testing** | ❌ Need full workflow | ✅ Can test query standalone |

---

## Migration Guide

### Step 1: Identify Actors Using Template Substitution

```sql
-- Find actors that rely on template substitution
SELECT 
    actor_id,
    actor_name,
    actor_type
FROM actors
WHERE script_code LIKE '%{session_%'
   OR script_code LIKE '%{conversation_%'
   OR prompt_template LIKE '%{session_%'
   OR prompt_template LIKE '%{conversation_%';
```

### Step 2: For Each Actor, Refactor

**Before:**
```python
# Actor relies on prompt_template with {conversation_3341_output}
# Wave processor substitutes it... or tries to
```

**After:**
```python
from core.checkpoint_utils import get_conversation_output

def main():
    posting_id = int(os.environ['POSTING_ID'])
    
    # Explicitly get what you need
    summary = get_conversation_output(posting_id, '3341')
    
    # Use it
    process(summary)
```

### Step 3: Update prompt_template Field

**Before:**
```
Here is the formatted summary:

{conversation_3341_output}

Please review it and...
```

**After:**
```
posting_id: {posting_id}
```

The prompt building now happens in the script code, not the template.

### Step 4: Test

```bash
# Run workflow on a single posting
python3 -m core.wave_batch_processor --workflow 3001 --posting-ids 4650

# Check the checkpoint
psql ... -c "
SELECT state_snapshot->'outputs'->'3341' 
FROM posting_state_checkpoints 
WHERE posting_id = 4650 
ORDER BY created_at DESC LIMIT 1;
"

# Verify the actor got the right data
# (Check logs or output)
```

---

## Common Patterns

### Pattern 1: Get Single Conversation Output
```python
summary = get_conversation_output(posting_id, '3341')
```

### Pattern 2: Get Multiple Outputs
```python
title = get_conversation_output(posting_id, '3335')
company = get_conversation_output(posting_id, '3336')
location = get_conversation_output(posting_id, '3337')
```

### Pattern 3: Conditional Data Access
```python
try:
    detailed_analysis = get_conversation_output(posting_id, '3340')
except ValueError:
    # Fallback if conversation 3340 hasn't run yet
    detailed_analysis = "No detailed analysis available"
```

### Pattern 4: Combine Multiple Outputs
```python
def build_comprehensive_report(posting_id):
    # Get all the pieces
    requirements = get_conversation_output(posting_id, '3338')
    benefits = get_conversation_output(posting_id, '3339')
    summary = get_conversation_output(posting_id, '3341')
    
    # Combine them however you want
    report = f"""
    # Job Summary
    {summary}
    
    # Requirements
    {requirements}
    
    # Benefits
    {benefits}
    """
    return report
```

### Pattern 5: Transform Before Using
```python
import json

# Get raw output
raw_data = get_conversation_output(posting_id, '3340')

# Parse if it's JSON
structured_data = json.loads(raw_data)

# Use structured data
for requirement in structured_data['requirements']:
    process(requirement)
```

---

## Troubleshooting

### Problem: "No output found for conversation X"

**Cause:** The conversation hasn't run yet, or failed.

**Solution:**
```python
# Check if the conversation output exists before using it
cur.execute("""
    SELECT state_snapshot->'outputs' ? %s as has_output
    FROM posting_state_checkpoints
    WHERE posting_id = %s
    ORDER BY created_at DESC LIMIT 1
""", (conversation_id, posting_id))

if cur.fetchone()[0]:
    output = get_conversation_output(posting_id, conversation_id)
else:
    # Handle missing data gracefully
    output = "[Data not yet available]"
```

### Problem: Getting quoted strings like `"\"actual text\""`

**Cause:** JSONB stores strings with quotes, and PostgreSQL sometimes double-wraps them.

**Solution:**
```python
if isinstance(output, str) and output.startswith('"'):
    output = json.loads(output)  # Remove outer quotes
```

### Problem: Query returns None

**Cause:** Checkpoint doesn't exist yet for this posting.

**Solution:**
```python
result = cur.fetchone()
if not result or not result[0]:
    raise ValueError(f"No checkpoint found for posting {posting_id}")
```

---

## Best Practices

1. **Create the helper function once, use everywhere**
   - Don't copy-paste the query into every actor
   - Use `core/checkpoint_utils.py` or similar

2. **Always ORDER BY created_at DESC LIMIT 1**
   - Gets the most recent checkpoint
   - Handles edge cases where multiple checkpoints exist

3. **Use the `?` operator to check key existence**
   - `state_snapshot->'outputs' ? '3341'`
   - Prevents errors if conversation hasn't run yet

4. **Handle JSONB string quoting**
   - Check if result starts with `"` and `json.loads()` it
   - JSONB can be weird about string encoding

5. **Fail loudly on missing data**
   - Better to raise an exception than silently use empty strings
   - Makes debugging much easier

6. **Log what you're fetching**
   ```python
   logger.info(f"Fetching conversation {conversation_id} output for posting {posting_id}")
   output = get_conversation_output(posting_id, conversation_id)
   logger.debug(f"Retrieved {len(output)} characters")
   ```

---

## Summary

**The checkpoint query pattern is:**
- ✅ More reliable (no wave boundary bugs)
- ✅ More flexible (can transform/combine data)
- ✅ More debuggable (explicit queries, clear errors)
- ✅ More testable (can test queries independently)
- ✅ More maintainable (one helper function, use everywhere)

**The cost is:**
- Slightly more code (but reusable helper makes this minimal)
- Need to know which conversation IDs to query (but you needed to know for templates too)

**The win is:**
- Your workflows actually work reliably
- No more mysterious `{conversation_X_output}` appearing in prompts
- Complete control over data flow

---

**Recommendation:** Use checkpoint queries for all new actors. Migrate existing actors as time permits or when they break.

**Questions?** See `docs/TEMPLATE_SUBSTITUTION_BUG.md` for the full history of why template substitution is unreliable.

---

**Last Updated:** 2025-11-17 06:00 UTC  
**Author:** Arden & xai  
**Status:** Production pattern, actively used in Workflow 3001
