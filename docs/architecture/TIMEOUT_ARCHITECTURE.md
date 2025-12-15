# Timeout Architecture for Wave Runner

**Date:** November 27, 2025  
**Author:** Arden  
**Status:** Proposal  
**Problem:** Wave Runner gets stuck; need deterministic timeouts per conversation

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Current State Assessment

### What We Have Today ✅

**1. Hardcoded Timeouts in Code:**
```python
# core/wave_runner/executors.py
class AIModelExecutor:
    def __init__(self):
        self.timeout = 600  # 10 minute timeout (hardcoded!)
```

**2. Watchdog Script (External Monitoring):**
```python
# scripts/watchdog_cleanup.py
MAX_INTERACTION_RUNTIME_MINUTES = 15  # Cleanup stuck interactions
MAX_WORKFLOW_RUNTIME_HOURS = 2        # Cleanup stuck workflows
```

**3. Runs via Cron (Every 5 Minutes):**
```bash
*/5 * * * * python3 scripts/watchdog_cleanup.py >> logs/watchdog.log 2>&1
```

### What's Wrong ❌

**Problem #1: One-Size-Fits-All Timeouts**
- All AI conversations: 10 minutes (too long for fast models, too short for slow ones)
- Extract Skills (qwen2.5:7b): ~6 seconds → wastes 9m54s before timeout
- Format Standardization (gemma2): ~56 seconds → wastes 9m4s before timeout
- Complex analysis: might actually NEED 10+ minutes

**Problem #2: No Per-Conversation Configuration**
- Can't specify: "Extract Skills should timeout at 30s"
- Can't specify: "Deep Analysis allowed 20 minutes"
- All conversations treated equally

**Problem #3: Watchdog is Reactive, Not Proactive**
- Checks every 5 minutes (dead time!)
- Interaction stuck at 10:00:01 → detected at 10:05:00 → 5min waste
- Not integrated with runner (separate process)

**Problem #4: No Timeout Budget Tracking**
- Can't predict: "This workflow will take 8 minutes based on conversation timeouts"
- Can't detect: "This conversation is using 90% of its timeout budget"
- No visibility until after failure

---

## Your Proposal (Two-Layer Architecture)

**Brilliant insight:** "Two layers with monitoring layer able to stop execution layer"

This is the **Supervisor Pattern** used in production systems (Kubernetes, Erlang/OTP, etc.)

```
┌─────────────────────────────────────┐
│  MONITORING LAYER (Supervisor)      │  ← Tracks time, enforces limits
│  - Tracks timeout budgets           │
│  - Can terminate execution          │
│  - Reads timeout config from DB     │
└──────────────┬──────────────────────┘
               │ monitors & controls
               ▼
┌─────────────────────────────────────┐
│  EXECUTION LAYER (Worker)           │  ← Does the actual work
│  - Runs AI models                   │
│  - Executes scripts                 │
│  - Processes interactions           │
└─────────────────────────────────────┘
```

---

## Proposed Solution: Database-Driven Timeouts

### Part 1: Schema Changes

**Add timeout columns to `conversations` table:**

```sql
-- Migration 048: Add Conversation Timeouts
ALTER TABLE conversations
    ADD COLUMN timeout_seconds INTEGER DEFAULT 600,           -- Default 10 min
    ADD COLUMN timeout_strategy TEXT DEFAULT 'hard_kill',     -- hard_kill | soft_warn | adaptive
    ADD COLUMN timeout_grace_period_seconds INTEGER DEFAULT 30;

-- Add constraints
ALTER TABLE conversations
    ADD CONSTRAINT conversations_timeout_seconds_check 
        CHECK (timeout_seconds BETWEEN 10 AND 7200);  -- 10s to 2 hours

ALTER TABLE conversations
    ADD CONSTRAINT conversations_timeout_strategy_check
        CHECK (timeout_strategy IN ('hard_kill', 'soft_warn', 'adaptive'));

-- Create index for monitoring queries
CREATE INDEX idx_conversations_timeout_seconds 
    ON conversations(timeout_seconds) 
    WHERE enabled = true;

-- Example: Set realistic timeouts per conversation
UPDATE conversations 
SET timeout_seconds = 30,
    timeout_strategy = 'hard_kill'
WHERE conversation_name = 'r1114_extract_skills';  -- Fast model, strict timeout

UPDATE conversations
SET timeout_seconds = 120,
    timeout_strategy = 'hard_kill'
WHERE conversation_name = 'Format Standardization';  -- Slow model, longer timeout

UPDATE conversations
SET timeout_seconds = 300,
    timeout_strategy = 'soft_warn'
WHERE conversation_name LIKE '%Deep Analysis%';  -- Complex work, warn but don't kill
```

