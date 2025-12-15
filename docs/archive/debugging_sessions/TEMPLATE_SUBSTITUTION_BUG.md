	# Template Substitution Bug - Workflow 3001

**Status:** ✅ PERMANENTLY FIXED (2025-12-07) - Dynamic extraction replaces hardcoded mappings  
**Severity:** High - Affected any workflow step using `{session_X_output}` or `{conversation_X_output}` template variables  
**Discovered:** 2025-11-15  
**Workaround Deployed:** 2025-11-15 20:25:00  
**First "Fix":** 2025-11-18 20:50:00 - Direct checkpoint query (WF3001 only, NOT general fix)  
**Recurrence:** 2025-12-07 - Same bug hit WF3005 with `{orphan_skills}` variable  
**Actual Fix:** 2025-12-07 - Dynamic extraction in `interaction_creator.py` and `executors.py`

---

## ✅ 2025-12-07: PERMANENTLY FIXED

**Root cause:** Hardcoded conversation ID mappings in `build_prompt_from_template()`

**Fix applied to:**
- `core/wave_runner/interaction_creator.py` - Removed 27 hardcoded mappings, added dynamic extraction
- `core/wave_runner/executors.py` - Removed 26 hardcoded mappings, added dynamic extraction

**How it works now:**
```python
# 4b. DYNAMIC parent output extraction (replaces hardcoded mappings)
for conv_id, parent_output in parents.items():
    if isinstance(parent_output, dict):
        # Generate conversation_XXXX_output pattern automatically
        variables[f'conversation_{conv_id}_output'] = parent_output.get('response', '')
        
        # Extract all other keys from script outputs
        for key, value in parent_output.items():
            if key not in ('response', 'model', 'latency_ms'):
                variables[key] = str(value)

# 4c. Generate session_X_output patterns based on parent order
for idx, (conv_id, parent_output) in enumerate(parents.items(), start=1):
    variables[f'session_{idx}_output'] = parent_output.get('response', '')
```

**What this means:**
- ANY new workflow with `{conversation_XXXX_output}` will work automatically
- ANY script output key becomes a template variable automatically
- No more editing Python code when creating new workflows

---

## Historical Context (Kept for Reference)

## Executive Summary

Workflow 3001's template substitution mechanism fails when workflows span multiple "waves" (processing batches). The `posting.outputs` dictionary, which should contain all prior conversation outputs for template variable substitution, becomes incomplete when checkpoints are reloaded between waves. This causes literal template placeholders like `{session_9_output}` to appear in final outputs instead of the actual conversation content.

**Impact:** 122 job posting summaries contained hallucinations due to this bug (cleared and regenerated as of 2025-11-17).

**Current Status:** Workaround implemented in `summary_saver` script (Actor 77) bypasses template substitution entirely by querying `posting_state_checkpoints` directly. The underlying bug in `wave_batch_processor.py` remains unfixed.

---

## Technical Details

### The Bug

**Location:** `core/wave_batch_processor.py`  
**Component:** Template variable substitution in prompt rendering  
**Symptom:** `posting.outputs` dict incomplete at Step 10 (execution_order 10)

**Expected behavior:**
```python
posting.outputs = {
    '3335': '<conversation 3335 output>',
    '3336': '<conversation 3336 output>',
    '3337': '<conversation 3337 output>',
    '3338': '<conversation 3338 output>',
    '3339': '<conversation 3339 output>',
    '3340': '<conversation 3340 output>',
    '3341': '<conversation 3341 output>',  # ← This is what we need
    '9184': '<conversation 9184 output>'
}
```

**Actual behavior (observed via debugging):**
```python
posting.outputs = {
    '9184': '<conversation 9184 output>'  # Only the most recent conversation!
}
```

**Result:** Template `{session_9_output}` or `{conversation_3341_output}` doesn't substitute because key '3341' is missing from the dict.

### Root Cause Analysis

**Wave-based processing creates the problem:**

1. **Wave 1** (execution_order 1-8): Conversations 3335-3340 complete
   - Outputs saved to `posting_state_checkpoints.state_snapshot->'outputs'`
   - `posting.outputs` dict has all 6 entries in memory

2. **3+ minute gap** between waves (observed via checkpoint timestamps)

3. **Wave 2** (execution_order 9-10): Workflow resumes
   - Checkpoint reloaded from database
   - `posting.outputs` dict **not fully restored**
   - Only contains conversation 9184 (most recent)
   - Missing: 3335, 3336, 3337, 3338, 3339, 3340, 3341

4. **Step 10 (Save Summary)** executes:
   - Prompt template contains `{session_9_output}`
   - Template substitution looks for key in `posting.outputs`
   - Key not found → literal `{session_9_output}` remains in prompt
   - LLM receives broken prompt → generates hallucination

**Evidence:**
```sql
-- Checkpoint timestamps show 3-minute gaps between steps
SELECT posting_id, step_name, created_at 
FROM posting_state_checkpoints 
WHERE posting_id = 4650 
ORDER BY created_at;

-- Result: 3-4 minute gaps between execution_order 8 and 9
```

