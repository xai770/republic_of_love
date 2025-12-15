# ADR-001: Priority-Based Branching Pattern

**Date:** November 26, 2025  
**Status:** ✅ Accepted  
**Deciders:** xai, Arden, Sandy  
**Context:** Workflow 3001 validation, Run 173-174 testing

---

## Context and Problem Statement

Workflow 3001 requires **two different types of branching**:

1. **Parallel Execution:** After Extract Summary, BOTH Grade A (gemma2) AND Grade B (qwen) should evaluate the summary simultaneously
2. **Conditional Branching:** After Grade B, either [PASS] → Format OR [FAIL] → Improve (only ONE path executes)

**The problem:** How do we implement BOTH parallel and conditional branching with ONE consistent pattern?

**Prior approaches that failed:**
- Separate `parallel_branches` table → Too complex, duplicates logic
- Boolean `is_parallel` flag → Doesn't handle conditional priority (which condition takes precedence?)
- Execution order field → Doesn't distinguish parallel vs conditional

---

## Decision

**Use `instruction_steps.branch_priority` as the ONLY mechanism for branching logic:**

### The Rule

```
IF (multiple instruction_steps match the output):
    group_by_priority = {}
    
    FOR each matching step:
        add to group_by_priority[step.branch_priority]
    
    highest_priority = max(group_by_priority.keys())
    
    EXECUTE ALL steps in group_by_priority[highest_priority]
    
    STOP (do not evaluate lower priorities)
```

### What This Means

**Same priority → ALL execute (Parallel):**
```sql
-- Extract Summary (conversation 9142) instruction_steps:
INSERT INTO instruction_steps (instruction_id, branch_condition, next_conversation_id, branch_priority)
VALUES
    (123, '*', 3336, 1),  -- Grade A (gemma2)
    (123, '*', 3337, 1);  -- Grade B (qwen)

-- Both have priority 1 → Both execute in parallel ✅
```

**Different priority → ONLY highest (Conditional):**
```sql
-- Grade B (conversation 3337) instruction_steps:
INSERT INTO instruction_steps (instruction_id, branch_condition, next_conversation_id, branch_priority)
VALUES
    (456, '[PASS]', 3341, 10),  -- Format
    (456, '[FAIL]', 3338, 10),  -- Improve
    (456, '*', 9999, 0);         -- Catchall (lower priority)

-- If output contains [PASS], only priority 10 [PASS] executes
-- If output contains [FAIL], only priority 10 [FAIL] executes  
-- Wildcard priority 0 NEVER executes (lower than 10)
```

**Within same priority → NO duplicates:**
```sql
-- Regrade (conversation 3339) OLD (broken):
INSERT INTO instruction_steps (instruction_id, branch_condition, next_conversation_id, branch_priority)
VALUES
    (789, '[FAIL]', 3340, 10),  -- Ticket
    (789, '*', 3340, 0);         -- Wildcard to ticket (DUPLICATE!)

-- Problem: If [FAIL] appears, BOTH match
-- With priority logic: Only priority 10 executes
-- Priority 0 wildcard NEVER executes ✅ (prevents duplicate ticket creation)
```

---

## Alternatives Considered

### Alternative 1: Separate `parallel_branches` Table

```sql
CREATE TABLE parallel_branches (
    instruction_id INTEGER,
    branch_group INTEGER,  -- All branches in same group execute in parallel
    next_conversation_id INTEGER
);
```

**Rejected because:**
- ❌ Adds complexity (now TWO tables for branching: instruction_steps + parallel_branches)
- ❌ Doesn't handle conditional priority (which condition wins?)
- ❌ Duplicates branching logic in two places

---

### Alternative 2: Boolean `is_parallel` Flag

```sql
ALTER TABLE instruction_steps ADD COLUMN is_parallel BOOLEAN DEFAULT FALSE;
```

**Rejected because:**
- ❌ Doesn't solve conditional priority (if multiple conditions match, which one?)
- ❌ Still need priority for conditional branches anyway
- ❌ Adding boolean when we already have numeric priority is redundant

---

### Alternative 3: Execution Order Field

```sql
ALTER TABLE instruction_steps ADD COLUMN execution_order INTEGER;
```

**Rejected because:**
- ❌ Execution order doesn't imply parallel vs sequential
- ❌ What does "order 1, 2, 3" mean? Sequential? Parallel? Both?
- ❌ Doesn't handle "execute all at priority X, stop at priority Y"

---

## Decision Outcome

### Chosen Solution: Priority-Based Branching

**Implementation:**
- File: `core/wave_runner/interaction_creator.py`
- Function: `_resolve_next_steps()`
- Lines: ~220-240

**Code pattern:**
```python
def _resolve_next_steps(self, parent_interaction, output_text):
    # Get all instruction_steps for completed interaction
    instruction_steps = self._get_instruction_steps(parent_interaction)
    
    # Group matching steps by priority
    from collections import defaultdict
    priority_groups = defaultdict(list)
    
    for step in instruction_steps:
        condition = step['branch_condition']
        priority = step['branch_priority'] or 0
        
        # Check if condition matches output
        if condition == '*' or condition in output_text:
            priority_groups[priority].append(step)
    
    # Execute ALL steps at highest matching priority ONLY
    if priority_groups:
        highest_priority = max(priority_groups.keys())
        matched_steps = priority_groups[highest_priority]
        
        for step in matched_steps:
            self._create_child_interaction(step, parent_interaction)
        
        return  # Stop - don't process lower priorities
```