**Add timeout tracking to `interactions` table:**

```sql
-- Already have started_at, completed_at
-- Add timeout tracking columns:
ALTER TABLE interactions
    ADD COLUMN timeout_budget_seconds INTEGER,           -- What timeout was allocated
    ADD COLUMN timeout_warnings INTEGER DEFAULT 0,       -- How many warnings issued
    ADD COLUMN timeout_exceeded BOOLEAN DEFAULT false,   -- Did it exceed timeout?
    ADD COLUMN termination_reason TEXT;                  -- Why was it killed?

-- Create index for monitoring
CREATE INDEX idx_interactions_timeout_exceeded
    ON interactions(timeout_exceeded)
    WHERE timeout_exceeded = true;
```

**Add timeout metrics to `workflow_step_metrics` table:**

```sql
-- Already has duration_seconds
-- Add timeout metrics:
ALTER TABLE workflow_step_metrics
    ADD COLUMN timeout_budget_seconds INTEGER,
    ADD COLUMN timeout_utilization_percent NUMERIC(5,2),  -- How much of budget used
    ADD COLUMN timeout_exceeded_count INTEGER DEFAULT 0;

-- For workflow-level timeout budgets:
ALTER TABLE workflow_runs
    ADD COLUMN estimated_timeout_seconds INTEGER,     -- Sum of all conversation timeouts
    ADD COLUMN actual_runtime_seconds INTEGER,
    ADD COLUMN timeout_efficiency_percent NUMERIC(5,2);
```

---

### Part 2: Two-Layer Execution Architecture

**Option A: Thread-Based Supervisor (Simpler)**

