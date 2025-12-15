# Workflow 3001 Validation Analysis

**Date**: 2025-11-13  
**Workflow**: Complete Job Processing Pipeline (PROD)  
**Total Warnings**: 20 (10 unreachable conversations + 10 missing error branches)

---

## Summary

Validation revealed **technical debt** accumulated from workflow evolution. The workflow has 19 conversations defined, but **10 are unreachable** from the start node. Additionally, **5 script actors lack error handling branches**, which could cause silent failures.

---

## Part 1: Unreachable Conversations (10 warnings)

### Issue

These conversations exist in the workflow definition but **no branch leads to them**:

| Execution Order | Canonical Name | Actor | Status |
|-----------------|----------------|-------|--------|
| 4 | `gemma2_grade` | gemma2:latest | ✗ Orphaned |
| 5 | `qwen25_grade` | qwen2.5:7b | ✗ Orphaned |
| 7 | `qwen25_regrade` | qwen2.5:7b | ✗ Orphaned |
| 8 | `create_ticket` | qwen2.5:7b | ❓ Partially used |
| 14 | `gopher_skill_extraction` | qwen2.5:7b | ✗ Orphaned |
| 15 | `save_job_skills` | job_skills_saver | ✗ Orphaned |
| 20 | `w1124_c2_skeptic` | gemma2:latest | ✗ Orphaned |
| 21 | `w1124_c3_expert` | qwen2.5:7b | ✗ Orphaned |

### Root Cause Analysis

#### 1. **Dual Grading System (C4, C5, C7) - DISABLED**

The workflow **originally had TWO graders**:
- `gemma2_grade` (C4) - First grader
- `qwen25_grade` (C5) - Second grader
- `qwen25_improve` (C6) - Improvement session if grading fails
- `qwen25_regrade` (C7) - Re-check after improvement

**Current flow**: `gemma3_extract (C3)` → **SKIPS C4, C5** → `qwen25_improve (C6)` → **SKIPS C7** → `format_standardization (C9)`

**Why disabled?**
- Likely **performance optimization** (2 graders → 1 grader → 0 graders?)
- Or **quality issues** (graders were too strict/lenient)
- Branch from C3 → C4 was deleted/disabled

**Decision needed:**
- ✂️ **Delete C4, C5, C7** (clean up dead code)
- 🔄 **Re-enable dual grading** (fix branch from C3 → C4)
- 📝 **Document why disabled** (keep in DB but mark as "backup graders")

---

#### 2. **Error Ticket System (C8) - HALF-ALIVE**

`create_ticket` (C8) **is referenced** by branches:
- `qwen25_grade` → `[*]` → `create_ticket` (unexpected output)
- `qwen25_regrade` → `[FAIL]` → `create_ticket` (still failing after improvement)

**But since C5 and C7 are unreachable**, the ticket system is **effectively disabled**.

**Decision needed:**
- If you **delete C5/C7**, also **delete C8** (ticket system unused)
- If you **re-enable C5/C7**, keep C8 for error tracking

---

#### 3. **Gopher Skills Extractor (C14, C15) - REPLACED**

The workflow **replaced** gopher skills extraction:
- **Old**: `gopher_skill_extraction (C14)` → `save_job_skills (C15)`
- **New**: `taxonomy_skill_extraction (C12)` → `taxonomy_skill_extraction (C13)` → **END**

**Current flow**: 
- `check_skills_exist (C11)` → `[RUN]` → `taxonomy_skill_extraction (C12)`
- **C12 is named "r1114_extract_skills"** (Recipe 1114)
- **C13 is duplicate canonical_name!** Both C12 and C13 are `taxonomy_skill_extraction`
- **No branch from C13 → C14 or C13 → C15**

**Data issue**: C13 has **duplicate canonical_name** with C12. This should be `taxonomy_skill_mapping` or similar.

**Decision needed:**
- ✂️ **Delete C14, C15** (old gopher extractor replaced by recipe 1114)
- 🔧 **Fix C13 canonical_name** (taxonomy_skill_extraction → taxonomy_skill_mapping?)
- 🔗 **Add branch C13 → C16** (continue to IHL scoring after skills extracted)

---

#### 4. **IHL Multi-Agent Debate (C20, C21) - INCOMPLETE**

The workflow **should have 3-agent IHL scoring**:
- `w1124_c1_analyst (C19)` - Find red flags
- `w1124_c2_skeptic (C20)` - Challenge analyst
- `w1124_c3_expert (C21)` - Final verdict

**Current flow**: `check_ihl_exists (C16)` → `[RUN]` → `w1124_c1_analyst (C19)` → **DEAD END**

**No branch from C19 → C20!** The analyst runs but the skeptic and expert never execute.

**Decision needed:**
- 🔗 **Add branches**: C19 → C20 → C21 → END
- Or ✂️ **Single-agent IHL**: Delete C20, C21, add C19 → END branch

---

## Part 2: Missing Error Branches (10 warnings)

