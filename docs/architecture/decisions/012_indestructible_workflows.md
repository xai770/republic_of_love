# ADR-012: Indestructible Workflows (Crash Recovery)

**Status:** Accepted  
**Date:** 2025-11-30  
**Deciders:** xai, Sandy  
**Tags:** reliability, crash-recovery, heartbeat

---

## Context

Workflow runs would fail permanently if:
- Server rebooted during processing
- OOM killed the Python process
- Terminal disconnected
- Any unhandled exception crashed the runner

There was no way to automatically resume interrupted workflows.

---

## Decision

**Implement heartbeat mechanism with automatic resume.**

### Architecture

```
┌─────────────────────────────────┐
│  WaveRunner Process             │
│  - Updates heartbeat every 30s  │
│  - Saves progress to state      │
│  - Catches SIGTERM/SIGINT       │
└───────────────┬─────────────────┘
                │ writes
                ▼
┌─────────────────────────────────┐
│  workflow_runs.state (JSONB)    │
│  {                              │
│    "last_heartbeat": "...",     │
│    "runner_pid": 12345,         │
│    "progress": {...}            │
│  }                              │
└───────────────┬─────────────────┘
                │ monitors
                ▼
┌─────────────────────────────────┐
│  Cron Job (every 5 minutes)     │
│  - Detects dead workflows       │
│  - Resumes automatically        │
└─────────────────────────────────┘
```

---

## Implementation

### 1. Heartbeat Thread

File: `core/wave_runner/runner.py`

```python
def _heartbeat_loop(self):
    """Background thread updates heartbeat every 30s."""
    while not self._stop_heartbeat:
        self.db.update_workflow_state(self.workflow_run_id, {
            "last_heartbeat": datetime.now().isoformat(),
            "runner_pid": os.getpid(),
            "runner_id": self.runner_id
        })
        time.sleep(30)
```

### 2. Graceful Shutdown Handler

```python
def _handle_interrupt(self, signum, frame):
    """Catch SIGTERM/SIGINT and mark workflow as interrupted."""
    self._stop_heartbeat = True
    self.db.update_workflow_run_status(self.workflow_run_id, 'interrupted')
    self.db.update_workflow_state(self.workflow_run_id, {
        "interrupted_at": datetime.now().isoformat(),
        "interrupt_signal": signum
    })
    sys.exit(0)
```

### 3. Resume Script

File: `scripts/resume_workflows.py`

```bash
# Check for dead workflows
python3 scripts/resume_workflows.py

# Resume them
python3 scripts/resume_workflows.py --resume
```

### 4. Cron Job

File: `scripts/auto_resume.sh`

```bash
*/5 * * * * /home/xai/Documents/ty_wave/scripts/auto_resume.sh
```

---

## Workflow Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Created, not started |
| `running` | Active (heartbeat within 2 min) |
| `interrupted` | Gracefully stopped (SIGTERM/SIGINT) |
| `dead` | Crashed (heartbeat > 2 min old) |
| `completed` | Finished successfully |

---

## Consequences

### Positive

1. **Workflows survive reboots** - Automatic resume
2. **No orphaned runs** - Cron detects and handles
3. **Visibility** - Can see last heartbeat, PID, progress

### Negative

1. **30s heartbeat overhead** - Minimal
2. **5 minute detection delay** - Acceptable for batch processing

---

## Verification

```sql
-- Check for stuck workflows
SELECT 
    workflow_run_id,
    status,
    state->>'last_heartbeat' as heartbeat,
    state->>'runner_pid' as pid
FROM workflow_runs
WHERE status = 'running'
ORDER BY workflow_run_id DESC;
```
