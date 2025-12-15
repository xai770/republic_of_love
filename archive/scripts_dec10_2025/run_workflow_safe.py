#!/usr/bin/env python3
"""
Safe Workflow Runner - Prevents Multiple Instances

Uses a PID file as a "lock" to ensure only one runner at a time.

═══════════════════════════════════════════════════════════════════════════════
HOW TO START THIS SCRIPT
═══════════════════════════════════════════════════════════════════════════════

    cd /home/xai/Documents/ty_learn
    ./scripts/run_workflow.sh 3001

That's it! The wrapper script handles:
- Activating the virtual environment
- Running in background with nohup (survives terminal close)
- Redirecting output to timestamped log file
- Printing monitoring commands

⚠️  DO NOT run directly with python3 - it will refuse:
    python3 scripts/run_workflow_safe.py 3001   # ❌ BLOCKED

═══════════════════════════════════════════════════════════════════════════════
WHY THE WRAPPER?
═══════════════════════════════════════════════════════════════════════════════

1. AUDIT TRAIL: Every execution is logged to conversation 9198 (Workflow Orchestrator)
   - Who started it? When? What workflow? How long did it run?
   - The wrapper sets a "secret handshake" that this script validates

2. BACKGROUND EXECUTION: Workflows take hours. Without nohup:
   - Close terminal → workflow dies
   - SSH timeout → workflow dies
   - With nohup → workflow survives

3. PREVENT DUPLICATES: PID file lock prevents starting twice

═══════════════════════════════════════════════════════════════════════════════
MONITORING & CONTROL
═══════════════════════════════════════════════════════════════════════════════

    # Watch the log
    tail -f logs/workflow_3001_*.log
    
    # Check status
    ./scripts/status.sh
    
    # Stop it
    kill $(cat /tmp/workflow_3001.pid)

═══════════════════════════════════════════════════════════════════════════════

The Lock Mechanism (like a bathroom lock):
1. Check if lock file exists
2. If yes - check if that process is still alive
   - Still alive? Exit (someone's using it)
   - Dead? Clean up old lock, continue
3. If no - create lock with our PID
4. Do the work
5. Remove lock when done

PID file location: /tmp/workflow_{id}.pid

Author: Sandy (ℶ)
Date: 2025-11-30
"""

import os
import sys
import signal
import atexit
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# GUARD: Enforce wrapper usage + record as interaction
# Uses shared module - single source of truth for the secret
# ═══════════════════════════════════════════════════════════════
from core.workflow_guard import require_wrapper, complete_workflow_interaction

# Get workflow_id early so we can use it in the interaction description
workflow_id_arg = sys.argv[1] if len(sys.argv) > 1 else "3001"

interaction_id = require_wrapper(
    script_name="run_workflow_safe.py",
    description=f"Workflow {workflow_id_arg} runner"
)


class WorkflowLock:
    """
    A lock that prevents multiple workflow runners.
    
    Think of it like this:
    - The PID file is a "OCCUPIED" sign on a bathroom door
    - The PID inside is WHO is using it
    - We can check if they're still there (process alive?)
    """
    
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
        self.pid_file = Path(f"/tmp/workflow_{workflow_id}.pid")
        self.locked = False
    
    def is_process_alive(self, pid: int) -> bool:
        """Check if a process is still running."""
        try:
            # Sending signal 0 doesn't kill - just checks if process exists
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False  # Process doesn't exist
        except PermissionError:
            return True   # Exists but we can't signal it
    
    def acquire(self) -> bool:
        """
        Try to acquire the lock.
        
        Returns:
            True if we got the lock
            False if someone else has it
        """
        # Step 1: Check if lock file exists
        if self.pid_file.exists():
            try:
                old_pid = int(self.pid_file.read_text().strip())
                
                # Step 2: Is that process still alive?
                if self.is_process_alive(old_pid):
                    # Someone's using it! Don't intrude.
                    print(f"🚫 Lock held by PID {old_pid} (still running)")
                    return False
                else:
                    # Old lock from dead process - clean it up
                    print(f"🧹 Cleaning stale lock from dead PID {old_pid}")
                    self.pid_file.unlink()
                    
            except (ValueError, FileNotFoundError):
                # Corrupted or disappeared - clean up
                if self.pid_file.exists():
                    self.pid_file.unlink()
        
        # Step 3: Create our lock
        my_pid = os.getpid()
        self.pid_file.write_text(str(my_pid))
        self.locked = True
        print(f"🔒 Lock acquired (PID {my_pid})")
        
        return True
    
    def release(self):
        """Release the lock (remove the PID file)."""
        if self.locked and self.pid_file.exists():
            try:
                # Only remove if it's still our PID
                current_pid = int(self.pid_file.read_text().strip())
                if current_pid == os.getpid():
                    self.pid_file.unlink()
                    print(f"🔓 Lock released")
            except:
                pass
        self.locked = False
    
    def __enter__(self):
        """Support 'with' statement."""
        if not self.acquire():
            raise RuntimeError(f"Could not acquire lock for workflow {self.workflow_id}")
        return self
    
    def __exit__(self, *args):
        """Auto-release when exiting 'with' block."""
        self.release()


