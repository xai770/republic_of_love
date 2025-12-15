# Code Refactoring Best Practices

**Purpose**: Reference guide for safe code refactoring in Turing workflows  
**Audience**: Developers maintaining workflow execution code  
**Status**: Production lessons learned (November 2025)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Overview

This guide documents best practices for refactoring large Python codebases, based on production experience refactoring the Turing workflow executor.

---

## Refactoring Principles

### 1. Extract, Don't Rewrite

**✅ DO**: Break monolithic code into focused modules
```python
# Before: 1,465-line file
workflow_executor.py (everything in one file)

# After: Modular design
posting_state.py (26 lines)      # Data class
wave_executor.py (358 lines)     # Batch processing
prompt_renderer.py (80 lines)    # Template rendering
workflow_executor.py (1,088 lines)  # Orchestration
```

**❌ DON'T**: Rewrite from scratch
- Loses domain knowledge embedded in code
- Introduces new bugs
- Takes longer than incremental refactoring

### 2. Test After Each Extraction

**Process**:
1. Extract one class/module
2. Run full test suite
3. Verify production behavior unchanged
4. Commit
5. Repeat

**Why**: Catch bugs immediately, not after 10 changes

### 3. Fix Bugs Through Structure

**Example**: Indentation bug in 379-line method

**Bad approach**: Manually fix indentation in giant method  
**Good approach**: Extract method to smaller function where indentation is obvious

```python
# Before: Bug hidden in 379 lines
def _process_wave(self, ...):
    for posting in postings:  # Line 948
        # ... 50 lines of setup ...
    
    try:  # Line 1000 - WRONG INDENTATION!
        # ... 200 lines of execution ...

# After: Bug obvious in focused function
class WaveProcessor:
    def process_wave(self, ...):
        for posting in postings:
            try:  # Correct indentation obvious
                # ... execution logic ...
```

**Lesson**: Proper structure prevents bugs naturally

---

## Common Refactoring Patterns

### Pattern 1: Extract Data Class

**When**: Data is passed around as dict or multiple parameters

**Before**:
```python
def process_posting(posting_id, outputs, execution_sequence, is_terminal, ...):
    # 8 parameters - hard to track
```

**After**:
```python
@dataclass
class PostingState:
    posting_id: int
    outputs: Dict[int, str]
    execution_sequence: List[int]
    is_terminal: bool

def process_posting(posting: PostingState):
    # Single parameter, clear contract
```

**Benefits**:
- Type safety
- Clear data structure
- Easier to add fields
- Self-documenting

### Pattern 2: Extract Processing Logic

**When**: Single method exceeds ~200 lines

**Before**:
```python
def _process_wave(self, ...):
    # 379 lines mixing:
    # - Batch chunking
    # - Per-posting execution
    # - Error handling
    # - State updates
    # - Logging
```

**After**:
```python
class WaveProcessor:
    def process_wave(self, ...):
        # 19 lines - orchestration only
        return self._process_chunk(postings)
    
    def _process_chunk(self, postings):
        for posting in postings:
            self._process_single_posting(posting)
    
    def _process_single_posting(self, posting):
        # Focused logic, easy to test
```

**Benefits**:
- Single responsibility per method
- Easier to test
- Obvious control flow

### Pattern 3: Extract Utility Class

**When**: Group of related utility functions

**Before**:
```python
def render_prompt(template, posting, workflow_def):
    # Template rendering logic

def get_variation_data(workflow_def, execution_order):
    # Extract variation data

# Functions scattered across file
```

**After**:
```python
class PromptRenderer:
    def __init__(self, workflow_definition):
        self.workflow_definition = workflow_definition
    
    def render(self, template, posting, execution_order):
        variation_data = self._get_variation_data(execution_order)
        return self._substitute_template(template, posting, variation_data)
```

**Benefits**:
- Related functions grouped
- Shared state (workflow_definition)
- Reusable across modules

---

## Technical Debt Management

### When to Remove Technical Debt

**✅ REMOVE NOW** if debt causes:
- Active bugs (indentation bug example)
- Performance issues (connection pooling bug)
- Developer confusion (dual-write complexity)

