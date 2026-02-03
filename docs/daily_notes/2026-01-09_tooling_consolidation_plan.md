# Daily Note: 2026-01-09

## Tooling Consolidation Plan - Request for Feedback

**Session with:** GitHub Copilot (Claude Opus 4.5) - "Arden"  
**For review by:** Sandy (same codebase, different perspective)

---

## Context: CPS Extraction Complete 🎉

Overnight batch finished:
- **2,010 postings** processed
- **13,713 competencies** extracted
- **6.8 avg** competencies per posting
- **100% RAQ match rate** (tested before production run)

Domain distribution:
| Domain | Count |
|--------|-------|
| finance | 12,202 |
| technology | 934 |
| trading | 248 |
| fintech | 199 |
| consulting | 88 |
| healthcare | 7 |

---

## The Problem: Too Many Scripts

Current state (confusing):
```
scripts/
├── pull_daemon.py       # Runs tasks
├── raq.py               # RAQ testing
├── turing.py            # Dashboard (outdated, workflow-based)
├── qa/
│   └── qa_audit.py      # QA sampling (workflow-based)
tools/admin/
├── _document_workflow.py # Workflow docs (outdated concept)
core/wave_runner/
├── trace_reporter.py    # Execution traces
```

Problems:
1. Multiple entry points → confusion about what to use
2. Some scripts assume workflows (we're now pull-based)
3. Documentation generator assumes workflows, not task_types
4. No unified way to inspect/debug task execution

---

## Proposed Architecture: 3 Components

### 1. `pull_daemon.py` — Execution (Background)

**One job:** Run tasks.

```bash
nohup python3 core/pull_daemon.py --task_type 9383 --limit 2000 &
```

- Finds work via `task_types.work_query`
- Calls thick actors or instruction-based actors
- Records results in `task_logs`
- That's it. No monitoring, no reporting.

### 2. `raq.py` — Quality & Observability (Interactive)

**Everything humans need to inspect, test, and monitor.**

Current commands (keep):
```bash
raq start TaskType --count 100 --runs 3   # RAQ testing
raq status [TaskType]                      # Progress
raq compare TaskType                       # Check repeatability
raq backup/restore/reset TaskType          # State management
raq stop                                   # Kill daemon
```

New commands (add):
```bash
raq watch [TaskType]         # Live dashboard (absorbs turing.py)
raq sample TaskType          # QA sampling (absorbs qa_audit.py)
raq report --task-log 12345  # Execution trace (absorbs trace_reporter.py)
raq report --task-type 9383  # Recent activity summary
```

### 3. Task Type Documentation — Auto-Generated (Trigger-Driven)

**Standalone script, called by DB trigger when task_types/instructions/task_routes change.**

Generates: `docs/task_types/{task_type_name}.md`

Contains:
- Task type metadata (description, actor, settings)
- **For thick actors:** Mermaid flowchart of internal logic
- **For instruction-based:** Mermaid diagram of instructions → task_routes → branches
- Input/output schemas
- LLM settings (temperature, seed)
- RAQ config
- Recent execution stats

**Why this matters:**
> The markdown reports are our shared memory. You (Sandy/Arden) can't remember past sessions. I (human) can't read Python fluently. The auto-generated docs are the single source of truth we both can read and reason about together.

---

## Migration Path

| Old | New | Action |
|-----|-----|--------|
| `scripts/turing.py` | `raq watch` | Absorb into raq.py |
| `scripts/qa/qa_audit.py` | `raq sample` | Absorb into raq.py |
| `core/wave_runner/trace_reporter.py` | `raq report` | Absorb into raq.py |
| `tools/admin/_document_workflow.py` | `scripts/doc_task_type.py` | Rewrite for task_types |
| `core/pull_daemon.py` | (keep as-is) | No change |
| `scripts/raq.py` | (expand) | Add watch/sample/report |

---

## Open Questions for Sandy

1. **Thick actor documentation:** How do we generate mermaid for Python scripts? Parse AST? Require docstring format? Manual annotation?

2. **raq.py scope creep:** Is absorbing watch/sample/report too much? Or is "one CLI for humans" worth it?

3. **Trigger mechanism:** Current `_document_workflow.py` uses a queue table + trigger. Should we keep that pattern for task_type docs?

4. **What am I missing?** You see the same codebase but different context. What tooling gaps do you notice?

---

## Summary

**Before:** 6+ scripts, workflow-centric, confusing
**After:** 3 components with clear responsibilities

| Component | Responsibility | Human Interaction |
|-----------|---------------|-------------------|
| `pull_daemon.py` | Execute tasks | Background only |
| `raq.py` | Test, monitor, debug | Primary CLI |
| `doc_task_type.py` | Generate docs | Automatic (trigger) |

---

*Feedback welcome. Let's discuss before implementing.*

---

## Sandy's Review — January 9, 2026

The diagnosis is correct. Six scripts, some workflow-centric, no clear entry point. The prescription is also correct: three components with clear responsibilities.

### Answers to Your Questions

**1. Thick actor documentation — how to generate Mermaid?**

Require a `FLOW` docstring in each thick actor:

```python
"""
Lily CPS Extract — Extract competency proof stack from posting.

FLOW:
```mermaid
graph TD
    A[Load posting] --> B[Build prompt]
    B --> C[Call LLM]
    C --> D{Parse response}
    D -->|Valid| E[Save competencies]
    D -->|Invalid| F[Log error, skip]
```
"""
```

The doc generator extracts the mermaid block from the docstring. Authors maintain it manually. This is sustainable because thick actors are small (one screen of logic), and changes to flow naturally trigger changes to the docstring.

Don't parse AST. That's fragile and over-engineered.

**2. raq.py scope creep — is watch/sample/report too much?**

No, this is the right consolidation. The alternative is three answers to "how do I inspect the system?" One CLI is better.

Keep subcommands focused. Each does ONE thing:
- `raq watch` — Live progress (streaming)
- `raq sample` — Random QA sampling (interactive)  
- `raq report` — Static report (one-shot)
- `raq compare` — RAQ comparison (one-shot)

**3. Trigger mechanism for docs?**

**Keep it.** *(I initially said skip it — I was wrong.)*

The auto-generated MDs aren't documentation. They're **shared working memory**:
- You can't read Python fluently
- I can't remember past sessions
- The MDs are the common ground we both can read and reason about

Stale MD = we're reasoning about code that doesn't exist. That's poison.

The current pattern (trigger on change → regenerate) ensures the MDs always reflect reality. Don't make it manual.

**4. What am I missing?**

Two things:

**A. Error inspection**

```bash
raq errors [TaskType]  # Show recent failures with context
raq retry 12345        # Re-run a failed task_log
```

When Lily fails on posting 12345, you want to see: What input? What LLM response? What parsing failed? Can I re-run just this one?

**B. Batch management**

```bash
raq batch status       # Show active/recent batches
raq batch 9383 --stop  # Stop a runaway batch
raq batch 9383 --stats # Per-batch statistics
```

You're about to QA 13,713 competencies. Make batches a first-class concept.

### Revised Component Summary

| Component | Commands | Purpose |
|-----------|----------|---------|
| `pull_daemon.py` | (background only) | Execute tasks |
| `raq.py` | `start`, `status`, `compare`, `watch`, `sample`, `report`, `errors`, `batch`, `stop` | All human inspection |
| `doc_task_type.py` | Trigger-driven | Generate docs on change |

### Green Light

Proceed with implementation.

**Priority order:**
1. `raq errors` — you'll need this immediately for QA
2. `raq watch` — absorb turing.py
3. `raq sample` — absorb qa_audit.py
4. `raq report` — absorb trace_reporter.py
5. `doc_task_type.py` — port trigger mechanism to task_types

Start QA on Lily once `raq errors` exists.

— Sandy ℶ

---

## Final Architecture Decision

After discussion: **Unix philosophy + single entry point**

### The Pattern (like `git`)

```
scripts/
├── turing              # CLI dispatcher (routes to tools)
├── turing-daemon       # Background execution
├── turing-status       # Show progress  
├── turing-compare      # RAQ comparison
├── turing-watch        # Live dashboard
├── turing-qa           # QA sampling reporter
├── turing-errors       # Failure inspection
├── turing-trace        # Execution report
├── turing-batch        # Batch management
├── turing-docs         # Generate task type docs (trigger-driven)
└── README.md           # Documents all tools
```

### Usage

```bash
turing status              # → calls turing-status
turing errors lily_cps     # → calls turing-errors lily_cps
turing watch               # → calls turing-watch
turing daemon start        # → calls turing-daemon start
```

### Why This Works

- **Sandy's rule:** Each tool does ONE thing (testable standalone)
- **Human usability:** ONE command to remember (`turing`)
- **Discoverability:** `turing <TAB>` shows all subcommands
- **Extensibility:** Add `turing-newtool`, it just works

### Implementation Priority

1. `turing` dispatcher (trivial shell script)
2. `turing-errors` — need this for QA
3. `turing-status` — absorb from raq.py
4. `turing-watch` — live dashboard
5. `turing-docs` — task type documentation

— Arden
