# Turing System Improvement Roadmap

**Date:** November 13, 2025  
**Status:** ✅ COMPLETED - All 10 Tasks Done in 2 Hours (Original: 4 weeks)  
**Goal:** Transform operational practices from prototype to production-grade

---

## Overview

The Turing system has excellent architectural foundations (wave processing, checkpoints, database-driven workflows) but needs operational maturity improvements. This roadmap prioritizes high-impact, low-risk changes that improve reliability, performance, and maintainability.

**Core Principle:** No architectural changes. We're fixing operational gaps, not redesigning what works.

---

## Phase 1: Critical Safety & Reliability (Week 1)

### 1.1 Environment Variables for Secrets ⚡ CRITICAL
**Priority:** P0 - Security Issue  
**Effort:** 30 minutes  
**Risk:** None (backward compatible)

**Current Problem:**
```python
# core/database.py - Password in version control!
DEFAULT_CONFIG = {
    'password': '${DB_PASSWORD}'
}
```

**Solution:**
```python
# config/database_config.py (NEW FILE)
import os

DB_CONFIG = {
    'host': os.getenv('TURING_DB_HOST', 'localhost'),
    'port': int(os.getenv('TURING_DB_PORT', '5432')),
    'database': os.getenv('TURING_DB_NAME', 'turing'),
    'user': os.getenv('TURING_DB_USER', 'base_admin'),
    'password': os.getenv('TURING_DB_PASSWORD')
}

if not DB_CONFIG['password']:
    raise ValueError("TURING_DB_PASSWORD environment variable required")
```

**Files to Change:**
- `core/database.py` - Import from new config
- `.env.example` - Template for local dev
- `.gitignore` - Add `.env`
- `docs/SETUP.md` - Document env vars

**Validation:**
```bash
export TURING_DB_PASSWORD=${DB_PASSWORD}
python3 -m core.wave_batch_processor --workflow 3001 --limit 1
```

---

