#!/usr/bin/env python3
"""
Turing Daemon - The pipeline execution engine.

Runs all actors in parallel with:
- ONE ticket per batch run (traceability)
- ThreadPoolExecutor with max_workers parallelism
- VPN rotation on 403 rate limits
- Aggregated results in ticket.output

Traceability: ticket.output.success_ids / failed_ids contain
all processed posting IDs. Query: WHERE output->'success_ids' ? '157692'

Usage:
    python3 core/turing_daemon.py                        # Run all enabled task_types
    python3 core/turing_daemon.py --task_type 1299       # Run specific task_type
    python3 core/turing_daemon.py --workers 20 --limit 5000
    python3 core/turing_daemon.py --dry-run              # Show what would run

Configuration:
    task_types.execution_type = 'bulk'  → parallel execution
    task_types.scale_limit              → max_workers for ThreadPoolExecutor
    task_types.batch_size               → How many subjects per batch ticket
"""

import argparse
import fcntl
import importlib.util
import logging
import os
import random
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection_raw, return_connection

# ============================================================================
# VPN ROTATION CONFIG (OpenVPN with ProtonVPN)
# ============================================================================
CONSECUTIVE_403_THRESHOLD = 3      # Trigger VPN rotation after this many
MAX_VPN_ROTATIONS = 10             # Give up after this many rotations
REQUESTS_PER_IP = 550              # Proactive rotation threshold

# ProtonVPN's de config load-balances across German servers
# Reconnecting gives a new IP automatically - no need to track configs
VPN_SCRIPT = PROJECT_ROOT / 'scripts' / 'vpn.sh'

# Thread synchronization
VPN_LOCK = threading.Lock()
VPN_ROTATING = threading.Event()

# Lock file
LOCK_FILE = PROJECT_ROOT / '.turing_daemon.lock'
ADVISORY_LOCK_ID = 73573


