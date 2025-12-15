# Turing System Improvement Roadmap - Phase 2

**Date:** November 13, 2025  
**Status:** 🚀 READY TO START  
**Previous Phase:** All 10 tasks completed (2 hours) + Critical connection pool bug fixed  
**Goal:** Production hardening and operational excellence

---

## Overview

Phase 1 achieved system stability (connection pooling, circuit breaker, validation). Phase 2 focuses on **operational visibility, maintainability, and production readiness**.

**Core Principle:** Make the invisible visible. If you can't see it, you can't fix it.

---

## Critical Issues (Must Fix)

### 1. Replace Print Statements with Structured Logging ⚡ P0
**Priority:** Critical - Blocking production deployment  
**Effort:** 1 hour  
**Risk:** None (additive only)

**Current Problem:**
- 97+ `print()` statements in core modules
- No machine-readable logs
- Debugging requires SSH + tail -f
- No historical log analysis
- Can't search/filter/aggregate

**Impact:**
```python
# Current (wave_batch_processor.py):
print(f"  Posting {posting.posting_id}: ✓ ({len(output)} chars) → {status}")

# Lost forever when terminal disconnects
# Can't query: "Show me all failed postings"
# Can't aggregate: "Average latency per conversation"
```

**Solution:**
```python
# Replace with structured logging
from core.logging_config import get_logger

logger = get_logger(__name__)

# Rich, queryable, persistent logs
logger.info("posting_completed",
    posting_id=posting.posting_id,
    conversation_id=conversation_id,
    conversation_name=conv['canonical_name'],
    output_length=len(output),
    next_conversation=status,
    latency_ms=execution_result.get('latency_ms', 0),
    actor_id=conv['actor_id'],
    actor_name=conv['actor_name'],
    execution_order=conv['execution_order']
)
```

**Files to Change:**
- `core/wave_batch_processor.py` - 50 print() statements
- `core/actor_router.py` - 1 print() statement  
- `core/workflow_executor.py` - 25 print() statements
- `core/result_saver.py` - 13 print() statements
- `core/error_handler.py` - 2 print() statements
- `core/taxonomy_helper.py` - 1 print() statement

**Validation:**
```bash
# Run workflow with JSON logging
python3 -m core.wave_batch_processor --workflow 3001 --limit 5 2>&1 | jq

# Should output structured JSON:
{
  "event": "posting_completed",
  "posting_id": 123,
  "conversation_name": "gemma3_extract",
  "output_length": 1234,
  "latency_ms": 2500,
  "timestamp": "2025-11-13T22:30:45.123456",
  "level": "info"
}

# Query logs
cat /tmp/workflow_3001.log | jq 'select(.event == "posting_failed")'
cat /tmp/workflow_3001.log | jq '.latency_ms' | awk '{sum+=$1; count++} END {print sum/count}'
```

**Expected Impact:**
- Enable production debugging without SSH
- Track performance metrics over time
- Aggregate cost/latency/throughput
- Alert on anomalies
- Audit trail for compliance

---

### 2. Fix Remaining Connection Leaks ⚡ P0
**Priority:** Critical - System stability  
**Effort:** 30 minutes  
**Risk:** Low (consistent with Phase 1 fixes)

**Current Problem:**
After fixing `wave_batch_processor.py` and `actor_router.py`, there are **43 more `conn.close()` calls** that will leak connections:

- `core/workflow_executor.py` - 18 instances
- `core/turing_orchestrator.py` - 12 instances  
- `core/recipe_engine.py` - 11 instances
- `core/result_saver.py` - 2 instances

**Why This Matters:**
These modules are used by **other workflows**. When they run, they'll exhaust the pool just like wave_batch_processor did.

**Solution:**
```bash
# Global search and replace in all core/ files
cd /home/xai/Documents/ty_learn/core

# Find all conn.close() calls
grep -n "conn.close()" *.py

# Replace with return_connection(conn)
sed -i 's/conn\.close()/return_connection(conn)/g' workflow_executor.py
sed -i 's/conn\.close()/return_connection(conn)/g' turing_orchestrator.py
sed -i 's/conn\.close()/return_connection(conn)/g' recipe_engine.py
sed -i 's/conn\.close()/return_connection(conn)/g' result_saver.py
sed -i 's/conn\.close()/return_connection(conn)/g' taxonomy_helper.py

# Add import where missing
# Verify no compilation errors
python3 -c "from core import workflow_executor, turing_orchestrator, recipe_engine, result_saver"
```

