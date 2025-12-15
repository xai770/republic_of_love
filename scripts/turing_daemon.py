#!/usr/bin/env python3
"""
Turing Daemon - Unified Workflow Engine
========================================

Single process that handles both queue claiming and interaction execution.
Replaces the separate queue_worker.py and wave_runner_daemon.py.

Key improvements:
- Single-instance locking (file + DB advisory lock)
- Heartbeat updates for stuck detection
- Conversation-order execution (respects workflow sequence)
- Input context injected at creation time

Usage:
    python3 scripts/turing_daemon.py
    python3 scripts/turing_daemon.py --poll-interval 5 --batch-size 10

Control:
    python3 scripts/turing_daemon.py --status   # Check if running
    python3 scripts/turing_daemon.py --stop     # Graceful shutdown

Authors: Arden + Sandy
Date: December 12, 2025
"""

import sys
import os
import time
import signal
import threading
import logging
import argparse
import fcntl
import atexit
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.wave_runner.runner import WaveRunner

# Lock file location (survives reboots, user-writable)
LOCK_FILE = PROJECT_ROOT / '.turing_daemon.lock'
ADVISORY_LOCK_ID = 73571  # Arbitrary unique ID for pg_advisory_lock


class SingleInstanceLock:
    """Prevent multiple daemon instances using file + DB locks."""
    
    def __init__(self, conn):
        self.conn = conn
        self.lock_file = None
        self.has_file_lock = False
        self.has_db_lock = False
    
    def acquire(self) -> bool:
        """
        Acquire both file and DB locks.
        Returns True if acquired, False if another instance running.
        """
        # 1. File lock (fast local check)
        try:
            self.lock_file = open(LOCK_FILE, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
            self.lock_file.flush()
            self.has_file_lock = True
        except (IOError, OSError):
            return False
        
        # 2. DB advisory lock (distributed safety)
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK_ID,))
            result = cursor.fetchone()[0]
            if not result:
                self.release()
                return False
            self.has_db_lock = True
        except Exception:
            self.release()
            return False
        
        return True
    
    def release(self):
        """Release all locks."""
        if self.has_db_lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))
                self.has_db_lock = False
            except Exception:
                pass
        
        if self.has_file_lock and self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                LOCK_FILE.unlink(missing_ok=True)
                self.has_file_lock = False
            except Exception:
                pass


