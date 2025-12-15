#!/usr/bin/env python3
"""
Run Workflow CLI

Database-driven workflow execution with validation and logging.
Every execution is logged as an interaction for full audit trail.

Usage:
    ./tools/run_workflow.py 3001                    # Global batch mode (default)
    ./tools/run_workflow.py 3001 --mode single_posting --posting-id 4920
    ./tools/run_workflow.py 3001 --mode single_run --workflow-run-id 123
    ./tools/run_workflow.py 3001 --max-iterations 100  # With limit (not recommended)
    
    # Query running workflows
    ./tools/run_workflow.py --list-running
    
    # Stop workflow (marks as failed)
    ./tools/run_workflow.py --stop --workflow-run-id 123

This replaces manual Python commands:
    # OLD (no audit trail, easy to mess up)
    python3 -c "from core.wave_runner.runner import WaveRunner; ..."
    
    # NEW (logged, validated, safe)
    ./tools/run_workflow.py 3001
"""

import argparse
import json
import os
import sys
import signal
import atexit
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection, return_connection

# Orchestrator conversation ID for audit logging
ORCHESTRATOR_CONVERSATION_ID = 9198


class PIDManager:
    """Manage PID file for workflow runs to prevent duplicate executions."""
    
    def __init__(self, workflow_id: int):
        self.workflow_id = workflow_id
        self.pid_file = Path(f"/tmp/workflow_{workflow_id}.pid")
        self.pid = os.getpid()
        self._acquired = False
    
    def acquire(self) -> bool:
        """Try to acquire the PID lock. Returns True if successful."""
        if self.pid_file.exists():
            try:
                existing_pid = int(self.pid_file.read_text().strip())
                # Check if process is still running
                os.kill(existing_pid, 0)  # Signal 0 = check existence
                print(f"❌ Workflow {self.workflow_id} already running (PID {existing_pid})")
                print(f"   Use 'scripts/check_running_batches.sh --force' to kill it")
                return False
            except ProcessLookupError:
                # Process is dead, stale PID file
                print(f"⚠️  Removing stale PID file (PID {existing_pid} not running)")
                self.pid_file.unlink()
            except ValueError:
                # Invalid PID file content
                print(f"⚠️  Removing invalid PID file")
                self.pid_file.unlink()
        
        # Write our PID
        self.pid_file.write_text(str(self.pid))
        self._acquired = True
        print(f"🔒 Acquired lock: {self.pid_file} (PID {self.pid})")
        return True
    
    def release(self):
        """Release the PID lock."""
        if not self._acquired:
            return
        if self.pid_file.exists():
            try:
                existing_pid = int(self.pid_file.read_text().strip())
                if existing_pid == self.pid:
                    self.pid_file.unlink()
                    print(f"🔓 Released lock: {self.pid_file}")
            except Exception as e:
                print(f"⚠️  Error releasing lock: {e}")


# Global PID manager for cleanup
_pid_manager = None


def capture_state_snapshot(conn) -> dict:
    """Capture current posting processing state."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL) as with_summary,
            COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as with_skills,
            COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as with_ihl
        FROM postings
    """)
    row = cursor.fetchone()
    cursor.close()
    return {
        "postings_total": row['total'],
        "postings_with_summary": row['with_summary'],
        "postings_with_skills": row['with_skills'],
        "postings_with_ihl": row['with_ihl'],
        "captured_at": datetime.now().isoformat()
    }


def estimate_pending_work(conn) -> dict:
    """Estimate how much work the workflow will do."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE extracted_summary IS NULL AND job_description IS NOT NULL) as pending_summary,
            COUNT(*) FILTER (WHERE skill_keywords IS NULL AND extracted_summary IS NOT NULL) as pending_skills,
            COUNT(*) FILTER (WHERE ihl_score IS NULL AND skill_keywords IS NOT NULL) as pending_ihl
        FROM postings
    """)
    row = cursor.fetchone()
    cursor.close()
    return {
        "pending_summary": row['pending_summary'],
        "pending_skills": row['pending_skills'],
        "pending_ihl": row['pending_ihl']
    }


def create_orchestrator_interaction(conn, input_data: dict, state_before: dict, expected_work: dict) -> int:
    """Create orchestrator interaction at START of workflow run."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interactions (
            conversation_id, actor_id, actor_type, execution_order, input, status, created_at, updated_at
        )
        SELECT 
            %s,
            c.actor_id,
            'script',
            COALESCE((SELECT MAX(execution_order) + 1 FROM interactions WHERE conversation_id = %s), 1),
            %s,
            'running',
            NOW(),
            NOW()
        FROM conversations c
        WHERE c.conversation_id = %s
        RETURNING interaction_id
    """, (
        ORCHESTRATOR_CONVERSATION_ID,
        ORCHESTRATOR_CONVERSATION_ID,
        json.dumps({
            **input_data,
            "action": "workflow_execution",
            "state_before": state_before,
            "expected_work": expected_work
        }),
        ORCHESTRATOR_CONVERSATION_ID
    ))
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    return row['interaction_id'] if row else None