**Validation:**
```bash
# Should return 0
grep -r "conn\.close()" core/*.py | wc -l

# All should use return_connection
grep -r "return_connection(conn)" core/*.py | wc -l  # Should be ~50
```

---

### 3. Add Error Tracking to Wave Processor ⚡ P1
**Priority:** High - Operational visibility  
**Effort:** 30 minutes  
**Risk:** None (additive only)

**Current Problem:**
When posting 4567 fails at wave 15 with "Actor timeout", the error goes to stdout and disappears. No database record, no historical tracking, no debugging trail.

**Solution:**
```python
# core/wave_batch_processor.py - Add error tracking to _process_wave()

def _process_wave(self, conversation_id: int, postings: List[PostingState]):
    """Process wave with comprehensive error tracking"""
    
    for posting in postings:
        try:
            # ... existing execution logic ...
            
        except Exception as e:
            # Log to database for persistence
            self._log_workflow_error(
                posting_id=posting.posting_id,
                workflow_run_id=posting.workflow_run_id,
                conversation_id=conversation_id,
                error_type=type(e).__name__,
                error_message=str(e),
                context={
                    'execution_order': conv['execution_order'],
                    'conversation_name': conv['canonical_name'],
                    'actor_id': conv['actor_id'],
                    'actor_name': conv['actor_name'],
                    'prompt_length': len(prompt),
                    'output_length': len(output) if 'output' in locals() else 0
                }
            )
            
            # Log structured event
            logger.error("posting_execution_failed",
                posting_id=posting.posting_id,
                conversation_id=conversation_id,
                error=str(e),
                traceback=traceback.format_exc()
            )
            
            # Mark posting as failed, continue to next
            posting.is_terminal = True
            posting.error = str(e)
            continue

def _log_workflow_error(self, posting_id: int, workflow_run_id: int,
                        conversation_id: int, error_type: str, 
                        error_message: str, context: Dict[str, Any]):
    """Log error to workflow_errors table for historical tracking"""
    try:
        with db_transaction() as cursor:
            cursor.execute("""
                INSERT INTO workflow_errors (
                    workflow_run_id, posting_id, conversation_id,
                    error_type, error_message, context, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (
                workflow_run_id, posting_id, conversation_id,
                error_type, error_message, json.dumps(context)
            ))
    except Exception as log_error:
        logger.warning("failed_to_log_error", error=str(log_error))
```

**Database Support:**
```sql
-- Already exists from migration 012
SELECT * FROM workflow_errors WHERE created_at > NOW() - INTERVAL '1 hour';

-- Create view for easy querying
CREATE OR REPLACE VIEW v_workflow_error_summary AS
SELECT 
    DATE_TRUNC('hour', created_at) as error_hour,
    error_type,
    COUNT(*) as error_count,
    COUNT(DISTINCT posting_id) as affected_postings,
    STRING_AGG(DISTINCT error_message, ' | ') as sample_messages
FROM workflow_errors
GROUP BY error_hour, error_type
ORDER BY error_hour DESC, error_count DESC;
```

**Validation:**
```bash
# Run workflow with intentional failures
python3 -m core.wave_batch_processor --workflow 3001 --limit 10

# Check error tracking
psql -U base_admin -d turing -c "
SELECT error_type, COUNT(*) 
FROM workflow_errors 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY error_type;
"
```

---

## Medium Priority (Should Fix)

### 4. Complete Entry Point Routing Migration 🎯 P1
**Priority:** Medium - Reduces brittleness  
**Effort:** 1 hour  
**Risk:** Medium (changes routing logic)

**Current Problem:**
`_get_pending_postings()` uses hardcoded string matching:
```python
if not stage_info['extracted_summary']:
    start_conv_name = 'gemma3_extract'  # FRAGILE!
elif not stage_info['has_skills']:
    start_conv_name = 'taxonomy_skill_extraction'  # FRAGILE!
```

Migration 018 added `is_entry_point` flags but the code wasn't updated.