class TuringDaemon:
    """Unified daemon for queue processing and interaction execution."""
    
    def __init__(
        self,
        poll_interval: int = 5,
        queue_batch_size: int = 10,
        runner_batch_size: int = 50,  # Process more at once for efficiency
        heartbeat_interval: int = 30,
        reaper_interval: int = 60,
        stuck_threshold: int = 120,  # 2 minutes
        workflow_id: int = 3001
    ):
        self.poll_interval = poll_interval
        self.queue_batch_size = queue_batch_size
        self.runner_batch_size = runner_batch_size
        self.heartbeat_interval = heartbeat_interval
        self.reaper_interval = reaper_interval
        self.stuck_threshold = stuck_threshold
        self.workflow_id = workflow_id
        
        self.running = True
        self.conn = None
        self.lock = None
        self.last_reap = 0
        self.last_heartbeat_log = 0
        self.last_completion_check = 0  # Track workflow completion checks
        self._heartbeat_interval = 10  # Log running status every 10s
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None
        
        # Setup logger immediately so it's available
        self.logger = self._setup_logging()
    
    def _heartbeat_loop(self):
        """Background thread that updates heartbeats and logs what's running every 10 seconds."""
        import psycopg2
        import psycopg2.extras
        
        # Use our own connection - don't share with main thread!
        heartbeat_conn = psycopg2.connect(
            dbname="turing",
            user="base_admin", 
            password="base_yoga_secure_2025",
            host="localhost"
        )
        
        try:
            while not self._heartbeat_stop.wait(self._heartbeat_interval):
                try:
                    cursor = heartbeat_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    
                    # Update heartbeat_at for all running interactions
                    cursor.execute("""
                        UPDATE interactions SET heartbeat_at = NOW() WHERE status = 'running'
                    """)
                    heartbeat_conn.commit()
                    
                    # Log what's running
                    cursor.execute("""
                        SELECT COALESCE(ins.instruction_name, '(unknown)') as instruction, 
                               a.actor_name, COUNT(*) as cnt,
                               MAX(EXTRACT(EPOCH FROM (NOW() - i.started_at)))::int as max_secs
                        FROM interactions i
                        JOIN actors a ON i.actor_id = a.actor_id
                        LEFT JOIN instructions ins ON i.instruction_id = ins.instruction_id
                        WHERE i.status = 'running'
                        GROUP BY ins.instruction_name, a.actor_name
                    """)
                    running = cursor.fetchall()
                    cursor.close()
                    
                    if running:
                        for row in running:
                            self.logger.info(f"  ⏳ {row['instruction']} via {row['actor_name']} ({row['cnt']} running, {row['max_secs']}s)")
                except Exception as e:
                    try:
                        heartbeat_conn.rollback()
                    except:
                        pass
        finally:
            heartbeat_conn.close()
        
        # Setup
        self.logger = self._setup_logging()
        load_dotenv(PROJECT_ROOT / '.env')
        
        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        log_dir = PROJECT_ROOT / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        logger = logging.getLogger('turing_daemon')
        logger.setLevel(logging.INFO)
        
        # Console handler
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(console)
        
        # File handler
        file_handler = logging.FileHandler(
            log_dir / f'turing_daemon_{datetime.now():%Y%m%d}.log'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        ))
        logger.addHandler(file_handler)
        
        return logger
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name}, shutting down...")
        self.running = False
    
    def _resume_interrupted_workflows(self):
        """Resume workflows interrupted by previous shutdown.
        
        This runs at startup to automatically resume any workflows that were
        marked as 'interrupted' when the daemon was previously stopped.
        No more manual intervention needed!
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE workflow_runs 
                SET status = 'running', updated_at = NOW()
                WHERE status = 'interrupted'
                RETURNING workflow_run_id, workflow_id
            """)
            resumed = cursor.fetchall()
            self.conn.commit()
            
            if resumed:
                self.logger.info(f"✅ Auto-resumed {len(resumed)} interrupted workflow(s): {[r[0] for r in resumed]}")
            else:
                self.logger.info("✅ No interrupted workflows to resume")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to resume interrupted workflows: {e}")
        finally:
            cursor.close()
    
    def _log_startup_state(self):
        """Log the current state of workflows and interactions at startup."""
        cursor = self.conn.cursor()
        try:
            # Get workflow run counts by status
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM workflow_runs 
                GROUP BY status
            """)
            workflow_counts = dict(cursor.fetchall())
            
            # Get interaction counts by status
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM interactions 
                GROUP BY status
            """)
            interaction_counts = dict(cursor.fetchall())
            
            # Get queue counts
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM queue 
                GROUP BY status
            """)
            queue_counts = dict(cursor.fetchall())
            
            self.logger.info("📊 STARTUP STATE:")
            self.logger.info(f"   Workflow runs: {workflow_counts}")
            self.logger.info(f"   Interactions:  {interaction_counts}")
            self.logger.info(f"   Queue:         {queue_counts}")
        except Exception as e:
            self.logger.error(f"Failed to log startup state: {e}")
        finally:
            cursor.close()
    
    def connect(self):
        """Establish database connection."""
        self.conn = psycopg2.connect(
            dbname="turing",
            user="base_admin", 
            password="base_yoga_secure_2025",
            host="localhost"
        )
        self.conn.autocommit = False
        self.logger.info("Connected to database")
    
    def run(self):
        """Main daemon loop."""
        self.connect()
        
        # Acquire single-instance lock
        self.lock = SingleInstanceLock(self.conn)
        if not self.lock.acquire():
            self.logger.error("Another instance is already running. Exiting.")
            return 1
        
        atexit.register(self.lock.release)
        self.logger.info("=" * 60)
        self.logger.info("TURING DAEMON STARTED")
        self.logger.info(f"  PID: {os.getpid()}")
        self.logger.info(f"  Poll interval: {self.poll_interval}s")
        self.logger.info(f"  Queue batch: {self.queue_batch_size}")
        self.logger.info(f"  Runner batch: {self.runner_batch_size}")
        self.logger.info(f"  Reaper interval: {self.reaper_interval}s")
        self.logger.info(f"  Stuck threshold: {self.stuck_threshold}s")
        self.logger.info("=" * 60)
        
        # Phase 1 fixes: Auto-resume and state logging
        self._log_startup_state()
        self._resume_interrupted_workflows()
        
        # Start heartbeat thread for transparency
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        # NOTE: Reaper runs in main loop, NOT in separate thread!
        # Running reaper in a thread creates a race condition with WaveRunner:
        # - Main thread blocks on Ollama call
        # - Reaper thread marks interaction as 'failed'
        # - Ollama returns, main thread overwrites with 'completed'
        # See docs/daily_notes/2025-12-14_turing_daemon_issues.md for details.
        
        try:
            while self.running:
                cycle_start = time.time()
                
                # Run reaper in main loop (safe - no race condition)
                if time.time() - self.last_reap > self.reaper_interval:
                    self._reap_stuck_interactions()
                    self.last_reap = time.time()
                
                # 1. Claim queue entries → create workflow runs
                claimed = self._claim_queue_batch()
                
                # 2. Complete finished workflow runs (every 30s)
                if time.time() - self.last_completion_check > 30:
                    self._complete_finished_workflows()
                    self.last_completion_check = time.time()
                
                # 3. Run pending interactions
                processed = self._run_interactions()
                
                # 4. Log heartbeat
                if claimed or processed:
                    self.logger.info(f"Cycle: claimed={claimed}, processed={processed}")
                    self.last_heartbeat_log = time.time()
                elif time.time() - self.last_heartbeat_log > 60:
                    self.logger.info("Idle - no pending work")
                    self.last_heartbeat_log = time.time()
                
                # 5. Sleep if cycle was fast
                elapsed = time.time() - cycle_start
                if elapsed < self.poll_interval:
                    time.sleep(self.poll_interval - elapsed)
                    
        except Exception as e:
            self.logger.exception(f"Fatal error: {e}")
            return 1
        finally:
            # Stop heartbeat thread
            self._heartbeat_stop.set()
            if self._heartbeat_thread:
                self._heartbeat_thread.join(timeout=2)
            self.lock.release()
            if self.conn:
                self.conn.close()
            self.logger.info("Daemon stopped")
        
        return 0
    
    def _claim_queue_batch(self) -> int:
        """
        Claim pending queue entries and create workflow runs.
        Returns number of entries claimed.
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Atomic claim with SKIP LOCKED
            # Now supports workflow_id, subject_type, subject_id for non-posting workflows
            cursor.execute("""
                WITH claimed AS (
                    SELECT queue_id, posting_id, start_step, model_override,
                           workflow_id, subject_type, subject_id
                    FROM queue
                    WHERE status = 'pending'
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY priority DESC, created_at
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE queue q
                SET status = 'processing', 
                    processing_started_at = NOW(),
                    expires_at = NOW() + INTERVAL '1 hour'
                FROM claimed c
                WHERE q.queue_id = c.queue_id
                RETURNING c.*
            """, (self.queue_batch_size,))
            
            claimed = cursor.fetchall()
            if not claimed:
                self.conn.commit()
                return 0
            
            # Create workflow runs and seed interactions
            for entry in claimed:
                try:
                    self._create_workflow_run(cursor, entry)
                except Exception as run_err:
                    self.logger.error(f"Failed to create run for posting {entry.get('posting_id')}: {run_err}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            
            self.conn.commit()
            return len(claimed)
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Queue claim error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0
    
    def _create_workflow_run(self, cursor, queue_entry: Dict):
        """Create a workflow run and seed interaction for a queue entry.
        
        Supports both posting-centric (WF3001) and subject-centric (WF3005) workflows.
        """
        # Use queue's workflow_id if specified, otherwise default
        workflow_id = queue_entry.get('workflow_id') or self.workflow_id
        posting_id = queue_entry.get('posting_id')  # May be None for non-posting workflows
        subject_type = queue_entry.get('subject_type', 'posting')
        subject_id = queue_entry.get('subject_id')
        start_step = queue_entry.get('start_step') or 'gemma3_extract'
        
        # 1. Create workflow run
        cursor.execute("""
            INSERT INTO workflow_runs (workflow_id, posting_id, status, started_at, created_by)
            VALUES (%s, %s, 'running', NOW(), 'turing_daemon')
            RETURNING workflow_run_id
        """, (workflow_id, posting_id))
        workflow_run_id = cursor.fetchone()['workflow_run_id']
        
        # 2. Get first conversation for this workflow by canonical_name
        cursor.execute("""
            SELECT c.conversation_id, c.actor_id, a.actor_type
            FROM conversations c
            JOIN actors a ON a.actor_id = c.actor_id
            WHERE c.canonical_name = %s AND c.enabled = true
        """, (start_step,))
        conv = cursor.fetchone()
        
        if not conv:
            self.logger.error(f"No conversation '{start_step}' found or not enabled")
            return None
        
        conversation_id = conv['conversation_id']
        actor_id = conv['actor_id']
        actor_type = conv['actor_type']
        
        # 3. Build input with context (Issue 5 fix: include posting_id/run_id at creation)
        input_data = {
            "_context": {
                "posting_id": posting_id,
                "workflow_run_id": workflow_run_id,
                "queue_id": queue_entry['queue_id'],
                "subject_type": subject_type,
                "subject_id": subject_id
            }
        }
        
        # Add model override if specified
        if queue_entry.get('model_override'):
            input_data['_context']['model_override'] = queue_entry['model_override']
        
        # 4. Create seed interaction (execution_order=1 for first step)
        cursor.execute("""
            INSERT INTO interactions 
                (conversation_id, workflow_run_id, posting_id, actor_id, actor_type, input, status, execution_order)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', 1)
            RETURNING interaction_id
        """, (conversation_id, workflow_run_id, posting_id, actor_id, actor_type, psycopg2.extras.Json(input_data)))
        
        interaction_id = cursor.fetchone()['interaction_id']
        
        # 5. Link seed interaction back to workflow_run
        cursor.execute("""
            UPDATE workflow_runs SET seed_interaction_id = %s WHERE workflow_run_id = %s
        """, (interaction_id, workflow_run_id))
        
        if posting_id:
            self.logger.info(f"Created run {workflow_run_id} for posting {posting_id} (interaction {interaction_id})")
        else:
            self.logger.info(f"Created run {workflow_run_id} for {subject_type}/{subject_id} (interaction {interaction_id})")
        return workflow_run_id
    
    def _run_interactions(self) -> int:
        """
        Execute pending interactions using WaveRunner.
        Returns number of interactions processed.
        
        Runs all pending interactions across all workflows (global_batch=True, no workflow filter).
        """
        try:
            # Create fresh connection for runner to avoid stale transaction state
            from core.database import get_connection_raw, return_connection
            import psycopg2.extras
            runner_conn = get_connection_raw()
            
            try:
                # Log what we're about to process
                cursor = runner_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("""
                    SELECT a.actor_name, COALESCE(ins.instruction_name, '(unknown)') as instruction, COUNT(*) as cnt
                    FROM interactions i
                    JOIN actors a ON i.actor_id = a.actor_id
                    LEFT JOIN instructions ins ON i.instruction_id = ins.instruction_id
                    WHERE i.status = 'running'
                    GROUP BY a.actor_name, ins.instruction_name
                """)
                running = cursor.fetchall()
                if running:
                    for row in running:
                        self.logger.info(f"  ▶ {row['instruction']} via {row['actor_name']} ({row['cnt']} running)")
                cursor.close()
                
                runner = WaveRunner(
                    db_conn=runner_conn,
                    global_batch=True
                    # No workflow_id filter - process ALL workflows
                )
                result = runner.run()  # No limit - process all available work
                
                # Update heartbeat for running interactions
                self._update_heartbeats()
                
                completed = result.get('interactions_completed', 0) if isinstance(result, dict) else 0
                failed = result.get('interactions_failed', 0) if isinstance(result, dict) else 0
                
                # Log recent completions with instruction names
                if completed > 0:
                    cursor = runner_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cursor.execute("""
                        SELECT COALESCE(ins.instruction_name, '(unknown)') as instruction, a.actor_name, COUNT(*) as cnt
                        FROM interactions i
                        JOIN actors a ON i.actor_id = a.actor_id
                        LEFT JOIN instructions ins ON i.instruction_id = ins.instruction_id
                        WHERE i.status = 'completed' 
                          AND i.completed_at > NOW() - INTERVAL '10 seconds'
                        GROUP BY ins.instruction_name, a.actor_name
                    """)
                    for row in cursor.fetchall():
                        self.logger.info(f"  ✓ {row['instruction']} via {row['actor_name']} ({row['cnt']} done)")
                    cursor.close()
                
                if completed > 0 or failed > 0:
                    self.logger.info(f"Runner processed: {completed} completed, {failed} failed")
                
                return completed + failed
                
            finally:
                # ALWAYS return connection to pool
                return_connection(runner_conn)
            
        except Exception as e:
            self.logger.exception(f"Runner error: {e}")
            return 0
    
    # NOTE: _reaper_loop() and _reap_stuck_interactions_with_conn() were removed.
    # Running reaper in a separate thread causes a race condition.
    # See docs/daily_notes/2025-12-14_turing_daemon_issues.md for details.
    # Reaper now runs in main loop via _reap_stuck_interactions().
    
    def _update_heartbeats(self):
        """Update heartbeat_at for all running interactions."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE interactions 
                SET heartbeat_at = NOW()
                WHERE status = 'running'
            """)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Heartbeat update error: {e}")
    
    def _reap_stuck_interactions(self):
        """
        Find and reset interactions that have been running too long.
        Uses per-conversation timeout_seconds when available, falls back to global threshold.
        Sets to 'failed' with failure_type='timeout_reaped'.
        
        Checks TWO conditions:
        1. Heartbeat stale (heartbeat_at older than timeout) - daemon died
        2. Runtime exceeded (started_at older than timeout) - interaction stuck in Ollama
        """
        cursor = self.conn.cursor()
        
        try:
            # First, count how many running interactions exist
            cursor.execute("""
                SELECT COUNT(*) FROM interactions WHERE status = 'running'
            """)
            running_count = cursor.fetchone()[0]
            
            # Use per-conversation timeout when available, fallback to global threshold
            # KEY FIX: Check started_at for ABSOLUTE runtime limit, not just heartbeat
            cursor.execute("""
                UPDATE interactions i
                SET status = 'failed',
                    failure_type = 'timeout_reaped',
                    error_message = format('Auto-reset: exceeded %%ss timeout (started %%s ago)', 
                                          COALESCE(c.timeout_seconds, %s),
                                          EXTRACT(EPOCH FROM (NOW() - i.started_at))::int),
                    completed_at = NOW()
                FROM conversations c
                WHERE i.conversation_id = c.conversation_id
                  AND i.status = 'running'
                  AND (
                      -- Condition 1: Heartbeat stale (daemon died mid-processing)
                      i.heartbeat_at < NOW() - (COALESCE(c.timeout_seconds, %s) || ' seconds')::interval
                      -- Condition 2: No heartbeat set yet
                      OR (i.heartbeat_at IS NULL 
                          AND i.started_at < NOW() - (COALESCE(c.timeout_seconds, %s) || ' seconds')::interval)
                      -- Condition 3: ABSOLUTE RUNTIME exceeded (stuck in Ollama)
                      OR i.started_at < NOW() - (COALESCE(c.timeout_seconds, %s) || ' seconds')::interval
                  )
                RETURNING i.interaction_id, c.canonical_name, c.timeout_seconds, 
                          EXTRACT(EPOCH FROM (NOW() - i.started_at))::int as runtime_secs
            """, (self.stuck_threshold, self.stuck_threshold, self.stuck_threshold, self.stuck_threshold))
            
            reaped = cursor.fetchall()
            self.conn.commit()
            
            if reaped:
                details = [f"{r[0]}({r[1]}:{r[2]}s timeout, ran {r[3]}s)" for r in reaped]
                self.logger.warning(f"🔪 Reaped {len(reaped)} stuck interactions: {details}")
            else:
                self.logger.debug(f"🔍 Reaper check: {running_count} running, none exceeded their timeout")
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Reaper error: {e}")

    def _complete_finished_workflows(self):
        """
        Mark workflow_runs as completed when all their interactions are done.
        
        A workflow_run is finished when it has NO interactions with status 
        'pending' or 'running'. It should be marked:
        - 'completed' if all interactions succeeded
        - 'failed' if any interaction failed
        """
        cursor = self.conn.cursor()
        
        try:
            # Find running workflow_runs where all interactions are terminal
            # Mark as 'completed' if no failures, 'failed' if any failures
            cursor.execute("""
                WITH finished_runs AS (
                    SELECT 
                        wr.workflow_run_id,
                        COUNT(*) FILTER (WHERE i.status = 'failed') as failed_count,
                        COUNT(*) as total_count
                    FROM workflow_runs wr
                    JOIN interactions i ON i.workflow_run_id = wr.workflow_run_id
                    WHERE wr.status = 'running'
                    GROUP BY wr.workflow_run_id
                    HAVING COUNT(*) FILTER (WHERE i.status IN ('pending', 'running')) = 0
                )
                UPDATE workflow_runs wr
                SET 
                    status = CASE 
                        WHEN fr.failed_count > 0 THEN 'failed'
                        ELSE 'completed'
                    END,
                    completed_at = NOW(),
                    updated_at = NOW()
                FROM finished_runs fr
                WHERE wr.workflow_run_id = fr.workflow_run_id
                RETURNING wr.workflow_run_id, wr.status, fr.total_count, fr.failed_count
            """)
            
            completed = cursor.fetchall()
            self.conn.commit()
            
            if completed:
                succeeded = [r for r in completed if r[1] == 'completed']
                failed = [r for r in completed if r[1] == 'failed']
                
                if succeeded:
                    self.logger.info(f"✅ Completed {len(succeeded)} workflow_runs: {[r[0] for r in succeeded[:5]]}{'...' if len(succeeded) > 5 else ''}")
                if failed:
                    self.logger.warning(f"❌ Marked {len(failed)} workflow_runs as failed: {[r[0] for r in failed[:5]]}{'...' if len(failed) > 5 else ''}")
                    
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Workflow completion check error: {e}")
        finally:
            cursor.close()

    def _cleanup_stale_queue(self):
        """
        Clean up stale queue entries:
        1. Mark 'processing' entries stuck >30 min as 'completed'
        2. Reset expires_at for 'pending' entries that have expired
        """
        cursor = self.conn.cursor()
        
        try:
            # 1. Complete stuck processing entries
            cursor.execute("""
                UPDATE queue
                SET status = 'completed'
                WHERE status = 'processing'
                  AND processing_started_at < NOW() - INTERVAL '30 minutes'
                RETURNING queue_id
            """)
            
            cleaned = cursor.fetchall()
            if cleaned:
                self.logger.info(f"Cleaned up {len(cleaned)} stale processing queue entries")
            
            # 2. Reset expired pending entries so they can be claimed
            cursor.execute("""
                UPDATE queue
                SET expires_at = NULL
                WHERE status = 'pending'
                  AND expires_at IS NOT NULL
                  AND expires_at < NOW()
                RETURNING queue_id
            """)
            
            reset = cursor.fetchall()
            if reset:
                self.logger.info(f"Reset {len(reset)} expired pending queue entries")
            
            self.conn.commit()
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Queue cleanup error: {e}")


