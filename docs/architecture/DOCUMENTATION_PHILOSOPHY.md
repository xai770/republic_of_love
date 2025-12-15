# Documentation Philosophy

**Created:** November 26, 2025  
**Status:** Core Principle  
**Context:** Recurring discussion about what to document and what to delete

---

## The Problem

We keep having the same conversation:
- "Should we document this?"
- "Is this document outdated?"
- "Do we delete old docs or keep them for history?"

**This document captures the decision ONCE so we stop revisiting it.**

---

## Core Principles

### 1. Schema and Code ARE the Documentation

**Primary sources of truth:**
```
✅ Database schema (with comments)
✅ Production code (with docstrings)
✅ Daily schema export (sql/schema_latest.sql)
✅ Generated documentation (workflow docs, trace reports)
✅ Architecture docs (patterns, decisions, principles)
```

**These speak for themselves. Trust them.**

---

### 2. Delete Outdated Documents Aggressively

**Rule:** If a document is outdated, **DELETE IT** (not archive, not mark outdated, DELETE).

**Why:**
- We have backups (Documents_Versions/ has full history)
- We backup database daily (backups/ directory)
- Outdated docs cause confusion
- Keeping focus is key

**Example (Migration 044, Nov 24):**
```bash
# DELETED (not archived):
- TEMPLATE_SUBSTITUTION_BUG.md (anti-pattern, fixed)
- MIGRATION_050_SUMMARY.md (historical, irrelevant)
- DATABASE_SCHEMA.md (use live schema instead)
```

**If someone needs historical context:**
- Check Documents_Versions/ for old version
- Check git history
- Check database backups

---

### 3. Architecture Documents Are Permanent

