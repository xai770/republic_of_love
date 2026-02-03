#!/usr/bin/env python3
"""
Pull Daemon - Unified execution engine for Turing task_types.

Each task_type declares its own work_query to find subjects.
Daemon iterates over pull-enabled task_types and executes them.

Two execution modes (inferred from structure):
1. Thick Actor: Script with no task_routes → direct execution
2. TaskTypeal: Has task_routes → WaveRunner with branching

Usage:
    python3 core/pull_daemon.py                    # Run all pull-enabled task_types
    python3 core/pull_daemon.py --task_type 9379  # Run specific task_type
    python3 core/pull_daemon.py --dry-run          # Show what would run without executing

RAQ Usage:
    python3 core/pull_daemon.py --task_type 9379 --batch-reason RAQ_TEST_V1
"""

import argparse
import atexit
import fcntl
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection
# Note: WaveRunner no longer used here - batcher.py handles execution


def compute_script_hash(script_path: Path) -> str:
    """Compute SHA1 hash of script file for drift detection."""
    if not script_path.exists():
        return None
    content = script_path.read_bytes()
    return sha1(content).hexdigest()


# Lock file for single-instance
LOCK_FILE = PROJECT_ROOT / '.pull_daemon.lock'
ADVISORY_LOCK_ID = 73572  # Different from old daemon


