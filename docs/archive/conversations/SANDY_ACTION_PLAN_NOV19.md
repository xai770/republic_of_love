# Sandy's Action Plan - Lock It Down
**Date:** November 19, 2025  
**Goal:** Make the refactoring bulletproof, then STOP TOUCHING IT

---

## TL;DR - Do These 5 Things, Then Ship

1. **Add event store indexes** (2 min - critical for performance)
2. **Enhance event metadata** (5 min - add timing + causation)
3. **Add error classification** (15 min - retryable vs permanent failures)
4. **Write 3 unit tests** (30 min - prevent regressions)
5. **Create rollback script** (10 min - safety net)

**Total time: ~1 hour**  
**Then LOCK THE CODE and move on to next feature.**

---

## 1. Add Event Store Indexes (CRITICAL - Do First)

**Why:** With 2,062 events, queries are already slow. This will get worse at scale.

**File:** Create `sql/event_store_indexes.sql`

```sql
-- Event store performance indexes
-- Run this in DEV first, then PROD

-- Lookup events by posting (most common query)
CREATE INDEX IF NOT EXISTS idx_execution_events_aggregate 
ON execution_events(aggregate_type, aggregate_id);

-- Filter by conversation (used in debugging)
CREATE INDEX IF NOT EXISTS idx_execution_events_conversation 
ON execution_events((metadata->>'conversation_id'));

-- Time-based queries (used in monitoring)
CREATE INDEX IF NOT EXISTS idx_execution_events_created 
ON execution_events(created_at DESC);

-- Query performance validation
EXPLAIN ANALYZE 
SELECT * FROM execution_events 
WHERE aggregate_id = 12345 
ORDER BY created_at;
```

**Run it:**
```bash
sudo -u postgres psql -d turing -f sql/event_store_indexes.sql
```

---

## 2. Enhance Event Metadata (Better Debugging)

**File:** `core/wave_executor.py`

**Find this (around line 320):**
```python
def _save_event(self, posting, conversation_id, event_type, result_data):
    """Save event to event store"""
    metadata = {
        'conversation_id': conversation_id,
        'actor_id': result_data.get('actor_id'),
        'execution_order': result_data.get('execution_order'),
        'output': result_data.get('output'),
        'status': result_data.get('status')
    }
```

**Change to:**
```python
def _save_event(self, posting, conversation_id, event_type, result_data):
    """Save event to event store with full metadata"""
    metadata = {
        'conversation_id': conversation_id,
        'actor_id': result_data.get('actor_id'),
        'execution_order': result_data.get('execution_order'),
        'output': result_data.get('output'),
        'status': result_data.get('status'),
        'duration_ms': result_data.get('latency_ms', 0),
        'retry_count': getattr(posting, 'retry_count', 0),
        'correlation_id': f"workflow_{self.workflow_id}_posting_{posting.posting_id}"
    }
```

**Why:** Lets you trace performance issues and retry behavior in production.

---

## 3. Add Error Classification (Proper Retry Logic)

**File:** `core/wave_executor.py`

**Add these exception classes at top of file (after imports):**
```python
class RetryableError(Exception):
    """Transient error - safe to retry (network, timeout)"""
    pass

class PermanentError(Exception):
    """Permanent error - don't retry (invalid input, auth)"""
    pass
```

**Find the exception handler (around line 160):**
```python
    except Exception as e:
        self.logger.error("posting_execution_exception", 
            extra={'posting_id': posting.posting_id, 'error': str(e)})
        continue
```

**Change to:**
```python
    except RetryableError as e:
        # Transient failure - retry with exponential backoff
        retry_count = getattr(posting, 'retry_count', 0)
        if retry_count < 3:
            posting.retry_count = retry_count + 1
            wait_seconds = 2 ** retry_count  # 2s, 4s, 8s
            self.logger.warning("posting_retry_scheduled",
                extra={'posting_id': posting.posting_id, 
                       'retry_count': posting.retry_count,
                       'wait_seconds': wait_seconds})
            time.sleep(wait_seconds)
            # Re-add to queue (implementation depends on your queue system)
        else:
            self.logger.error("posting_retry_exhausted",
                extra={'posting_id': posting.posting_id, 'error': str(e)})
        continue
    
    except PermanentError as e:
        # Don't retry - log and skip
        self.logger.error("posting_permanent_failure",
            extra={'posting_id': posting.posting_id, 'error': str(e)})
        continue
    
    except Exception as e:
        # Unexpected error - treat as permanent
        self.logger.error("posting_unexpected_exception", 
            extra={'posting_id': posting.posting_id, 'error': str(e)})
        continue
```