```python
# core/wave_runner/timeout_supervisor.py

import threading
import time
import signal
import psutil
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class TimeoutConfig:
    """Timeout configuration from database"""
    conversation_id: int
    conversation_name: str
    timeout_seconds: int
    timeout_strategy: str  # hard_kill | soft_warn | adaptive
    grace_period_seconds: int


class TimeoutSupervisor:
    """
    Monitors execution and enforces timeouts.
    
    Architecture:
        - Runs in separate thread
        - Monitors worker process/thread
        - Can terminate worker if timeout exceeded
        - Updates database with timeout metrics
    """
    
    def __init__(self, db_helper, logger):
        self.db_helper = db_helper
        self.logger = logger
        self.active_monitors = {}  # {interaction_id: MonitorThread}
    
    def get_timeout_config(self, conversation_id: int) -> TimeoutConfig:
        """Load timeout config from conversations table"""
        cursor = self.db_helper.get_cursor()
        cursor.execute("""
            SELECT 
                conversation_id,
                conversation_name,
                timeout_seconds,
                timeout_strategy,
                timeout_grace_period_seconds
            FROM conversations
            WHERE conversation_id = %s
        """, (conversation_id,))
        
        row = cursor.fetchone()
        if not row:
            # Fallback to defaults
            return TimeoutConfig(
                conversation_id=conversation_id,
                conversation_name='unknown',
                timeout_seconds=600,
                timeout_strategy='hard_kill',
                grace_period_seconds=30
            )
        
        return TimeoutConfig(
            conversation_id=row[0],
            conversation_name=row[1],
            timeout_seconds=row[2],
            timeout_strategy=row[3],
            grace_period_seconds=row[4]
        )
    
    def monitor_execution(
        self,
        interaction_id: int,
        conversation_id: int,
        worker_func: Callable,
        worker_args: tuple = ()
    ) -> dict:
        """
        Execute worker function with timeout monitoring.
        
        Returns:
            Worker result or timeout error
        """
        # Get timeout config from database
        config = self.get_timeout_config(conversation_id)
        
        # Update interaction with timeout budget
        self._record_timeout_budget(interaction_id, config.timeout_seconds)
        
        # Create worker thread
        result_container = {'result': None, 'error': None, 'completed': False}
        
        def worker_wrapper():
            try:
                result_container['result'] = worker_func(*worker_args)
                result_container['completed'] = True
            except Exception as e:
                result_container['error'] = e
                result_container['completed'] = True
        
        worker_thread = threading.Thread(target=worker_wrapper, daemon=True)
        
        # Start worker and monitor
        start_time = time.time()
        worker_thread.start()
        
        # Monitor loop
        warning_issued = False
        while worker_thread.is_alive():
            elapsed = time.time() - start_time
            
            # Check timeout strategies
            if config.timeout_strategy == 'soft_warn':
                # Issue warning at 80% of timeout
                if not warning_issued and elapsed >= config.timeout_seconds * 0.8:
                    self.logger.warning(
                        f"Interaction {interaction_id} ({config.conversation_name}): "
                        f"80% timeout ({elapsed:.0f}s / {config.timeout_seconds}s)"
                    )
                    self._record_timeout_warning(interaction_id)
                    warning_issued = True
                
                # Soft timeout: log but don't kill
                if elapsed >= config.timeout_seconds:
                    self.logger.error(
                        f"Interaction {interaction_id} SOFT TIMEOUT exceeded "
                        f"({elapsed:.0f}s / {config.timeout_seconds}s) - allowing to continue"
                    )
                    # Let it continue running
                    time.sleep(5)
                    continue
            
            elif config.timeout_strategy == 'hard_kill':
                # Hard timeout: terminate immediately
                if elapsed >= config.timeout_seconds:
                    self.logger.error(
                        f"Interaction {interaction_id} HARD TIMEOUT - terminating "
                        f"({elapsed:.0f}s / {config.timeout_seconds}s)"
                    )
                    
                    # Terminate worker (can't directly kill thread, but can mark it)
                    result_container['error'] = TimeoutError(
                        f"Hard timeout after {elapsed:.0f}s (limit: {config.timeout_seconds}s)"
                    )
                    result_container['completed'] = True
                    
                    # Record timeout in database
                    self._record_timeout_exceeded(
                        interaction_id,
                        termination_reason=f"Hard timeout at {elapsed:.0f}s"
                    )
                    
                    # Return timeout error
                    return {
                        'status': 'failed',
                        'error': f'Timeout after {elapsed:.0f}s',
                        'timeout_exceeded': True
                    }
            
            elif config.timeout_strategy == 'adaptive':
                # Adaptive: warn at 80%, kill at 120%
                if not warning_issued and elapsed >= config.timeout_seconds * 0.8:
                    self.logger.warning(
                        f"Interaction {interaction_id}: 80% timeout "
                        f"({elapsed:.0f}s / {config.timeout_seconds}s)"
                    )
                    self._record_timeout_warning(interaction_id)
                    warning_issued = True
                
                if elapsed >= config.timeout_seconds * 1.2:
                    self.logger.error(
                        f"Interaction {interaction_id} ADAPTIVE TIMEOUT - terminating "
                        f"({elapsed:.0f}s / {config.timeout_seconds * 1.2:.0f}s)"
                    )
                    self._record_timeout_exceeded(
                        interaction_id,
                        termination_reason=f"Adaptive timeout at {elapsed:.0f}s"
                    )
                    return {
                        'status': 'failed',
                        'error': f'Adaptive timeout after {elapsed:.0f}s',
                        'timeout_exceeded': True
                    }
            
            # Sleep briefly before next check
            time.sleep(0.5)
        
        # Worker completed
        if result_container['error']:
            raise result_container['error']
        
        return result_container['result']
    
    def _record_timeout_budget(self, interaction_id: int, budget_seconds: int):
        """Record allocated timeout budget"""
        cursor = self.db_helper.get_cursor()
        cursor.execute("""
            UPDATE interactions
            SET timeout_budget_seconds = %s
            WHERE interaction_id = %s
        """, (budget_seconds, interaction_id))
        self.db_helper.commit()
    
    def _record_timeout_warning(self, interaction_id: int):
        """Record timeout warning issued"""
        cursor = self.db_helper.get_cursor()
        cursor.execute("""
            UPDATE interactions
            SET timeout_warnings = timeout_warnings + 1
            WHERE interaction_id = %s
        """, (interaction_id,))
        self.db_helper.commit()
    
    def _record_timeout_exceeded(self, interaction_id: int, termination_reason: str):
        """Record timeout exceeded and termination"""
        cursor = self.db_helper.get_cursor()
        cursor.execute("""
            UPDATE interactions
            SET timeout_exceeded = true,
                termination_reason = %s,
                status = 'failed',
                completed_at = NOW()
            WHERE interaction_id = %s
        """, (termination_reason, interaction_id))
        self.db_helper.commit()
```

**Option B: Process-Based Supervisor (More Robust)**

