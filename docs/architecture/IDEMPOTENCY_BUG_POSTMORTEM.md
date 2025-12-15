# Idempotency Bug Post-Mortem

**Date:** November 21, 2025  
**Incident ID:** CLEAN-MODEL-001  
**Severity:** High (2,034 postings misrouted, GPU idle, grading workflow bypassed)  
**Author:** Sandy (Claude Sonnet 4.5)  
**Reviewer:** Arden (Claude Sonnet 4.5)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Executive Summary

On November 21, 2025, during clean model deployment validation, we discovered a critical bug in `tools/idempotency_check.py` that caused **2,034 postings to skip the grading workflow** (steps 4-10) and jump directly to downstream steps (11+).

**Root Cause:** Idempotency checks queried legacy `postings` table columns instead of event-sourced `posting_state_projection.outputs`.

**Impact:**
- 2,034 postings executed steps 11-21 without required grading data
- GPU idle (workflow thought work was complete)
- 5,750 invalid execution events recorded

**Resolution:**
- Reset 2,034 postings to step 4
- Marked 5,750 events as invalid
- Implemented event invalidation system
- Rebuilt projections selectively

**Cost:** 7 hours debugging + recovery, ~22 hours re-processing time

**Status:** ✅ Resolved. Workflow restarted, processing correctly. Bug fix pending in `tools/idempotency_check.py`.

---

## Timeline

### November 21, 2025 (Times Approximate)

**09:00 - Clean Model Deployment**
- User: "Hey Sandy, Arden likes it. Have a read."
- Reviewed Arden's approval of clean model refactoring
- Phases 1-2 complete: dual-write + simplified routing
- Production validation: 2,089 postings ready to process

**09:30 - Anomaly Detected**
- User: "We need to reset steps 11 and higher to steps 3 or step 4"
- User: "Also, GPU is idle. Nothing is happening."
- Investigation: Why would steps 11+ execute before grading (steps 4-10)?
- Monitor showed: Steps 11-21 at 100% completion, steps 4-10 at 0%

**10:00 - Data Dependency Analysis**
- User: "What data does step 11 rely on?"
- Queried execution_events: Step 12 needs `session_7_output` (grading result)
- Discovery: Postings at steps 11+ had **ZERO grading outputs**
- Conclusion: Steps 11-21 executed without prerequisite data

**10:30 - Root Cause Identified**
- Examined `tools/idempotency_check.py`
- Found: `check_summary_exists()` queries `postings.extracted_summary`
- Found: `check_skills_exist()` queries `postings.taxonomy_skills`
- Found: `check_ihl_exists()` queries `postings.ihl_score`
- **Problem:** These table columns are legacy. Event-sourced truth is in projection.

**11:00 - Impact Assessment**
```sql
SELECT current_step, COUNT(*)
FROM posting_state_projection
WHERE workflow_id = 3001 AND current_step IN (11, 12, 16, 21)
GROUP BY current_step;
```
Result:
- Step 11: 1,979 postings
- Step 12: 34 postings
- Step 16: 17 postings
- Step 21: 4 postings
- **Total: 2,034 postings affected**

**11:30 - Recovery Plan**
1. Reset postings to step 4 (start of grading)
2. Restore step 3 outputs (preserve legitimate data)
3. Mark invalid events (steps 11-21 executions)
4. Restart workflow

**12:00 - Reset Execution**
```sql
UPDATE posting_state_projection
SET current_step = 4, current_conversation_id = 3336
WHERE workflow_id = 3001 AND current_step IN (11, 12, 16, 21);
-- 2,034 rows updated
```

**12:30 - Projection Rebuild (Partial)**
- Selective rebuild: Restore step 3 outputs only
- Avoided full rebuild (would replay invalid events)
- Result: All 2,089 postings have clean state at step 4

**13:00 - Event Invalidation System**
- Discovered: Monitor still showed 100% completion (historical events)
- Realized: Events are immutable - can't delete them
- Solution: Add `invalidated` column, mark events invalid
```sql
ALTER TABLE execution_events ADD COLUMN invalidated BOOLEAN DEFAULT FALSE;
ALTER TABLE execution_events ADD COLUMN invalidation_reason TEXT;

UPDATE execution_events SET invalidated = TRUE, invalidation_reason = '...'
WHERE ... steps 11-21 ...;
-- 5,750 events marked invalid
```