**Why it happens:**
The checkpoint reload logic in `wave_batch_processor.py` doesn't properly reconstruct the `posting.outputs` dictionary from the JSONB `state_snapshot->'outputs'` field. This is likely a deserialization issue or an incomplete restore operation.

### Affected Workflows

**Currently Known:**
- Workflow 3001 (job posting enrichment) - Step 10 (execution_order 10)

**Potentially Affected:**
- Any workflow using wave-based processing (batch size < total postings)
- Any workflow step referencing `{session_X_output}` or `{conversation_X_output}` in prompts
- Multi-wave workflows where later steps depend on earlier conversation outputs

---

## Workaround Implementation

### Solution

Modified the `summary_saver` script (Actor 77) to bypass template substitution entirely by querying the checkpoint directly.

**File:** `actors` table, script_code for actor_id = 77  
**Modified:** 2025-11-15 20:25:00  
**Status:** Deployed and working ✓  

### Code Changes

**Before (broken):**
```python
# Relied on template substitution in prompt
# Prompt template contained: {session_9_output}
# This would fail when posting.outputs was incomplete
```

**After (working):**
```python
def get_formatted_summary_from_checkpoint(posting_id: int) -> str:
    """
    Query checkpoint directly for conversation 3341's output.
    Bypasses broken template substitution mechanism.
    
    Returns the formatted summary from Step 9 (Format Standardization).
    """
    cur.execute("""
        SELECT state_snapshot->'outputs'->'3341' as formatted_summary
        FROM posting_state_checkpoints
        WHERE posting_id = %s
          AND state_snapshot->'outputs' ? '3341'
        ORDER BY created_at DESC
        LIMIT 1
    """, (posting_id,))
    
    result = cur.fetchone()
    if not result or not result[0]:
        raise ValueError(f"No formatted summary found in checkpoint for posting {posting_id}")
    
    return result[0]

# Main execution
posting_id = int(os.environ['POSTING_ID'])
formatted_summary = get_formatted_summary_from_checkpoint(posting_id)

# Save to database
cur.execute("""
    UPDATE postings 
    SET extracted_summary = %s,
        updated_at = NOW()
    WHERE posting_id = %s
""", (formatted_summary, posting_id))
```

**Key insight:** The checkpoint JSONB `state_snapshot->'outputs'->'3341'` contains the correct data. The problem is only in the `posting.outputs` dict reconstruction during wave reload.

### Validation

**Testing:**
```sql
-- Verify checkpoint contains the data
SELECT 
    posting_id,
    state_snapshot->'outputs'->'3341' as conv_3341_output,
    LENGTH(state_snapshot->'outputs'->'3341'::text) as output_length
FROM posting_state_checkpoints
WHERE posting_id = 4650
  AND state_snapshot->'outputs' ? '3341'
ORDER BY created_at DESC
LIMIT 1;

-- Result: ✓ Data exists in checkpoint, 2800+ chars of properly formatted summary
```

**Post-deployment results:**
- All new summaries (after 2025-11-15 20:25:00) are clean ✓
- No template placeholders appearing in summaries ✓
- Workflow 3001 running successfully ✓

---

## Limitations of Workaround

### What's Fixed
✓ Workflow 3001 Step 10 now works correctly  
✓ Job posting summaries are being generated properly  
✓ No more `{session_9_output}` placeholders in output  

### What's NOT Fixed
❌ The underlying bug in `wave_batch_processor.py` remains  
❌ Other workflows using template substitution will fail the same way  
❌ Any future workflow step using `{session_X_output}` syntax will break  
❌ No general solution - each affected step needs individual workaround  

### Technical Debt Created

1. **Hardcoded conversation ID:** The workaround queries for `'3341'` specifically. If Workflow 3001 structure changes (conversation IDs renumbered), the workaround breaks.

2. **No template flexibility:** Original design allowed dynamic template variables. Workaround removes this flexibility - must query specific keys.

3. **Copy-paste required:** Every affected workflow step needs a similar workaround written individually.

4. **Hidden failure mode:** Developers creating new workflows won't know template substitution is broken until they hit the bug.

---

## Proposed Solutions

### Option 1: Fix the Root Cause (Recommended)

**Objective:** Fix checkpoint reload logic in `wave_batch_processor.py` to properly restore `posting.outputs` dict.

**Location:** `core/wave_batch_processor.py`  
**Component:** Checkpoint deserialization/restore function  

**Investigation needed:**
```python
# Find where checkpoint is loaded
# Likely something like:
checkpoint = get_latest_checkpoint(posting_id, workflow_run_id)
posting.state = checkpoint.state_snapshot

# Problem: posting.outputs is not being populated from checkpoint.state_snapshot['outputs']
# Solution: Explicitly restore the outputs dict
posting.outputs = checkpoint.state_snapshot.get('outputs', {})

# BUT: Verify all keys are strings (JSONB stores everything as strings)
# May need type conversion if code expects integer keys
```

**Steps:**
1. Add debug logging to checkpoint reload to see what's actually in `posting.outputs` after restore
2. Compare with what's in `state_snapshot->'outputs'` in database
3. Identify the deserialization gap
4. Fix the restore logic to properly populate `posting.outputs`
5. Test with multi-wave workflow to verify outputs persist across waves