### Issue

5 script actors lack `[FAILED]` and `[TIMEOUT]` branches. If they fail, **the posting goes TERMINAL** (silent death, no retry, no alert).

| Conversation | Actor | Missing Branches | Impact |
|--------------|-------|------------------|--------|
| `fetch_db_jobs` (C1) | db_job_fetcher | `[FAILED]`, `[TIMEOUT]` | **CRITICAL** - No jobs fetched |
| `check_summary_exists` (C2) | idempotency_check | `[FAILED]`, `[TIMEOUT]` | Medium - Assumes RUN on error |
| `save_summary_check_ihl` (C10) | summary_saver_ihl_checker | `[FAILED]`, `[TIMEOUT]` | **HIGH** - Summary lost |
| `check_skills_exist` (C11) | idempotency_check | `[FAILED]`, `[TIMEOUT]` | Medium - Assumes RUN on error |
| `check_ihl_exists` (C16) | idempotency_check | `[FAILED]`, `[TIMEOUT]` | Medium - Assumes RUN on error |

### Root Cause

The current wave batch processor has this behavior:

```python
# From core/wave_batch_processor.py line ~450
def _evaluate_branch_conditions(self, branches, conversation_output):
    for branch in sorted(branches, key=lambda b: b['priority'], reverse=True):
        if self._match_branch_condition(branch['condition'], conversation_output):
            return branch
    
    # 🚨 SCREAM: No matching branch found!
    if conversation_output in ['[FAILED]', '[TIMEOUT]', '[ERROR]']:
        raise RuntimeError(f"🚨 UNMATCHED ERROR STATE: {conversation_output}")
    
    return None  # Posting goes TERMINAL
```

**Without error branches:**
1. Script fails → outputs `[FAILED]`
2. No branch matches `[FAILED]`
3. RuntimeError raised → workflow CRASHES
4. Posting marked as `FAILED` in workflow_runs

**This is GOOD** (fail-fast), but we should **handle errors gracefully**:
- Log error to tracking system
- Retry with backoff
- Skip to next stage (if non-critical)
- Alert operator

### Recommended Error Branches

#### 1. `fetch_db_jobs` (C1) - CRITICAL

```yaml
branches:
  - condition: '[RATE_LIMITED]'
    next_conversation: check_summary_exists
    description: Skip to extraction if fetcher rate-limited
  
  # NEW: Error handling
  - condition: '[FAILED]'
    next_conversation: null  # TERMINATE workflow
    description: API failure - cannot proceed without jobs
  
  - condition: '[TIMEOUT]'
    next_conversation: null  # TERMINATE workflow
    description: API timeout - cannot proceed
```

**Rationale**: If we can't fetch jobs, the entire workflow is meaningless. Terminate early.

---

#### 2. `check_summary_exists` (C2) - DEFAULT TO RUN

```yaml
branches:
  - condition: '[SKIP]'
    next_conversation: save_summary_check_ihl
  
  - condition: '[RUN]'
    next_conversation: gemma3_extract
  
  # NEW: Error handling (assume RUN on failure)
  - condition: '[FAILED]'
    next_conversation: gemma3_extract
    description: Check failed - assume summary missing, run extraction
  
  - condition: '[TIMEOUT]'
    next_conversation: gemma3_extract
    description: Check timed out - assume summary missing
```

**Rationale**: Idempotency checks are **non-critical**. If check fails, **assume missing** and run the operation.

---

#### 3. `save_summary_check_ihl` (C10) - RETRY LOGIC

```yaml
branches:
  - condition: '[HAS_IHL]'
    next_conversation: taxonomy_skill_extraction
  
  - condition: '[NO_IHL]'
    next_conversation: check_skills_exist
  
  # NEW: Error handling (retry save operation)
  - condition: '[FAILED]'
    next_conversation: save_summary_check_ihl  # Retry same conversation
    max_iterations: 3
    description: Save failed - retry up to 3 times
  
  - condition: '[TIMEOUT]'
    next_conversation: check_skills_exist  # Skip to next stage
    description: Save timed out - continue workflow (summary lost but non-fatal)
```

**Rationale**: Database saves should **retry**. If retries exhausted, continue workflow (data loss is bad but non-fatal).

---

#### 4. `check_skills_exist` (C11) - DEFAULT TO RUN

```yaml
branches:
  - condition: '[SKIP]'
    next_conversation: check_ihl_exists
  
  - condition: '[RUN]'
    next_conversation: taxonomy_skill_extraction
  
  # NEW: Error handling (assume RUN on failure)
  - condition: '[FAILED]'
    next_conversation: taxonomy_skill_extraction
    description: Check failed - assume skills missing
  
  - condition: '[TIMEOUT]'
    next_conversation: taxonomy_skill_extraction
    description: Check timed out - assume skills missing
```

**Rationale**: Same as C2 - idempotency checks are non-critical.

---

#### 5. `check_ihl_exists` (C16) - DEFAULT TO RUN