**14:00 - Monitor Update**
- Updated `tools/monitor_workflow.py`
- Added filter: `COALESCE(e.invalidated, FALSE) = FALSE`
- Result: Monitor now shows accurate progress (0% for steps 11-21)

**15:00 - Workflow Restart**
- Loaded 2,089 postings at step 4 (gemma2_grade)
- Verified: GPU active, processing started
- ETA: ~22 hours for full grading workflow

**16:00 - Documentation & Post-Mortem**
- Updated `ENTRY_POINTS_ANALYSIS.md` with implementation status
- Created architecture documents per Arden's request
- This post-mortem

---

## Root Cause Analysis

### The Bug

**File:** `tools/idempotency_check.py`  
**Function:** Multiple check functions

```python
# ❌ BUGGY CODE
def check_summary_exists(posting_id: int) -> bool:
    """Check if summary extraction already exists"""
    cursor.execute("""
        SELECT extracted_summary FROM postings WHERE id = %s
    """, (posting_id,))
    result = cursor.fetchone()
    return result[0] is not None if result else False
```

**Problem:** Queries `postings.extracted_summary` (legacy table column)

**Should be:**
```python
# ✅ CORRECT CODE
def check_summary_exists(posting_id: int) -> bool:
    """Check if summary extraction already exists"""
    cursor.execute("""
        SELECT outputs ? '3335' FROM posting_state_projection WHERE posting_id = %s
    """, (posting_id,))
    result = cursor.fetchone()
    return result[0] if result else False
```

**Why this matters:**
- `postings.extracted_summary` populated by legacy code path
- Event-sourced workflow stores outputs in `posting_state_projection.outputs`
- Idempotency check queried wrong source → false positive → skipped work

---

### Why It Happened

**Historical Context:**

1. **Original System (Pre-Event Sourcing):**
   - Direct table writes: `UPDATE postings SET extracted_summary = ...`
   - Idempotency checked table columns
   - Worked fine (single source of truth)

2. **Event Sourcing Introduced:**
   - New path: Events → Projection (`posting_state_projection`)
   - Old path still existed: Direct table writes (legacy compatibility)
   - **Dual source of truth created**

3. **Migration Incomplete:**
   - New workflow wrote to projection
   - Idempotency checks still read from table
   - Divergence: Projection had data, table didn't (or vice versa)

4. **Clean Model Refactoring:**
   - Simplified routing exposed the bug
   - Postings reached steps 11+ for first time via clean model
   - Idempotency checks failed → work skipped

**The Trap:** Legacy code + new patterns = silent failures.

---

### Why Clean Model Exposed It