def update_orchestrator_interaction(conn, interaction_id: int, result: dict, state_after: dict, state_before: dict):
    """Update orchestrator interaction at END of workflow run with results and state delta."""
    delta = {
        "total": state_after['postings_total'] - state_before['postings_total'],
        "summary": state_after['postings_with_summary'] - state_before['postings_with_summary'],
        "skills": state_after['postings_with_skills'] - state_before['postings_with_skills'],
        "ihl": state_after['postings_with_ihl'] - state_before['postings_with_ihl']
    }
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE interactions 
        SET 
            output = %s,
            status = %s,
            updated_at = NOW()
        WHERE interaction_id = %s
    """, (
        json.dumps({
            **result,
            "state_after": state_after,
            "delta": delta
        }),
        'completed' if result.get('status') == 'completed' else 'failed',
        interaction_id
    ))
    conn.commit()
    cursor.close()


def run_workflow(args):
    """Execute workflow via workflow_executor actor with full audit trail."""
    global _pid_manager
    
    # === PID Management ===
    _pid_manager = PIDManager(args.workflow_id)
    
    if args.force:
        # Kill existing process if --force
        if _pid_manager.pid_file.exists():
            try:
                existing_pid = int(_pid_manager.pid_file.read_text().strip())
                os.kill(existing_pid, signal.SIGTERM)
                print(f"🔪 Killed existing process (PID {existing_pid})")
                import time
                time.sleep(1)
            except:
                pass
    
    if not _pid_manager.acquire():
        return 1
    
    # Register cleanup
    atexit.register(_pid_manager.release)
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    
    conn = get_connection()
    
    # Import here to use existing actor infrastructure
    from core.wave_runner.actors.workflow_executor import WorkflowExecutorActor
    
    # Build input
    input_data = {
        "workflow_id": args.workflow_id,
        "mode": args.mode,
        "posting_id": args.posting_id,
        "target_workflow_run_id": args.workflow_run_id,
        "max_iterations": args.max_iterations,
        "requested_by": os.environ.get('USER', 'unknown')
    }
    
    # === PHASE 1: Capture state BEFORE ===
    state_before = capture_state_snapshot(conn)
    expected_work = estimate_pending_work(conn)
    
    print(f"🚀 Starting workflow {args.workflow_id} in {args.mode} mode...")
    print(f"   Requested by: {input_data['requested_by']}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"📊 State Before:")
    print(f"   Total: {state_before['postings_total']}, Summary: {state_before['postings_with_summary']}, Skills: {state_before['postings_with_skills']}, IHL: {state_before['postings_with_ihl']}")
    print(f"📋 Expected Work:")
    print(f"   Summaries: {expected_work['pending_summary']}, Skills: {expected_work['pending_skills']}, IHL: {expected_work['pending_ihl']}")
    print()
    
    # === Create orchestrator interaction (audit log) ===
    orch_interaction_id = create_orchestrator_interaction(conn, input_data, state_before, expected_work)
    if orch_interaction_id:
        print(f"📝 Audit interaction created: {orch_interaction_id}")
    
    # Create and run actor
    actor = WorkflowExecutorActor()
    actor.input_data = input_data
    actor.db_conn = conn
    
    # Execute
    result = actor.process()
    
    # === PHASE 2: Capture state AFTER ===
    state_after = capture_state_snapshot(conn)
    
    # Display result
    if result.get('status') == 'completed':
        print("✅ COMPLETED")
        print(f"   Interactions completed: {result.get('interactions_completed', 0)}")
        print(f"   Interactions failed: {result.get('interactions_failed', 0)}")
        print(f"   Batches processed: {result.get('batches_processed', 0)}")
        print(f"   Duration: {result.get('duration_seconds', 0)}s")
    elif result.get('status') == 'rejected':
        print("❌ REJECTED")
        print(f"   Reason: {result.get('rejection_reason')}")
        print(f"   Error: {result.get('error')}")
    else:
        print("💥 FAILED")
        print(f"   Error: {result.get('error')}")
        print(f"   Duration: {result.get('duration_seconds', 0)}s")
    
    # === Show delta ===
    print()
    print(f"📊 State After:")
    print(f"   Total: {state_after['postings_total']}, Summary: {state_after['postings_with_summary']}, Skills: {state_after['postings_with_skills']}, IHL: {state_after['postings_with_ihl']}")
    print(f"📈 Delta:")
    print(f"   Total: +{state_after['postings_total'] - state_before['postings_total']}, Summary: +{state_after['postings_with_summary'] - state_before['postings_with_summary']}, Skills: +{state_after['postings_with_skills'] - state_before['postings_with_skills']}, IHL: +{state_after['postings_with_ihl'] - state_before['postings_with_ihl']}")
    
    # === Update orchestrator interaction with results ===
    if orch_interaction_id:
        update_orchestrator_interaction(conn, orch_interaction_id, result, state_after, state_before)
        print(f"\n📝 Audit interaction updated: {orch_interaction_id}")
    
    return_connection(conn)
    return 0 if result.get('status') == 'completed' else 1


def list_running(args):
    """List currently running workflows."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            wr.workflow_run_id,
            w.workflow_id,
            w.workflow_name,
            wr.status,
            wr.started_at,
            EXTRACT(EPOCH FROM (NOW() - wr.started_at))::int as running_seconds,
            (SELECT COUNT(*) FROM interactions i WHERE i.workflow_run_id = wr.workflow_run_id AND i.status = 'completed') as completed,
            (SELECT COUNT(*) FROM interactions i WHERE i.workflow_run_id = wr.workflow_run_id AND i.status = 'pending') as pending
        FROM workflow_runs wr
        JOIN workflows w ON wr.workflow_id = w.workflow_id
        WHERE wr.status = 'running'
        ORDER BY wr.started_at DESC
    """)
    
    rows = cursor.fetchall()
    cursor.close()
    return_connection(conn)
    
    if not rows:
        print("No workflows currently running.")
        return 0
    
    print(f"{'Run ID':<8} {'WF ID':<6} {'Name':<30} {'Running':<10} {'Done':<6} {'Pending':<7}")
    print("-" * 75)
    for row in rows:
        running = f"{row['running_seconds'] // 60}m {row['running_seconds'] % 60}s"
        print(f"{row['workflow_run_id']:<8} {row['workflow_id']:<6} {row['workflow_name'][:29]:<30} {running:<10} {row['completed']:<6} {row['pending']:<7}")
    
    return 0


def stop_workflow(args):
    """Stop a running workflow by marking it as failed."""
    if not args.workflow_run_id:
        print("Error: --workflow-run-id required for --stop")
        return 1
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Mark workflow_run as failed
    cursor.execute("""
        UPDATE workflow_runs 
        SET status = 'failed', updated_at = NOW()
        WHERE workflow_run_id = %s AND status = 'running'
        RETURNING workflow_run_id
    """, (args.workflow_run_id,))
    
    row = cursor.fetchone()
    
    if row:
        # Also mark pending interactions as failed
        cursor.execute("""
            UPDATE interactions 
            SET status = 'failed', error_message = 'Stopped by user'
            WHERE workflow_run_id = %s AND status IN ('pending', 'running')
        """, (args.workflow_run_id,))
        
        conn.commit()
        print(f"✅ Stopped workflow_run {args.workflow_run_id}")
    else:
        print(f"⚠️  No running workflow_run with ID {args.workflow_run_id}")
    
    cursor.close()
    return_connection(conn)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Run workflows with validation and logging',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s 3001                              # Global batch mode
    %(prog)s 3001 --mode single_posting --posting-id 4920
    %(prog)s --list-running                    # Show running workflows
    %(prog)s --stop --workflow-run-id 123      # Stop a workflow
        """
    )
    
    parser.add_argument('workflow_id', type=int, nargs='?', help='Workflow ID to run')
    parser.add_argument('--mode', choices=['global_batch', 'single_posting', 'single_run'],
                        default='global_batch', help='Execution mode (default: global_batch)')
    parser.add_argument('--posting-id', type=int, help='Posting ID (for single_posting mode)')
    parser.add_argument('--workflow-run-id', type=int, help='Workflow run ID (for single_run mode or --stop)')
    parser.add_argument('--max-iterations', type=int, help='Max iterations (not recommended for production)')
    parser.add_argument('--list-running', action='store_true', help='List currently running workflows')
    parser.add_argument('--stop', action='store_true', help='Stop a running workflow')
    parser.add_argument('--force', action='store_true', help='Kill existing process and take over')
    
    args = parser.parse_args()
    
    if args.list_running:
        return list_running(args)
    
    if args.stop:
        return stop_workflow(args)
    
    if not args.workflow_id:
        parser.print_help()
        return 1
    
    return run_workflow(args)


if __name__ == '__main__':
    sys.exit(main())