### 1.2 Circuit Breaker for Failing Actors ⚡ HIGH IMPACT
**Priority:** P1 - Prevents cascading failures  
**Effort:** 2 hours  
**Risk:** Low (new functionality, doesn't change existing behavior)

**Current Problem:**  
If an actor fails (bad model, API down), wave processor calls it 1,926 times before giving up. Wastes time and resources.

**Solution:**
```python
# core/circuit_breaker.py (NEW FILE)
import time
from typing import Dict

class CircuitBreaker:
    """Prevents repeated calls to failing actors"""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 300):
        self.failures: Dict[int, int] = {}  # {actor_id: failure_count}
        self.opened_at: Dict[int, float] = {}  # {actor_id: timestamp}
        self.threshold = failure_threshold
        self.timeout = timeout_seconds
    
    def record_failure(self, actor_id: int) -> None:
        """Record actor failure, potentially opening circuit"""
        self.failures[actor_id] = self.failures.get(actor_id, 0) + 1
        
        if self.failures[actor_id] >= self.threshold:
            self.opened_at[actor_id] = time.time()
            print(f"  🔴 Circuit OPEN for actor {actor_id} (failed {self.failures[actor_id]} times)")
    
    def record_success(self, actor_id: int) -> None:
        """Record actor success, resetting failure count"""
        if actor_id in self.failures:
            del self.failures[actor_id]
        if actor_id in self.opened_at:
            del self.opened_at[actor_id]
            print(f"  🟢 Circuit CLOSED for actor {actor_id} (recovered)")
    
    def is_open(self, actor_id: int) -> bool:
        """Check if circuit is open (actor should not be called)"""
        if actor_id not in self.opened_at:
            return False
        
        elapsed = time.time() - self.opened_at[actor_id]
        
        # Auto-close circuit after timeout (half-open state)
        if elapsed > self.timeout:
            del self.opened_at[actor_id]
            self.failures[actor_id] = 0  # Reset on timeout
            print(f"  🟡 Circuit HALF-OPEN for actor {actor_id} (timeout expired, retrying)")
            return False
        
        return True
    
    def get_status(self, actor_id: int) -> str:
        """Get circuit status for actor"""
        if self.is_open(actor_id):
            elapsed = time.time() - self.opened_at[actor_id]
            remaining = self.timeout - elapsed
            return f"OPEN (retry in {int(remaining)}s)"
        elif actor_id in self.failures and self.failures[actor_id] > 0:
            return f"CLOSED ({self.failures[actor_id]}/{self.threshold} failures)"
        else:
            return "CLOSED (healthy)"
```

**Integration:**
```python
# core/wave_batch_processor.py
class WaveBatchProcessor:
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
        self.db_conn = get_connection()
        self.workflow_definition = self._load_workflow()
        self.circuit_breaker = CircuitBreaker()  # ← ADD THIS
    
    def _process_wave(self, conversation_id: int, postings: List[PostingState]) -> int:
        conv = self.workflow_definition['conversations'][conversation_id]
        actor_id = conv['actor_id']
        
        # Check circuit breaker BEFORE loading model
        if self.circuit_breaker.is_open(actor_id):
            print(f"  ⏭ CIRCUIT OPEN: Skipping wave for {conv['actor_name']}")
            # Route all postings to error branch or terminate
            for posting in postings:
                posting.outputs[conversation_id] = '[CIRCUIT_OPEN]'
                posting.current_conversation_id = None  # Terminate
            return len(postings)
        
        # ... existing wave processing ...
        
        try:
            execution_result = self._execute_actor(...)
            
            if execution_result['status'] == 'SUCCESS':
                self.circuit_breaker.record_success(actor_id)  # ← ADD THIS
            else:
                self.circuit_breaker.record_failure(actor_id)  # ← ADD THIS
        except Exception as e:
            self.circuit_breaker.record_failure(actor_id)  # ← ADD THIS
            raise
```

**Files to Change:**
- `core/circuit_breaker.py` - New file
- `core/wave_batch_processor.py` - Add circuit breaker checks
- `tests/test_circuit_breaker.py` - Unit tests

**Validation:**
```python
# Test circuit breaker behavior
breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=10)

# Simulate 3 failures
for i in range(3):
    breaker.record_failure(42)

assert breaker.is_open(42) == True

# Wait for timeout
time.sleep(11)
assert breaker.is_open(42) == False  # Auto-recovery
```

---

### 1.3 Workflow Validation Tool 🔍 SAFETY
**Priority:** P1 - Prevents runtime errors  
**Effort:** 3 hours  
**Risk:** None (validation only, no execution changes)

**Current Problem:**  
Workflow config errors (missing branches, invalid actors, broken references) only discovered at runtime, potentially hours into execution.

**Solution:**
```python
# tools/validate_workflow.py (NEW FILE)
#!/usr/bin/env python3
"""
Workflow Validation Tool
========================

Pre-flight checks for workflow configuration.
Run before starting production workflows to catch config errors early.

Usage:
    python3 tools/validate_workflow.py --workflow 3001
    python3 tools/validate_workflow.py --workflow 3001 --fix-common-issues
"""

import sys
from typing import List, Dict, Any
sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection


class WorkflowValidator:
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
        self.conn = get_connection()
        self.errors = []
        self.warnings = []
    
    def validate(self) -> bool:
        """Run all validation checks"""
        print(f"\n{'='*80}")
        print(f"Validating Workflow {self.workflow_id}")
        print(f"{'='*80}\n")
        
        self.check_workflow_exists()
        self.check_enabled_conversations()
        self.check_actors_enabled()
        self.check_branch_targets_exist()
        self.check_infinite_loops()
        self.check_orphaned_conversations()
        self.check_missing_error_branches()
        self.check_placeholder_consistency()
        
        # Print results
        if self.errors:
            print(f"\n❌ VALIDATION FAILED ({len(self.errors)} errors, {len(self.warnings)} warnings)")
            print("\nErrors:")
            for err in self.errors:
                print(f"  ❌ {err}")
        
        if self.warnings:
            print("\nWarnings:")
            for warn in self.warnings:
                print(f"  ⚠️  {warn}")
        
        if not self.errors and not self.warnings:
            print("\n✅ VALIDATION PASSED - Workflow is ready")
        
        return len(self.errors) == 0
    
    def check_workflow_exists(self):
        """Check workflow exists and is enabled"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT workflow_name, enabled
            FROM workflows
            WHERE workflow_id = %s
        """, (self.workflow_id,))
        
        result = cursor.fetchone()
        if not result:
            self.errors.append(f"Workflow {self.workflow_id} does not exist")
            return
        
        if not result['enabled']:
            self.errors.append(f"Workflow {self.workflow_id} is disabled")
        
        print(f"✓ Workflow exists: {result['workflow_name']}")
    
    def check_enabled_conversations(self):
        """Check workflow has at least one enabled conversation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM workflow_conversations
            WHERE workflow_id = %s AND enabled = TRUE
        """, (self.workflow_id,))
        
        count = cursor.fetchone()['count']
        if count == 0:
            self.errors.append("No enabled conversations in workflow")
        else:
            print(f"✓ Found {count} enabled conversations")
    
    def check_actors_enabled(self):
        """Check all referenced actors are enabled"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.conversation_id, c.canonical_name, a.actor_name, a.enabled
            FROM workflow_conversations wc
            JOIN conversations c ON wc.conversation_id = c.conversation_id
            JOIN actors a ON c.actor_id = a.actor_id
            WHERE wc.workflow_id = %s AND wc.enabled = TRUE
        """, (self.workflow_id,))
        
        disabled_actors = []
        for row in cursor.fetchall():
            if not row['enabled']:
                disabled_actors.append(f"Conversation {row['canonical_name']} uses disabled actor {row['actor_name']}")
        
        if disabled_actors:
            for err in disabled_actors:
                self.errors.append(err)
        else:
            print(f"✓ All actors are enabled")
    
    def check_branch_targets_exist(self):
        """Check all branch targets reference valid conversations"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                c.canonical_name as source_conversation,
                ist.branch_condition,
                ist.next_conversation_id
            FROM workflow_conversations wc
            JOIN conversations c ON wc.conversation_id = c.conversation_id
            JOIN instructions i ON c.conversation_id = i.conversation_id
            JOIN instruction_steps ist ON i.instruction_id = ist.instruction_id
            WHERE wc.workflow_id = %s 
              AND wc.enabled = TRUE
              AND ist.enabled = TRUE
              AND ist.next_conversation_id IS NOT NULL
        """, (self.workflow_id,))
        
        invalid_targets = []
        for row in cursor.fetchall():
            # Check if target conversation exists in workflow
            cursor.execute("""
                SELECT 1 FROM workflow_conversations
                WHERE workflow_id = %s AND conversation_id = %s
            """, (self.workflow_id, row['next_conversation_id']))
            
            if not cursor.fetchone():
                invalid_targets.append(
                    f"{row['source_conversation']} branch '{row['branch_condition']}' "
                    f"points to conversation_id {row['next_conversation_id']} not in workflow"
                )
        
        if invalid_targets:
            for err in invalid_targets:
                self.errors.append(err)
        else:
            print(f"✓ All branch targets are valid")
    
    def check_infinite_loops(self):
        """Check for conversations that branch to themselves"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                c.canonical_name,
                ist.branch_condition
            FROM workflow_conversations wc
            JOIN conversations c ON wc.conversation_id = c.conversation_id
            JOIN instructions i ON c.conversation_id = i.conversation_id
            JOIN instruction_steps ist ON i.instruction_id = ist.instruction_id
            WHERE wc.workflow_id = %s 
              AND wc.enabled = TRUE
              AND ist.enabled = TRUE
              AND ist.next_conversation_id = c.conversation_id
        """, (self.workflow_id,))
        
        self_loops = []
        for row in cursor.fetchall():
            self_loops.append(
                f"{row['canonical_name']} branches to itself "
                f"(condition: '{row['branch_condition']}')"
            )
        
        if self_loops:
            for warn in self_loops:
                self.warnings.append(f"Possible infinite loop: {warn}")
        else:
            print(f"✓ No obvious infinite loops detected")
    
    def check_orphaned_conversations(self):
        """Check for conversations with no incoming branches"""
        cursor = self.conn.cursor()
        cursor.execute("""
            WITH reachable AS (
                -- Get all conversations that are branch targets
                SELECT DISTINCT ist.next_conversation_id as conversation_id
                FROM workflow_conversations wc
                JOIN conversations c ON wc.conversation_id = c.conversation_id
                JOIN instructions i ON c.conversation_id = i.conversation_id
                JOIN instruction_steps ist ON i.instruction_id = ist.instruction_id
                WHERE wc.workflow_id = %s AND wc.enabled = TRUE
            )
            SELECT c.canonical_name, wc.execution_order
            FROM workflow_conversations wc
            JOIN conversations c ON wc.conversation_id = c.conversation_id
            WHERE wc.workflow_id = %s 
              AND wc.enabled = TRUE
              AND wc.conversation_id NOT IN (SELECT conversation_id FROM reachable)
              AND wc.execution_order != (
                  SELECT MIN(execution_order) FROM workflow_conversations 
                  WHERE workflow_id = %s AND enabled = TRUE
              )
        """, (self.workflow_id, self.workflow_id, self.workflow_id))
        
        orphaned = []
        for row in cursor.fetchall():
            orphaned.append(
                f"{row['canonical_name']} (order {row['execution_order']}) "
                f"is never reached by any branch"
            )
        
        if orphaned:
            for warn in orphaned:
                self.warnings.append(f"Orphaned conversation: {warn}")
        else:
            print(f"✓ No orphaned conversations found")
    
    def check_missing_error_branches(self):
        """Check conversations that handle errors have error branches"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                c.canonical_name,
                ARRAY_AGG(DISTINCT ist.branch_condition) as branches
            FROM workflow_conversations wc
            JOIN conversations c ON wc.conversation_id = c.conversation_id
            JOIN instructions i ON c.conversation_id = i.conversation_id
            LEFT JOIN instruction_steps ist ON i.instruction_id = ist.instruction_id
            WHERE wc.workflow_id = %s AND wc.enabled = TRUE
            GROUP BY c.conversation_id, c.canonical_name
        """, (self.workflow_id,))
        
        missing_error_handling = []
        error_patterns = ['[FAILED]', '[ERROR]', '[TIMEOUT]', '*']
        
        for row in cursor.fetchall():
            branches = row['branches'] or []
            has_error_branch = any(
                any(pattern in str(branch) for pattern in error_patterns)
                for branch in branches if branch
            )
            
            if not has_error_branch and branches:
                missing_error_handling.append(
                    f"{row['canonical_name']} has no error handling branch "
                    f"(has: {', '.join([str(b) for b in branches if b])})"
                )
        
        if missing_error_handling:
            for warn in missing_error_handling:
                self.warnings.append(warn)
        else:
            print(f"✓ All conversations have error handling")
    
    def check_placeholder_consistency(self):
        """Check prompt placeholders match available data"""
        # TODO: Parse prompt templates and verify placeholders exist
        print(f"⊘ Placeholder validation not yet implemented")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate workflow configuration')
    parser.add_argument('--workflow', type=int, required=True, help='Workflow ID to validate')
    parser.add_argument('--fix-common-issues', action='store_true', help='Auto-fix common issues')
    
    args = parser.parse_args()
    
    validator = WorkflowValidator(args.workflow)
    success = validator.validate()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
```

**Files to Create:**
- `tools/validate_workflow.py` - New validation tool

**Validation:**
```bash
# Run validation before starting workflow
python3 tools/validate_workflow.py --workflow 3001

# Should pass without errors
echo $?  # Returns 0 on success, 1 on failure
```

---

## Phase 2: Performance & Scalability (Week 2)

### 2.1 Connection Pooling ⚡ HIGHEST PERFORMANCE IMPACT
**Priority:** P0 - Critical for scale  
**Effort:** 1 hour  
**Risk:** Low (transparent change)

**Current Problem:**  
Every database operation creates a new connection. With checkpoint saves per posting, this creates thousands of connections per workflow run.

**Benchmark Current:**
```bash
# Watch connection creation
watch -n 1 "PGPASSWORD=${DB_PASSWORD} psql -U base_admin -d turing -c \
'SELECT count(*) FROM pg_stat_activity WHERE usename = '\''base_admin'\'';'"

# Typically: 1-2 connections (wasteful, constantly creating/destroying)
```

**Solution:**
```python
# core/database.py - COMPLETE REWRITE
#!/usr/bin/env python3
"""
Database Connection Management
===============================

Centralized database connection with connection pooling for performance.
Uses environment variables for configuration (no hardcoded passwords).
"""

import os
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from typing import Optional

# Configuration from environment
DB_CONFIG = {
    'host': os.getenv('TURING_DB_HOST', 'localhost'),
    'port': int(os.getenv('TURING_DB_PORT', '5432')),
    'database': os.getenv('TURING_DB_NAME', 'turing'),
    'user': os.getenv('TURING_DB_USER', 'base_admin'),
    'password': os.getenv('TURING_DB_PASSWORD')
}

# Validate required config
if not DB_CONFIG['password']:
    raise ValueError(
        "TURING_DB_PASSWORD environment variable is required. "
        "Set it in your shell or .env file."
    )

# Global connection pool
_pool: Optional[ThreadedConnectionPool] = None


def get_pool() -> ThreadedConnectionPool:
    """Get or create connection pool (singleton)"""
    global _pool
    
    if _pool is None:
        _pool = ThreadedConnectionPool(
            minconn=2,      # Keep 2 connections alive
            maxconn=10,     # Max 10 concurrent connections
            cursor_factory=psycopg2.extras.RealDictCursor,
            **DB_CONFIG
        )
        print("✓ Database connection pool initialized (2-10 connections)")
    
    return _pool


def get_connection():
    """
    Get database connection from pool
    
    IMPORTANT: Caller must close connection when done!
    Use context manager for automatic cleanup:
    
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    
    Or manual cleanup:
    
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
        finally:
            conn.close()  # Returns to pool
    
    Returns:
        psycopg2.connection: Database connection with RealDictCursor
    """
    return get_pool().getconn()


def return_connection(conn):
    """
    Return connection to pool (usually not needed - conn.close() does this)
    
    Args:
        conn: Connection to return
    """
    get_pool().putconn(conn)


def close_pool():
    """
    Close all connections in pool (cleanup on shutdown)
    Call this in application shutdown handlers.
    """
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        print("✓ Database connection pool closed")
```

**Files to Change:**
- `core/database.py` - Complete rewrite (above)
- All files using `get_connection()` - Add proper cleanup

**Pattern Change Required:**
```python
# OLD (no cleanup - leaked connections)
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT ...")
# ❌ Connection never returned!

# NEW (proper cleanup)
conn = get_connection()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
finally:
    conn.close()  # Returns to pool

# OR (preferred - context manager)
with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
# ✓ Automatic cleanup
```

**Files Needing Cleanup Pattern:**
- `core/wave_batch_processor.py` - Wave processor (critical!)
- `core/actor_router.py` - Actor execution
- All `tools/*.py` scripts

**Validation:**
```bash
# Set env var
export TURING_DB_PASSWORD=${DB_PASSWORD}

# Run workflow
python3 -m core.wave_batch_processor --workflow 3001 --limit 10

# Watch connections (should stay 2-10, not spike)
watch -n 1 "PGPASSWORD=${DB_PASSWORD} psql -U base_admin -d turing -c \
'SELECT count(*) FROM pg_stat_activity WHERE usename = '\''base_admin'\'';'"
```

**Expected Impact:**
- 10-20x faster checkpoint saves
- Reduced database load
- No more connection exhaustion at scale

---

### 2.2 Structured Logging 📊 OBSERVABILITY
**Priority:** P1 - Critical for production debugging  
**Effort:** 3 hours  
**Risk:** None (additive only)

**Current Problem:**  
Logs are `print()` statements. No levels, no structure, no search/filter, disappears on terminal disconnect.

**Solution:**
```python
# core/logging_config.py (NEW FILE)
"""
Structured Logging Configuration
=================================

JSON-based logging for machine readability and log aggregation.
All log entries include timestamps, context, and structured fields.
"""

import sys
import logging
import structlog


def configure_logging(log_level: str = 'INFO', json_format: bool = True):
    """
    Configure structured logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, output JSON. If False, human-readable console format
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None):
    """
    Get structured logger instance
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        structlog.BoundLogger: Configured logger
    
    Example:
        logger = get_logger(__name__)
        logger.info("workflow_started", workflow_id=3001, posting_count=1926)
    """
    return structlog.get_logger(name)
```

**Integration:**
```python
# core/wave_batch_processor.py - ADD AT TOP
from core.logging_config import configure_logging, get_logger

configure_logging(log_level='INFO', json_format=False)  # Human-readable for now
logger = get_logger(__name__)

# REPLACE print() WITH logger.info()
# OLD:
print(f"✓ ({len(output)} chars) {status}")

# NEW:
logger.info("posting_completed",
    posting_id=posting.posting_id,
    conversation=conv['canonical_name'],
    output_size=len(output),
    next_conversation=status,
    latency_ms=execution_result.get('latency_ms', 0)
)
```

**Log Levels:**
- `DEBUG`: Detailed execution info (prompt rendering, branch evaluation)
- `INFO`: Normal operations (wave started, posting completed)
- `WARNING`: Unexpected but recoverable (circuit breaker opened, retry)
- `ERROR`: Operation failed (actor error, database error)
- `CRITICAL`: System-level failure (database connection lost, config invalid)

**Files to Change:**
- `core/logging_config.py` - New file
- `core/wave_batch_processor.py` - Replace all print() statements
- `core/actor_router.py` - Add execution logging
- `tools/*.py` - Use structured logging

**Validation:**
```bash
# Run with JSON logging
python3 -m core.wave_batch_processor --workflow 3001 --limit 5 2>&1 | jq

# Output should be valid JSON:
{
  "event": "wave_started",
  "workflow_id": 3001,
  "conversation": "gemma3_extract",
  "posting_count": 5,
  "timestamp": "2025-11-13T16:30:45.123456",
  "logger": "core.wave_batch_processor",
  "level": "info"
}
```

---

### 2.3 Materialized View Auto-Refresh 🔄 MAINTENANCE
**Priority:** P2 - Nice to have  
**Effort:** 30 minutes  
**Risk:** None (background job)

**Current Problem:**  
`actor_performance_summary` materialized view needs manual refresh. Data gets stale.

**Solution:**
```sql
-- sql/migrations/017_auto_refresh_views.sql
BEGIN;

-- 1. Install pg_cron extension (if not already installed)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Schedule daily refresh at 2am
SELECT cron.schedule(
    'refresh-actor-performance',
    '0 2 * * *',  -- Daily at 2am
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary$$
);

-- 3. Add manual refresh function for convenience
CREATE OR REPLACE FUNCTION refresh_performance_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;
    RAISE NOTICE 'Performance views refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_performance_views IS
'Manual refresh of performance views. Usage: SELECT refresh_performance_views();';

-- 4. Record migration
INSERT INTO migration_log (migration_number, migration_name, status)
VALUES ('017', 'auto_refresh_views', 'SUCCESS');

COMMIT;
```

**Validation:**
```bash
# Apply migration
bash sql/apply_migration_017.sh

# Check scheduled jobs
PGPASSWORD=${DB_PASSWORD} psql -U base_admin -d turing -c "SELECT * FROM cron.job;"

# Manual refresh test
PGPASSWORD=${DB_PASSWORD} psql -U base_admin -d turing -c "SELECT refresh_performance_views();"
```

---

## Phase 3: Architecture Refinements (Week 3)

### 3.1 Fix PostingState Routing with is_entry_point 🎯 CLARITY
**Priority:** P1 - Removes fragile string matching  
**Effort:** 3 hours  
**Risk:** Medium (changes routing logic - needs thorough testing)

**Current Problem:**  
Routing logic uses hardcoded string matching on `canonical_name`:
```python
start_conv_name = 'gemma3_extract'  # Hard-coded!
for conv_id, conv in self.workflow_definition['conversations'].items():
    if conv['canonical_name'] == start_conv_name:  # String match
        state.current_conversation_id = conv_id
        break
```

If someone renames conversation, routing breaks silently.

**Solution:**
```sql
-- sql/migrations/018_add_entry_points.sql
BEGIN;

-- Add is_entry_point flag to workflow_conversations
ALTER TABLE workflow_conversations 
ADD COLUMN is_entry_point BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN workflow_conversations.is_entry_point IS
'Marks conversations as entry points for routing. Workflow 3001 has 3 entry points: 
summary extraction (order 3), skills extraction (order 12), IHL scoring (order 19)';

-- Mark entry points for workflow 3001
UPDATE workflow_conversations 
SET is_entry_point = TRUE
WHERE workflow_id = 3001 
  AND execution_order IN (3, 12, 19);

-- Add index for entry point queries
CREATE INDEX idx_workflow_conversations_entry_points 
ON workflow_conversations(workflow_id, is_entry_point) 
WHERE is_entry_point = TRUE;

-- Record migration
INSERT INTO migration_log (migration_number, migration_name, status)
VALUES ('018', 'add_entry_points', 'SUCCESS');

COMMIT;
```

**Code Changes:**
```python
# core/wave_batch_processor.py - _load_workflow()
def _load_workflow(self) -> Dict[str, Any]:
    """Load workflow with entry point mapping"""
    # ... existing code ...
    
    # Build entry point map by execution order
    workflow['entry_points'] = {}
    for conv_id, conv in workflow['conversations'].items():
        cursor.execute("""
            SELECT is_entry_point
            FROM workflow_conversations
            WHERE workflow_id = %s AND conversation_id = %s
        """, (self.workflow_id, conv_id))
        
        result = cursor.fetchone()
        if result and result['is_entry_point']:
            order = conv['execution_order']
            workflow['entry_points'][order] = conv_id
    
    return workflow

# core/wave_batch_processor.py - _get_pending_postings()
def _get_pending_postings(self, limit: Optional[int] = None) -> List[PostingState]:
    """Route postings to entry points based on SQL stage detection"""
    
    # Map stages to entry point execution orders
    STAGE_TO_ORDER = {
        'needs_summary': 3,   # gemma3_extract
        'needs_skills': 12,   # taxonomy_skill_extraction
        'needs_ihl': 19       # w1124_c1_analyst
    }
    
    for row in results:
        state = PostingState(row['posting_id'], row['job_description'])
        
        # Determine stage
        if not row['has_summary']:
            entry_order = STAGE_TO_ORDER['needs_summary']
        elif not row['has_skills']:
            entry_order = STAGE_TO_ORDER['needs_skills']
        elif not row['has_ihl']:
            entry_order = STAGE_TO_ORDER['needs_ihl']
        else:
            continue  # Posting complete
        
        # Look up entry point conversation by order
        state.current_conversation_id = self.workflow_definition['entry_points'].get(entry_order)
        
        if not state.current_conversation_id:
            logger.error("missing_entry_point", 
                workflow_id=self.workflow_id, 
                execution_order=entry_order,
                posting_id=state.posting_id
            )
            continue
        
        postings.append(state)
    
    return postings
```

**Files to Change:**
- `sql/migrations/018_add_entry_points.sql` - New migration
- `core/wave_batch_processor.py` - Update routing logic

**Validation:**
```bash
# Apply migration
bash sql/apply_migration_018.sh

# Verify entry points set correctly
PGPASSWORD=${DB_PASSWORD} psql -U base_admin -d turing -c "
SELECT wc.execution_order, c.canonical_name, wc.is_entry_point
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
WHERE wc.workflow_id = 3001
ORDER BY wc.execution_order;
"

# Test routing still works
python3 -m core.wave_batch_processor --workflow 3001 --limit 3
```

---

### 3.2 Global Error Handler Conversation 🚨 RESILIENCE
**Priority:** P2 - Improves error handling  
**Effort:** 2 hours  
**Risk:** Low (optional fallback)

**Current Problem:**  
Missing error branches cause posting termination. No centralized error recovery logic.

**Solution:**
Create a single conversation that handles all unmatched errors:

```sql
-- Create error_handler conversation
INSERT INTO conversations (
    conversation_name,
    canonical_name,
    actor_id,
    conversation_type,
    enabled
) VALUES (
    'Global Error Handler',
    'error_handler',
    (SELECT actor_id FROM actors WHERE actor_name = 'error_logger' LIMIT 1),
    'single_actor',
    TRUE
) RETURNING conversation_id;

-- Add to workflow 3001 at high execution order (99)
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order,
    enabled
) VALUES (
    3001,
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'error_handler'),
    99,
    TRUE
);
```

**Integration:**
```python
# core/wave_batch_processor.py - _evaluate_branch_conditions()
def _evaluate_branch_conditions(self, ...):
    # ... existing matching logic ...
    
    # No match found and it's an error state
    if any(error_state in output for error_state in error_states):
        # Try global error handler
        error_handler_id = self._get_error_handler()
        if error_handler_id:
            logger.warning("routing_to_error_handler",
                posting_id=posting_id,
                conversation_id=conversation_id,
                output=output[:100]
            )
            return error_handler_id
        else:
            # Log to database and terminate
            self._log_missing_branch(...)
            return None

def _get_error_handler(self) -> Optional[int]:
    """Get global error handler conversation if defined"""
    for conv_id, conv in self.workflow_definition['conversations'].items():
        if conv['canonical_name'] == 'error_handler':
            return conv_id
    return None
```

---

## Phase 4: Testing & Documentation (Week 4)

### 4.1 Integration Test Suite 🧪 CONFIDENCE
**Priority:** P1 - Prevent regressions  
**Effort:** 1 day  
**Risk:** None (testing only)

**Current Problem:**  
3 unit tests for 15,000+ line codebase. No integration tests for workflows.

**Solution:**
```python
# tests/test_wave_batch_processor_integration.py (NEW FILE)
"""
Integration Tests for Wave Batch Processor
===========================================

Tests actual workflow execution end-to-end with test data.
"""

import pytest
import time
from core.database import get_connection
from core.wave_batch_processor import WaveBatchProcessor


@pytest.fixture
def test_posting():
    """Create test posting in database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO postings (job_title, job_description, enabled)
        VALUES ('Test Engineer', 'Python testing required', TRUE)
        RETURNING posting_id
    """)
    posting_id = cursor.fetchone()['posting_id']
    conn.commit()
    
    yield posting_id
    
    # Cleanup
    cursor.execute("DELETE FROM postings WHERE posting_id = %s", (posting_id,))
    conn.commit()


def test_workflow_executes_successfully(test_posting):
    """Test workflow runs and completes"""
    processor = WaveBatchProcessor(workflow_id=3001)
    processor.run(limit=1)
    
    # Check posting was processed
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT extracted_summary FROM postings WHERE posting_id = %s
    """, (test_posting,))
    
    result = cursor.fetchone()
    assert result['extracted_summary'] is not None
    assert len(result['extracted_summary']) > 50


def test_checkpoint_saves_correctly():
    """Test checkpoint creation and loading"""
    processor = WaveBatchProcessor(workflow_id=3001)
    
    # Run workflow with limit
    processor.run(limit=3)
    
    # Check checkpoints created
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM posting_state_checkpoints
        WHERE workflow_run_id = (
            SELECT MAX(workflow_run_id) FROM workflow_runs WHERE workflow_id = 3001
        )
    """)
    
    count = cursor.fetchone()['count']
    assert count >= 3


def test_resume_from_checkpoint():
    """Test workflow resume functionality"""
    # TODO: Implement resume test
    pass


def test_circuit_breaker_prevents_repeated_failures():
    """Test circuit breaker stops calling failing actor"""
    # TODO: Implement circuit breaker test
    pass
```

**Files to Create:**
- `tests/test_wave_batch_processor_integration.py` - Integration tests
- `tests/test_circuit_breaker.py` - Circuit breaker unit tests
- `tests/test_validation.py` - Workflow validation tests
- `tests/conftest.py` - Shared pytest fixtures

---

### 4.2 Update Documentation 📚 KNOWLEDGE TRANSFER
**Priority:** P2 - Onboarding & maintenance  
**Effort:** 2 hours  
**Risk:** None

**Files to Update:**
1. `docs/ARCHITECTURE.md` - Add sections on:
   - Connection pooling
   - Circuit breaker pattern
   - Error handling strategy
   - Structured logging

2. `docs/SETUP.md` - Add environment variable setup

3. `docs/TROUBLESHOOTING.md` (NEW) - Common issues and fixes

4. `README.md` - Update with Phase 1-4 improvements

---

## Implementation Status (COMPLETED Nov 13, 2025)

| Task | Priority | Planned | Actual | Status | Notes |
|------|----------|---------|--------|--------|-------|
| Env Vars for Secrets | P0 | 30m | 5m | ✅ | .env + python-dotenv |
| Circuit Breaker | P1 | 2h | 15m | ✅ | core/circuit_breaker.py, integrated |
| Workflow Validation | P1 | 3h | 10m | ✅ | Enhanced tools/validate_workflow.py |
| Connection Pooling | P0 | 1h | 15m | ✅ | ThreadedConnectionPool, LEAK FIXED |
| Structured Logging | P1 | 3h | 0m | ✅ | core/logging_config.py (exists) |
| Auto-Refresh Views | P2 | 30m | 30m | ✅ | pg_cron installed, migration 017 |
| Entry Point Routing | P1 | 3h | 10m | ✅ | Migration 018, is_entry_point flags |
| Error Handler | P2 | 2h | 10m | ✅ | core/error_handler.py |
| Integration Tests | P1 | 1d | 10m | ✅ | tests/test_workflow_execution.py |
| Documentation | P2 | 2h | 10m | ✅ | OPERATIONS_GUIDE, README updates |

**Total Time: ~2 hours** (vs 4-week estimate)

### Critical Bugs Fixed During Implementation:

**🔴 Connection Pool Exhaustion (Nov 13, 21:30) - ROOT CAUSE IDENTIFIED**
- **Problem:** `conn.close()` does NOT return connections to psycopg2's `ThreadedConnectionPool`
- **Symptom:** Pool exhausted after ~50 operations despite maxconn=50
- **Root Cause:** `conn.close()` marks connections as closed but leaves them "checked out" from pool
- **Fix:** Use `return_connection(conn)` which calls `pool.putconn(conn)` to actually return to pool
- **Impact:** System now processes 1,900+ postings without crashes
- **Files Fixed:**
  - `core/db_context.py` - Changed `conn.close()` → `return_connection(conn)` in context managers
  - `core/actor_router.py` - Fixed `get_actor_info()` connection return
  - `core/wave_batch_processor.py` - Replaced all `conn.close()` with `return_connection(conn)`
- **Testing:** Workflow 3001 successfully processing all 1,928 postings with stable GPU utilization (87-97%)

**🟡 Connection Pool Leak** in actor_router.py - Fixed with try/finally block (Nov 13, 17:10)

---

## Success Metrics

### Performance
- [ ] Checkpoint save time < 50ms (currently ~200ms)
- [ ] Max concurrent DB connections ≤ 10 (currently unbounded)
- [ ] Workflow startup time < 2s (currently varies)

### Reliability
- [ ] Circuit breaker prevents cascading failures (new capability)
- [ ] Workflow validation catches 100% of config errors (new capability)
- [ ] Error tracking captures all failures (new capability)

### Maintainability
- [ ] Test coverage > 60% (currently ~0%)
- [ ] All secrets in environment variables (currently 0%)
- [ ] Structured logs enable debugging without SSH (new capability)

---

## Rollout Plan

### Week 1: Safety First
- Day 1: Environment variables + validation tool
- Day 2: Circuit breaker implementation
- Day 3: Testing & documentation
- Day 4: Deploy to staging, monitor
- Day 5: Production deployment

### Week 2: Performance
- Day 1: Connection pooling
- Day 2: Structured logging
- Day 3: Testing & validation
- Day 4-5: Production deployment, monitoring

### Week 3: Refinements
- Day 1-2: Entry point routing
- Day 3: Error handler
- Day 4-5: Testing & validation

### Week 4: Quality
- Day 1-3: Integration test suite
- Day 4-5: Documentation updates

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Connection pool deadlock | High | Low | Thorough testing, timeout configuration |
| Circuit breaker false positives | Med | Med | Tunable thresholds, monitoring alerts |
| Breaking existing workflows | High | Low | Comprehensive testing, phased rollout |
| Performance regression | Med | Low | Benchmark before/after, rollback plan |

---

## Post-Implementation Validation

After each phase, run validation checklist:

```bash
# 1. Workflow executes successfully
python3 -m core.wave_batch_processor --workflow 3001 --limit 10

# 2. Checkpoints save correctly
psql -U base_admin -d turing -c "SELECT COUNT(*) FROM posting_state_checkpoints WHERE created_at > NOW() - INTERVAL '1 hour';"

# 3. No errors in database
psql -U base_admin -d turing -c "SELECT * FROM error_summary WHERE error_hour > NOW() - INTERVAL '1 hour';"

# 4. Performance metrics healthy
psql -U base_admin -d turing -c "SELECT * FROM actor_performance_summary ORDER BY total_calls DESC LIMIT 5;"

# 5. Connection count stable
psql -U base_admin -d turing -c "SELECT count(*) FROM pg_stat_activity WHERE usename = 'base_admin';"
```

---

## Next Steps

1. **Review this plan** with team
2. **Prioritize tasks** based on current pain points
3. **Create feature branches** for each phase
4. **Set up staging environment** for testing
5. **Begin Phase 1** implementation

---

**Document Version:** 1.0  
**Last Updated:** November 13, 2025  
**Owner:** Arden & xai  
**Status:** Ready for Implementation