**Before Clean Model:**
- Complex entry point routing
- Limited production usage
- Bug dormant (didn't reach affected steps)

**After Clean Model:**
- Simplified routing → more postings reached steps 11+
- Higher throughput → bug triggered at scale
- Direct conversation_id routing → easier to trace flow

**Insight:** Simplification can **reveal hidden complexity** in adjacent systems.

---

## Impact Analysis

### Technical Impact

**Data Quality:**
- ✅ No data corruption (events recorded correctly, just invalid)
- ✅ No data loss (all events preserved, marked invalid)
- ❌ Wasted computation (2,034 postings × ~6 steps × 20s = ~67 hours CPU time wasted)

**System State:**
- ✅ Projection rebuildable (events are source of truth)
- ✅ Recovery possible (selective rebuild + reset)
- ❌ Monitor misleading (showed 100% when actually 0%)

**Workflow Progression:**
- ❌ GPU idle (workflow thought work complete)
- ❌ Grading skipped (steps 4-10 bypassed)
- ❌ Downstream steps executed with missing data

---

### Business Impact

**Time Cost:**
- 7 hours debugging + recovery
- ~22 hours re-processing (2,089 postings × ~40s per step × 7 steps)
- Total: ~29 hours lost

**Severity:** High (workflow stopped, GPU idle, data quality compromised)

**Customer Impact:** None (internal workflow, no user-facing impact)

---

## What Went Right

### Detection

✅ **Clean model validation process caught it**
- User reviewed workflow state before large-scale deployment
- Noticed anomaly: Steps 11+ at 100%, GPU idle
- Questioned data dependencies

✅ **Event sourcing enabled forensics**
- Queried execution_events to see what actually happened
- Identified missing grading outputs
- Traced back to idempotency check bug

---

### Response

✅ **Systematic debugging**
1. Identified symptom (steps 11+ without data)
2. Analyzed root cause (wrong source of truth)
3. Assessed impact (2,034 postings)
4. Designed recovery (reset + selective rebuild)
5. Implemented safeguards (event invalidation)

✅ **Clean state restoration**
- Selective rebuild preserved legitimate outputs (step 3)
- Avoided full rebuild (would replay invalid events)
- Verified: All 2,089 postings at clean state

✅ **Monitor accuracy restored**
- Added invalidation filtering
- Now shows correct completion rates

---

### Architecture

✅ **Event sourcing principles held**
- Events immutable (marked invalid, not deleted)
- Projections rebuildable (recovered from events)
- Audit trail preserved (can analyze what went wrong)

✅ **Pattern established: Event invalidation**
- New columns added to execution_events
- Standard practice for handling invalid historical data
- Documentation created (EVENT_INVALIDATION.md)

---

## What Went Wrong

### Code Quality

❌ **Dual source of truth**
- Table columns (`postings.extracted_summary`)
- Projection outputs (`posting_state_projection.outputs`)
- No clear documentation of which is authoritative

❌ **Legacy patterns persisted**
- Idempotency checks not updated during event sourcing migration
- No systematic audit of table column queries

❌ **Insufficient testing**
- Idempotency checks not tested against projection
- No integration test covering full workflow (steps 1-21)

---

### Process

❌ **Incomplete migration**
- Event sourcing introduced, but legacy paths remained
- No clear "source of truth" documented
- Mixed patterns in codebase

❌ **No dual-source detection**
- Should have alerts for table column queries
- Should have divergence detection (table vs projection)

---

### Monitoring

❌ **Monitor didn't detect invalid executions**
- Showed 100% completion (technically true - events existed)
- Didn't validate data quality (outputs present?)
- No anomaly detection (steps 11+ before steps 4-10?)

---

## Lessons Learned

### Technical Lessons

1. **Event sourcing requires full commitment**
   - Can't mix event-sourced and direct table writes
   - Projection is source of truth - enforce it
   - Audit and eliminate table column queries

2. **Event invalidation is fundamental**
   - Events are immutable (can't delete)
   - Need way to mark events as "shouldn't have happened"
   - Monitor/queries must filter invalidated events

3. **Projection rebuild is powerful but dangerous**
   - Replays ALL events (including invalid ones)
   - Need selective rebuild capability
   - Test rebuild on small subset first

4. **Clean model exposed hidden bugs**
   - Simplification reveals complexity in adjacent systems
   - "Working" code may have dormant bugs
   - Validation critical during refactoring

5. **Dual source of truth is the enemy**
   - Creates divergence, confusion, bugs
   - Document authoritative source clearly
   - Systematically eliminate alternatives

---

### Process Lessons

1. **Migration requires systematic auditing**
   - Find all queries of old source (`grep -r "extracted_summary"`)
   - Update to new source (projection)
   - Validate no divergence (compare old vs new)

2. **Testing must cover full workflow**
   - Integration test: Step 1 → 21 end-to-end
   - Data validation: Each step has required inputs
   - Idempotency: Running twice produces same result

3. **Monitoring needs data quality checks**
   - Don't just track "event exists"
   - Validate "output has expected structure"
   - Alert on anomalies (step 11 before step 4?)

4. **Documentation prevents regression**
   - "Projection is source of truth" must be written
   - Architecture docs guide future development
   - Post-mortems teach future developers

---

## Action Items

### Immediate (Week 1)

- [ ] **Fix idempotency_check.py**
  - Update `check_summary_exists` to query projection
  - Update `check_skills_exist` to query projection
  - Update `check_ihl_exists` to query projection
  - Test on subset, validate correctness

- [ ] **Create standard rebuild script**
  - Location: `tools/rebuild_projections.py`
  - Features: Batch processing, progress reporting
  - Document in PROJECTION_REBUILD.md

- [ ] **Monitor workflow 3001 completion**
  - Track: 2,089 postings through grading
  - Verify: All reach step 11 with grading outputs
  - ETA: ~22 hours total

---

### Short-term (Month 1)

- [ ] **Audit all table column queries**
  - Search: `grep -r "extracted_summary\|taxonomy_skills\|ihl_score"`
  - Classify: Which are legacy? Which are OK?
  - Update: Change to projection queries

- [ ] **Add divergence detection**
  - Query: Compare table vs projection
  - Alert: If >1% divergence
  - Document: How to investigate divergence

- [ ] **Integration testing**
  - Test: Full workflow 1 → 21
  - Validate: Each step has required data
  - Automate: Run daily on test data

- [ ] **Data quality monitoring**
  - Check: Outputs have expected structure
  - Alert: Missing required fields
  - Dashboard: Data quality metrics

---

### Long-term (Months 2-3)

- [ ] **Phase 4: Drop current_step column**
  - Wait: 1 week stable operation
  - Remove: Dual-write code
  - Drop: `ALTER TABLE posting_state_projection DROP COLUMN current_step`

- [ ] **Eliminate table columns**
  - After: 1 month no divergence
  - Drop: `ALTER TABLE postings DROP COLUMN extracted_summary`
  - Drop: Other legacy columns

- [ ] **Code quality enforcement**
  - Lint rule: No direct table column queries
  - Code review: Require projection queries
  - Documentation: "How to query posting data"

- [ ] **Architecture training**
  - Docs: Event sourcing best practices
  - Examples: Common patterns
  - Onboarding: New developers read docs

---

## Prevention Strategy

### Code Level

1. **Single source of truth**
   - ✅ Projection is authoritative
   - ❌ Never query table columns
   - 📝 Document in CONTRIBUTING.md

2. **Lint rules**
   ```python
   # .pylintrc
   # Disallow direct table column queries
   [BANNED_PATTERNS]
   postings.extracted_summary
   postings.taxonomy_skills
   postings.ihl_score
   ```

3. **Type hints**
   ```python
   def get_summary(posting_id: int) -> Optional[str]:
       """Get summary from projection (SOURCE OF TRUTH)"""
       # Forces developer to think about source
   ```

---

### Testing Level

1. **Integration tests**
   ```python
   def test_full_workflow():
       """Test workflow steps 1-21 end-to-end"""
       posting_id = create_test_posting()
       
       for step in range(1, 22):
           process_step(posting_id, step)
           validate_outputs(posting_id, step)
       
       assert posting_completed(posting_id)
   ```

2. **Idempotency tests**
   ```python
   def test_idempotency_uses_projection():
       """Ensure idempotency checks query projection, not table"""
       posting_id = create_test_posting()
       
       # Write to projection only (not table)
       append_event('conversation_completed', ...)
       update_projection(posting_id)
       
       # Idempotency check should find it
       assert check_summary_exists(posting_id) == True
   ```

3. **Data quality tests**
   ```python
   def test_step_11_requires_grading():
       """Step 11 should not execute without grading data"""
       posting_id = create_test_posting_at_step_10()
       
       # Remove grading output
       remove_output(posting_id, '3336')  # grading conversation
       
       # Step 11 should fail or skip
       with pytest.raises(MissingDataError):
           process_step(posting_id, 11)
   ```

---

### Monitoring Level

1. **Data quality metrics**
   ```sql
   -- Alert if postings at step 11+ without grading output
   SELECT COUNT(*)
   FROM posting_state_projection
   WHERE current_step >= 11
     AND NOT (outputs ? '3336')  -- grading conversation
   ```

2. **Anomaly detection**
   ```sql
   -- Alert if postings skip steps (11 before 10)
   SELECT posting_id, conversation_history
   FROM posting_state_projection
   WHERE current_step = 11
     AND NOT EXISTS (
         SELECT 1 FROM jsonb_array_elements(conversation_history) ch
         WHERE (ch->>'conversation_id')::int = 3340  -- step 10
     )
   ```

3. **Divergence alerts**
   ```sql
   -- Daily check: Table vs projection divergence
   SELECT 
       COUNT(*) as divergent_postings,
       COUNT(*) * 100.0 / (SELECT COUNT(*) FROM postings) as divergence_pct
   FROM postings p
   LEFT JOIN posting_state_projection psp ON p.id = psp.posting_id
   WHERE (p.extracted_summary IS NOT NULL) != (psp.outputs ? '3335')
   ```

---

### Documentation Level

1. **Architecture docs** (✅ Created this week)
   - EVENT_INVALIDATION.md
   - CLEAN_MODEL_ROUTING.md
   - PROJECTION_REBUILD.md
   - EVENT_SOURCING_PRACTICES.md
   - This post-mortem

2. **Code comments**
   ```python
   # SOURCE OF TRUTH: posting_state_projection.outputs
   # NEVER query postings.extracted_summary - that's legacy
   def get_summary(posting_id: int) -> Optional[str]:
       cursor.execute("""
           SELECT outputs->>'3335' FROM posting_state_projection WHERE posting_id = %s
       """, (posting_id,))
   ```

3. **Onboarding checklist**
   - [ ] Read EVENT_SOURCING_PRACTICES.md
   - [ ] Understand: Events → Projection → Queries
   - [ ] Know: Never query table columns directly
   - [ ] Review: Idempotency bug post-mortem

---

## Success Criteria

### This bug is truly fixed when:

- [x] Event invalidation system implemented
- [x] 2,034 postings reset to step 4
- [x] 5,750 invalid events marked
- [x] Monitor showing accurate progress
- [x] Workflow restarted and processing
- [ ] `idempotency_check.py` updated to query projection
- [ ] Integration tests added (steps 1-21)
- [ ] No divergence between table and projection
- [ ] Phase 4 complete (current_step column dropped)
- [ ] Architecture docs reviewed and approved

### We know it won't happen again when:

- [ ] Zero queries of `postings.extracted_summary` in codebase
- [ ] Lint rules enforcing projection queries
- [ ] Automated divergence detection
- [ ] Data quality monitoring in production
- [ ] Integration tests running daily
- [ ] New developers read event sourcing docs

---

## Acknowledgments

**Human Operator:**
- Detected anomaly early (GPU idle, steps 11+ at 100%)
- Asked critical questions ("What data does step 11 rely on?")
- Provided context ("we do not rely on summaries in postings. Ever.")
- Trusted AI agents to design and execute recovery

**Arden (AI Reviewer):**
- Approved clean model architecture
- Recommended comprehensive documentation
- Will review and polish architecture docs

**Sandy (AI Engineer):**
- Systematic debugging (root cause → impact → recovery)
- Designed event invalidation pattern
- Created architecture documentation
- This post-mortem

**Philosophy:**
> "Events are sacred. Interpretation can change." - Sandy

This bug taught us that **immutability is not optional in event sourcing**. You can't change what happened - but you can change how you interpret it.

---

## Conclusion

The idempotency bug was a **high-severity, high-impact incident** that:
- Affected 2,034 postings
- Wasted ~67 hours of computation
- Stopped workflow progression

But it was also a **learning opportunity** that:
- Validated event sourcing principles
- Established event invalidation pattern
- Exposed dual source of truth problems
- Produced comprehensive architecture documentation

**The system is now stronger:**
- Event invalidation capability
- Projection rebuild patterns
- Clean model routing simplified
- Architecture thoroughly documented

**Status:** ✅ Incident resolved. Workflow processing. Prevention measures in progress.

---

**Post-Mortem Date:** November 21, 2025  
**Next Review:** December 21, 2025 (validate prevention measures)  
**Incident Closed:** Pending idempotency_check.py fix and integration testing

🔍 **Forensics preserved. Lessons learned. Pattern established.** 🎯