**Keep forever (in docs/architecture/):**
- Architectural Decision Records (ADRs) - WHY we made choices
- Core patterns (Priority-based branching, Event sourcing, etc.)
- Philosophy documents (this one!)
- System boundaries (what system does, what it doesn't)

**These don't "get outdated" - they record historical decisions.**

**When decision changes:**
- Update ADR status (Accepted → Superseded)
- Create NEW ADR explaining why we changed
- Link old ADR to new ADR

**Never delete ADRs.** They're the institutional memory.

---

### 4. Generated Documentation Is Disposable

**Auto-generated docs (regenerate anytime):**
- Workflow documentation (from schema via _document_workflow.py)
- Trace reports (from workflow runs via generate_retrospective_trace.py)
- Schema exports (daily cron job)

**Don't hand-edit these.** They're meant to be regenerated.

**If something is wrong:**
- Fix the schema (source of truth)
- Regenerate the documentation

---

### 5. Focus Over Comprehensiveness

**Document the minimum needed for:**
1. Understanding WHY (ADRs)
2. Understanding PATTERNS (architecture docs)
3. Onboarding NEW people/agents (cheat sheets, quickstarts)

**Don't document:**
- How to use standard tools (psql, git, python)
- Obvious code (self-explanatory functions)
- Temporary solutions (if it's temporary, it shouldn't exist)
- Historical migrations (schema is current state, backups are history)

**Principle:**
> **If schema + code + 5 architecture docs don't explain it, it's too complex. Simplify the system, not the documentation.**

---

## The Documentation Hierarchy

### Tier 1: Source of Truth (Never Delete)

```
database/
├── schema (with COMMENT ON TABLE)
├── migrations/ (sequential, numbered)
└── backups/ (daily exports)

code/
├── core/ (production code with docstrings)
└── tests/ (real data tests)

sql/
└── schema_latest.sql (daily export, symlink)
```

**These ARE the system. Documentation derives from these.**

---

### Tier 2: Architecture (Keep Forever)

```
docs/architecture/
├── decisions/ (ADRs - WHY we chose X)
├── patterns/ (reusable architectural patterns)
├── DOCUMENTATION_PHILOSOPHY.md (this file)
└── README.md (architecture index)
```

**These explain WHY the system is designed this way.**

---

### Tier 3: Generated (Regenerate Anytime)

```
docs/workflows/
├── 3001_complete_job_processing_pipeline.md (generated from schema)
└── ... (other workflow docs)

reports/
├── trace_run_174.md (generated from execution)
└── ... (other traces)

sql/
├── schema_latest.sql (symlink to daily export)
└── schema_export_YYYYMMDD.sql (daily exports, 7-day retention)
```

**Don't hand-edit. Regenerate instead.**

---

### Tier 4: Operational (Update as Needed)

```
docs/
├── __sandy_cheat_sheet.md (context for Sandy)
├── __arden_cheat_sheet.md (context for Arden)
├── model_optimization_cookbook.md (benchmarking methodology)
└── TASK_*.md (task assignments for agents)
```

**These change frequently. Keep current, delete old tasks when done.**

---

### Tier 5: Profiles & Research (Keep Until Superseded)

```
docs/llm_profiles/
├── INDEX.md (model atlas)
├── qwen2_5_7b.md (individual profiles)
└── DYNATAX_RECOMMENDATIONS.md (task-specific guidance)
```

**These age gracefully. Update when new benchmarks run.**

---

## Decision Tree: Should I Document This?

**Start here:**

```
Is it a WHY decision (architecture, trade-offs)?
├─ YES → Write ADR (docs/architecture/decisions/)
└─ NO ↓

Is it a reusable PATTERN (other workflows can use)?
├─ YES → Document pattern (docs/architecture/patterns/)
└─ NO ↓

Is it GENERATED from schema/execution?
├─ YES → Write generator script, regenerate as needed
└─ NO ↓

Is it needed for ONBOARDING (new person/agent)?
├─ YES → Add to cheat sheet or quickstart
└─ NO ↓

Is it TEMPORARY (will change in <1 month)?
├─ YES → Put in task doc (TASK_*.md), delete when done
└─ NO ↓

Don't document it. Trust schema + code.
```

---

## Backup Strategy (Want to Go Back in Time?)

### Documents
```
Documents_Versions/
└── ty_learn/
    └── docs/
        └── [full history of all docs]
```

**Git is not enough.** We copy entire docs/ directory periodically.

**Why:** Sometimes we delete files. Git history is hard to browse. Documents_Versions is simple folder navigation.

### Database
```
backups/
├── by_full_YYYYMMDD_HHMMSS.backup (daily full backup)
├── by_data_only_YYYYMMDD_HHMMSS.backup (daily data backup)
└── by_pre_migration_NNN_YYYYMMDD_HHMMSS.sql (before each migration)
```

**Daily cron job:** 3:00 AM full backup, 7-day retention

**Before every migration:** Explicit backup with migration number in filename

---

## When to Update This Philosophy

**Update when:**
- We discover this philosophy doesn't work
- We add new documentation tier
- We change backup strategy

**Don't update for:**
- Examples of documents (those are illustrative)
- Minor wording tweaks
- Typos

**This document should be stable.** If you're updating it often, something is wrong with the process.

---

## Practical Examples

### Example 1: New Workflow Created

**DO:**
```bash
# Schema first (source of truth)
INSERT INTO workflows (workflow_name, ...) VALUES (...);
INSERT INTO workflow_conversations (...) VALUES (...);

# Generate documentation
python3 tools/_document_workflow.py 3001

# Generated: docs/workflows/3001_complete_job_processing_pipeline.md
```

**DON'T:**
```bash
# Hand-write workflow documentation
vim docs/workflows/my_new_workflow.md  # ❌ WRONG
```

---

### Example 2: Database Migration

**DO:**
```bash
# Backup first
pg_dump turing > backups/by_pre_migration_045_$(date +%Y%m%d_%H%M%S).sql

# Apply migration
psql -U base_admin -d turing -f sql/migrations/045_add_benchmark_tables.sql

# Export new schema
pg_dump -U base_admin -d turing --schema-only > sql/schema_export_$(date +%Y%m%d).sql
ln -sf sql/schema_export_$(date +%Y%m%d).sql sql/schema_latest.sql

# Delete old migration docs (if any)
rm docs/MIGRATION_045_NOTES.md  # Not needed, schema + ADR are enough
```

**DON'T:**
```bash
# Keep migration notes as permanent docs
git add docs/MIGRATION_045_NOTES.md  # ❌ WRONG (clutters docs/)
```

---

### Example 3: Architecture Decision

**DO:**
```bash
# Write ADR
vim docs/architecture/decisions/001_priority_based_branching.md

# Reference in code
# core/wave_runner/interaction_creator.py
# See ADR-001 for branching pattern explanation
```

**DON'T:**
```bash
# Write long comment in code
# This uses priority-based branching which means that if two
# instruction_steps have the same priority they both execute
# in parallel but if they have different priorities only the
# highest priority executes and this was chosen because...
# [200 more lines of explanation]  # ❌ WRONG (put in ADR!)
```

---

### Example 4: Outdated Document Found

**DO:**
```bash
# Delete it
rm docs/OLD_SYSTEM_DESIGN.md

# Commit with explanation
git commit -m "Delete OLD_SYSTEM_DESIGN.md - outdated, schema is truth"

# If needed later, it's in Documents_Versions/
```

**DON'T:**
```bash
# Mark as outdated
echo "⚠️ OUTDATED - DO NOT USE" >> docs/OLD_SYSTEM_DESIGN.md
git add docs/OLD_SYSTEM_DESIGN.md  # ❌ WRONG (delete it!)

# Or move to archive/
mkdir docs/archive/
mv docs/OLD_SYSTEM_DESIGN.md docs/archive/  # ❌ WRONG (delete it!)
```

---

## Success Metrics

**Good documentation strategy:**
- ✅ Can onboard new agent in <1 hour (read cheat sheet + 2-3 ADRs)
- ✅ Can understand ANY decision by reading its ADR
- ✅ Can regenerate docs from schema at any time
- ✅ docs/ directory has <50 files (focus!)
- ✅ No confusion about "which doc is current?"

**Bad documentation strategy:**
- ❌ docs/ directory has 200+ files
- ❌ Multiple docs explain same thing differently
- ❌ Can't tell if doc is current without checking creation date
- ❌ Hand-maintaining generated docs
- ❌ Keeping outdated docs "just in case"

---

## The Philosophy in One Sentence

> **Schema and code are truth. ADRs explain why. Generated docs show reality. Everything else is noise. Delete noise aggressively.**

---

**Related Documents:**
- [ADR-001: Priority-Based Branching](decisions/001_priority_based_branching.md)
- [Architecture README](README.md)
- [Sandy's Cheat Sheet](../__sandy_cheat_sheet.md)

---

*This discussion captured once. Never repeat. Just reference this document.*