```yaml
branches:
  - condition: '[SKIP]'
    next_conversation: null  # Workflow complete
  
  - condition: '[RUN]'
    next_conversation: w1124_c1_analyst
  
  # NEW: Error handling (assume RUN on failure)
  - condition: '[FAILED]'
    next_conversation: w1124_c1_analyst
    description: Check failed - assume IHL missing
  
  - condition: '[TIMEOUT]'
    next_conversation: w1124_c1_analyst
    description: Check timed out - assume IHL missing
```

**Rationale**: Same as C2, C11 - assume missing on error.

---

## Recommended Actions

### Phase 1: Clean Up Dead Code (Low Risk)

1. ✂️ **Delete unreachable conversations** (C4, C5, C7, C8, C14, C15, C20, C21)
   - Remove from `workflow_conversations` table
   - Archive conversation definitions for historical reference
   - Update documentation

2. 🔧 **Fix C13 duplicate canonical_name**
   - Change `taxonomy_skill_extraction` → `taxonomy_skill_mapping`
   - Add branch: C13 → C16 (continue to IHL check)

### Phase 2: Add Error Handling (Medium Risk)

3. 🔗 **Add error branches to 5 conversations**
   - C1: TERMINATE on error (critical)
   - C2, C11, C16: DEFAULT TO RUN on error (idempotency checks)
   - C10: RETRY on error (database save)

4. 🧪 **Test error scenarios**
   - Simulate script failures
   - Verify retry logic works
   - Confirm error logging

### Phase 3: Future Enhancements (Optional)

5. 📊 **Add error tracking conversation**
   - New conversation: `log_workflow_error`
   - Captures error details, creates ticket, sends alert
   - All error branches → `log_workflow_error` → TERMINATE

6. 🔄 **Re-enable dual grading** (if needed)
   - Add branch: C3 → C4 (gemma3_extract → gemma2_grade)
   - Add branch: C6 → C7 (qwen25_improve → qwen25_regrade)
   - Keep C8 error ticket system

7. 🤝 **Complete IHL multi-agent debate**
   - Add branch: C19 → C20 (analyst → skeptic)
   - Add branch: C20 → C21 (skeptic → expert)
   - Add branch: C21 → END (expert → complete)

---

## Testing Plan

### Step 1: Export Current Workflow

```bash
python3 tools/export_workflows_to_yaml.py --workflow 3001
cp workflows/3001_complete_job_processing_pipeline.yaml backups/3001_before_cleanup.yaml
```

### Step 2: Edit YAML (Phase 1 Changes)

Remove unreachable conversations from YAML file.

### Step 3: Validate Changes

```bash
python3 tools/validate_workflow.py --file workflows/3001_complete_job_processing_pipeline.yaml
```

Expected result: **0 warnings** (all unreachable conversations removed).

### Step 4: Import to DEV Environment

```bash
# First, create a DEV copy of workflow 3001
psql -c "INSERT INTO workflows (workflow_name, environment) VALUES ('Complete Job Processing Pipeline - DEV', 'DEV') RETURNING workflow_id;"

# Import YAML to DEV workflow
python3 tools/import_workflows_from_yaml.py --file workflows/3001_complete_job_processing_pipeline.yaml --dry-run

# If dry-run looks good, import for real
python3 tools/import_workflows_from_yaml.py --file workflows/3001_complete_job_processing_pipeline.yaml
```

### Step 5: Test DEV Workflow

```bash
# Run on test posting
python3 -m core.wave_batch_processor --workflow 3004 --posting 4520

# Debug execution
python3 tools/debug_posting.py --posting 4520
```

### Step 6: Deploy to PROD (if DEV tests pass)

```bash
python3 tools/import_workflows_from_yaml.py --file workflows/3001_complete_job_processing_pipeline.yaml
```

---

## Risk Assessment

| Change | Risk Level | Impact | Rollback Plan |
|--------|-----------|--------|---------------|
| Delete unreachable conversations | **LOW** | No runtime impact (already unused) | Restore from backup YAML |
| Fix C13 canonical_name | **LOW** | Improves clarity | Revert canonical_name change |
| Add error branches | **MEDIUM** | Changes error handling behavior | Restore original branches |
| Re-enable dual grading | **HIGH** | Increases LLM calls, latency | Delete added branches |

---

## Conclusion

The validation tool successfully identified **20 legitimate issues** in the production workflow:

1. **10 unreachable conversations** - Technical debt from workflow evolution (should be deleted)
2. **10 missing error branches** - Silent failure risk (should add retry/skip/terminate logic)

Both issues are **fixable** with YAML edits + import. The YAML workflow system enables:
- **Version control** (git diff shows exact changes)
- **Code review** (team approval before deployment)
- **Testing** (validate in DEV before PROD)
- **Rollback** (revert to previous YAML version)

**Next step**: Choose Phase 1 (cleanup only) or Phase 1 + Phase 2 (cleanup + error handling).
