# Session Chaining Implementation Options

**Date:** 2025-10-22  
**Context:** Runner v3.1 doesn't support `{session_N_output}` substitution  
**Current Workaround:** Manual output embedding during recipe creation  

---

## Problem Statement

Multi-session recipes need to pass outputs between sessions:
- Session A: gemma3:1b extracts job description
- Session B: gemma2:latest validates Session A's extraction
- **Issue:** Session B needs Session A's `response_received` to grade it

**Current State:**
- `depends_on_session_id` ensures execution order ✅
- Output substitution not implemented ❌
- Placeholder `{session_1_output}` remains unreplaced in prompts

---

## Option 1: Temp Files

### Implementation
```python
# In runner, after Session A completes:
session_output_file = f"/tmp/llmcore_session_{session_run_id}.txt"
with open(session_output_file, 'w') as f:
    f.write(session_a_response)

# Before Session B starts, replace placeholders:
prompt = prompt_template.replace('{session_1_output}', 
                                  open(session_output_file).read())
```

### Schema Changes
**NONE** - No database modifications needed

### Pros
✅ Simple implementation  
✅ No schema migration  
✅ Handles large outputs (no TEXT field limits)  
✅ Easy debugging (files visible in /tmp)  
✅ Fast implementation (< 1 hour)  

### Cons
❌ File management overhead (cleanup, naming)  
❌ Not database-native (breaks audit trail)  
❌ Race conditions in parallel runs  
❌ Platform-dependent (/tmp on Linux/Mac, %TEMP% on Windows)  
❌ Outputs lost if files deleted before Session B runs  
❌ No historical tracking of intermediate outputs  

### Production Readiness
⚠️ **Good for prototyping, risky for production**
- Works well for single-server deployments
- Problems with distributed systems or container restarts
- Manual cleanup needed (cron job to delete old files)

---

## Option 2A: Add `session_output` to `session_runs` Table

### Implementation
```sql
-- Add column to session_runs
ALTER TABLE session_runs ADD COLUMN session_output TEXT;

-- After Session A completes, store its output:
UPDATE session_runs 
SET session_output = (
    SELECT response_received 
    FROM instruction_runs 
    WHERE session_run_id = ? 
    ORDER BY step_number DESC LIMIT 1
)
WHERE session_run_id = ?;

-- Before Session B starts, query Session A's output:
SELECT session_output 
FROM session_runs 
WHERE recipe_run_id = ? AND session_number = 1;
```

### Runner Changes
```python
# After completing session
if session_run.status == 'SUCCESS':
    # Get final instruction response
    cursor.execute("""
        SELECT response_received 
        FROM instruction_runs 
        WHERE session_run_id = ? 
        ORDER BY step_number DESC LIMIT 1
    """, (session_run_id,))
    final_output = cursor.fetchone()[0]
    
    # Store in session_runs
    cursor.execute("""
        UPDATE session_runs 
        SET session_output = ? 
        WHERE session_run_id = ?
    """, (final_output, session_run_id))

# Before starting dependent session
def render_prompt_with_session_outputs(prompt_template, recipe_run_id):
    # Find all {session_N_output} placeholders
    import re
    placeholders = re.findall(r'{session_(\d+)_output}', prompt_template)
    
    for session_num in placeholders:
        cursor.execute("""
            SELECT session_output 
            FROM session_runs 
            WHERE recipe_run_id = ? AND session_number = ?
        """, (recipe_run_id, int(session_num)))
        
        output = cursor.fetchone()
        if output and output[0]:
            prompt_template = prompt_template.replace(
                f'{{session_{session_num}_output}}', 
                output[0]
            )
    
    return prompt_template
```

### Schema Changes
```sql
ALTER TABLE session_runs ADD COLUMN session_output TEXT;
```

### Pros
✅ Database-native (complete audit trail)  
✅ No file management needed  
✅ Historical tracking (outputs preserved forever)  
✅ Works in distributed systems  
✅ Survives container restarts  
✅ Clean SQL queries for debugging  
✅ Aligns with existing architecture  

### Cons
❌ Schema migration required  
❌ TEXT field size limits (SQLite: 1GB, but practical limit ~100MB)  
❌ Increased database size for large outputs  
❌ Slightly slower than temp files (disk I/O)  

