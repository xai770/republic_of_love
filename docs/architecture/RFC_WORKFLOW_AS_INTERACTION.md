# RFC: Workflow Execution as Interaction

**Author**: Arden  
**Date**: 2025-11-30  
**Status**: ✅ Implemented (Phase 1)

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Logging Only | ✅ Done - `tools/run_workflow.py` |
| Phase 2 | Workflow Triggers | 🔮 Future |
| Phase 3 | Human Approval Gates | 🔮 Future |

**Orchestrator Conversation ID:** 9198

**Query audit log:**
```sql
SELECT interaction_id, input->>'workflow_id' as workflow, 
       output->'delta' as delta, created_at 
FROM interactions WHERE conversation_id = 9198 
ORDER BY created_at DESC LIMIT 5;
```

---

## Problem Statement

> "I really don't get why we run one batch and get result A, then run another and get result B. Are we in control?"

Currently:
- Workflow runs are **opaque** - we start them, hope for the best
- No **before/after snapshots** stored with the run
- No **causal link** between "we did A" and "we got B"
- Debugging requires log archaeology

---

## Proposal: Every Workflow Start = One Interaction

### The Orchestrator Conversation

Create a new conversation:

```sql
INSERT INTO conversations (conversation_name, system_prompt, model_name)
VALUES (
    'Workflow Orchestrator',
    'You coordinate workflow execution. Log everything.',
    'system'  -- Not an LLM, a system process
);
```

### Interaction Structure

When starting workflow 3001:

```json
{
    "interaction_id": 20062,
    "conversation_id": 9200,  // Workflow Orchestrator
    "workflow_run_id": 456,
    "status": "completed",
    "input": {
        "action": "start_workflow",
        "workflow_id": 3001,
        "mode": "global_batch",
        "triggered_by": "manual",
        "operator": "xai",
        "state_snapshot": {
            "postings_total": 847,
            "postings_with_summary": 288,
            "postings_with_skills": 231,
            "postings_with_ihl": 230,
            "pending_interactions": 13
        },
        "expected_work": {
            "summaries_to_process": 555,
            "skills_to_process": 57,
            "ihl_to_process": 1
        }
    },
    "output": {
        "status": "completed",
        "duration_ms": 20015498,
        "interactions_created": 2980,
        "interactions_completed": 2980,
        "interactions_failed": 0,
        "state_after": {
            "postings_total": 847,
            "postings_with_summary": 335,
            "postings_with_skills": 288,
            "postings_with_ihl": 287
        },
        "delta": {
            "summaries": "+47",
            "skills": "+57",
            "ihl": "+57"
        }
    }
}
```

---

## Benefits

### 1. Traceability
```sql
-- What happened on Nov 28?
SELECT * FROM interactions 
WHERE conversation_id = 9200  -- Orchestrator
  AND created_at::date = '2025-11-28';
```

### 2. Reproducibility Analysis
```sql
-- Compare two runs of the same workflow
SELECT 
    input->>'state_snapshot' as before,
    output->>'state_after' as after,
    output->>'delta' as changes
FROM interactions
WHERE conversation_id = 9200
  AND input->>'workflow_id' = '3001'
ORDER BY created_at DESC
LIMIT 2;
```

### 3. Anomaly Detection
```sql
-- Runs where expected != actual
SELECT * FROM interactions
WHERE conversation_id = 9200
  AND (input->'expected_work'->>'summaries_to_process')::int 
      != (output->'delta'->>'summaries')::int;
```

### 4. Cascading Workflows
```sql
-- Workflow 3002 triggered by workflow 3001
INSERT INTO interactions (conversation_id, input)
VALUES (9200, '{
    "action": "start_workflow",
    "workflow_id": 3002,
    "triggered_by": "workflow_completion",
    "parent_interaction_id": 20062,
    ...
}');
```

---

## Implementation

### Phase 1: Logging Only (Low Risk)

Modify `workflow_executor.py` to:
1. Create orchestrator interaction BEFORE running
2. Capture state snapshot
3. Update interaction AFTER completion

```python
# In WorkflowExecutor.execute()

# 1. Capture before state
state_before = self._capture_state_snapshot()

# 2. Create orchestrator interaction
orch_interaction = self.db.create_interaction(
    conversation_id=ORCHESTRATOR_CONVERSATION_ID,
    input={
        "action": "start_workflow",
        "workflow_id": workflow_id,
        "state_snapshot": state_before,
        "expected_work": self._estimate_work()
    }
)

# 3. Run the actual workflow
result = self.runner.run_workflow(...)

# 4. Update orchestrator interaction
self.db.update_interaction(
    interaction_id=orch_interaction.id,
    status="completed",
    output={
        "state_after": self._capture_state_snapshot(),
        "interactions_completed": result.completed,
        ...
    }
)
```

### Phase 2: Workflow Triggers (Medium Risk)

Allow workflows to trigger other workflows:

```yaml
# In workflow definition
on_completion:
  - workflow_id: 3002
    condition: "summaries_processed > 0"
```

### Phase 3: Human Approval Gates (Future)

```yaml
# In workflow definition  
steps:
  - name: summarize
    ...
  - name: human_review
    type: approval_gate
    notify: ["gershon@example.com"]
  - name: extract_skills
    requires: human_review.approved
```

---

## Answer to "Sounds boring?"

No. This is **infrastructure**. 

Boring infrastructure is what separates:
- "I think the batch ran?" 
- from "Run 456 processed 2980 interactions, +47 summaries, anomaly detected in step 3"

The database is your lab notebook. Every experiment logged. Every result traceable.

---

## Next Steps

1. **Sandy analyzes Nov 28 run** - establishes baseline
2. **Create Orchestrator conversation** - 5 min
3. **Modify workflow_executor.py** - 30 min
4. **Test with small workflow** - verify logging works
5. **Document in cookbook** - update procedures

---

*Want me to implement Phase 1?*
