# TuringOrchestrator - Quick Reference Card

## 🎼 What Is It?
Gopher's spiritual successor - an autonomous workflow orchestration system that:
- 🔍 Discovers pending work automatically
- 📋 Understands workflow contracts
- 🚀 Executes tasks with validation
- 🔗 Chains workflows intelligently

## ⚡ Quick Start (3 Lines)
```python
from core.turing_orchestrator import TuringOrchestrator
orchestrator = TuringOrchestrator()
orchestrator.process_pending_tasks(max_tasks=10)
```

## 🛠️ Common Commands

### Discover What Needs Doing
```python
pending = orchestrator.discover_pending_tasks()
# Returns: [{task_type, workflow_id, count, sample_ids, priority}]

for task in pending:
    print(f"{task['description']} - Priority: {task['priority']}")
```

### Process Pending Tasks
```python
# Production mode (commits to DB)
results = orchestrator.process_pending_tasks(max_tasks=10, dry_run=False)

# Test mode (no DB commits)
results = orchestrator.process_pending_tasks(max_tasks=3, dry_run=True)

# Check results
print(f"Processed: {results['tasks_processed']}")
print(f"Success: {results['success_count']}/{results['tasks_processed']}")
```

### Execute Single Workflow
```python
result = orchestrator.execute_workflow(
    workflow_id=1121,
    inputs={'posting_id': 1},
    dry_run=False
)
print(f"Status: {result['status']}, Time: {result['time_seconds']}s")
```

### Chain Workflows
```python
chain = [
    (1126, {'document_text': 'Resume content...'}),  # Import profile
    (2002, {})  # Extract skills (profile_id auto-passed)
]
results = orchestrator.chain_workflows(chain)
```

### Search Workflows
```python
matches = orchestrator.find_workflow("extract skills from job")
for match in matches:
    print(f"Workflow {match.workflow_id}: {match.workflow_name}")
```

### List All Capabilities
```python
capabilities = orchestrator.list_capabilities()
for cap in capabilities:
    print(cap)
# Output:
# Workflow 1121: Job Skills Extraction
#   Input:  ['posting_id']
#   Output: ['skills', 'posting_id']
```

## 📊 Current State

### Registered Workflows (4)
- **1121**: Job Skills Extraction (input: posting_id → output: skills[])
- **2002**: Profile Skills Extraction (input: profile_id → output: skills[])
- **1122**: Profile Skills Legacy (input: profile_id → output: skills[])
- **1126**: Profile Document Import (input: document_text → output: profile_id)

### Pending Tasks (as of Nov 6, 2025)
- **126 jobs** need skills extraction (posting_id 1, 118, 119, ...)
- All ready to process with workflow 1121

### Testing Results
```
✅ 3/3 tasks succeeded (100% success rate)
⏱️  Average time: ~13s per task
✅ All executions validated with contracts
📊 22 skills extracted from 3 test jobs
```

## 🎯 Use Cases

### Daily Batch Processing
```python
# Run this every morning
orchestrator = TuringOrchestrator()
results = orchestrator.process_pending_tasks(max_tasks=50)
print(f"Morning batch: {results['success_count']} jobs processed")
```

### Targeted Processing
```python
# Only process specific workflow
pending = orchestrator.discover_pending_tasks()
for task in pending:
    if task['workflow_id'] == 1121:  # Jobs only
        orchestrator.process_pending_tasks(max_tasks=10)
```

### Safe Testing
```python
# Test without breaking anything
results = orchestrator.process_pending_tasks(
    max_tasks=5,
    dry_run=True  # All validation runs, but no DB commits
)
```

## 🚨 Important Notes

### Distinction: TuringOrchestrator vs ExecAgent
- **TuringOrchestrator**: Autonomous workflow orchestrator (THIS!)
  - Discovers pending work
  - Executes workflows
  - Chains intelligently
  
- **ExecAgent**: Virtual terminal (NOT YET BUILT)
  - Command parser: `{ExecAgent curl ...}`
  - Different system entirely

### Validation Always On
- All executions go through contract validation
- Input checked BEFORE LLM call
- Output validated AFTER completion
- Smart output wrapping for common mismatches

### Dry-Run Mode
- `dry_run=True`: All logic runs, validation runs, LLM calls made
- BUT: Workflow execution sets `commit=False`
- Use for testing new workflows safely

## 📁 Files

- **Core**: `core/turing_orchestrator.py` (~420 lines)
- **Docs**: `TURING_ORCHESTRATOR_COMPLETE.md` (full guide)
- **Test**: `test_autonomous_execution.py` (standalone test)
- **Cheat Sheet**: `docs/___ARDEN_CHEAT_SHEET.md` (updated)

## 🔮 Coming Next: Phase 4.2

### LLM-Based Planning
```python
# Natural language goals (COMING SOON)
orchestrator.plan_and_execute(
    "Extract skills from all jobs fetched today and match with profile 17"
)
# LLM will plan and execute entire workflow chain
```

### Features Coming
1. OpenAI function calling for planning
2. Execution DAG building
3. Parallel task execution
4. Scheduling (cron/daemon)
5. Error recovery with retry
6. Result tracking and reports

## 📞 Quick Help

**Demo**: `python core/turing_orchestrator.py`
**Test**: `python test_autonomous_execution.py`
**Docs**: See `TURING_ORCHESTRATOR_COMPLETE.md`

**Questions?** Check the main documentation or ask! 🚀