class PullDaemon:
    """
    Pull-based daemon that lets task_types find their own work.
    
    Key principles:
    - TaskTypes declare work_query (what subjects need processing)
    - Daemon executes, doesn't decide
    - Thick actors run directly (no WaveRunner overhead)
    - TaskTypeal actors use full WaveRunner machinery
    """
    
    def __init__(
        self,
        poll_interval: int = 5,
        heartbeat_interval: int = 30,
        reaper_interval: int = 60,
        stuck_threshold: int = 300,
        task_type_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        batch_reason: Optional[str] = None,
        limit: Optional[int] = None,
        run_once: bool = False,
        dry_run: bool = False,
        subjects: Optional[List[int]] = None,  # RAQ: specific subjects to process
        force: bool = False  # Bypass lint gate
    ):
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.reaper_interval = reaper_interval
        self.stuck_threshold = stuck_threshold
        self.task_type_id = task_type_id  # Filter to one task_type
        self.workflow_id = workflow_id  # Filter to task_types in this workflow
        self.batch_reason = batch_reason  # RAQ batch prefix
        self.limit = limit  # Max items to process (for RAQ)
        self.run_once = run_once  # Exit after processing available work
        self.dry_run = dry_run
        self.subjects = subjects  # RAQ: specific subjects to process
        self.force = force  # Bypass lint gate
        
        # Cache for lint failures (avoid re-checking every subject)
        self._lint_failed_task_types = set()
        
        self.conn = None
        self.running = True
        self.lock_file = None
        self.has_lock = False
        
        self.last_reap = 0
        self.last_heartbeat = 0
        self.total_processed = 0  # Track for --limit
        
        self.logger = self._setup_logging()
        
        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        logger = logging.getLogger('pull_daemon')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            ))
            logger.addHandler(handler)
        
        return logger
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _acquire_lock(self) -> bool:
        """Acquire file + DB advisory lock."""
        # File lock
        try:
            self.lock_file = open(LOCK_FILE, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
            self.lock_file.flush()
        except (IOError, OSError):
            self.logger.error("Another daemon is already running (file lock)")
            return False
        
        # DB advisory lock
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT pg_try_advisory_lock(%s) AS locked", (ADVISORY_LOCK_ID,))
            row = cursor.fetchone()
            if not row['locked']:
                self.logger.error("Another daemon is already running (DB lock)")
                self._release_lock()
                return False
        except Exception as e:
            self.logger.error(f"Failed to acquire DB lock: {e}")
            self._release_lock()
            return False
        
        self.has_lock = True
        return True
    
    def _release_lock(self):
        """Release all locks."""
        if self.has_lock and self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))
            except Exception:
                pass
        
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                pass
        
        self.has_lock = False
    
    def connect(self):
        """Establish database connection."""
        self.conn = psycopg2.connect(
            dbname="turing",
            user="base_admin",
            password="base_yoga_secure_2025",
            host="localhost",
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        self.conn.autocommit = False
    
    # =========================================================================
    # MAIN LOOP
    # =========================================================================
    
    def run(self) -> int:
        """Main daemon loop."""
        self.connect()
        
        if not self._acquire_lock():
            return 1
        
        atexit.register(self._release_lock)
        
        self.logger.info("=" * 60)
        self.logger.info("PULL DAEMON STARTED")
        self.logger.info(f"  PID: {os.getpid()}")
        self.logger.info(f"  Poll interval: {self.poll_interval}s")
        if self.task_type_id:
            self.logger.info(f"  TaskType filter: {self.task_type_id}")
        if self.workflow_id:
            self.logger.info(f"  Workflow filter: {self.workflow_id}")
        if self.batch_reason:
            self.logger.info(f"  Batch reason: {self.batch_reason}")
        if self.limit:
            self.logger.info(f"  Item limit: {self.limit}")
        if self.subjects:
            self.logger.info(f"  RAQ subjects: {len(self.subjects)} locked subjects")
        if self.run_once:
            self.logger.info("  RUN ONCE MODE - exit after batch complete")
        if self.dry_run:
            self.logger.info("  DRY RUN MODE - no changes will be made")
        self.logger.info("=" * 60)
        
        try:
            while self.running:
                cycle_start = time.time()
                
                # Reap stuck tickets
                if time.time() - self.last_reap > self.reaper_interval:
                    self._reap_stuck()
                    self.last_reap = time.time()
                
                # Process each pull-enabled task_type
                processed = self._poll_task_types()
                
                # Run-once: exit when no work found
                if self.run_once and processed == 0:
                    self.logger.info("Run-once: no more work found, exiting")
                    break
                
                # Heartbeat
                if time.time() - self.last_heartbeat > self.heartbeat_interval:
                    self._log_status()
                    self.last_heartbeat = time.time()
                
                # Sleep (but not in run-once mode with work remaining)
                if not self.run_once:
                    elapsed = time.time() - cycle_start
                    if elapsed < self.poll_interval:
                        time.sleep(self.poll_interval - elapsed)
                    
        except Exception as e:
            self.logger.exception(f"Fatal error: {e}")
            return 1
        finally:
            self._release_lock()
            if self.conn:
                self.conn.close()
            self.logger.info("Daemon stopped")
        
        return 0
    
    # =========================================================================
    # CONVERSATION POLLING
    # =========================================================================
    
    def _get_pull_task_types(self) -> List[Dict]:
        """Get task_types that are pull-enabled and have capacity.
        
        IMPORTANT: Orders by requires_model first to enable model-first batching.
        This keeps the GPU loaded with one model until all work for that model
        is exhausted before switching. See Directive 15.
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                c.task_type_id,
                c.task_type_name,
                c.work_query,
                c.scale_limit,
                c.batch_size,
                c.poll_priority,
                c.requires_model,
                c.execution_type,
                c.script_path,
                c.script_code_hash,
                c.actor_id,
                a.actor_type,
                (SELECT COUNT(*) FROM tickets i 
                 WHERE i.task_type_id = c.task_type_id 
                 AND i.status = 'running') as active_count,
                EXISTS(SELECT 1 FROM instructions ins 
                       JOIN task_routes tr ON tr.from_instruction_id = ins.instruction_id
                       WHERE ins.task_type_id = c.task_type_id) as has_task_routes
            FROM task_types c
            LEFT JOIN actors a ON a.actor_id = c.actor_id
            WHERE c.enabled = TRUE
              AND c.work_query IS NOT NULL
        """
        
        params = []
        if self.task_type_id:
            query += " AND c.task_type_id = %s"
            params.append(self.task_type_id)
        # workflow_id filter removed - using pull architecture now
        
        # Model-first batching: group by model, then by priority
        # This keeps GPU loaded with one model until exhausted
        query += " ORDER BY c.requires_model NULLS LAST, c.poll_priority DESC, c.task_type_id"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def _poll_task_types(self) -> int:
        """Poll all pull-enabled task_types with MODEL-FIRST batching.
        
        GPU efficiency requires loading a model once and exhausting ALL work 
        for that model before switching. This loops within each model group
        until no task types have remaining work, then moves to next model.
        
        See Directive 14: Model-first batching.
        """
        task_types = self._get_pull_task_types()
        cycle_processed = 0
        
        # Group task types by model for model-first batching
        model_groups = {}
        for conv in task_types:
            model = conv.get('requires_model') or '__none__'
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(conv)
        
        # Process each model group, exhausting all work before switching models
        for model, convs in model_groups.items():
            if not self.running:
                break
                
            model_display = model if model != '__none__' else '(no model)'
            self.logger.debug(f"🔄 Processing model group: {model_display} ({len(convs)} task types)")
            
            # Keep looping until no task type in this model group has work
            model_had_work = True
            while model_had_work and self.running:
                model_had_work = False
                
                for conv in convs:
                    # Check if we've hit the limit
                    if self.limit and self.total_processed >= self.limit:
                        self.logger.info(f"Reached limit of {self.limit} items")
                        self.running = False
                        break
                    
                    # Re-check capacity (may have changed since last iteration)
                    available = self._get_available_capacity(conv)
                    if available <= 0:
                        continue
                    
                    # Calculate how many to fetch (respect global limit)
                    fetch_count = min(available, conv['batch_size'])
                    if self.limit:
                        remaining = self.limit - self.total_processed
                        fetch_count = min(fetch_count, remaining)
                    
                    # Find work via work_query
                    subjects = self._find_work(conv, limit=fetch_count)
                    
                    if not subjects:
                        continue
                    
                    # This model group still has work - continue after this pass
                    model_had_work = True
                    
                    self.logger.info(
                        f"📋 {conv['task_type_name']}: found {len(subjects)} subjects "
                        f"(capacity: {available}/{conv['scale_limit']}, model: {model_display})"
                    )
                    
                    # Process each subject
                    for subject in subjects:
                        if self.dry_run:
                            self.logger.info(f"  [DRY RUN] Would process: {subject}")
                            continue
                        
                        success = self._process_subject(conv, subject)
                        if success:
                            cycle_processed += 1
                            self.total_processed += 1
                            
                            # Check limit again
                            if self.limit and self.total_processed >= self.limit:
                                self.logger.info(f"Reached limit of {self.limit} items")
                                self.running = False
                                break
                    
                    # Update last_poll_at
                    self._update_last_poll(conv['task_type_id'])
        
        return cycle_processed
    
    def _find_work(self, conv: Dict, limit: int) -> List[Dict]:
        """Run task_type's work_query to find subjects."""
        
        # RAQ mode: use locked subjects if provided
        if self.subjects:
            return self._find_locked_subjects(conv, limit)
        
        work_query = conv['work_query']
        if not work_query:
            return []
        
        # Over-fetch to account for exclusions (10x or at least 100)
        fetch_size = max(limit * 10, 100)
        work_query = work_query.replace(':batch_size', str(fetch_size))
        
        # Infer subject_type from work_query content or task_type_name
        # Order matters: check most specific patterns first
        work_query_lower = work_query.lower()
        name_lower = conv['task_type_name'].lower()
        if 'classification_proposals' in work_query_lower:
            subject_type = 'owl'  # arbitrator/commit work on owl entities (owl_id, not owl_pending_id)
        elif 'owl_pending' in work_query_lower or 'owl' in name_lower:
            subject_type = 'owl_pending'
        elif 'skill' in work_query_lower or 'skill' in name_lower:
            subject_type = 'skill'  
        else:
            subject_type = 'posting'
        
        # Wrap to exclude already-processed or in-progress subjects
        # Also check enabled = TRUE so RAQ reset can re-enable subjects
        # Note: work_query must return subject_id; we add subject_type here
        wrapped_query = f"""
            WITH candidates AS ({work_query})
            SELECT c.subject_id, '{subject_type}' as subject_type FROM candidates c
            WHERE NOT EXISTS (
                SELECT 1 FROM tickets i
                WHERE i.task_type_id = {conv['task_type_id']}
                  AND i.subject_id = c.subject_id
                  AND i.subject_type = '{subject_type}'
                  AND i.status IN ('pending', 'running', 'completed')
                  AND i.enabled = TRUE
            )
            LIMIT {limit}
        """
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(wrapped_query)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"work_query failed for {conv['task_type_name']}: {e}")
            self.conn.rollback()
            return []
    
    def _find_locked_subjects(self, conv: Dict, limit: int) -> List[Dict]:
        """Find work from locked subject list (RAQ mode)."""
        # Get subject_type from work_query (usually 'posting')
        subject_type = 'posting'  # Default for most task_types
        
        # Build query for locked subjects not yet processed
        # IMPORTANT: Validate subjects actually exist in postings to avoid
        # infinite loops when postings are deleted between RAQ runs
        subject_ids = ','.join(str(s) for s in self.subjects)
        query = f"""
            SELECT p.posting_id as subject_id, '{subject_type}' as subject_type
            FROM postings p
            WHERE p.posting_id = ANY(ARRAY[{subject_ids}])
              AND p.invalidated = FALSE
              AND p.enabled = TRUE
              AND NOT EXISTS (
                SELECT 1 FROM tickets i
                WHERE i.task_type_id = {conv['task_type_id']}
                  AND i.subject_id = p.posting_id
                  AND i.status IN ('pending', 'running', 'completed')
                  AND i.enabled = TRUE
            )
            LIMIT {limit}
        """
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"locked subjects query failed: {e}")
            self.conn.rollback()
            return []
    
    def _get_available_capacity(self, conv: Dict) -> int:
        """Get current available capacity for a task type (re-query active count)."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """SELECT COUNT(*) as cnt FROM tickets 
               WHERE task_type_id = %s AND status = 'running'""",
            (conv['task_type_id'],)
        )
        active_count = cursor.fetchone()['cnt']
        return conv['scale_limit'] - active_count
    
    def _update_last_poll(self, task_type_id: int):
        """Update last_poll_at timestamp."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE task_types SET last_poll_at = NOW() WHERE task_type_id = %s",
            (task_type_id,)
        )
        self.conn.commit()
    
    # =========================================================================
    # SUBJECT PROCESSING
    # =========================================================================
    
    def _process_subject(self, conv: Dict, subject: Dict) -> bool:
        """Process one subject for a task_type. Retries once on failure."""
        subject_id = subject['subject_id']
        subject_type = subject.get('subject_type', 'posting')
        
        # GATEKEEPER: Check lint before execution
        if not self._check_lint_gate(conv):
            return False
        
        # Try up to 2 times (original + 1 retry)
        for attempt in range(2):
            # Create ticket for this attempt
            ticket_id = self._create_ticket(conv, subject, status='pending')
            if not ticket_id:
                return False
            
            try:
                if self._is_thick_actor(conv):
                    # Thick actor: claim it ourselves, execute directly
                    self._claim_ticket(ticket_id)
                    result = self._execute_thick(conv, subject, ticket_id)
                    
                    # Check for soft failures (actor returned success: False)
                    if isinstance(result, dict) and result.get('success') is False:
                        error_msg = result.get('error', 'Actor returned success: False')
                        raise RuntimeError(f"Actor failed: {error_msg}")
                    
                    self._complete_ticket(ticket_id, result)
                else:
                    # TaskTypeal: WaveRunner claims and processes
                    self._execute_task_typeal(conv, subject, ticket_id)
                
                self.logger.info(
                    f"  ✅ {conv['task_type_name']} completed for {subject_type}:{subject_id}"
                )
                return True
            except Exception as e:
                # Rollback any aborted transaction before recording failure
                self.conn.rollback()
                
                if attempt == 0:
                    # First failure - log warning and retry
                    self.logger.warning(f"  ⚠️ {conv['task_type_name']} failed for {subject_id}, retrying: {e}")
                    self._fail_ticket(ticket_id, f"Attempt 1: {e}")
                    continue
                else:
                    # Second failure - give up
                    self.logger.error(f"  ❌ {conv['task_type_name']} failed for {subject_id} (2 attempts): {e}")
                    self._fail_ticket(ticket_id, f"Attempt 2 (final): {e}")
                    return False
        
        return False  # Should not reach here
    
    def _is_thick_actor(self, conv: Dict) -> bool:
        """
        Determine if task_type uses thick actor pattern.
        
        Thick actors have execution_type='thick' or 'script' and execute directly.
        'thin' actors require WaveRunner infrastructure.
        """
        return conv.get('execution_type') in ('thick', 'script')
    
    def _check_lint_gate(self, conv: Dict) -> bool:
        """
        GATEKEEPER: Check if task_type passes lint before execution.
        
        Returns True if OK to run, False if blocked.
        Thick actors must pass turing-lint to run in production.
        Run: python3 tools/turing_lint.py --register TASK_ID
        """
        task_type_id = conv['task_type_id']
        
        # Don't re-check known failures
        if task_type_id in self._lint_failed_task_types:
            return False
        
        # --force bypasses lint gate
        if self.force:
            return True
        
        # Thin actors don't need lint (no script to lint)
        if not self._is_thick_actor(conv):
            return True
        
        # Check lint_status in database
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT lint_status, lint_checked_at, lint_errors
            FROM task_types WHERE task_type_id = %s
        """, (task_type_id,))
        row = cursor.fetchone()
        
        if not row or row['lint_status'] is None:
            # Never linted - block
            self._lint_failed_task_types.add(task_type_id)
            self.logger.warning(
                f"🚫 LINT GATE: {conv['task_type_name']} has never been linted. "
                f"Run: python3 tools/turing_lint.py --register {task_type_id}"
            )
            return False
        
        if row['lint_status'] != 'passed':
            # Lint failed - block
            self._lint_failed_task_types.add(task_type_id)
            errors = row.get('lint_errors') or []
            error_summary = '; '.join(e.get('description', 'unknown') for e in errors[:3])
            self.logger.warning(
                f"🚫 LINT GATE: {conv['task_type_name']} failed lint check. "
                f"Errors: {error_summary}. "
                f"Fix issues and re-run: python3 tools/turing_lint.py --register {task_type_id}"
            )
            return False
        
        return True
    
    def _create_ticket(self, conv: Dict, subject: Dict, status: str = 'running') -> Optional[int]:
        """Create ticket record to claim work.
        
        Args:
            conv: TaskType config
            subject: Work subject (subject_id, subject_type, etc.)
            status: 'running' for thick actors (immediate execution)
                    'pending' for task_typeal (WaveRunner picks up)
        """
        import secrets
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Get or create batch if batch_reason specified
            batch_id = None
            if self.batch_reason:
                batch_id = self._get_or_create_batch(conv['task_type_id'])
            
            # Generate chain_id for loop protection (new chains start at depth 0)
            # Use random 63-bit integer (fits in bigint, stays positive)
            chain_id = secrets.randbits(63)
            chain_depth = 0
            
            cursor.execute("""
                INSERT INTO tickets (
                    task_type_id,
                    actor_id,
                    actor_type,
                    subject_type,
                    subject_id,
                    status,
                    input,
                    started_at,
                    batch_id,
                    execution_order,
                    chain_id,
                    chain_depth,
                    code_hash
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s,
                    %s,
                    NOW(),
                    %s,
                    1,
                    %s,
                    %s,
                    %s
                )
                RETURNING ticket_id
            """, (
                conv['task_type_id'],
                conv.get('actor_id'),
                conv.get('actor_type', 'script'),  # Use actor_type from actors table, default to script
                subject.get('subject_type', 'posting'),
                subject['subject_id'],
                status,
                psycopg2.extras.Json(subject),  # Pass subject fields at root level
                batch_id,
                chain_id,
                chain_depth,
                conv.get('script_code_hash')  # Track which code version produced this
            ))
            
            row = cursor.fetchone()
            
            # Update batch item count
            if batch_id:
                cursor.execute("""
                    UPDATE batches SET item_count = item_count + 1
                    WHERE batch_id = %s
                """, (batch_id,))
            
            self.conn.commit()
            return row['ticket_id']
            
        except Exception as e:
            self.logger.error(f"Failed to create ticket: {e}")
            self.conn.rollback()
            return None
    
    def _get_or_create_batch(self, task_type_id: int) -> int:
        """Get existing batch or create new one for RAQ grouping."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Look for existing running batch with same reason
        cursor.execute("""
            SELECT batch_id FROM batches
            WHERE task_type_id = %s
              AND reason = %s
              AND status = 'running'
            ORDER BY started_at DESC
            LIMIT 1
        """, (task_type_id, self.batch_reason))
        
        row = cursor.fetchone()
        if row:
            return row['batch_id']
        
        # Create new batch
        cursor.execute("""
            INSERT INTO batches (task_type_id, reason, status, created_by)
            VALUES (%s, %s, 'running', 'pull_daemon')
            RETURNING batch_id
        """, (task_type_id, self.batch_reason))
        
        row = cursor.fetchone()
        self.conn.commit()
        return row['batch_id']
    
    def _claim_ticket(self, ticket_id: int):
        """Claim ticket by setting to running status."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET status = 'running',
                started_at = NOW(),
                heartbeat_at = NOW(),
                updated_at = NOW()
            WHERE ticket_id = %s
        """, (ticket_id,))
        self.conn.commit()
    
    def _complete_ticket(self, ticket_id: int, output: Dict):
        """Mark ticket as completed with output."""
        # Extract consistency from output (set by BaseThickActor)
        consistency = output.pop('_consistency', '1/1')
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET status = 'completed',
                output = %s,
                consistency = %s,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE ticket_id = %s
        """, (psycopg2.extras.Json(output), consistency, ticket_id))
        self.conn.commit()
    
    def _fail_ticket(self, ticket_id: int, error: str):
        """Mark ticket as failed."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET status = 'failed',
                output = %s,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE ticket_id = %s
        """, (psycopg2.extras.Json({'error': error}), ticket_id))
        self.conn.commit()
    
    # =========================================================================
    # EXECUTION MODES
    # =========================================================================
    
    def _execute_thick(self, conv: Dict, subject: Dict, ticket_id: int) -> Dict:
        """
        Execute thick actor: load script, call process(), return output.
        
        The actor does everything - we just record the result.
        """
        script_path = conv.get('script_path')
        if not script_path:
            raise ValueError(f"No script_path for task_type {conv['task_type_name']}")
        
        full_path = PROJECT_ROOT / script_path
        if not full_path.exists():
            raise FileNotFoundError(f"Script not found: {full_path}")
        
        # Drift detection: compare file hash with stored hash
        stored_hash = conv.get('script_code_hash')
        current_hash = compute_script_hash(full_path)
        if stored_hash and current_hash and stored_hash != current_hash:
            self.logger.warning(
                f"⚠️ SCRIPT DRIFT DETECTED: {conv['task_type_name']} "
                f"(stored: {stored_hash[:8]}... vs file: {current_hash[:8]}...) "
                f"Run: ./tools/turing/turing-hash-scripts --update"
            )
        
        # Import and instantiate actor
        import importlib.util
        spec = importlib.util.spec_from_file_location("actor_module", full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the actor class (subclass of ScriptActorBase)
        actor_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) 
                and name != 'ScriptActorBase'
                and hasattr(obj, 'process')):
                actor_class = obj
                break
        
        if not actor_class:
            raise ValueError(f"No actor class found in {script_path}")
        
        # Fetch chain_id and chain_depth from ticket
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT chain_id, chain_depth FROM tickets WHERE ticket_id = %s",
            (ticket_id,)
        )
        task_log_row = cursor.fetchone()
        chain_id = task_log_row['chain_id'] if task_log_row else None
        chain_depth = task_log_row['chain_depth'] if task_log_row else 0
        
        # Build input data
        input_data = {
            'posting_id': subject['subject_id'],
            'subject_type': subject.get('subject_type', 'posting'),
            'subject_id': subject['subject_id'],
            'ticket_id': ticket_id,
            'task_type_id': conv['task_type_id'],
            'chain_id': chain_id,
            'chain_depth': chain_depth,
        }
        
        # Run actor with injected connection
        actor = actor_class(db_conn=self.conn)
        actor.input_data = input_data
        result = actor.process()
        
        return result
    
    def _execute_task_typeal(self, conv: Dict, subject: Dict, ticket_id: int) -> Dict:
        """
        For task_typeal workflows: seed ticket already created as 'pending'.
        
        The batcher will pick it up and process the entire tree via:
        1. Execute the seed ticket
        2. create_child_tickets() creates children
        3. Repeat until tree is exhausted
        
        This separation of concerns means:
        - Pull daemon: finds work, creates seed tickets
        - Batcher: processes tickets, follows the tree
        """
        # Nothing to do - ticket already created as 'pending'
        # Batcher will process it and follow the task_routes tree
        return {'status': 'seeded', 'ticket_id': ticket_id}
    
    # =========================================================================
    # HOUSEKEEPING
    # =========================================================================
    
    def _reap_stuck(self):
        """Mark stuck tickets as failed."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET status = 'failed',
                output = jsonb_build_object('error', 'Stuck - no heartbeat'),
                completed_at = NOW()
            WHERE status = 'running'
              AND heartbeat_at < NOW() - INTERVAL '%s seconds'
            RETURNING ticket_id
        """, (self.stuck_threshold,))
        
        reaped = cursor.fetchall()
        if reaped:
            self.logger.warning(f"Reaped {len(reaped)} stuck tickets")
        
        self.conn.commit()
    
    def _log_status(self):
        """Log current status."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT 
                c.task_type_name,
                COUNT(*) FILTER (WHERE i.status = 'running') as running,
                COUNT(*) FILTER (WHERE i.status = 'pending') as pending,
                COUNT(*) FILTER (WHERE i.status = 'completed' 
                    AND i.completed_at > NOW() - INTERVAL '1 hour') as completed_1h
            FROM task_types c
            LEFT JOIN tickets i ON c.task_type_id = i.task_type_id
            WHERE c.work_query IS NOT NULL
            GROUP BY c.task_type_name
            HAVING COUNT(*) FILTER (WHERE i.status = 'running') > 0
                OR COUNT(*) FILTER (WHERE i.status = 'completed' 
                    AND i.completed_at > NOW() - INTERVAL '1 hour') > 0
        """)
        
        rows = cursor.fetchall()
        if rows:
            self.logger.info("Status:")
            for row in rows:
                self.logger.info(
                    f"  {row['task_type_name']}: "
                    f"running={row['running']}, pending={row['pending']}, "
                    f"completed(1h)={row['completed_1h']}"
                )


def main():
    parser = argparse.ArgumentParser(description="Pull Daemon for Turing task_types")
    parser.add_argument('--task_type', '-c', type=int, help='Process only this task_type')
    parser.add_argument('--workflow', '-w', type=int, help='Process task_types in this workflow')
    parser.add_argument('--batch-reason', '-r', help='RAQ batch reason/prefix')
    parser.add_argument('--limit', '-l', type=int, help='Max items to process (for RAQ)')
    parser.add_argument('--subjects', '-s', help='Comma-separated subject IDs (RAQ mode)')
    parser.add_argument('--run-once', action='store_true', help='Exit after processing available work')
    parser.add_argument('--poll-interval', type=int, default=5, help='Seconds between polls')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run without executing')
    parser.add_argument('--force', '-f', action='store_true', 
                        help='Bypass lint gate (use with caution)')
    
    args = parser.parse_args()
    
    # Parse subjects if provided
    subjects = None
    if args.subjects:
        subjects = [int(s.strip()) for s in args.subjects.split(',')]
    
    daemon = PullDaemon(
        task_type_id=args.task_type,
        workflow_id=args.workflow,
        batch_reason=args.batch_reason,
        limit=args.limit,
        subjects=subjects,
        run_once=args.run_once,
        poll_interval=args.poll_interval,
        dry_run=args.dry_run,
        force=args.force
    )
    
    sys.exit(daemon.run())


if __name__ == '__main__':
    main()