### Production Readiness
✅ **Production-ready**
- Scales well
- Safe for distributed deployments
- Complete audit trail
- Easy to query and debug

---

## Option 2B: Add `context_storage` JSON to `recipe_runs` Table

### Implementation
```sql
-- Add column to recipe_runs for shared context
ALTER TABLE recipe_runs ADD COLUMN context_storage TEXT; -- JSON blob

-- Store session outputs as JSON
UPDATE recipe_runs 
SET context_storage = json_set(
    COALESCE(context_storage, '{}'),
    '$.session_1_output', 
    (SELECT response_received FROM instruction_runs WHERE session_run_id = ?)
)
WHERE recipe_run_id = ?;

-- Retrieve for Session B
SELECT json_extract(context_storage, '$.session_1_output')
FROM recipe_runs
WHERE recipe_run_id = ?;
```

### Runner Changes
```python
def store_session_output(recipe_run_id, session_number, output):
    cursor.execute("""
        UPDATE recipe_runs 
        SET context_storage = json_set(
            COALESCE(context_storage, '{}'),
            ?, ?
        )
        WHERE recipe_run_id = ?
    """, (f'$.session_{session_number}_output', output, recipe_run_id))

def get_session_output(recipe_run_id, session_number):
    cursor.execute("""
        SELECT json_extract(context_storage, ?)
        FROM recipe_runs
        WHERE recipe_run_id = ?
    """, (f'$.session_{session_number}_output', recipe_run_id))
    return cursor.fetchone()[0]
```

### Schema Changes
```sql
ALTER TABLE recipe_runs ADD COLUMN context_storage TEXT; -- JSON
```

### Pros
✅ Centralized storage (all session outputs in one place)  
✅ Flexible (can store arbitrary data: outputs, metrics, metadata)  
✅ Recipe-scoped (easy to pass data between any sessions)  
✅ JSON queryable (can extract specific fields)  
✅ No new tables needed  

### Cons
❌ JSON parsing overhead  
❌ Less intuitive than dedicated columns  
❌ Harder to query in SQL (JSON functions needed)  
❌ Same TEXT size limits as Option 2A  

### Production Readiness
✅ **Production-ready with flexibility**
- Best for complex workflows with multiple data passing needs
- Overkill for simple session chaining
- Useful if you need to pass metadata, scores, etc.

---

## Option 3: Hybrid - Per-Instruction Output Storage

### Implementation
Already exists! `instruction_runs.response_received` stores every response.

**Enhancement:** Add inter-instruction chaining within same session

```sql
-- instruction_runs already has response_received
-- Add support for {step_N_output} placeholders within same session

-- Before executing step 2 in same session:
SELECT response_received 
FROM instruction_runs 
WHERE session_run_id = ? AND step_number = 1;
```

### Runner Changes
```python
def render_prompt_with_step_outputs(prompt_template, session_run_id, current_step):
    """Allow {step_1_output}, {step_2_output} within same session"""
    import re
    placeholders = re.findall(r'{step_(\d+)_output}', prompt_template)
    
    for step_num in placeholders:
        if int(step_num) >= current_step:
            raise ValueError(f"Cannot reference future step {step_num}")
        
        cursor.execute("""
            SELECT response_received 
            FROM instruction_runs 
            WHERE session_run_id = ? AND step_number = ?
        """, (session_run_id, int(step_num)))
        
        output = cursor.fetchone()
        if output and output[0]:
            prompt_template = prompt_template.replace(
                f'{{step_{step_num}_output}}', 
                output[0]
            )
    
    return prompt_template
```

### Schema Changes
**NONE** - Uses existing `instruction_runs.response_received`

### Pros
✅ No schema changes  
✅ Already stores all outputs  
✅ Enables multi-step workflows within sessions  
✅ Complements session-level chaining  

### Cons
❌ Only works within same session  
❌ Doesn't solve cross-session chaining  
❌ Requires different placeholder naming (`{step_N_output}` vs `{session_N_output}`)  

### Production Readiness
✅ **Production-ready as complementary feature**
- Useful for complex multi-step sessions
- Doesn't solve the main problem (cross-session chaining)
- Should implement alongside Option 2A or 2B

---

## Recommendation Matrix