---

## Consequences

### Positive ✅

1. **Simple:** One pattern handles both parallel and conditional
2. **Flexible:** Easy to add new branches (just set priority)
3. **Prevents duplicates:** Lower priority wildcards never execute if higher priority matches
4. **No special cases:** No need for separate parallel/conditional logic
5. **Database-enforced:** Priority is numeric column, easy to query and reason about

### Negative ⚠️

1. **Non-obvious:** Priority doing double-duty (parallel AND conditional) requires documentation
2. **Convention-dependent:** Developers must know the pattern (same priority = parallel)
3. **No schema enforcement:** Database can't prevent "wrong" priorities (must validate in code)

### Neutral 🔷

1. **Priority values are arbitrary:** Using 0, 1, 10, 100 is convention, not requirement
2. **Must maintain consistency:** If you change priorities, must understand the pattern

---

## Validation

### Test Case: Run 174 (November 26, 2025)

**Workflow:** 3001 Complete Job Processing Pipeline  
**Posting:** 4794 (failure path)

**Parallel Execution Test:**
```sql
-- Extract Summary (interaction 540) creates TWO children:
SELECT interaction_id, conversation_id, parent_interaction_id
FROM interactions
WHERE workflow_run_id = 174 
  AND parent_interaction_id = 540;

-- Result:
-- 541 | 3336 | 540  (Grade A)
-- 542 | 3337 | 540  (Grade B)
-- ✅ BOTH created from same parent (parallel execution confirmed)
```

**Conditional Execution Test:**
```sql
-- Grade B [FAIL] creates ONE child (not two):
SELECT interaction_id, conversation_id, parent_interaction_id
FROM interactions  
WHERE workflow_run_id = 174
  AND parent_interaction_id = 542;

-- Result:
-- 543 | 3338 | 542  (Improve)
-- ✅ ONLY Improve created (not Format) (conditional execution confirmed)
```

**Duplicate Prevention Test:**
```sql
-- Regrade [FAIL] creates ONE ticket (not two):
SELECT COUNT(*) FROM interactions
WHERE workflow_run_id = 174
  AND conversation_id = 3340;  -- Ticket conversation

-- Result: 1
-- ✅ Only ONE ticket (duplicate prevented by priority logic)
```

**Evidence:**
- Trace report: `reports/trace_final_validation_run_174.md`
- Database queries: All passing
- Workflow completion: 15/15 interactions (100%)

---

## Implementation Notes

### Priority Convention (Current Standard)

```
Priority 100:  Critical always-execute (Save, Check)
Priority 10:   Normal conditional ([PASS], [FAIL])
Priority 1:    Parallel wildcard (Grade A + Grade B)
Priority 0:    Catchall fallback (usually shouldn't execute)
```

**This is convention, not requirement.** The pattern works with any numeric priorities.

---

### Common Patterns

**Pattern 1: Parallel Grading**
```sql
-- Both graders, same priority, both execute
('*', 3336, 1),  -- Grade A
('*', 3337, 1);  -- Grade B
```

**Pattern 2: Conditional with Catchall**
```sql
-- Pass/fail at high priority, wildcard as fallback
('[PASS]', 3341, 10),  -- Format
('[FAIL]', 3338, 10),  -- Improve  
('*', 3340, 0);        -- Ticket (only if neither PASS nor FAIL found)
```

**Pattern 3: Always Execute (No Conditions)**
```sql
-- Single wildcard at high priority
('*', 3342, 100);  -- Always go to Save
```

**Pattern 4: Multiple Parallels then Converge**
```sql
-- Multiple parallel paths, all same priority
('*', 3350, 1),  -- Extract Skills
('*', 3360, 1),  -- Extract Certifications  
('*', 3370, 1);  -- Extract Education
-- All three execute in parallel, then converge at next step
```

---

## Related Decisions

- **ADR-002** (future): Event-sourcing state management
- **ADR-003** (future): No template substitution (query database for parent outputs)
- **ADR-004** (future): Hybrid schema for benchmarks (relational + JSONB)

---

## References

**Documentation:**
- [Workflow 3001 Documentation](../../workflows/3001_complete_job_processing_pipeline.md)
- [Workflow 3001 Session Notes](../../Workflow_3001_2025-Nov-26_notes.md)
- [Sandy's Cheat Sheet](../../__sandy_cheat_sheet.md)

**Code:**
- Implementation: `core/wave_runner/interaction_creator.py` (line ~222)
- Tests: Run 173, Run 174 validation

**Database:**
- Table: `instruction_steps`
- Column: `branch_priority INTEGER`
- Queries: See validation section above

---

## Superseded By

None. This decision is current and active.

---

## Notes

**Discovery:** This pattern was discovered during Run 173-174 validation (November 26, 2025) when fixing the duplicate ticket creation bug. The "break statement prevents parallel execution" issue led to the realization that priority could handle BOTH use cases.

**Key insight:** Priority isn't just "which branch wins" - it's "which priority LEVEL wins, then ALL branches at that level execute."

**Simplicity:** The entire branching complexity of Workflow 3001 (16 conversations, parallel + conditional paths) is handled by this ONE pattern.

---

*End of ADR-001*