class TuringDaemon:
    """
    Turing Daemon - the pipeline execution engine.
    
    Features:
    - Creates ONE ticket per batch (traceability)
    - Uses ThreadPoolExecutor for parallel execution
    - Aggregates all results into ticket.output
    - VPN rotation on 403 rate limits
    """
    
    def __init__(
        self,
        task_type_id: Optional[int] = None,
        workers: Optional[int] = None,  # Override scale_limit
        limit: Optional[int] = None,
        run_once: bool = True,
        dry_run: bool = False,
        batch_reason: Optional[str] = None,
    ):
        self.task_type_id = task_type_id
        self.workers_override = workers
        self.limit = limit
        self.run_once = run_once
        self.dry_run = dry_run
        self.batch_reason = batch_reason or f"BULK_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.conn = None
        self.running = True
        self.lock_file = None
        
        # VPN state
        self._consecutive_403s = 0
        self._vpn_rotation_count = 0
        self._current_vpn_index = -1
        self._request_count = 0
        self._request_lock = threading.Lock()
        
        # Results aggregation (thread-safe)
        self._results_lock = threading.Lock()
        self._success_ids: List[int] = []
        self._failed_ids: Dict[int, str] = {}  # id -> error
        self._skipped_ids: Dict[int, str] = {}  # id -> reason
        
        self.logger = self._setup_logging()
        
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger('turing_daemon')
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Don't double-log to root logger
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            ))
            logger.addHandler(handler)
        return logger
    
    def _handle_signal(self, signum, frame):
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _acquire_lock(self) -> bool:
        """Acquire file + DB advisory lock."""
        try:
            self.lock_file = open(LOCK_FILE, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
            self.lock_file.flush()
        except (IOError, OSError):
            self.logger.error("Another turing_daemon is already running (file lock)")
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT pg_try_advisory_lock(%s) AS locked", (ADVISORY_LOCK_ID,))
            result = cursor.fetchone()
            if not result['locked']:
                self.logger.error("Another turing_daemon is already running (DB lock)")
                return False
        except Exception as e:
            self.logger.error(f"Failed to acquire DB lock: {e}")
            return False
        
        return True
    
    def _release_lock(self):
        """Release locks."""
        if self.conn:
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
            except OSError:
                pass
    
    # =========================================================================
    # VPN ROTATION
    # =========================================================================
    
    def _rotate_vpn(self) -> bool:
        """Rotate VPN using OpenVPN. Thread-safe - only one rotation at a time.
        
        ProtonVPN's de config load-balances across German servers.
        Reconnecting gives a new IP automatically.
        """
        with VPN_LOCK:
            VPN_ROTATING.set()
            try:
                self.logger.info("🔄 ROTATING VPN (reconnect for new IP)")
                
                # Use vpn.sh rotate for clean disconnect/reconnect
                result = subprocess.run(
                    [str(VPN_SCRIPT), 'rotate'],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode != 0:
                    self.logger.warning(f"  ⚠️ VPN rotate failed: {result.stderr}")
                else:
                    self.logger.info(f"  ✅ VPN rotated")
                    time.sleep(2)  # Let connection stabilize
                
                self._request_count = 0  # Reset proactive counter
                return result.returncode == 0
                
            except Exception as e:
                self.logger.warning(f"  ⚠️ VPN rotation error: {e}")
                return False
            finally:
                VPN_ROTATING.clear()
    
    def _check_proactive_rotation(self):
        """Check if we should proactively rotate VPN before hitting rate limit."""
        with self._request_lock:
            self._request_count += 1
            if self._request_count >= REQUESTS_PER_IP:
                self.logger.info(f"🔄 Proactive VPN rotation at {self._request_count} requests...")
                self._rotate_vpn()
    
    def _handle_rate_limit(self) -> bool:
        """Handle rate limiting. Returns True if recovered, False if exhausted."""
        self._vpn_rotation_count += 1
        
        if self._vpn_rotation_count > MAX_VPN_ROTATIONS:
            self.logger.error(f"🛑 RATE LIMIT: Exhausted all {MAX_VPN_ROTATIONS} VPN rotations")
            return False
        
        self.logger.warning(f"🛑 RATE LIMIT HIT - {self._consecutive_403s} consecutive 403s, rotating VPN #{self._vpn_rotation_count}...")
        
        self._rotate_vpn()
        self._consecutive_403s = 0
        return True
    
    # =========================================================================
    # TASK TYPE LOADING
    # =========================================================================
    
    def _get_bulk_task_types(self) -> List[Dict]:
        """Get task_types with execution_type='bulk'."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT 
                t.task_type_id,
                t.actor_id,
                t.task_type_name,
                t.script_path,
                t.work_query,
                t.scale_limit,
                t.batch_size,
                t.execution_type,
                t.enabled
            FROM task_types t
            WHERE t.execution_type = 'bulk'
              AND t.enabled = true
              AND t.work_query IS NOT NULL
        """
        
        if self.task_type_id:
            query += f" AND t.task_type_id = {self.task_type_id}"
        
        query += " ORDER BY t.priority DESC"
        
        cursor.execute(query)
        return list(cursor.fetchall())
    
    def _find_work(self, task_type: Dict, limit: int) -> List[Dict]:
        """Execute work_query to find subjects."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        work_query = task_type['work_query']
        if not work_query:
            return []
        
        # Handle named parameters like :batch_size
        import re
        work_query = re.sub(r':batch_size\b', str(limit), work_query, flags=re.IGNORECASE)
        
        # Add LIMIT if not present
        if 'LIMIT' not in work_query.upper():
            work_query = f"{work_query} LIMIT {limit}"
        else:
            # Replace existing LIMIT with our limit
            work_query = re.sub(r'LIMIT\s+\d+', f'LIMIT {limit}', work_query, flags=re.IGNORECASE)
        
        try:
            cursor.execute(work_query)
            rows = cursor.fetchall()
            
            # Normalize to have subject_id
            subjects = []
            for row in rows:
                subject = dict(row)
                if 'subject_id' not in subject:
                    # Try common ID columns
                    for key in ['posting_id', 'profile_id', 'id']:
                        if key in subject:
                            subject['subject_id'] = subject[key]
                            break
                subjects.append(subject)
            
            return subjects
        except Exception as e:
            self.logger.error(f"work_query failed: {e}")
            return []
    
    def _load_actor(self, task_type: Dict):
        """Load actor class from script_path."""
        script_path = task_type.get('script_path')
        if not script_path:
            raise ValueError(f"No script_path for {task_type['task_type_name']}")
        
        full_path = PROJECT_ROOT / script_path
        if not full_path.exists():
            raise FileNotFoundError(f"Script not found: {full_path}")
        
        spec = importlib.util.spec_from_file_location("actor_module", full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find actor class
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and name != 'ScriptActorBase' and hasattr(obj, 'process'):
                return obj
        
        raise ValueError(f"No actor class found in {script_path}")
    
    # =========================================================================
    # TICKET MANAGEMENT
    # =========================================================================
    
    def _create_batch_ticket(self, task_type: Dict, subject_count: int) -> int:
        """Create ONE ticket for the entire batch."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            INSERT INTO tickets (
                task_type_id,
                actor_id,
                actor_type,
                execution_order,
                subject_type,
                subject_id,
                status,
                input,
                started_at
            ) VALUES (
                %s,
                %s,
                'script',
                1,
                'batch',
                0,
                'running',
                %s,
                NOW()
            )
            RETURNING ticket_id
        """, (
            task_type['task_type_id'],
            task_type['actor_id'],
            psycopg2.extras.Json({
                'batch_reason': self.batch_reason,
                'subject_count': subject_count,
                'max_workers': self.workers_override or task_type['scale_limit'],
            })
        ))
        
        row = cursor.fetchone()
        self.conn.commit()
        return row['ticket_id']
    
    def _complete_batch_ticket(self, ticket_id: int):
        """Complete ticket with aggregated results."""
        cursor = self.conn.cursor()
        
        output = {
            'success_count': len(self._success_ids),
            'failed_count': len(self._failed_ids),
            'skipped_count': len(self._skipped_ids),
            'success_ids': self._success_ids,
            'failed_ids': self._failed_ids,
            'skipped_ids': self._skipped_ids,
            'vpn_rotations': self._vpn_rotation_count,
        }
        
        cursor.execute("""
            UPDATE tickets
            SET status = 'completed',
                output = %s,
                completed_at = NOW()
            WHERE ticket_id = %s
        """, (psycopg2.extras.Json(output), ticket_id))
        self.conn.commit()
    
    def _fail_batch_ticket(self, ticket_id: int, error: str):
        """Mark batch ticket as failed."""
        cursor = self.conn.cursor()
        
        output = {
            'error': error,
            'success_count': len(self._success_ids),
            'failed_count': len(self._failed_ids),
            'success_ids': self._success_ids,
            'failed_ids': self._failed_ids,
        }
        
        cursor.execute("""
            UPDATE tickets
            SET status = 'failed',
                output = %s,
                completed_at = NOW()
            WHERE ticket_id = %s
        """, (psycopg2.extras.Json(output), ticket_id))
        self.conn.commit()
    
    # =========================================================================
    # WORKER EXECUTION
    # =========================================================================
    
    def _process_one(self, actor_class, subject: Dict) -> Tuple[int, str, Optional[str]]:
        """
        Process one subject. Called by worker threads.
        
        Returns:
            (subject_id, status, error_or_none)
            status: 'success', 'failed', 'skipped', 'rate_limited'
        """
        subject_id = subject['subject_id']
        
        # Wait if VPN rotation is in progress
        while VPN_ROTATING.is_set():
            time.sleep(0.5)
        
        # Check proactive rotation
        self._check_proactive_rotation()
        
        # Each worker gets its own DB connection
        conn = get_connection_raw()
        try:
            actor = actor_class(db_conn=conn)
            actor.input_data = subject
            
            result = actor.process()
            
            if isinstance(result, dict):
                # Check for success (two patterns: 'success': True or 'status': 'success')
                if result.get('success') or result.get('status') == 'success':
                    return (subject_id, 'success', None)
                
                # Check for skip (two patterns: 'skip_reason' or 'status': 'skip')
                skip_reason = result.get('skip_reason') or result.get('reason')
                if skip_reason or result.get('status') == 'skip':
                    return (subject_id, 'skipped', skip_reason or 'skipped')
                
                error = result.get('error', 'Unknown error')
                http_status = result.get('http_status')
                
                # Detect rate limiting
                if http_status == 403 or '403' in str(error) or 'rate' in str(error).lower():
                    return (subject_id, 'rate_limited', error)
                
                return (subject_id, 'failed', error)
            
            return (subject_id, 'failed', 'Actor returned non-dict')
            
        except Exception as e:
            error_str = str(e)
            if '403' in error_str or 'rate' in error_str.lower():
                return (subject_id, 'rate_limited', error_str)
            return (subject_id, 'failed', error_str)
        finally:
            return_connection(conn)
    
    def _aggregate_result(self, subject_id: int, status: str, error: Optional[str]):
        """Thread-safe result aggregation."""
        with self._results_lock:
            if status == 'success':
                self._success_ids.append(subject_id)
                self._consecutive_403s = 0
            elif status == 'skipped':
                self._skipped_ids[subject_id] = error or 'skipped'
                self._consecutive_403s = 0
            elif status == 'rate_limited':
                self._failed_ids[subject_id] = error or 'rate_limited'
                self._consecutive_403s += 1
            else:
                self._failed_ids[subject_id] = error or 'unknown'
                self._consecutive_403s = 0
    
    # =========================================================================
    # MAIN RUN LOOP
    # =========================================================================
    
    def run(self):
        """Main entry point."""
        self.conn = get_connection_raw()
        
        if not self._acquire_lock():
            return_connection(self.conn)
            return
        
        try:
            task_types = self._get_bulk_task_types()
            
            if not task_types:
                self.logger.info("No bulk task_types found")
                return
            
            for task_type in task_types:
                if not self.running:
                    break
                
                self._run_task_type(task_type)
                
        except Exception as e:
            self.logger.exception(f"Fatal error: {e}")
        finally:
            self._release_lock()
            return_connection(self.conn)
    
    def _run_task_type(self, task_type: Dict):
        """Run one task_type with parallel workers."""
        name = task_type['task_type_name']
        max_workers = self.workers_override or task_type['scale_limit'] or 50
        fetch_limit = self.limit or 50000
        
        self.logger.info(f"📋 {name}: Finding work...")
        
        # Find subjects
        subjects = self._find_work(task_type, fetch_limit)
        if not subjects:
            self.logger.info(f"  No work found for {name}")
            return
        
        self.logger.info(f"  Found {len(subjects)} subjects, launching {max_workers} workers")
        
        if self.dry_run:
            self.logger.info(f"  [DRY RUN] Would process {len(subjects)} subjects")
            return
        
        # Load actor class
        try:
            actor_class = self._load_actor(task_type)
        except Exception as e:
            self.logger.error(f"  Failed to load actor: {e}")
            return
        
        # Reset aggregation state
        self._success_ids = []
        self._failed_ids = {}
        self._skipped_ids = {}
        self._consecutive_403s = 0
        self._vpn_rotation_count = 0
        self._request_count = 0
        rate_limited = False
        
        # Create batch ticket
        ticket_id = self._create_batch_ticket(task_type, len(subjects))
        self.logger.info(f"  Created ticket {ticket_id}")
        
        # Run with thread pool
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._process_one, actor_class, subject): subject
                    for subject in subjects
                }
                
                completed = 0
                for future in as_completed(futures):
                    if not self.running:
                        break
                    
                    subject_id, status, error = future.result()
                    self._aggregate_result(subject_id, status, error)
                    
                    completed += 1
                    
                    # Check rate limit threshold
                    if self._consecutive_403s >= CONSECUTIVE_403_THRESHOLD:
                        if not self._handle_rate_limit():
                            self.logger.error(f"Rate limit exhausted for {name}, moving to next actor")
                            rate_limited = True
                            break
                    
                    # Progress logging
                    if completed % 500 == 0:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        self.logger.info(
                            f"  Progress: {completed}/{len(subjects)} "
                            f"({len(self._success_ids)} ok, {len(self._failed_ids)} fail) "
                            f"@ {rate:.1f}/sec"
                        )
            
            # Complete ticket
            elapsed = time.time() - start_time
            self._complete_batch_ticket(ticket_id)
            
            self.logger.info(
                f"✅ {name} complete: {len(self._success_ids)} success, "
                f"{len(self._failed_ids)} failed, {len(self._skipped_ids)} skipped "
                f"in {elapsed:.1f}s ({self._vpn_rotation_count} VPN rotations)"
            )
            
        except Exception as e:
            self._fail_batch_ticket(ticket_id, str(e))
            self.logger.error(f"❌ {name} failed: {e}")


def main():
    parser = argparse.ArgumentParser(description='Turing daemon - pipeline execution engine')
    parser.add_argument('--task_type', type=int, help='Run specific task_type')
    parser.add_argument('--workers', type=int, help='Override max workers')
    parser.add_argument('--limit', type=int, help='Max subjects to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run')
    parser.add_argument('--batch-reason', type=str, help='Batch reason prefix')
    
    args = parser.parse_args()
    
    daemon = TuringDaemon(
        task_type_id=args.task_type,
        workers=args.workers,
        limit=args.limit,
        dry_run=args.dry_run,
        batch_reason=args.batch_reason,
    )
    
    daemon.run()


if __name__ == '__main__':
    main()