| Criteria | Temp Files | session_runs.session_output | recipe_runs.context_storage | Hybrid |
|----------|------------|------------------------------|------------------------------|--------|
| **Implementation Time** | 1 hour | 4 hours | 6 hours | 2 hours |
| **Schema Migration** | None | Simple ALTER | Simple ALTER | None |
| **Production Ready** | ⚠️ Prototype | ✅ Yes | ✅ Yes | ✅ Complementary |
| **Audit Trail** | ❌ Lost | ✅ Complete | ✅ Complete | ✅ Complete |
| **Distributed Systems** | ❌ Problematic | ✅ Works | ✅ Works | ✅ Works |
| **Query Complexity** | N/A | Simple SQL | JSON functions | Simple SQL |
| **Storage Efficiency** | Good | Good | Fair (JSON overhead) | Excellent |
| **Flexibility** | Low | Medium | High | Medium |

---

## Recommended Solution: Option 2A + Option 3

### Why This Combination?

**Option 2A: `session_runs.session_output`**
- Solves cross-session chaining (Session A → Session B)
- Database-native, production-ready
- Simple to implement and query
- Complete audit trail

**Option 3: Per-instruction chaining**
- Enables multi-step workflows within sessions
- Uses existing data (no schema changes)
- Complements cross-session chaining

### Implementation Plan

#### Phase 1: Add `session_output` Column (1 hour)
```sql
-- Migration script
ALTER TABLE session_runs ADD COLUMN session_output TEXT;
CREATE INDEX idx_session_runs_output ON session_runs(session_run_id, session_output);
```

#### Phase 2: Update Runner to Store Session Outputs (2 hours)
```python
# After session completes successfully
final_output = get_final_instruction_output(session_run_id)
store_session_output(session_run_id, final_output)
```

#### Phase 3: Implement Placeholder Substitution (1 hour)
```python
# Before rendering prompt for dependent session
prompt = render_with_session_outputs(prompt_template, recipe_run_id)
prompt = render_with_step_outputs(prompt, session_run_id, current_step)
```

#### Phase 4: Test with Recipe 1110 (30 min)
```bash
# Re-run our 5-job pipeline
python3 recipe_run_test_runner_v32.py --max-runs 5

# Verify Session B receives Session A outputs
sqlite3 llmcore.db "SELECT session_output FROM session_runs WHERE recipe_run_id = 1243"
```

### Total Implementation: 4.5 hours

---

## Usage Example After Implementation

```python
# Session A instruction (unchanged)
extraction_prompt = """
Create concise summary: {variations_param_1}
===OUTPUT TEMPLATE===...
"""

# Session B instruction (now works!)
grading_prompt = """
## Raw posting:
{variations_param_1}

## Summary from Session 1:
{session_1_output}  # ← This will be replaced with actual Session A output!

Grade: [PASS] or [FAIL]
"""

# Multi-step session (bonus!)
analysis_prompt = """
Step 1 extracted: {step_1_output}
Step 2 validated: {step_2_output}
Now synthesize both into final recommendation...
"""
```

---

## Migration Risk Assessment

### Low Risk ✅
- Adding nullable TEXT column (backward compatible)
- Existing recipes continue to work
- Only new recipes use session chaining

### Testing Required
- [ ] Verify session_output stored correctly
- [ ] Test {session_N_output} substitution
- [ ] Test with Recipe 1110 (5 jobs, 2 sessions)
- [ ] Verify backward compatibility (old recipes still run)
- [ ] Performance test (large outputs ~1MB)

### Rollback Plan
If issues arise:
```sql
-- Remove column (data loss acceptable since it's new feature)
ALTER TABLE session_runs DROP COLUMN session_output;
```

---

## Conclusion

**Recommended:** Implement **Option 2A (`session_runs.session_output`) + Option 3 (per-instruction chaining)**

**Rationale:**
1. Production-ready architecture
2. Database-native (complete audit trail)
3. Simple implementation (4.5 hours)
4. Enables both cross-session AND multi-step workflows
5. Low migration risk
6. Backward compatible

**Quick Win:** Start with Option 2A only (4 hours) to unblock Recipe 1110 testing

**Future Enhancement:** Add Option 2B (`recipe_runs.context_storage`) if you need to pass complex metadata between sessions (scores, metrics, config)