**Solution:**
```python
# core/wave_batch_processor.py - _get_pending_postings()

def _get_pending_postings(self, limit: Optional[int] = None) -> List[PostingState]:
    """Fetch postings with entry point routing"""
    
    # Map stages to entry point execution orders
    STAGE_TO_ORDER = {
        'needs_summary': 3,   # execution_order where is_entry_point=true
        'needs_skills': 12,   # execution_order where is_entry_point=true
        'needs_ihl': 19       # execution_order where is_entry_point=true
    }
    
    for row in results:
        state = PostingState(row['posting_id'], row['job_description'])
        
        # Determine stage from SQL results
        if not row['has_summary']:
            entry_order = STAGE_TO_ORDER['needs_summary']
        elif not row['has_skills']:
            entry_order = STAGE_TO_ORDER['needs_skills']
        elif not row['has_ihl']:
            entry_order = STAGE_TO_ORDER['needs_ihl']
        else:
            continue  # Posting complete
        
        # Look up entry point conversation by order (from workflow definition)
        entry_conv_id = self.workflow_definition['entry_points'].get(entry_order)
        
        if not entry_conv_id:
            logger.error("missing_entry_point",
                workflow_id=self.workflow_id,
                execution_order=entry_order,
                posting_id=state.posting_id
            )
            continue
        
        state.current_conversation_id = entry_conv_id
        postings.append(state)
    
    return postings
```

**Update _load_workflow() to build entry point map:**
```python
def _load_workflow(self) -> Dict[str, Any]:
    """Load workflow with entry point mapping"""
    # ... existing code ...
    
    # Build entry point map: {execution_order: conversation_id}
    workflow['entry_points'] = {}
    
    cursor.execute("""
        SELECT wc.conversation_id, wc.execution_order
        FROM workflow_conversations wc
        WHERE wc.workflow_id = %s 
          AND wc.is_entry_point = TRUE
        ORDER BY wc.execution_order
    """, (self.workflow_id,))
    
    for row in cursor.fetchall():
        workflow['entry_points'][row['execution_order']] = row['conversation_id']
    
    logger.info("workflow_loaded",
        workflow_id=self.workflow_id,
        entry_points=workflow['entry_points'],
        conversation_count=len(workflow['conversations'])
    )
    
    return workflow
```

**Validation:**
```bash
# Test routing still works
python3 -m core.wave_batch_processor --workflow 3001 --limit 5

# Verify entry points loaded
grep "entry_points" /tmp/workflow_3001_*.log | jq
```

---

### 5. Add Circuit Breaker State Visibility 📊 P1
**Priority:** Medium - Operational monitoring  
**Effort:** 45 minutes  
**Risk:** None (additive only)

**Current Problem:**
Circuit breaker opens/closes but there's no visibility:
- Which actors are paused?
- When did they fail?
- When will they retry?
- Historical failure patterns?

**Solution:**
```sql
-- sql/migrations/019_circuit_breaker_state.sql
BEGIN;

CREATE TABLE circuit_breaker_events (
    event_id SERIAL PRIMARY KEY,
    actor_id INTEGER NOT NULL REFERENCES actors(actor_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('failure', 'open', 'half_open', 'closed', 'success')),
    failure_count INTEGER,
    cooldown_seconds INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    context JSONB
);

CREATE INDEX idx_circuit_breaker_actor ON circuit_breaker_events(actor_id, created_at DESC);
CREATE INDEX idx_circuit_breaker_type ON circuit_breaker_events(event_type, created_at DESC);

COMMENT ON TABLE circuit_breaker_events IS 'Historical log of circuit breaker state changes';

-- Current circuit breaker state view
CREATE VIEW v_circuit_breaker_status AS
SELECT 
    a.actor_id,
    a.actor_name,
    a.actor_type,
    CASE 
        WHEN recent.event_type = 'open' THEN 'OPEN'
        WHEN recent.event_type = 'half_open' THEN 'HALF_OPEN'
        ELSE 'CLOSED'
    END as circuit_state,
    recent.failure_count,
    recent.created_at as last_state_change,
    recent.cooldown_seconds,
    EXTRACT(EPOCH FROM (recent.created_at + (recent.cooldown_seconds || ' seconds')::INTERVAL - NOW())) as cooldown_remaining_sec
FROM actors a
LEFT JOIN LATERAL (
    SELECT event_type, failure_count, cooldown_seconds, created_at
    FROM circuit_breaker_events
    WHERE actor_id = a.actor_id
    ORDER BY created_at DESC
    LIMIT 1
) recent ON true
WHERE a.enabled = TRUE
ORDER BY recent.created_at DESC NULLS LAST;

COMMENT ON VIEW v_circuit_breaker_status IS 'Real-time circuit breaker state for all actors';

INSERT INTO migration_log (migration_number, migration_name, status)
VALUES ('019', 'circuit_breaker_state', 'SUCCESS');

COMMIT;
```

