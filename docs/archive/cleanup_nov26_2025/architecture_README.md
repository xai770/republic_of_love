# Turing Architecture Documentation

**Version**: 4.1  
**Last Updated**: 2025-11-25  
**Purpose**: Encyclopedia-style architecture reference for developers and AI assistants

**Status**: Updated for Wave Runner V2 with Workflow State + Traceability (Nov 25, 2025)

---

## 📚 Documentation Structure

This directory contains **timeless reference documentation**. Each file is an encyclopedia entry covering a specific subsystem with complete technical details, best practices, and examples.

### Core System Documentation

1. **[WORKFLOW_CREATION_COOKBOOK.md](WORKFLOW_CREATION_COOKBOOK.md)** ✅ Complete
   - Complete guide for building workflows
   - Step-by-step migration process
   - Checkpoint query patterns (database queries, NOT templates!)
   - Conversation tagging requirements
   - Pre-flight checklist and best practices

2. **[WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md)** ✅ Complete
   - How workflows run
   - Wave processing mechanics
   - Execution order grouping (Nov 2025 optimization)
   - Branching logic (⚠️ known bug: doesn't stop after first match)
   - Idempotency checks
   - **Workflow state management** (Nov 25: event-sourcing with semantic keys)
   - **Traceability system** (Nov 25: stores actual prompts sent to AI)

2a. **[WORKFLOW_STATE_ARCHITECTURE.md](WORKFLOW_STATE_ARCHITECTURE.md)** ✅ Production (Nov 25, 2025)
   - Event-sourcing pattern with JSONB state
   - Semantic keys vs conversation IDs
   - Variable substitution with workflow state
   - Idempotency integration
   - State-based data flow
   - Production-validated in Workflow 3001

3. **[CHECKPOINT_SYSTEM.md](CHECKPOINT_SYSTEM.md)** ✅ Complete
   - Crash recovery mechanics
   - State serialization
   - Checkpoint queries pattern (database, NOT in-memory)
   - Template substitution anti-pattern (AVOID!)
   - Why posting.outputs failed in production

4. **[EVENT_SOURCING_ARCHITECTURE.md](EVENT_SOURCING_ARCHITECTURE.md)** ✅ Complete
   - Pure event sourcing system
   - Event store, projections, snapshots
   - Event types and metadata
   - Python API and best practices
   - Migration strategy and performance tuning

5. **[REFACTORING_BEST_PRACTICES.md](REFACTORING_BEST_PRACTICES.md)** ✅ Complete
   - Safe code refactoring patterns
   - Extract vs rewrite strategies
   - File size guidelines
   - Testing strategies
   - Common pitfalls and rollback plans

6. **[CLEAN_MODEL_ROUTING.md](CLEAN_MODEL_ROUTING.md)** ✅ Production
   - Model selection and routing
   - Validated in Workflow 3001
   
7. **[EVENT_INVALIDATION.md](EVENT_INVALIDATION.md)** ✅ Production
   - Event invalidation patterns
   - Production-tested

8. **[PROJECTION_REBUILD.md](PROJECTION_REBUILD.md)** ✅ Production
   - Rebuilding projections from events
   - Validated in Workflow 3001

19. [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) ✅ Production
    - Troubleshooting workflows
    - **CRAWL → WALK → RUN testing pattern** (Nov 25)
    - **Trace report analysis** (Nov 25: full prompt/response visibility)
    - Production-validated patterns

10. **[IDEMPOTENCY_BUG_POSTMORTEM.md](IDEMPOTENCY_BUG_POSTMORTEM.md)** ✅ Reference
    - Historical bug analysis
    - Nov 21, 2025

11. **[EVENT_SOURCING_PRACTICES.md](EVENT_SOURCING_PRACTICES.md)** ✅ Production
    - Production-validated practices
    - Workflow 3001 tested

### Wave Runner V2 (Current System - Nov 2025)

12. **[../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md](../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md)** ✅ Production
    - Complete implementation plan with gate reviews
    - Phase 1 & 2 complete (A+ 99/100)
    - Production-ready execution engine
    - Zero mocks architecture

13. **[../WAVE_RUNNER_V2_REQUIREMENTS.md](../WAVE_RUNNER_V2_REQUIREMENTS.md)** ✅ Complete
    - Original requirements and design
    - Anti-pattern documentation
    - Architecture decisions

14. **[../WAVE_RUNNER_V2_DESIGN_DECISIONS.md](../WAVE_RUNNER_V2_DESIGN_DECISIONS.md)** ✅ Complete
    - Key architectural choices
    - Trade-offs and rationale

15. **[../WAVE_RUNNER_V2_FLOWCHARTS.md](../WAVE_RUNNER_V2_FLOWCHARTS.md)** ✅ Complete
    - Visual workflow diagrams
    - System flow documentation

16. **[../SCRIPT_ACTOR_COOKBOOK.md](../SCRIPT_ACTOR_COOKBOOK.md)** ✅ Production
    - How to write script actors
    - Anti-patterns to avoid (template substitution!)
    - Database query patterns

### Testing & Operations (Nov 2025)

17. **[HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md)** 🟡 Design (Nov 24, 2025)
    - Human task queue architecture
    - 3 implementation options (database-only, email, full platform)
    - Workflow pause/resume patterns
    - Recommendation: Start with Option A (30 min implementation)

18. **[TEST_DATA_MANAGEMENT.md](TEST_DATA_MANAGEMENT.md)** 🟢 Recommended (Nov 24, 2025)
    - Shadow testing strategy (no fake data needed)
    - Model A/B testing patterns
    - Canary rollout approach (5% → 100%)
    - Automatic champion selection via model_performance view
    - Migration 043v2 applied

19. **[DATA_LIFECYCLE.md](DATA_LIFECYCLE.md)** 🟢 Recommended (Nov 24, 2025)
    - Complete data archival and deletion strategy
    - 3-tier system: Configuration (immortal), Execution (mortal), User data (ephemeral)
    - GDPR compliance with immediate deletion
    - 30-day archive with partition-based cleanup
    - Next: Migration 045 (create archive tables)

### Workflow Documentation

20. **[../workflows/3001_complete_job_processing_pipeline.md](3001_complete_job_processing_pipeline%20(serial%20grader).md)** ✅ Production Ready
    - End-to-end job posting enrichment pipeline
    - Database fetcher → Schema validator → Skill extraction → Quality checks → Database writer
    - Event sourcing with workflow_runs + interaction_events
    - Human-in-loop for quality failures

21. **[../workflows/DYNAMIC_FIELD_MAPPING.md](../workflows/DYNAMIC_FIELD_MAPPING.md)** 🟡 Design
    - LLM-generated field mappings for multi-source job extraction
    - Handle LinkedIn, Indeed, Glassdoor with different schemas
    - Generate once, cache, reuse for all jobs from same source
    - Auto-detect schema drift and regenerate
    - Cost: $0.001 per source vs $200 hardcoded parser
    - Nov 24, 2025

22. **[../workflows/MODEL_CAPABILITY_TESTING.md](../workflows/MODEL_CAPABILITY_TESTING.md)** 🟡 Design
    - Smart tiered capability testing for LLM models
    - Tier 1 (basic) → Tier 2 (intermediate) → Tier 3 (advanced)
    - Fail-fast approach: Skip higher tiers on lower tier failures
    - 40% compute reduction vs naive testing
    - "A model that cannot count to three, will not be able to count to four"
    - Nov 24, 2025

17. **[../SCRIPT_ACTOR_CODE_LIFECYCLE.md](../SCRIPT_ACTOR_CODE_LIFECYCLE.md)** ✅ Production
    - Version control for actors
    - Deployment patterns

18. **[../STAGING_TABLE_DESIGN.md](../STAGING_TABLE_DESIGN.md)** ✅ Production
    - Data flow through staging tables
    - Validation patterns

### Schema & Current State

19. **[../SCHEMA_MAINTENANCE_COOKBOOK.md](../SCHEMA_MAINTENANCE_COOKBOOK.md)** ✅ Current
    - Schema evolution guide
    - Migration patterns

20. **[../SCHEMA_CODE_SYNC_ANALYSIS.md](../SCHEMA_CODE_SYNC_ANALYSIS.md)** ✅ Latest (Nov 24, 2025)
    - Dead schema detection
    - Orphaned code analysis
    - Current: 950 columns, 19 unused (2%)
    - **70 ghost tables cleaned up** (Nov 24)

21. **[../CLEANUP_MIGRATION_044_NOV24.md](../CLEANUP_MIGRATION_044_NOV24.md)** ✅ Complete (Nov 24, 2025)
    - Migration 044: Deleted 6 legacy tables
    - production_runs, test_cases_history, career_analyses (legacy recipes)
    - dialogue_step_placeholders (anti-pattern), trigger_executions, workflow_scripts (superseded)
    - Result: 68 tables (was 74), 17 empty (was 23)
    - Backup: by_pre_cleanup_20251124_143549.sql

### Quick References

21. **[../CONVERSATION_TAG_QUICK_REFERENCE.md](../CONVERSATION_TAG_QUICK_REFERENCE.md)** - Tag lookup
    - Conversation tags by category
    - Tag selection guidelines
    - Usage examples

22. **[../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md)** ✅ Critical
    - **THE RIGHT WAY:** Query database for parent outputs
    - **THE WRONG WAY:** Template substitution (posting.outputs)
    - Migration guide from anti-pattern
    - Production-validated (Workflow 3001)

23. **[../WORKFLOW_3001_READINESS_REPORT.md](../WORKFLOW_3001_READINESS_REPORT.md)** ✅ Current
    - Workflow 3001 integration status
    - LLM integration guidance
    - Prompt building architecture (Nov 24 corrections)

24. **[../DISASTER_RECOVERY_PLAN.md](../DISASTER_RECOVERY_PLAN.md)** - Operations
    - Backup and restore procedures
    - Recovery patterns

25. **[../CLEANUP_NOV24_2025.md](../CLEANUP_NOV24_2025.md)** ✅ Latest
    - Documentation cleanup record
    - 48 files removed (19 docs, 29 code files)
    - Ghost table cleanup validation

### Deleted/Archived (Do NOT Reference These!)

**DELETED Nov 24, 2025** (Referenced old schema - recipe_runs, session_runs, posting.outputs):
- ❌ `DATABASE_SCHEMA.md` - Replaced by current schema in database
- ❌ `ACTOR_SYSTEM.md` - Superseded by Wave Runner V2 docs
- ❌ `CONNECTION_POOLING.md` - Implementation details moved to code
- ❌ `CODE_DEPLOYMENT.md` - Superseded by SCRIPT_ACTOR_CODE_LIFECYCLE.md
- ❌ `FILE_VERSIONING.md` - Integrated into code lifecycle docs
- ❌ `TEMPLATE_SUBSTITUTION_BUG.md` - Anti-pattern documented in CHECKPOINT_QUERY_PATTERN.md
- ❌ `MIGRATION_050_SUMMARY.md` - Historical, no longer relevant
- ❌ `CHECKPOINT_MIGRATION_CHECKLIST.md` - Migration complete
- ❌ `TEMPLATE_VS_QUERY_ARCHITECTURE.md` - Integrated into CHECKPOINT_QUERY_PATTERN.md
- ❌ `HALLUCINATION_DETECTION_COOKBOOK.md` - Old QA patterns
- ❌ `PYTHON_TO_TURING_MIGRATION_GUIDE.md` - Old migration path
- ❌ `SKILL_MATCHING.md` - Moved to archive
- ❌ `EXEC_AGENT.md` - Experimental, discontinued
- ❌ `SCHEMA_DISCUSSIONS.md` - Historical

**Why deleted:** These docs referenced tables that no longer exist (recipe_runs, session_runs, variations, canonicals) and patterns we explicitly avoid (template substitution, posting.outputs dict).

---

## 🎯 Quick Reference

**Starting Point**: Read this README, then:
- **New to the system?** → Start with [../README.md](../README.md) for docs overview
- **Building workflows?** → [WORKFLOW_CREATION_COOKBOOK.md](WORKFLOW_CREATION_COOKBOOK.md)
- **Understanding execution?** → [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md)
- **Workflow state?** → [WORKFLOW_STATE_ARCHITECTURE.md](WORKFLOW_STATE_ARCHITECTURE.md) 🆕 Nov 25
- **Wave Runner V2?** → [../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md](../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md)
- **Writing script actors?** → [../SCRIPT_ACTOR_COOKBOOK.md](../SCRIPT_ACTOR_COOKBOOK.md)
- **Debugging?** → [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md)
- **Checkpoint queries?** → [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) ⚠️ Critical!
- **Event sourcing?** → [EVENT_SOURCING_ARCHITECTURE.md](EVENT_SOURCING_ARCHITECTURE.md)
- **Refactoring code?** → [REFACTORING_BEST_PRACTICES.md](REFACTORING_BEST_PRACTICES.md)
- **Schema maintenance?** → [../SCHEMA_MAINTENANCE_COOKBOOK.md](../SCHEMA_MAINTENANCE_COOKBOOK.md)

---

## 📖 Document Categories

### 🏗️ **Core Architecture** (Read First)
1. [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md) - How workflows run
2. [CHECKPOINT_SYSTEM.md](CHECKPOINT_SYSTEM.md) - State management (**NOT in-memory!**)
3. [EVENT_SOURCING_ARCHITECTURE.md](EVENT_SOURCING_ARCHITECTURE.md) - Event store system
4. [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - **Database queries, NOT templates!**

### 🚀 **Wave Runner V2** (Current System)
5. [../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md](../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md) - Complete plan
6. [../WAVE_RUNNER_V2_REQUIREMENTS.md](../WAVE_RUNNER_V2_REQUIREMENTS.md) - Requirements
7. [../SCRIPT_ACTOR_COOKBOOK.md](../SCRIPT_ACTOR_COOKBOOK.md) - Writing actors
8. [../SCRIPT_ACTOR_CODE_LIFECYCLE.md](../SCRIPT_ACTOR_CODE_LIFECYCLE.md) - Deployment
9. [../STAGING_TABLE_DESIGN.md](../STAGING_TABLE_DESIGN.md) - Data flow

### 🔧 **Implementation Guides**
10. [WORKFLOW_CREATION_COOKBOOK.md](WORKFLOW_CREATION_COOKBOOK.md) - Create workflows
11. [REFACTORING_BEST_PRACTICES.md](REFACTORING_BEST_PRACTICES.md) - Safe refactoring
12. [../SCHEMA_MAINTENANCE_COOKBOOK.md](../SCHEMA_MAINTENANCE_COOKBOOK.md) - Schema evolution

### 🧪 **Testing & Operations**
13. [HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md) - Human task queue design
14. [TEST_DATA_MANAGEMENT.md](TEST_DATA_MANAGEMENT.md) - Shadow testing strategy
15. [DATA_LIFECYCLE.md](DATA_LIFECYCLE.md) - Archive/deletion strategy

### 🛡️ **Reliability & Recovery**
16. [CHECKPOINT_SYSTEM.md](CHECKPOINT_SYSTEM.md) - Crash recovery
17. [EVENT_SOURCING_PRACTICES.md](EVENT_SOURCING_PRACTICES.md) - Production practices
18. [PROJECTION_REBUILD.md](PROJECTION_REBUILD.md) - Rebuild projections

### 🔍 **Debugging & QA**
19. [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) - Troubleshooting
20. [IDEMPOTENCY_BUG_POSTMORTEM.md](IDEMPOTENCY_BUG_POSTMORTEM.md) - Case study

### 📝 **Workflows**
21. [../workflows/3001_complete_job_processing_pipeline.md](3001_complete_job_processing_pipeline%20(serial%20grader).md) - Production pipeline
22. [../workflows/DYNAMIC_FIELD_MAPPING.md](../workflows/DYNAMIC_FIELD_MAPPING.md) - Multi-source extraction
23. [../workflows/MODEL_CAPABILITY_TESTING.md](../workflows/MODEL_CAPABILITY_TESTING.md) - Tiered testing

### 📊 **Current Status**
18. [../WORKFLOW_3001_READINESS_REPORT.md](../WORKFLOW_3001_READINESS_REPORT.md) - Integration status
19. [../SCHEMA_CODE_SYNC_ANALYSIS.md](../SCHEMA_CODE_SYNC_ANALYSIS.md) - Schema health (Nov 24)
20. [../CLEANUP_NOV24_2025.md](../CLEANUP_NOV24_2025.md) - Cleanup record (48 files)
21. [../CLEANUP_MIGRATION_044_NOV24.md](../CLEANUP_MIGRATION_044_NOV24.md) - Migration 044 (6 tables)

---

## 📋 Status

**Current**: ✅ Updated for Wave Runner V2 (November 24, 2025)

### Active Documentation (25 files)

**Architecture (14 files):**
- WORKFLOW_CREATION_COOKBOOK.md - Complete workflow guide
- WORKFLOW_EXECUTION.md - Execution mechanics
- CHECKPOINT_SYSTEM.md - State management (database queries!)
- EVENT_SOURCING_ARCHITECTURE.md - Event store system
- REFACTORING_BEST_PRACTICES.md - Safe refactoring
- CLEAN_MODEL_ROUTING.md - Model selection
- EVENT_INVALIDATION.md - Event patterns
- PROJECTION_REBUILD.md - Projection rebuilding
- WORKFLOW_DEBUGGING_COOKBOOK.md - Troubleshooting
- IDEMPOTENCY_BUG_POSTMORTEM.md - Bug analysis
- EVENT_SOURCING_PRACTICES.md - Production practices
- HUMAN_IN_LOOP.md - Human task queue (NEW Nov 24)
- TEST_DATA_MANAGEMENT.md - Shadow testing (NEW Nov 24)
- DATA_LIFECYCLE.md - Archive strategy (NEW Nov 24)

**Wave Runner V2 (9 files in parent dir):**
- WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md - Complete plan (A+ 99/100)
- WAVE_RUNNER_V2_REQUIREMENTS.md - Requirements
- WAVE_RUNNER_V2_DESIGN_DECISIONS.md - Design choices
- WAVE_RUNNER_V2_FLOWCHARTS.md - Visual docs
- SCRIPT_ACTOR_COOKBOOK.md - Actor development
- SCRIPT_ACTOR_CODE_LIFECYCLE.md - Version control
- STAGING_TABLE_DESIGN.md - Data flow
- SCHEMA_MAINTENANCE_COOKBOOK.md - Schema evolution
- SCHEMA_CODE_SYNC_ANALYSIS.md - Schema health (Nov 24)

**Testing & Operations (3 files):**
- HUMAN_IN_LOOP.md - Human task queue (Nov 24 design)
- TEST_DATA_MANAGEMENT.md - Shadow testing strategy (Nov 24)
- DATA_LIFECYCLE.md - Archive/deletion strategy (Nov 24)

**Workflows (3 files in parent workflows/ dir):**
- 3001_complete_job_processing_pipeline.md - Production pipeline
- DYNAMIC_FIELD_MAPPING.md - Multi-source extraction (Nov 24 design)
- MODEL_CAPABILITY_TESTING.md - Tiered model testing (Nov 24 design)

**Current State (7 files in parent dir):**
- WORKFLOW_3001_READINESS_REPORT.md - Integration status
- CHECKPOINT_QUERY_PATTERN.md - **Critical anti-pattern guide**
- CLEANUP_NOV24_2025.md - Cleanup record (48 files deleted)
- CLEANUP_MIGRATION_044_NOV24.md - Migration 044 record (6 tables deleted)
- DATA_CLEANUP_PROPOSAL_NOV24.md - Cleanup proposal (approved, executed)
- DISASTER_RECOVERY_PLAN.md - Operations
- CONVERSATION_TAG_QUICK_REFERENCE.md - Tag lookup

**Total**: 32 active documents (was 25 before Nov 24 session - added 7 today)

**Benefits**:
- ✅ Zero references to deleted schema
- ✅ Clear separation: Wave Runner V2 (current) vs archived (old)
- ✅ Anti-patterns explicitly documented
- ✅ Production-validated patterns
- ✅ Clean codebase (48 files + 6 tables removed Nov 24)
- ✅ Migration 044 applied (68 tables, 17 empty)

**Archive**: Historical content in `/home/xai/Documents_Versions/ty_learn`

---

## ⚠️ Critical Anti-Patterns (AVOID!)

**DO NOT:**
1. ❌ Use template substitution with {placeholders}
2. ❌ Build prompts at execution time
3. ❌ Rely on in-memory state (posting.outputs dict)
4. ❌ Use recipe_runs, session_runs tables (deleted!)
5. ❌ Reference variations, canonicals, facets tables (deleted!)

**DO:**
1. ✅ Query database for parent interaction outputs
2. ✅ Build prompts when creating interaction records
3. ✅ Use interactions table as source of truth
4. ✅ Store prompts in interaction.input JSONB
5. ✅ Follow CHECKPOINT_QUERY_PATTERN.md

**Reference**: [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - The definitive guide

---

## 🎓 Recommended Reading Paths

### For New Developers
1. [../README.md](../README.md) - Documentation overview
2. [WORKFLOW_CREATION_COOKBOOK.md](WORKFLOW_CREATION_COOKBOOK.md) - Build workflows
3. [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md) - Execution model
4. [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - **Critical patterns**
5. [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) - Troubleshooting

### For Sandy (Implementer)
1. [../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md](../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md) - Current system
2. [../WORKFLOW_3001_READINESS_REPORT.md](../WORKFLOW_3001_READINESS_REPORT.md) - Next task
3. [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - **Must read!**
4. [../SCRIPT_ACTOR_COOKBOOK.md](../SCRIPT_ACTOR_COOKBOOK.md) - Actor patterns
5. [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) - Debug guide

### For Arden (AI Assistant)
1. [../___ARDEN_CHEAT_SHEET.md](../___ARDEN_CHEAT_SHEET.md) - Quick reference
2. [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - **Anti-patterns**
3. [../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md](../WAVE_RUNNER_V2_IMPLEMENTATION_PLAN.md) - Current state
4. [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) - Debug patterns
5. [../CLEANUP_NOV24_2025.md](../CLEANUP_NOV24_2025.md) - Recent cleanup

### For Debugging Production Issues
1. [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) - Diagnostic checklist
2. [CHECKPOINT_SYSTEM.md](CHECKPOINT_SYSTEM.md) - Recovery mechanics
3. [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - State access patterns
4. [IDEMPOTENCY_BUG_POSTMORTEM.md](IDEMPOTENCY_BUG_POSTMORTEM.md) - Bug history

### For Building Workflows
1. [WORKFLOW_CREATION_COOKBOOK.md](WORKFLOW_CREATION_COOKBOOK.md) - Complete guide
2. [../CONVERSATION_TAG_QUICK_REFERENCE.md](../CONVERSATION_TAG_QUICK_REFERENCE.md) - Tag selection
3. [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - **Database queries (NOT templates!)**
4. [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md) - Execution model
5. [../SCRIPT_ACTOR_COOKBOOK.md](../SCRIPT_ACTOR_COOKBOOK.md) - Write actors

### For System Refactoring
1. [REFACTORING_BEST_PRACTICES.md](REFACTORING_BEST_PRACTICES.md) - Safe patterns
2. [EVENT_SOURCING_ARCHITECTURE.md](EVENT_SOURCING_ARCHITECTURE.md) - Event store
3. [../SCHEMA_MAINTENANCE_COOKBOOK.md](../SCHEMA_MAINTENANCE_COOKBOOK.md) - Schema evolution
4. [../SCHEMA_CODE_SYNC_ANALYSIS.md](../SCHEMA_CODE_SYNC_ANALYSIS.md) - Current health

---

## 🔄 Documentation Freshness Policy

**Philosophy:** The most beautiful system is the one that emerges from good habits, not enforcement.

### How We Keep Docs Fresh

**1. Standard Headers** (always include):
```markdown
**Last Updated:** 2025-11-25
**Dependencies:** runner.py, executors.py (optional but helpful)
```

**2. Natural Updates**:
- Changed `runner.py`? → Update WORKFLOW_EXECUTION.md
- Fixed a bug? → Update WORKFLOW_DEBUGGING_COOKBOOK.md  
- New pattern discovered? → Update relevant cookbook
- **Update the date** when you edit

**3. Quarterly Spot Check**:
```bash
# Show docs not touched in 90 days
git log --since="90 days ago" --name-only --pretty=format: docs/architecture/ | sort -u

# Review the 2-3 docs not in that list - still accurate?
```

**That's it.** No automation scripts. No JSON metadata. No cron jobs.

Just: Accurate headers + Git history + Discipline = Fresh docs ✨

---

**Maintained by**: Arden (GitHub Copilot)  
**Last Review**: 2025-11-25 (Post-traceability update)  
**Format**: Encyclopedia (timeless reference)  
**Status**: Production-ready with Wave Runner V2 + Traceability ✨

**Key Philosophy:**
> "Template substitution is bad. Really bad. Like, totally."
> "The database is your source of truth."
> "Wave Runner is an executor, not a builder."
> "Prompts are pre-built and stored in the database."
> "The most beautiful code is the code you don't write."