def run_workflow(workflow_id: int, max_iterations: int):
    """Run the workflow with proper locking."""
    
    # Create the lock
    lock = WorkflowLock(workflow_id)
    
    # Try to acquire it
    if not lock.acquire():
        print(f"\n❌ Another instance is already running workflow {workflow_id}")
        print(f"   Check: cat /tmp/workflow_{workflow_id}.pid")
        print(f"   Force: rm /tmp/workflow_{workflow_id}.pid  (if you're sure it's dead)")
        sys.exit(1)
    
    # Register cleanup for when we exit (normal or crash)
    def cleanup():
        lock.release()
    
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))  # Handle kill command
    signal.signal(signal.SIGINT, lambda *args: sys.exit(0))   # Handle Ctrl+C
    
    # Now do the actual work
    print(f"\n🚀 Starting Workflow {workflow_id}")
    print(f"   PID: {os.getpid()}")
    print(f"   Parent interaction: #{interaction_id}")
    print(f"   Max iterations: {max_iterations}")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST')
        )
        
        # Import and run
        from core.wave_runner.runner import WaveRunner
        
        runner = WaveRunner(
            db_conn=conn,
            global_batch=True,
            workflow_id=workflow_id,  # Filter to just this workflow
            runner_id=f'safe_runner_{os.getpid()}',
            trigger_interaction_id=interaction_id  # Links all child work back to this run
        )
        
        stats = runner.run(max_iterations=max_iterations)
        
        print()
        print("=" * 50)
        print("✅ RUN COMPLETE")
        print(f"   Completed: {stats['interactions_completed']}")
        print(f"   Failed: {stats['interactions_failed']}")
        print(f"   Iterations: {stats['iterations']}")
        print(f"   Duration: {stats['duration_ms'] / 1000:.1f}s")
        
        # Mark workflow interaction as complete
        complete_workflow_interaction(interaction_id, output=stats)
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        # Mark workflow interaction as failed
        complete_workflow_interaction(interaction_id, error=str(e))
        raise
    finally:
        # Lock is auto-released via atexit
        pass


def main():
    parser = argparse.ArgumentParser(
        description='Safe workflow runner with lock protection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Normal run
    python3 scripts/run_workflow_safe.py
    
    # Background run with nohup
    nohup python3 -u scripts/run_workflow_safe.py > logs/batch.log 2>&1 &
    
    # Check if running
    cat /tmp/workflow_3001.pid
    
    # Force unlock (careful!)
    rm /tmp/workflow_3001.pid
        """
    )
    
    parser.add_argument('--workflow', type=int, default=3001,
                        help='Workflow ID (default: 3001)')
    parser.add_argument('--max-iterations', type=int, default=10000,
                        help='Maximum iterations (default: 10000)')
    
    args = parser.parse_args()
    
    run_workflow(args.workflow, args.max_iterations)


if __name__ == '__main__':
    main()