**Integration with circuit_breaker.py:**
```python
# core/circuit_breaker.py - Add database logging

def record_failure(self, actor_id: int) -> None:
    """Record failure and log to database"""
    self.failures[actor_id] = self.failures.get(actor_id, 0) + 1
    
    # Log to database
    self._log_event(actor_id, 'failure', self.failures[actor_id])
    
    if self.failures[actor_id] >= self.threshold:
        self.opened_at[actor_id] = time.time()
        self._log_event(actor_id, 'open', self.failures[actor_id], 
                       cooldown_seconds=self.timeout)
        logger.warning("circuit_breaker_opened",
            actor_id=actor_id,
            failure_count=self.failures[actor_id],
            cooldown_seconds=self.timeout
        )

def record_success(self, actor_id: int) -> None:
    """Record success and log to database"""
    if actor_id in self.failures:
        del self.failures[actor_id]
    if actor_id in self.opened_at:
        del self.opened_at[actor_id]
        self._log_event(actor_id, 'closed', 0)
        logger.info("circuit_breaker_closed", actor_id=actor_id)
    else:
        self._log_event(actor_id, 'success', 0)

def _log_event(self, actor_id: int, event_type: str, failure_count: int, 
               cooldown_seconds: Optional[int] = None):
    """Log circuit breaker event to database"""
    try:
        with db_transaction() as cursor:
            cursor.execute("""
                INSERT INTO circuit_breaker_events 
                (actor_id, event_type, failure_count, cooldown_seconds)
                VALUES (%s, %s, %s, %s)
            """, (actor_id, event_type, failure_count, cooldown_seconds))
    except Exception as e:
        logger.warning("failed_to_log_circuit_breaker_event", error=str(e))
```

**Validation:**
```bash
# Apply migration
bash sql/apply_migration_019.sh

# Check circuit breaker status
psql -U base_admin -d turing -c "SELECT * FROM v_circuit_breaker_status;"

# Monitor events
watch -n 5 "psql -U base_admin -d turing -c 'SELECT * FROM circuit_breaker_events ORDER BY created_at DESC LIMIT 10;'"
```

---

### 6. Optimize Checkpoint Strategy 💾 P2
**Priority:** Medium - Reduce database bloat  
**Effort:** 1 hour  
**Risk:** Medium (changes persistence logic)

**Current Problem:**
Checkpoint after EVERY conversation:
- 2,000 postings × 12 conversations = 24,000 rows per workflow run
- 95% of checkpoints are never used (only for crash recovery)
- Database bloat, slow queries

**Better Strategy:**
Checkpoint only at **stage boundaries** (major milestones):
- After stage 1 complete (summary extraction done)
- After stage 2 complete (skills extraction done)
- After stage 3 complete (IHL scoring done)

**Solution:**
```python
# core/wave_batch_processor.py - Add checkpoint_conversations config

CHECKPOINT_CONVERSATIONS = {
    'save_summary_check_ihl',      # After stage 1 (order 10)
    'save_skills_check_ihl',       # After stage 2 (order 15)
    'w1124_c1_analyst'             # After stage 3 (order 19)
}

def _process_wave(self, conversation_id: int, postings: List[PostingState]):
    """Process wave with strategic checkpointing"""
    
    for posting in postings:
        # ... existing execution logic ...
        
        # Only checkpoint at strategic milestones
        conv_name = conv['canonical_name']
        if conv_name in CHECKPOINT_CONVERSATIONS:
            self._save_checkpoint(posting)
            logger.debug("checkpoint_saved",
                posting_id=posting.posting_id,
                conversation=conv_name,
                execution_order=conv['execution_order']
            )
```

