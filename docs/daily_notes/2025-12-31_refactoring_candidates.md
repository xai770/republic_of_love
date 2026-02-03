# Python Files: Refactoring Analysis for Arden

**Date**: 2025-12-31  
**Purpose**: Help Arden identify where to split large files

## The Big Ones (>500 lines)

| File | Lines | Methods | Verdict |
|------|-------|---------|---------|
| qa_audit.py | 1393 | 21 | 🔴 **SPLIT NOW** |
| runner.py | 1065 | 18 | 🟡 Manageable but watch |
| interaction_creator.py | 1065 | 8 | 🟢 OK - complex but coherent |
| turing.py | 1054 | ~25 | 🟡 Could extract metrics modules |
| turing_daemon.py | 1042 | ? | 🟡 Needs review |
| turing_orchestrator.py | 850 | ? | 🟢 Probably fine |

---

## 🔴 qa_audit.py - NEEDS REFACTORING

**Lines**: 1393  
**Location**: [scripts/qa/qa_audit.py](scripts/qa/qa_audit.py)

### Problem: God Class

`QAAudit` class does EVERYTHING:
- Discovery sampling (6 dimensions)
- Finding management  
- Run tracking
- Reporting
- Remediation
- Reprocessing

### Current Structure

```
QAAudit class (1200+ lines)
├── create_run, complete_run (run lifecycle)
├── create_interaction, add_finding (RAQ compliance)
├── discover_summaries (250 lines!) - 6-dimension sampling for summaries
├── discover_skills (250 lines!) - 6-dimension sampling for skills
├── show_status
├── review_findings
├── remediate_findings
├── _classify_finding, _get_classification_reason, _apply_fixes
├── _dismiss_false_positives
├── generate_report (225 lines!)
└── reprocess_remediated
```

### Proposed Split

```
scripts/qa/
├── qa_audit.py          # CLI entry point + QAAudit thin coordinator (~200 lines)
├── discovery.py         # DiscoverySampler - 6-dimension sampling (~300 lines)
├── findings.py          # FindingManager - CRUD + remediation (~250 lines)  
├── reporting.py         # ReportGenerator - markdown/stats (~250 lines)
└── checks.py            # Individual check functions (~200 lines)
```

### Why This Split?

1. **discovery.py**: `discover_summaries` and `discover_skills` share 90% of their code (6-dimension sampling). Extract to `DiscoverySampler` with configurable target.

2. **findings.py**: `add_finding`, `remediate_findings`, `_classify_finding`, `_apply_fixes`, `_dismiss_false_positives` - all finding lifecycle.

3. **reporting.py**: `generate_report` is 225 lines on its own. Pure output formatting, no business logic.

4. **checks.py**: The actual quality checks (similarity, length thresholds, etc.)

---

## 🟡 runner.py - WATCH BUT OK

**Lines**: 1065  
**Location**: [core/wave_runner/runner.py](core/wave_runner/runner.py)

### Current Structure

```
WaveRunner class
├── __init__ (70 lines - lots of setup)
├── _setup_signal_handlers
├── _start/_stop/_heartbeat_loop/_update_heartbeat (50 lines)
├── _mark_workflows_interrupted
├── _update_progress_state
├── run (main loop, ~125 lines)
├── _execute_batch (120 lines)
├── _check_should_skip
├── _execute_interaction (300 lines!) ← biggest method
├── _execute_ai_model, _execute_script, _execute_human
├── _generate_trace_report
└── _extract_semantic_state
```

### Verdict: Manageable

- One clear responsibility: execute workflow interactions
- Long methods but they're complex logic, not repetition
- Already extracted: `WorkGrouper`, `ModelCache`, `InteractionCreator`, `DatabaseHelper`

### Possible Improvements (Low Priority)

1. Extract `_execute_interaction` to separate class if it grows more
2. The heartbeat stuff could become `HeartbeatManager` (~100 lines)
3. Signal handling could be mixin or decorator

**Don't refactor unless adding new features makes it worse.**

---

## 🟢 interaction_creator.py - LEAVE ALONE

**Lines**: 1065  
**Location**: [core/wave_runner/interaction_creator.py](core/wave_runner/interaction_creator.py)

### Why It's Fine

Only 8 methods:
- `_get_ancestor_outputs`
- `build_prompt_from_template` (300 lines but complex template logic)
- `check_parallel_group_complete`
- `get_wait_for_group_info`
- `get_next_conversations`
- `_evaluate_branch_condition`
- `create_child_interactions`

This is **inherently complex** work:
- Walking ancestor chains
- Template variable substitution  
- Parallel group coordination
- Branch condition evaluation

Splitting would scatter related logic across files and make debugging harder.

---

## 🟡 turing.py - METRICS DASHBOARD

**Lines**: 1054  
**Location**: [scripts/turing.py](scripts/turing.py)

### Structure

~25 standalone functions:
- `get_pipeline_status`
- `get_skill_progress`
- `get_hierarchy_progress`
- `get_interaction_progress`
- `get_throughput`
- `get_latency`
- `get_skill_kpis`
- `get_wf3006_progress`
- ... many more

### Verdict: Could Split by Domain

```
scripts/
├── turing.py           # CLI + main display (~200 lines)
├── metrics/
│   ├── pipeline.py     # get_pipeline_status, get_interaction_progress
│   ├── skills.py       # get_skill_progress, get_skill_kpis
│   ├── performance.py  # get_throughput, get_latency
│   └── workflows.py    # get_wf3006_progress, etc.
```

**Low priority** - it works fine, just a big dashboard script.

---

## Priority Order for Arden

1. **qa_audit.py** - Split now. God class, repetitive patterns, hard to test
2. **turing.py** - Split when adding new metrics (natural break point)
3. **runner.py** - Extract heartbeat if adding new lifecycle features
4. **Leave interaction_creator.py alone** - complexity is inherent, not structural

---

## Signs a File Needs Splitting

✅ **Split when:**
- Same pattern repeated 2+ times (6-dimension sampling)
- Methods over 200 lines
- Class does multiple unrelated things
- Hard to name the file's single responsibility
- Tests require mocking half the class

❌ **Don't split when:**
- Complexity is inherent (template substitution)
- Methods are long but not repetitive
- Splitting would scatter related logic
- "It's long" is the only complaint

---

*"The way out is subtraction, not addition" - but don't subtract cohesion.*
