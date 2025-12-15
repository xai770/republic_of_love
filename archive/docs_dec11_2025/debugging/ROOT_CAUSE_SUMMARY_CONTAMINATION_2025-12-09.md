# Root Cause Analysis: Summary Contamination Bug

**Date:** 2025-12-09  
**Severity:** CRITICAL  
**Impact:** 99% of postings (1,722/1,740) have wrong `extracted_summary`

## Executive Summary

A design flaw in the workflow state management caused 99% of job posting summaries to be contaminated with wrong data. When batch workflows process multiple postings under a single `workflow_run_id`, they share a single `state` JSON blob. Templates using variables like `{current_summary}` read from this shared state, causing cross-posting contamination.

## Root Cause

### The Bug Location

**File:** `core/wave_runner/interaction_creator.py`  
**Lines:** 205-211

```python
# Workflow state (semantic keys) - PREFERRED for new templates
'extract_summary': workflow_state.get('extract_summary', ''),
'improved_summary': workflow_state.get('improved_summary', ''),
'current_summary': workflow_state.get('current_summary', ''),
```

The `workflow_state` is fetched from `workflow_runs.state` (a single JSON column per workflow run).

### Why It Failed

1. **Batch runs share workflow_run_id**: When 40 postings are processed in one batch, they all have `workflow_run_id = 5698`

2. **Shared state blob**: The `workflow_runs.state` column is a single JSON object:
   ```json
   {
     "current_summary": "Network Deployment Engineer...",
     "extract_summary": "Network Deployment Engineer...",
     "improved_summary": "Network Deployment Engineer..."
   }
   ```

3. **Cross-contamination**: 
   - Posting A processes → saves its summary to state
   - Posting B reads state → gets Posting A's summary!

4. **Template dependency**: The Dec 2 template used `{current_summary}` or `{improved_summary}` which resolved from this shared state

## Evidence

### Contaminated Workflow Run

```sql
SELECT workflow_run_id, (state->>'current_summary')::text FROM workflow_runs WHERE workflow_run_id = 5698;
-- Result: "Network Deployment Engineer" content for ALL 40 postings
```

### Timing Pattern

| Posting | Job Title | workflow_run_id | Status |
|---------|-----------|-----------------|--------|
| 10475 | Tax QA, Associate | 5698 | ❌ WRONG |
| 10495 | Network Deployment Engineer | 5698 | ❌ Source of contamination |
| 10462 | Market Specialist | 5739 | ✅ Separate run = correct |

### Correct Ancestry

The ancestry chain for posting 10475 is CORRECT:
- gemma3_extract (conv 3335): "Tax QA, Associate" ✅
- qwen25_grade (conv 3337): "[PASS]" ✅

The AI extraction worked perfectly. The contamination happened during template substitution when reading from shared workflow state.

## Fix Applied

**Date:** 2025-12-08  
**Change:** Updated `format_standardization` template from workflow state variables to explicit conversation output:

**Before:**
```
INPUT (use the best available summary - improved version if available, otherwise original):
{current_summary}
```

**After:**
```
INPUT (use the best available summary from extraction):
{conversation_3335_output}
```

This uses the **ancestry-based variable** `{conversation_3335_output}` which is resolved by querying the specific posting's interaction history, NOT from shared workflow state.

## Long-term Recommendations

1. **Remove workflow state usage from per-posting templates**
   - Workflow state should only be used for global workflow metadata (job counts, progress, etc.)
   - Per-posting data should always use `{conversation_XXXX_output}` patterns

2. **Add validation in prompt builder**
   - Log warning when templates use workflow state variables in posting-based workflows
   - Consider failing fast if batch run tries to use posting-specific state variables

3. **Consider posting-keyed state**
   - If workflow state per posting is needed, use: `state.postings[posting_id].current_summary`
   - Or create a separate `workflow_posting_state` table

## Remediation Required

1. **Regenerate summaries for contaminated postings**
   - ~1,700 postings need their `extracted_summary` regenerated
   - Re-run format_standardization with the fixed template
   - Use the correct `{conversation_3335_output}` variable

2. **Verify Dec 3+ postings**
   - Some may have been processed with separate workflow runs (correct)
   - Some may still be contaminated if processed in batch runs

## Lessons Learned

1. **Batch processing requires isolation**: Shared state between items is a major contamination risk
2. **Template variables should be explicit**: `{conversation_3335_output}` is safer than `{current_summary}`
3. **Testing should include batch scenarios**: Unit tests with single postings don't catch this
4. **Audit trail matters**: The stored `interactions.input` showed exactly what was substituted, enabling diagnosis
