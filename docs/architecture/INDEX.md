# Architecture Documentation Index

**Last Updated:** December 7, 2025  
**Maintainer:** Arden  

---

## Core Architecture (Read These First)

These documents define how Turing works. They're authoritative.

| Document | Purpose | Lines | Status |
|----------|---------|-------|--------|
| [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md) | Wave processing, actor execution, branching | 1260 | ✅ Updated Dec 7 |
| [WORKFLOW_STATE_ARCHITECTURE.md](WORKFLOW_STATE_ARCHITECTURE.md) | State management, event sourcing pattern | 963 | ✅ Active |
| [CHECKPOINT_SYSTEM.md](CHECKPOINT_SYSTEM.md) | Crash recovery, state restoration | 623 | ✅ Active |
| [DATA_LIFECYCLE.md](DATA_LIFECYCLE.md) | How data flows through the system | 656 | ✅ Active |

---

## Cookbooks (How-To Guides)

Step-by-step guides for common tasks.

| Document | Purpose | Lines | Status |
|----------|---------|-------|--------|
| [WORKFLOW_CREATION_COOKBOOK.md](WORKFLOW_CREATION_COOKBOOK.md) | Create new workflows | 1111 | ✅ Active |
| [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) | Debug workflow issues | 1306 | ✅ Active |

---

## Design Patterns

Reusable patterns and best practices.

| Document | Purpose | Lines | Status |
|----------|---------|-------|--------|
| [EVENT_SOURCING_ARCHITECTURE.md](EVENT_SOURCING_ARCHITECTURE.md) | Event-driven state management | 446 | ✅ Active |
| [EVENT_SOURCING_PRACTICES.md](EVENT_SOURCING_PRACTICES.md) | Practical event sourcing tips | 803 | ✅ Active |
| [EVENT_INVALIDATION.md](EVENT_INVALIDATION.md) | How to invalidate bad events | 379 | ✅ Active |
| [PROJECTION_REBUILD.md](PROJECTION_REBUILD.md) | Rebuilding state from events | 531 | ✅ Active |
| [REFACTORING_BEST_PRACTICES.md](REFACTORING_BEST_PRACTICES.md) | Safe code refactoring | 500 | ✅ Active |

---

## Proposals & RFCs

Ideas under consideration or partially implemented.

| Document | Purpose | Lines | Status |
|----------|---------|-------|--------|
| [ENTITY_REGISTRY.md](ENTITY_REGISTRY.md) | Entity Registry: universal entity/alias/hierarchy pattern | 439 | ✅ Active (Dec 8) |
| [HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md) | Human task queue design | 368 | 🟡 Proposal |
| [RFC_WORKFLOW_AS_INTERACTION.md](RFC_WORKFLOW_AS_INTERACTION.md) | Workflow runs as logged events | 249 | ✅ Phase 1 Done |
| [TIMEOUT_ARCHITECTURE.md](TIMEOUT_ARCHITECTURE.md) | Timeout handling strategies | 696 | 🟡 Proposal |

---

## Specialized Topics

Focused documentation for specific subsystems.

| Document | Purpose | Lines | Status |
|----------|---------|-------|--------|
| [CLEAN_MODEL_ROUTING.md](CLEAN_MODEL_ROUTING.md) | Model selection per step | 495 | ✅ Active |
| [DATA_MANAGEMENT_PRINCIPLES.md](DATA_MANAGEMENT_PRINCIPLES.md) | Data philosophy ("Damn Book") | 375 | ✅ Active |
| [TEST_DATA_MANAGEMENT.md](TEST_DATA_MANAGEMENT.md) | Test fixture strategies | 406 | ✅ Active |
| [DOCUMENTATION_PHILOSOPHY.md](DOCUMENTATION_PHILOSOPHY.md) | What to document, what to delete | 402 | ✅ Active |

---

## Post-Mortems

Lessons from past incidents. Keep for reference.

| Document | Purpose | Lines | Status |
|----------|---------|-------|--------|
| [IDEMPOTENCY_BUG_POSTMORTEM.md](IDEMPOTENCY_BUG_POSTMORTEM.md) | Nov 21 model routing failure | 676 | 📚 Historical |

---

## Architecture Decision Records (ADRs)

Located in `decisions/`. Each captures a specific technical decision.

| ADR | Decision | Status |
|-----|----------|--------|
| [001_priority_based_branching.md](decisions/001_priority_based_branching.md) | Branch execution by priority | ✅ Active |
| [008_global_batch_mode.md](decisions/008_global_batch_mode.md) | Global (non-posting) workflows | ✅ Active |
| [009_format_model_selection.md](decisions/009_format_model_selection.md) | Format step model choice | ✅ Active |
| [010_extraction_model_selection.md](decisions/010_extraction_model_selection.md) | Extraction model benchmarks | ✅ Active |
| [011_save_all_skills.md](decisions/011_save_all_skills.md) | Save all skills pattern | ✅ Active |
| [012_indestructible_workflows.md](decisions/012_indestructible_workflows.md) | Never delete workflow runs | ✅ Active |

---

## Stale Docs (Need Update or Archive)

Run `python3 tools/check_stale_docs.py` to find docs referencing updated code.

As of Dec 5, 2025:
- Most docs reference Nov 2025 code versions
- Core architecture is stable; minor updates needed for new patterns

---

## Quick Reference: Production Workflows

| Workflow | Purpose | Status | Key Files |
|----------|---------|--------|-----------|
| WF3001 | Job posting extraction | ✅ 100% (1,689) | `scripts/prod/run_workflow_3001.py` |
| WF1125 | Multi-agent profile analysis | 🔄 Testing | `scripts/prod/run_workflow_1125.py` |
| WF3004 | Entity Registry reorganization | 🔄 Active | `scripts/prod/run_workflow_3004.py` |

---

## Key Code Files

These are the core implementation files. If the doc and code disagree, **code wins**.

| File | Purpose | Last Modified |
|------|---------|---------------|
| `core/wave_runner/runner.py` | Wave execution engine (41KB) | Dec 4, 2025 |
| `core/wave_runner/interaction_creator.py` | Child creation, parallel fan-out (36KB) | Dec 5, 2025 |
| `core/wave_runner/executors.py` | Actor execution (14KB) | Dec 5, 2025 |
| `core/wave_runner/database.py` | DB operations (17KB) | Dec 4, 2025 |

### Key Script Actors (Recently Updated)

| Actor | Purpose | Size |
|-------|---------|------|
| `actors/skill_taxonomy_saver.py` | Apply ALIAS/NEW/SPLIT/SKIP decisions | 15KB |
| `actors/profile_skills_saver.py` | Save profile skills with fuzzy matching | 13KB |
| `actors/posting_skills_saver.py` | Save posting skills to taxonomy | 12KB |
| `actors/db_job_fetcher.py` | Fetch jobs from external APIs | 23KB |

---

*"Schema + Code = Truth. Docs are for understanding, not authority."*