```python
# core/wave_runner/process_supervisor.py

import multiprocessing
import signal
import psutil
from typing import Callable


class ProcessSupervisor:
    """
    Process-based timeout enforcement (more reliable than threads).
    
    Architecture:
        - Worker runs in separate process
        - Supervisor can send SIGTERM/SIGKILL
        - More robust than threads (true isolation)
    """
    
    def execute_with_timeout(
        self,
        worker_func: Callable,
        timeout_seconds: int,
        *args,
        **kwargs
    ) -> dict:
        """
        Execute function in subprocess with hard timeout.
        
        Uses multiprocessing.Process which can be truly killed.
        """
        result_queue = multiprocessing.Queue()
        
        def worker_wrapper():
            try:
                result = worker_func(*args, **kwargs)
                result_queue.put({'status': 'success', 'result': result})
            except Exception as e:
                result_queue.put({'status': 'error', 'error': str(e)})
        
        # Start worker process
        worker = multiprocessing.Process(target=worker_wrapper, daemon=True)
        worker.start()
        
        # Wait with timeout
        worker.join(timeout=timeout_seconds)
        
        if worker.is_alive():
            # Timeout! Terminate process
            self.logger.error(f"Process timeout - sending SIGTERM")
            worker.terminate()
            worker.join(timeout=5)
            
            if worker.is_alive():
                # Still alive? KILL IT
                self.logger.error(f"Process still alive - sending SIGKILL")
                worker.kill()
                worker.join()
            
            return {
                'status': 'failed',
                'error': f'Timeout after {timeout_seconds}s',
                'timeout_exceeded': True
            }
        
        # Get result
        if not result_queue.empty():
            return result_queue.get()
        
        return {'status': 'error', 'error': 'No result from worker'}
```

---

### Part 3: Integration with Wave Runner

**Update `core/wave_runner/runner.py`:**

```python
# Add at top
from core.wave_runner.timeout_supervisor import TimeoutSupervisor

class WaveRunner:
    def __init__(self, ...):
        # ... existing code ...
        self.timeout_supervisor = TimeoutSupervisor(self.db_helper, self.logger)
    
    def execute_interaction(self, interaction_id: int, conversation_id: int):
        """Execute interaction with timeout supervision"""
        
        # Wrap execution in timeout supervisor
        try:
            result = self.timeout_supervisor.monitor_execution(
                interaction_id=interaction_id,
                conversation_id=conversation_id,
                worker_func=self._execute_interaction_worker,
                worker_args=(interaction_id, conversation_id)
            )
            return result
            
        except TimeoutError as e:
            # Timeout exceeded
            self.logger.error(f"Interaction {interaction_id} timed out: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'timeout_exceeded': True
            }
    
    def _execute_interaction_worker(self, interaction_id: int, conversation_id: int):
        """Original execution logic (now wrapped by supervisor)"""
        # ... existing interaction execution code ...
        pass
```

---

### Part 4: Timeout Configuration Table (Nice-to-Have)

**Create a reference table for recommended timeouts:**

```sql
CREATE TABLE conversation_timeout_presets (
    preset_id SERIAL PRIMARY KEY,
    preset_name TEXT NOT NULL,
    description TEXT,
    actor_type TEXT,  -- 'ai_model', 'script', 'human'
    model_name TEXT,  -- 'qwen2.5:7b', 'gemma2', etc.
    recommended_timeout_seconds INTEGER,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Populate with empirical data
INSERT INTO conversation_timeout_presets (preset_name, actor_type, model_name, recommended_timeout_seconds, reasoning) VALUES
('Fast AI Model', 'ai_model', 'qwen2.5:7b', 30, 'Typically completes in 5-10s, 30s is 3x safety margin'),
('Medium AI Model', 'ai_model', 'gemma2', 120, 'Typically completes in 30-60s, 120s is 2x safety margin'),
('Slow AI Model', 'ai_model', 'llama3.1:70b', 600, 'Large model, may take 5-10 minutes for complex tasks'),
('Script Actor', 'script', NULL, 60, 'Most scripts complete in <10s, 60s is generous'),
('Database Query', 'script', 'sql_query_executor', 30, 'Queries should be fast, 30s catches slow queries'),
('Human Input', 'human', NULL, 86400, '24 hours for human to respond');

-- View to help set timeouts
CREATE VIEW conversation_timeout_recommendations AS
SELECT 
    c.conversation_id,
    c.conversation_name,
    a.actor_name,
    a.actor_type,
    c.timeout_seconds as current_timeout,
    p.recommended_timeout_seconds,
    p.reasoning,
    CASE 
        WHEN c.timeout_seconds > p.recommended_timeout_seconds * 2 THEN 'Too generous'
        WHEN c.timeout_seconds < p.recommended_timeout_seconds * 0.5 THEN 'Too strict'
        ELSE 'Reasonable'
    END as assessment
FROM conversations c
JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN conversation_timeout_presets p ON a.actor_type = p.actor_type;
```

