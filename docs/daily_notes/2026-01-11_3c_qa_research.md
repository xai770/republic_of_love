# 2026-01-11: 3C QA Research

## Summary

Investigated LLM consistency as a QA signal. Key finding: **consistency detects uncertainty, not correctness**.

## Experiments

### 1. Reverse Spelling Test

Found the "edge" where models start failing:

| Length | Behavior | 3C Useful? |
|--------|----------|------------|
| 2-3 chars | Always correct | No |
| 4-5 chars | Edge — sometimes right | **YES** |
| 6+ chars | Inconsistently wrong | Flag only |

### 2. Same Session vs Separate Sessions

| Approach | Result |
|----------|--------|
| Same session (context) | Locks in — consistent but may repeat errors |
| Separate sessions | Truly independent — better for detecting uncertainty |

**Conclusion:** Use SEPARATE sessions for 3C validation.

### 3. Lily CPS Extraction (20 postings × 3 attempts)

| Confidence | Count | Percent |
|------------|-------|---------|
| High (3/3) | 9 | 45% |
| Medium (2/3) | 11 | 55% |
| Low (1/3) | 0 | 0% |

### 4. Variation Analysis

The variations are NOT naming inconsistencies — they're **extraction threshold** differences:

```
Business Banking Manager:
  ✓ Always: client relationship management, communication, credit assessment, loan assessment
  ? Sometimes: product development, regulatory compliance

Fund Transfer Pricing:
  ✓ Always: communication, fixed income analysis, independent work, pnl reporting, risk calculation
  ? Sometimes: macro economic analysis, python
```

**Pattern:** Model extracts "core" skills consistently, but varies on "implied" skills.

## Key Insights

1. **Consistency ≠ Correctness** — Model can be 3/3 consistent but wrong (saw "package" → `ecapgakp` 3x)

2. **Inconsistency = Uncertainty** — When model varies, it's uncertain. Use this as a QA flag.

3. **Extraction threshold is the issue** — Lily's naming is consistent, but her decision to include/exclude borderline skills varies.

## Proposed Fix

Add to Lily's prompt:
```
### Extraction Rules
- ONLY extract skills EXPLICITLY mentioned in the job description
- Do NOT infer skills from job title or industry
- If a skill is "nice to have" but vague, skip it
- When in doubt, leave it out
```

## Implementation

### task_logs.consistency column

Added `VARCHAR(10) DEFAULT '1/1'` to track:
- `3/3` — high confidence (all attempts agreed)
- `2/3` — medium confidence (majority agreed)
- `1/3` — low confidence (no consensus)
- `1/1` — no 3C used (legacy/resource-saving)

### BaseThickActor

Created [base_thick_actor.py](../../core/wave_runner/actors/base_thick_actor.py) with:
- `call_llm_with_3c()` — 3 separate sessions, returns ThreeC_Result
- `last_consistency` property — for task_logs
- `_consistency` in output — pull_daemon extracts and saves

### pull_daemon

Updated `_complete_task_log()` to extract `_consistency` from output and save to task_logs.

## Next Steps

1. ✅ Build task type reporter to review full prompts
2. ✅ Review Lily's input_template (instruction 3579)
3. ✅ Test prompt improvements with llm_chat — Lily agreed the rule makes sense
4. ✅ Tested old vs new: OLD 1/5 consistent, NEW 2/5 consistent
5. ✅ Updated instruction 3579 with Extraction Threshold rule
6. ⬜ Re-run full lily_cps_extract batch with improved prompt

## Prompt Update (instruction 3579)

Added extraction threshold rule to Lily's template:

```
### Extraction Threshold
- ONLY extract skills EXPLICITLY stated in the job description
- Do NOT infer skills from:
  - Job title alone (don't assume "Engineer" means python)
  - Industry norms (don't add "regulatory compliance" just because it's finance)
  - General requirements ("work independently" is not a skill)
- If a requirement is vague or ambiguous, SKIP IT
- Better to miss a borderline skill than include something implied
- Rule: If you can't quote the exact phrase from the JD, don't include it
```

**Test Results:**
- "Business Banking Manager" posting: OLD varies, NEW consistent (3/3)
- 5 random postings: OLD 1/5 consistent, NEW 2/5 consistent

Template grew from 6493 → 7004 chars.