**Database Cleanup:**
```sql
-- Delete checkpoints older than 7 days (only keep recent for debugging)
DELETE FROM posting_state_checkpoints 
WHERE created_at < NOW() - INTERVAL '7 days';

-- Add index for faster cleanup
CREATE INDEX idx_checkpoint_created ON posting_state_checkpoints(created_at);
```

**Validation:**
```bash
# Run workflow with new checkpoint strategy
python3 -m core.wave_batch_processor --workflow 3001 --limit 100

# Check checkpoint count (should be ~300 instead of ~1200)
psql -U base_admin -d turing -c "
SELECT COUNT(*) 
FROM posting_state_checkpoints 
WHERE created_at > NOW() - INTERVAL '1 hour';
"
```

---

## Nice to Have (Future)

### 7. Add Workflow Metrics Dashboard 📊 P2
**Priority:** Low - Operational excellence  
**Effort:** 2 hours  
**Risk:** None (view only)

**Solution:**
```sql
-- sql/migrations/020_workflow_metrics.sql
BEGIN;

CREATE TABLE workflow_metrics (
    metric_id SERIAL PRIMARY KEY,
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(workflow_run_id),
    conversation_id INTEGER REFERENCES conversations(conversation_id),
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    metric_unit TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_metrics_run ON workflow_metrics(workflow_run_id);
CREATE INDEX idx_metrics_conversation ON workflow_metrics(conversation_id);
CREATE INDEX idx_metrics_name ON workflow_metrics(metric_name, created_at DESC);

-- Metrics view
CREATE VIEW v_workflow_performance AS
SELECT 
    w.workflow_name,
    c.conversation_name,
    a.actor_name,
    COUNT(*) as execution_count,
    AVG(wm.metric_value) FILTER (WHERE metric_name = 'latency_ms') as avg_latency_ms,
    SUM(wm.metric_value) FILTER (WHERE metric_name = 'tokens_input') as total_tokens_input,
    SUM(wm.metric_value) FILTER (WHERE metric_name = 'tokens_output') as total_tokens_output,
    SUM(wm.metric_value) FILTER (WHERE metric_name = 'cost_usd') as total_cost_usd
FROM workflow_metrics wm
JOIN workflow_runs wr ON wr.workflow_run_id = wm.workflow_run_id
JOIN workflows w ON w.workflow_id = wr.workflow_id
LEFT JOIN conversations c ON c.conversation_id = wm.conversation_id
LEFT JOIN actors a ON a.actor_id = c.actor_id
WHERE wm.created_at > NOW() - INTERVAL '24 hours'
GROUP BY w.workflow_name, c.conversation_name, a.actor_name
ORDER BY total_cost_usd DESC NULLS LAST;

INSERT INTO migration_log (migration_number, migration_name, status)
VALUES ('020', 'workflow_metrics', 'SUCCESS');

COMMIT;
```

---

### 8. Enforce Workflow Validation on Start 🔍 P2
**Priority:** Low - Prevent misconfigurations  
**Effort:** 30 minutes  
**Risk:** None (validation only)

**Solution:**
```python
# core/wave_batch_processor.py - Add validation in __init__

def __init__(self, workflow_id: int):
    """Initialize processor with validation"""
    self.workflow_id = workflow_id
    
    # Validate workflow configuration BEFORE loading
    validation_result = self._validate_workflow()
    if not validation_result['is_valid']:
        errors = '\n  - '.join(validation_result['errors'])
        raise ValueError(f"Workflow {workflow_id} validation failed:\n  - {errors}")
    
    # Load workflow after validation passes
    self.workflow_definition = self._load_workflow()
    self.circuit_breaker = CircuitBreaker()
    
    logger.info("workflow_processor_initialized",
        workflow_id=workflow_id,
        conversation_count=len(self.workflow_definition['conversations'])
    )

def _validate_workflow(self) -> Dict[str, Any]:
    """Validate workflow configuration before execution"""
    # Reuse validation logic from tools/validate_workflow.py
    from tools.validate_workflow import WorkflowValidator
    
    validator = WorkflowValidator(self.workflow_id)
    return validator.validate()
```