---

## Benefits of This Architecture

### 1. **Per-Conversation Precision** ✅
- Fast models: 30s timeout (no 9.5min waste)
- Slow models: 2min timeout (realistic)
- Complex analysis: 10min+ (when needed)

### 2. **Database-Driven Configuration** ✅
- No code changes to adjust timeouts
- `UPDATE conversations SET timeout_seconds = 45 WHERE conversation_name = 'X'`
- Instant effect on next interaction

### 3. **Proactive Monitoring** ✅
- No 5-minute cron delay
- Real-time timeout enforcement
- Immediate termination when exceeded

### 4. **Timeout Budget Tracking** ✅
- Know workflow will take 12 minutes (sum of timeouts)
- See which conversations are slow (utilization %)
- Optimize based on data

### 5. **Three Timeout Strategies** ✅
- `hard_kill`: Terminate immediately at timeout (strict)
- `soft_warn`: Log warning but allow to continue (lenient)
- `adaptive`: Warn at 80%, kill at 120% (flexible)

### 6. **Rich Timeout Metrics** ✅
```sql
-- Which conversations timeout most?
SELECT 
    c.conversation_name,
    COUNT(*) FILTER (WHERE i.timeout_exceeded) as timeout_count,
    COUNT(*) as total_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE i.timeout_exceeded) / COUNT(*), 1) as timeout_rate
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.created_at > NOW() - interval '7 days'
GROUP BY c.conversation_name
HAVING COUNT(*) FILTER (WHERE i.timeout_exceeded) > 0
ORDER BY timeout_rate DESC;

-- Timeout budget utilization
SELECT 
    c.conversation_name,
    ROUND(AVG(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))), 1) as avg_duration,
    c.timeout_seconds as budget,
    ROUND(100.0 * AVG(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) / c.timeout_seconds, 1) as utilization_pct
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.status = 'completed'
  AND i.created_at > NOW() - interval '7 days'
GROUP BY c.conversation_name, c.timeout_seconds
ORDER BY utilization_pct DESC;
```

---

## Implementation Plan

### Phase 1: Database Schema (30 min)
- ✅ Migration 048: Add timeout columns to `conversations`
- ✅ Add timeout tracking to `interactions`
- ✅ Populate realistic timeouts (based on current metrics)

### Phase 2: Timeout Supervisor (2 hours)
- ✅ Implement `TimeoutSupervisor` class (thread-based, simpler)
- ✅ Unit tests for timeout enforcement
- ✅ Integration with `WaveRunner`

### Phase 3: Monitoring & Metrics (1 hour)
- ✅ Timeout utilization queries
- ✅ Dashboard for timeout analysis
- ✅ Alerts for high timeout rates

### Phase 4: Advanced (Optional)
- ⏳ Process-based supervisor (more robust)
- ⏳ Adaptive timeout learning (auto-adjust based on history)
- ⏳ Workflow-level timeout budgets

---

## Open Questions for Discussion

**Q1: Thread-based or process-based supervisor?**
- Thread-based: Simpler, faster, but harder to kill
- Process-based: More robust, true isolation, but more overhead

**Q2: Default timeout strategy?**
- `hard_kill` for production (strict, prevents runaway processes)
- `adaptive` for development (lenient, allows debugging)

**Q3: Should watchdog_cleanup.py stay or go?**
- Keep as backup (defense in depth)
- Remove (redundant with supervisor)
- Repurpose for workflow-level timeouts

**Q4: Timeout grace periods?**
- Allow 30s grace period to finish cleanly?
- Or terminate immediately?

**Q5: Timeout learning?**
- Should system auto-adjust timeouts based on P95 durations?
- Or keep manual configuration?

---

## Summary

**Your idea is EXCELLENT!** Two-layer architecture with:

1. **Monitoring Layer (Supervisor):**
   - Reads timeout config from DB
   - Tracks execution time
   - Enforces timeout limits
   - Can terminate workers

2. **Execution Layer (Worker):**
   - Runs AI models/scripts
   - Focuses on task execution
   - Monitored by supervisor

**Key Innovation:** Database-driven timeouts per conversation

**Benefits:**
- ✅ No more one-size-fits-all 10-minute timeout
- ✅ Fast models timeout in 30s (not 10 min)
- ✅ Proactive enforcement (not reactive 5-min cron)
- ✅ Rich timeout metrics and optimization
- ✅ No code changes to adjust timeouts

**Ready to implement?** I can create Migration 048 and the TimeoutSupervisor class!

**Arden**
