# Workflow Orchestration - Database-Driven Execution

**Status:** ✅ IMPLEMENTED (Phase 1 + Audit System)  
**Created:** 2025-11-28  
**Last Updated:** 2025-12-10  
**Author:** Arden  

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Overview

Workflow execution is database-driven with validation, audit logging, and state tracking.

**Canonical Runner:** `tools/run_workflow.py`

**Core Files:**
- `tools/run_workflow.py` - CLI tool with state snapshots, PID lock, audit trail
- `core/wave_runner/runner.py` - Wave execution engine
- `core/wave_runner/interaction_creator.py` - Child creation with parallel support

## Usage

```bash
# RECOMMENDED: Background with logging (via wrapper)
./scripts/run_workflow.sh 3001

# Direct execution (foreground, blocks terminal)
./tools/run_workflow.py 3001

# Single posting mode
./tools/run_workflow.py 3001 --mode single_posting --posting-id 4920

# Resume specific workflow_run
./tools/run_workflow.py 3001 --mode single_run --workflow-run-id 123

# List running workflows
./tools/run_workflow.py --list-running

# Stop a running workflow
./tools/run_workflow.py --stop --workflow-run-id 123

# Force restart (kills existing)
./tools/run_workflow.py 3001 --force
```

## Safety Checks (Implemented)

1. **Duplicate Detection** - Rejects if workflow already running in global_batch mode
2. **Rate Limiting** - Max 1 batch per minute per workflow  
3. **Audit Trail** - Every execution logged with before/after state

## Audit System (NEW - Nov 30)

**Conversation:** `Workflow Orchestrator` (ID: 9198)

Every workflow execution creates an interaction with full state tracking:

```json
{
  "input": {
    "workflow_id": 3001,
    "mode": "global_batch",
    "requested_by": "xai",
    "action": "workflow_execution",
    "state_before": {
      "postings_total": 847,
      "postings_with_summary": 288,
      "postings_with_skills": 231,
      "postings_with_ihl": 230
    },
    "expected_work": {
      "pending_summary": 555,
      "pending_skills": 57,
      "pending_ihl": 1
    }
  },
  "output": {
    "status": "completed",
    "interactions_completed": 1234,
    "duration_seconds": 567,
    "state_after": {...},
    "delta": {
      "total": 0,
      "summary": 47,
      "skills": 57,
      "ihl": 56
    }
  }
}
```

**Query execution history:**
```sql
SELECT 
    interaction_id,
    created_at,
    input->>'workflow_id' as workflow,
    input->'state_before'->>'postings_total' as before_total,
    output->'state_after'->>'postings_total' as after_total,
    output->'delta' as changes
FROM interactions 
WHERE conversation_id = 9198
ORDER BY created_at DESC;
```

---

## Safety Features (Implemented)

1. **PID Locking** - File at `/tmp/workflow_{id}.pid` prevents duplicate runs
2. **Duplicate Detection** - Rejects if workflow already running in global_batch mode
3. **Rate Limiting** - Max 1 batch per minute per workflow  
4. **Audit Trail** - Every execution logged with before/after state
5. **Force Mode** - `--force` flag to kill existing and take over

---

## Background: The Problem Solved

**Nov 27-28, 2025 - Execution Chaos:**
- Manual Python commands with no audit trail
- "What ran yesterday?" = unknown
- Orphaned processes running for 9+ hours undetected

**Nov 30, 2025 - Solution:**
- Every run logged as interaction with before/after state
- "We did A, we got B" is now answerable from the database

---

## Future Phases (Not Implemented)

### Phase 2: Health Monitoring
- Cron-based health checks every 5 minutes
- Detect stuck runners, unresponsive Ollama
- Auto-fix recoverable issues (stuck interactions)

### Phase 3: Continuous Workflows  
- Long-running daemon with sleep loop
- PostgreSQL LISTEN/NOTIFY for new work

---

**See Also:**
- `docs/WORKFLOW_COOKBOOK.md` - Pre-flight checklist, run procedures
- `docs/architecture/RFC_WORKFLOW_AS_INTERACTION.md` - Design rationale