---

### 9. Archive Cleanup 🧹 P3
**Priority:** Low - Code hygiene  
**Effort:** 15 minutes  
**Risk:** None (deletion only)

**Current Problem:**
- `archive/` has 3 copies of `by_recipe_runner.py`
- Multiple legacy implementations of same modules
- 500+ MB of redundant code

**Solution:**
```bash
# Verify core/ modules work
python3 -c "from core import wave_batch_processor, actor_router, workflow_executor"

# Aggressive cleanup
cd /home/xai/Documents/ty_learn
rm -rf archive/scripts_nov12_2025/legacy/
rm -rf archive/experimental_scripts_2025/

# Keep one compressed backup
tar -czf archive_full_backup_$(date +%Y%m%d).tar.gz archive/
mv archive_full_backup_*.tar.gz backups/

# Document what was archived
echo "Archived legacy code to backups/ on $(date)" >> archive/ARCHIVE_LOG.md
```

---

## Implementation Schedule

### Day 1: Critical Fixes (3 hours)
- **Hour 1**: Replace all print() with structured logging
- **Hour 2**: Fix remaining conn.close() leaks + error tracking
- **Hour 3**: Testing & validation

### Day 2: Operational Visibility (3 hours)
- **Hour 1**: Complete entry point routing migration
- **Hour 2**: Add circuit breaker state tracking
- **Hour 3**: Optimize checkpoint strategy

### Day 3: Nice to Have (2 hours)
- **Hour 1**: Workflow metrics dashboard
- **Hour 2**: Validation enforcement + archive cleanup

---

## Success Metrics

### System Reliability
- [ ] Zero connection pool exhaustions in 24h of operation
- [ ] All errors logged to database (100% tracking)
- [ ] Circuit breaker events visible in monitoring

### Operational Visibility
- [ ] Can query "Show me all failed postings in last hour"
- [ ] Can calculate "Average cost per posting"
- [ ] Can track "GPU utilization per conversation"

### Code Quality
- [ ] Zero print() statements in core/ modules
- [ ] All database operations use return_connection()
- [ ] Archive reduced by 80%

---

## Rollout Plan

### Phase 2.1: Critical Fixes (Deploy Day 1)
1. Morning: Implement logging + connection fixes
2. Afternoon: Deploy to staging
3. Evening: Monitor for 4 hours
4. Night: Production deployment

### Phase 2.2: Operational Improvements (Deploy Day 2)
1. Morning: Implement entry points + circuit breaker tracking
2. Afternoon: Deploy to staging
3. Evening: Production deployment

### Phase 2.3: Nice to Have (Deploy Day 3)
1. Morning: Implement metrics + validation
2. Afternoon: Deploy to production

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Logging overhead slows execution | Med | Low | Use async logging, batch writes |
| Entry point routing breaks existing workflows | High | Low | Thorough testing, phased rollout |
| Checkpoint optimization loses state | High | Low | Keep old logic as fallback |
| Breaking changes in refactoring | Med | Low | Comprehensive testing before deployment |

---

## Post-Implementation Validation

After each phase:

```bash
# 1. Workflow executes successfully
python3 -m core.wave_batch_processor --workflow 3001 --limit 100

# 2. Logs are structured and queryable
cat /tmp/workflow_3001_*.log | jq 'select(.event == "posting_failed")' | wc -l

# 3. No connection leaks
psql -U base_admin -d turing -c "
SELECT COUNT(*) FROM pg_stat_activity WHERE usename = 'base_admin';
"
# Should stay < 10 during execution

# 4. Errors tracked in database
psql -U base_admin -d turing -c "
SELECT * FROM v_workflow_error_summary 
WHERE error_hour > NOW() - INTERVAL '1 hour';
"

# 5. Circuit breaker visible
psql -U base_admin -d turing -c "
SELECT * FROM v_circuit_breaker_status 
WHERE circuit_state != 'CLOSED';
"
```

---

**Document Version:** 1.0  
**Last Updated:** November 13, 2025  
**Owner:** Arden & xai  
**Status:** Ready for Implementation  
**Estimated Total Time:** 8 hours (vs Phase 1: 2 hours)

Let's get cracking! 🚀