**⏸️ DOCUMENT AND DEFER** if debt is:
- Cosmetic naming issues (canonical_name)
- Working but suboptimal (chunk_size=35)
- Requires migration (deprecated tables)

### How to Remove Dual-Write Complexity

**Problem**: Code writes to multiple tables for same data

**Solution**: Event sourcing with projections

**Before**:
```python
def save_output(posting, output):
    # Write to 3 places
    cursor.execute("INSERT INTO llm_interactions ...")
    cursor.execute("INSERT INTO conversation_runs ...")
    cursor.execute("INSERT INTO posting_state_checkpoints ...")
    
    # Schema mismatches, constraint violations, complexity
```

**After**:
```python
def save_output(posting, output):
    # Write to event store only
    event_store.append_event(
        event_type='script_execution_completed',
        aggregate_id=posting.posting_id,
        event_data={'output': output}
    )
    # Projections auto-update from events
```

**Benefits**:
- Single source of truth
- No schema mismatches
- Simpler code
- Full audit trail

---

## File Size Guidelines

### Target Sizes

| File Type | Target Size | Max Size | Action if Exceeded |
|-----------|-------------|----------|-------------------|
| Data class | 20-50 lines | 100 lines | Extract to separate classes |
| Utility module | 100-300 lines | 500 lines | Split by responsibility |
| Core logic | 300-600 lines | 1,000 lines | Extract processors/handlers |
| Orchestrator | 600-1,200 lines | 1,500 lines | Delegate to specialized classes |

### Warning Signs

**File needs refactoring if:**
- ❌ Single method exceeds 200 lines
- ❌ File exceeds 1,500 lines
- ❌ Can't understand code flow without scrolling
- ❌ Failed 3+ times to fix bug due to complexity
- ❌ Multiple people afraid to touch file

---

## Testing Strategy

### Unit Tests

**What to test**: Extracted classes in isolation

```python
def test_wave_processor_success():
    processor = WaveProcessor(...)
    postings = [PostingState(posting_id=1, ...)]
    
    result = processor.process_wave(
        conversation_id=1,
        postings=postings,
        execute_actor_func=mock_executor
    )
    
    assert result == 1  # 1 posting processed
```

**Benefits**:
- Fast (no database, no network)
- Focused (one class at a time)
- Reliable (no external dependencies)

### Integration Tests

**What to test**: End-to-end workflow with real database

```python
def test_full_workflow_execution():
    # Run workflow with 10 postings
    workflow = WorkflowExecutor(workflow_id=3001)
    workflow.run()
    
    # Verify all postings processed
    assert count_completed_postings() == 10
```

**Benefits**:
- Catches integration bugs
- Validates database interactions
- Proves system works end-to-end

### When to Write Tests

**Recommended order**:
1. **Before refactoring**: Write integration tests for current behavior
2. **During refactoring**: Write unit tests for extracted classes
3. **After refactoring**: Verify integration tests still pass

**Why**: Integration tests catch regressions, unit tests prevent future bugs

---

## Common Pitfalls

### Pitfall 1: Over-Engineering

**❌ Don't**:
```python
class PostingStateFactory:
    def create_posting_state(self):
        return PostingStateBuilder().with_id(1).with_outputs({}).build()

# 5 classes for simple data structure
```

**✅ Do**:
```python
@dataclass
class PostingState:
    posting_id: int
    outputs: Dict = field(default_factory=dict)

# Simple, clear, sufficient
```

**Rule**: Add complexity only when needed

### Pitfall 2: Premature Abstraction

**❌ Don't**: Extract classes before understanding patterns

**✅ Do**: 
1. Wait until pattern repeats 2-3 times
2. Extract common code to shared class
3. Refactor callers to use new class

**Rule**: "Three strikes and you refactor"

### Pitfall 3: Breaking API Contracts

**Problem**: Refactoring changes public API

**Before**:
```python
# Other code depends on this signature
def process_wave(conversation_id, postings):
    ...
```

**Bad refactoring**:
```python
# BREAKING CHANGE - other code breaks
def process_wave(self, conversation_id, posting_list, config):
    ...
```