def check_status():
    """Check if daemon is running."""
    if not LOCK_FILE.exists():
        print("Daemon is NOT running (no lock file)")
        return 1
    
    try:
        with open(LOCK_FILE) as f:
            lines = f.readlines()
            pid = int(lines[0].strip())
            started = lines[1].strip() if len(lines) > 1 else "unknown"
        
        # Check if PID is alive
        try:
            os.kill(pid, 0)
            print(f"Daemon is RUNNING (PID {pid}, started {started})")
            return 0
        except OSError:
            print(f"Daemon is NOT running (stale lock file, PID {pid})")
            LOCK_FILE.unlink(missing_ok=True)
            return 1
    except Exception as e:
        print(f"Error checking status: {e}")
        return 1


def stop_daemon():
    """Send SIGTERM to running daemon."""
    if not LOCK_FILE.exists():
        print("Daemon is not running")
        return 0
    
    try:
        with open(LOCK_FILE) as f:
            pid = int(f.readline().strip())
        
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to PID {pid}")
        
        # Wait for shutdown
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                print("Daemon stopped")
                return 0
        
        print("Daemon did not stop gracefully, sending SIGKILL")
        os.kill(pid, signal.SIGKILL)
        return 0
        
    except Exception as e:
        print(f"Error stopping daemon: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Turing Daemon - Unified Workflow Engine')
    parser.add_argument('--status', action='store_true', help='Check if daemon is running')
    parser.add_argument('--stop', action='store_true', help='Stop running daemon')
    parser.add_argument('--poll-interval', type=int, default=5, help='Seconds between polls')
    parser.add_argument('--queue-batch', type=int, default=10, help='Queue entries per cycle')
    parser.add_argument('--runner-batch', type=int, default=50, help='Interactions per cycle')
    parser.add_argument('--workflow-id', type=int, default=3001, help='Workflow ID to process')
    
    args = parser.parse_args()
    
    if args.status:
        return check_status()
    
    if args.stop:
        return stop_daemon()
    
    # Run daemon
    daemon = TuringDaemon(
        poll_interval=args.poll_interval,
        queue_batch_size=args.queue_batch,
        runner_batch_size=args.runner_batch,
        workflow_id=args.workflow_id
    )
    return daemon.run()


if __name__ == '__main__':
    sys.exit(main())