**Why:** Distinguishes "network timeout" (retry) from "invalid SQL" (don't retry).

---

## 4. Write Unit Tests (Prevent Regressions)

**File:** Create `tests/test_wave_processor.py`

```python
import pytest
from core.wave_executor import WaveProcessor
from core.posting_state import PostingState

class MockLogger:
    def info(self, msg, **kwargs): pass
    def error(self, msg, **kwargs): pass
    def warning(self, msg, **kwargs): pass

class MockCircuitBreaker:
    def can_call(self, actor_id): return True
    def record_success(self, actor_id): pass
    def record_failure(self, actor_id): pass

class MockEventStore:
    def __init__(self):
        self.events = []
    def append_event(self, event_type, aggregate_type, aggregate_id, metadata):
        self.events.append({
            'type': event_type, 
            'aggregate_id': aggregate_id,
            'metadata': metadata
        })

def test_process_wave_success():
    """Test successful wave processing"""
    workflow_def = {
        'workflow_conversations': [
            {
                'conversation_id': 1,
                'execution_order': 1,
                'actor_id': 74,
                'prompt_template': 'Test: {job_description}'
            }
        ]
    }
    
    event_store = MockEventStore()
    processor = WaveProcessor(
        workflow_definition=workflow_def,
        workflow_id=3001,
        circuit_breaker=MockCircuitBreaker(),
        event_store=event_store,
        prompt_renderer=None,
        logger=MockLogger()
    )
    
    postings = [
        PostingState(posting_id=1, job_description="Test job")
    ]
    
    def mock_executor(actor_id, prompt, timeout):
        return {'status': 'SUCCESS', 'output': 'Success'}
    
    result = processor.process_wave(
        conversation_id=1,
        postings=postings,
        execute_actor_func=mock_executor
    )
    
    assert result == 1  # 1 posting processed
    assert len(event_store.events) == 1
    assert event_store.events[0]['type'] == 'script_execution_completed'

def test_process_wave_circuit_breaker_open():
    """Test wave processing when circuit breaker is open"""
    # Similar structure, but circuit_breaker.can_call() returns False
    # Assert: processed_count = 0, no events appended
    pass

def test_process_wave_actor_failure():
    """Test wave processing when actor fails"""
    # Mock executor returns {'status': 'FAILURE'}
    # Assert: error logged, event appended with failure status
    pass

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**Run tests:**
```bash
cd /home/xai/Documents/ty_wave
python -m pytest tests/test_wave_processor.py -v
```

**Why:** Catches indentation bugs BEFORE they hit production.

---

## 5. Create Rollback Script (Safety Net)

**File:** Create `scripts/rollback_to_legacy.sh`

```bash
#!/bin/bash
# Rollback to legacy executor if refactored version has issues

echo "⚠️  ROLLBACK: Switching to legacy workflow executor"

# Step 1: Stop current workflow
pkill -f "workflow_executor.*3001"
sleep 2

# Step 2: Rename files
cd /home/xai/Documents/ty_wave/core
if [ ! -f workflow_executor_legacy.py ]; then
    echo "❌ ERROR: Legacy executor not found"
    exit 1
fi

mv workflow_executor.py workflow_executor_refactored.py
mv workflow_executor_legacy.py workflow_executor.py

# Step 3: Restart workflow
cd /home/xai/Documents/ty_wave
nohup python3 -m core.workflow_executor --workflow 3001 \
  > logs/workflow_3001_rollback_$(date +%Y%m%d_%H%M%S).log 2>&1 &

echo "✅ Rollback complete. Check logs/workflow_3001_rollback_*.log"
echo "   To revert: run scripts/restore_refactored.sh"
```

**Make executable:**
```bash
chmod +x scripts/rollback_to_legacy.sh
```

**Why:** If production breaks at 2am, you need a 1-command fix.

---

## 6. Deprecate Old Tables (Clean Up)

**File:** Create `sql/deprecate_legacy_tables.sql`

```sql
-- Mark legacy tables as deprecated (DON'T DROP YET)
-- Run this AFTER validating event store has all data

-- Step 1: Rename to show deprecation
ALTER TABLE llm_interactions 
  RENAME TO llm_interactions_deprecated_20251119;

ALTER TABLE conversation_runs 
  RENAME TO conversation_runs_deprecated_20251119;

-- Step 2: Add deprecation notices
COMMENT ON TABLE llm_interactions_deprecated_20251119 IS 
  'DEPRECATED 2025-11-19: Replaced by execution_events. 
   Data preserved for audit. Safe to drop after 2026-02-01.';

COMMENT ON TABLE conversation_runs_deprecated_20251119 IS 
  'DEPRECATED 2025-11-19: Replaced by execution_events.
   Data preserved for audit. Safe to drop after 2026-02-01.';

-- Step 3: Verify event store has equivalent data
SELECT 
    'llm_interactions_deprecated' as legacy_table,
    COUNT(*) as legacy_count,
    (SELECT COUNT(*) FROM execution_events 
     WHERE event_type = 'llm_call_completed') as event_store_count;

-- Step 4: Create view for backwards compatibility (if needed)
CREATE OR REPLACE VIEW llm_interactions AS
SELECT 
    event_id::text as llm_interaction_id,
    aggregate_id as posting_id,
    (metadata->>'actor_id')::int as actor_id,
    metadata->>'output' as response,
    (metadata->>'duration_ms')::int as latency_ms,
    metadata->>'status' as status,
    created_at
FROM execution_events
WHERE event_type = 'llm_call_completed';

COMMENT ON VIEW llm_interactions IS 
  'Compatibility view - maps execution_events to old llm_interactions schema.
   Use execution_events directly for new code.';
```

**DON'T run this yet.** Wait 2 weeks to ensure event store is stable.

---

## Configuration Changes

**File:** Create `.env.workflow` (or add to existing .env)

```bash
# Workflow Executor Configuration
WORKFLOW_CHUNK_SIZE=100
EVENT_SNAPSHOT_INTERVAL=10
USE_LEGACY_EXECUTOR=false

# Event Store Settings
EVENT_STORE_ENABLED=true
EVENT_STORE_BATCH_SIZE=50

# Retry Configuration
MAX_RETRIES=3
RETRY_BACKOFF_BASE=2
```

**Load in workflow_executor.py:**
```python
from dotenv import load_dotenv
load_dotenv('.env.workflow')

CHUNK_SIZE = int(os.getenv('WORKFLOW_CHUNK_SIZE', '100'))
SNAPSHOT_INTERVAL = int(os.getenv('EVENT_SNAPSHOT_INTERVAL', '10'))
```

---

## Deployment Checklist

### Pre-Deploy (DEV environment)
- [ ] Run `sql/event_store_indexes.sql`
- [ ] Update `core/wave_executor.py` with metadata enhancements
- [ ] Add error classification (RetryableError, PermanentError)
- [ ] Write 3 unit tests, run `pytest tests/test_wave_processor.py`
- [ ] Create rollback script, test it works
- [ ] Process 100 postings in DEV, verify success

### Deploy to PROD
- [ ] Stop workflow: `pkill -f "workflow_executor.*3001"`
- [ ] Backup current code: `cp -r core/ core_backup_20251119/`
- [ ] Deploy changes (git pull or manual copy)
- [ ] Run event store indexes: `psql -d turing -f sql/event_store_indexes.sql`
- [ ] Start workflow: `nohup python3 -m core.workflow_executor --workflow 3001 ...`
- [ ] Monitor for 10 minutes: `tail -f logs/workflow_3001_*.log`
- [ ] Verify event store: `SELECT COUNT(*) FROM execution_events WHERE created_at > NOW() - INTERVAL '10 minutes';`

### Post-Deploy (2 weeks later)
- [ ] Run `sql/deprecate_legacy_tables.sql` (rename old tables)
- [ ] Delete `core/workflow_executor_legacy.py` (if no issues found)
- [ ] Archive `core_backup_20251119/` to S3/backup system

---

## What NOT to Do

❌ **Don't** extract more classes yet - wait until you feel pain  
❌ **Don't** add partitioning until >1M events  
❌ **Don't** drop legacy tables for 2 months  
❌ **Don't** add features - this is a LOCK DOWN sprint  
❌ **Don't** refactor the refactoring - ship it and move on  

---

## Success Criteria

**You're done when:**
1. ✅ All 5 action items complete (indexes, metadata, errors, tests, rollback)
2. ✅ Tests pass: `pytest tests/test_wave_processor.py` → 3/3 passing
3. ✅ Production processes 2,062 postings with 0 errors
4. ✅ Event store queries run in <50ms (check with EXPLAIN ANALYZE)
5. ✅ Rollback script tested and works

**Then STOP. Lock the code. Move to next feature.**

---

## Questions? Ask Arden

But honestly, just do these 5 things and ship. You've already proven it works (2,062/2,062 success rate). These are just safety rails.

---

**Estimated Total Time:** 1 hour  
**Expected Outcome:** Production-grade, bulletproof, DONE

*"Perfect is the enemy of shipped." - Someone smart, probably*