**Estimated effort:** 2-4 hours (investigation + fix + testing)

**Risk:** Medium - Changes core workflow processing, needs thorough testing

---

### Option 2: Deprecate Template Substitution

**Objective:** Document that template substitution is broken and shouldn't be used.

**Actions:**
1. Add warning to workflow documentation: "Do not use `{session_X_output}` or `{conversation_X_output}` template variables - query checkpoints directly instead"
2. Update workflow creation guide with checkpoint query pattern
3. Create utility function for checkpoint queries:
   ```python
   def get_conversation_output(posting_id: int, conversation_id: str) -> str:
       """Standard pattern for retrieving prior conversation outputs"""
       # ... checkpoint query implementation
   ```
4. Refactor existing workflows to use checkpoint queries instead of templates

**Estimated effort:** 1-2 days (documentation + refactoring)

**Risk:** Low - Makes current state official rather than changing behavior

**Downside:** Loses the elegance of template-based prompts

---

### Option 3: Hybrid Approach

**Objective:** Fix template substitution for simple cases, use checkpoint queries for complex cases.

**Strategy:**
1. Fix the root cause for single-conversation references: `{conversation_3341_output}`
2. Keep checkpoint query pattern for complex aggregations or transformations
3. Document when to use each approach

**Estimated effort:** 3-5 hours

**Risk:** Medium - Creates two "right ways" to do things (confusing for developers)

---

## Recommendations

### Immediate (Next Session)

1. **Fix the QA script false positive:**
   - Change `LIKE '%session_%output%'` to `~ 'session[_][0-9]+[_]output'`
   - Prevents catching "Session Manager" job titles

2. **Verify the 122 regenerated summaries:**
   - Run QA script after workflow completes
   - Ensure all are clean (no hallucinations)

3. **Monitor for new patterns:**
   - Word frequency outliers
   - Meta-commentary variations
   - Any new hallucination types

### Short-term (This Week)

4. **Decide on root cause fix vs deprecation:**
   - If template substitution is used elsewhere → fix it
   - If Workflow 3001 is the only user → document deprecation

5. **Add automated QA gate:**
   - Integrate `sql/qa_check_hallucinations.sql` as final workflow step
   - Workflow should fail loudly if hallucinations detected
   - Create monitoring alert

### Long-term (This Month)

6. **Audit other workflows:**
   - Search for `{session_` or `{conversation_` in all actor scripts
   - Identify other affected workflows
   - Apply workarounds or fixes as needed

7. **Add regression testing:**
   - Create test workflow that spans multiple waves
   - Verify template substitution works across wave boundaries
   - Run in CI/CD before deploying workflow changes

---

## Related Documentation

- **Hallucination Detection Cookbook:** `/home/xai/Documents/ty_learn/docs/HALLUCINATION_DETECTION_COOKBOOK.md`
- **QA Check Script:** `/home/xai/Documents/ty_learn/sql/qa_check_hallucinations.sql`
- **Workflow 3001 Status:** `/home/xai/Documents/ty_learn/CURRENT_STATUS_WORKFLOW_3001.md`
- **Pattern Evolution Log:** See HALLUCINATION_DETECTION_COOKBOOK.md Section 5

---

## Questions for Discussion

1. **Priority:** Should we fix the root cause or officially deprecate template substitution?

2. **Scope:** Are there other workflows using template variables? (Need to audit actors table)

3. **Testing:** What's the best way to test multi-wave checkpoint restore behavior?

4. **Architecture:** Is template substitution the right pattern, or should we always query checkpoints directly for reliability?

5. **Migration:** If we fix the root cause, do we migrate the workaround back to using templates, or leave it as-is?

---

## Appendix: Debug Queries

### Check if posting.outputs is incomplete
```sql
-- Compare what's in checkpoint vs what template substitution sees
SELECT 
    posting_id,
    jsonb_object_keys(state_snapshot->'outputs') as output_keys,
    created_at
FROM posting_state_checkpoints
WHERE posting_id = 4650
ORDER BY created_at DESC
LIMIT 5;
```

### Find all template variables in use
```sql
-- Search actor scripts for template variable usage
SELECT 
    actor_id,
    actor_name,
    script_code
FROM actors
WHERE script_code LIKE '%{session_%'
   OR script_code LIKE '%{conversation_%';
```

### Verify checkpoint data integrity
```sql
-- Ensure conversation outputs are actually saved to checkpoints
SELECT 
    posting_id,
    state_snapshot->'outputs' ? '3341' as has_conv_3341,
    state_snapshot->'outputs' ? '3335' as has_conv_3335,
    LENGTH(state_snapshot->'outputs'->'3341'::text) as conv_3341_length,
    created_at
FROM posting_state_checkpoints
WHERE posting_id = 4650
  AND workflow_run_id IN (SELECT workflow_run_id FROM workflow_runs WHERE workflow_id = 3001)
ORDER BY created_at DESC;
```

---

**Last Updated:** 2025-11-17 05:44 UTC  
**Author:** Arden (debugging session with xai)  
**Next Review:** After workflow 3001 completes regenerating 122 summaries