**Good refactoring**:
```python
# Maintain API, delegate internally
def process_wave(conversation_id, postings):
    processor = WaveProcessor()
    return processor.process_wave(conversation_id, postings)
```

**Rule**: Keep public APIs stable during refactoring

---

## Rollback Strategy

### Before Refactoring

1. **Backup current code**:
```bash
cp workflow_executor.py workflow_executor_pre_refactor_backup.py
```

2. **Tag commit**:
```bash
git tag pre-refactor-nov19-2025
git push --tags
```

3. **Document rollback plan** in commit message

### If Production Breaks

**Quick rollback** (< 2 minutes):
```bash
# 1. Stop service
pkill -f workflow_executor

# 2. Restore old code
mv workflow_executor.py workflow_executor_refactored.py
mv workflow_executor_pre_refactor_backup.py workflow_executor.py

# 3. Restart service
nohup python3 -m core.workflow_executor --workflow 3001 &
```

**Proper fix** (after rollback):
1. Investigate issue in dev environment
2. Fix bug
3. Test thoroughly
4. Re-deploy refactored version

---

## Metrics for Success

### Code Quality Metrics

**Before refactoring**:
- Main file: 1,465 lines
- Largest method: 379 lines  
- Cyclomatic complexity: ~50
- Test coverage: 0%

**After refactoring**:
- Main file: 1,088 lines (-26%)
- Largest method: 19 lines (delegation)
- Cyclomatic complexity: ~15
- Test coverage: 80%+

### Production Metrics

**Before**:
- Postings processed: 59/2,062 (2.8%)
- Failure rate: 97.2%
- Bug fix attempts: 5 failed manual fixes

**After**:
- Postings processed: 2,062/2,062 (100%)
- Failure rate: 0%
- Bug fix: Natural fix through proper structure

---

## Lessons Learned

### What Worked

1. **Incremental extraction**: One class at a time, test after each
2. **Bug fix through structure**: Indentation bug disappeared naturally
3. **Event sourcing commitment**: Removed dual-write complexity
4. **Production validation**: Ran full workflow after each change

### What We'd Do Differently

1. **Write tests first**: Should have had integration tests before starting
2. **Analyze dependencies earlier**: Should have mapped table dependencies up front
3. **Smaller commits**: Could have committed after each class extraction
4. **Capture baseline metrics**: Should have measured performance before refactoring

### Key Takeaways

1. **File size matters**: 1,465-line files are unmanageable; 358-line classes are reviewable
2. **Structure prevents bugs**: Indentation bugs hide in large methods
3. **Event sourcing simplifies**: Removing dual-writes eliminates bug classes
4. **Extract, don't rewrite**: Modular refactoring safer than big-bang rewrites

---

## Quick Reference Checklist

Before refactoring:
- [ ] Write integration tests for current behavior
- [ ] Backup current code
- [ ] Tag commit for rollback
- [ ] Document rollback plan

During refactoring:
- [ ] Extract one class at a time
- [ ] Write unit tests for extracted class
- [ ] Run integration tests after extraction
- [ ] Verify production metrics unchanged
- [ ] Commit after each successful extraction

After refactoring:
- [ ] Achieve 80%+ test coverage
- [ ] Run full workflow in production
- [ ] Monitor for 24-48 hours
- [ ] Archive backup code after validation
- [ ] Update documentation

---

## References

- **Example Refactoring**: See `/docs/archive/case_studies/workflow_executor_refactoring_nov2025.md`
- **Event Sourcing**: [EVENT_SOURCING_ARCHITECTURE.md](EVENT_SOURCING_ARCHITECTURE.md)
- **Testing Guide**: [../TESTING_GUIDE.md](../TESTING_GUIDE.md)
- **Production Lessons**: [../archive/conversations/REFACTORING_NOV19_2025.md](../archive/conversations/REFACTORING_NOV19_2025.md)

---

**Last Updated**: November 19, 2025  
**Based On**: Production refactoring of workflow_executor.py  
**Status**: Best practices extracted from real experience ✅
