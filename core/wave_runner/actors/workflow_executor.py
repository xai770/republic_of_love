#!/usr/bin/env python3
"""
Workflow Executor Actor

Executes workflows with validation and logging.
This makes workflow execution itself a logged interaction.

Input:
    {
        "workflow_id": 3001,
        "mode": "global_batch",  # or "single_posting", "single_run"
        "posting_id": null,      # for single_posting mode
        "workflow_run_id": null, # for single_run mode
        "max_iterations": null,  # null = no limit (recommended)
        "requested_by": "xai"
    }

Output:
    {
        "status": "completed" | "failed" | "rejected",
        "interactions_completed": 123,
        "interactions_failed": 0,
        "duration_seconds": 456,
        "rejection_reason": null,
        "error": null
    }

Safety checks:
    - No duplicate active runs (same workflow_id in 'running' state)
    - Rate limit (max 1 batch per minute per workflow)
"""

import json
import sys
from datetime import datetime

sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.script_actor_template import ScriptActorBase


class WorkflowExecutorActor(ScriptActorBase):
    """Execute workflows with validation and full audit trail."""
    
    def process(self):
        """Execute a workflow after validation."""
        workflow_id = self.input_data.get('workflow_id')
        mode = self.input_data.get('mode', 'global_batch')
        posting_id = self.input_data.get('posting_id')
        target_workflow_run_id = self.input_data.get('target_workflow_run_id')
        max_iterations = self.input_data.get('max_iterations')
        requested_by = self.input_data.get('requested_by', 'unknown')
        
        # Validate required fields
        if not workflow_id:
            return {
                "status": "rejected",
                "rejection_reason": "Missing workflow_id",
                "error": "workflow_id is required"
            }
        
        # Safety check 1: Duplicate active runs
        is_duplicate, active_count = self._check_duplicate_runs(workflow_id)
        if is_duplicate and mode == 'global_batch':
            return {
                "status": "rejected",
                "rejection_reason": "Workflow already running",
                "error": f"Workflow {workflow_id} has {active_count} active run(s)"
            }
        
        # Safety check 2: Rate limit (1 batch per minute)
        if mode == 'global_batch':
            is_rate_limited, last_run_ago = self._check_rate_limit(workflow_id)
            if is_rate_limited:
                return {
                    "status": "rejected",
                    "rejection_reason": "Rate limit exceeded",
                    "error": f"Last batch was {last_run_ago}s ago. Wait 60s."
                }
        
        # All checks passed - execute
        start_time = datetime.now()
        
        try:
            from core.wave_runner.runner import WaveRunner
            from core.database import get_connection, return_connection
            
            conn = get_connection()
            
            # Build runner based on mode
            if mode == 'global_batch':
                runner = WaveRunner(conn, global_batch=True)
            elif mode == 'single_posting':
                if not posting_id:
                    return_connection(conn)
                    return {"status": "rejected", "rejection_reason": "Missing posting_id"}
                runner = WaveRunner(conn, posting_id=posting_id)
            elif mode == 'single_run':
                if not target_workflow_run_id:
                    return_connection(conn)
                    return {"status": "rejected", "rejection_reason": "Missing target_workflow_run_id"}
                runner = WaveRunner(conn, workflow_run_id=target_workflow_run_id)
            else:
                return_connection(conn)
                return {"status": "rejected", "rejection_reason": f"Unknown mode: {mode}"}
            
            # Run
            print(f"   Starting runner (max_iterations={max_iterations})...")
            if max_iterations:
                stats = runner.run(max_iterations=max_iterations)
            else:
                stats = runner.run()
            print(f"   Runner complete: {stats}")
            
            return_connection(conn)
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "completed",
                "workflow_id": workflow_id,
                "mode": mode,
                "requested_by": requested_by,
                "interactions_completed": stats.get('interactions_completed', 0),
                "interactions_failed": stats.get('interactions_failed', 0),
                "duration_seconds": int(duration),
                "batches_processed": stats.get('batches_processed', 0)
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return {
                "status": "failed",
                "workflow_id": workflow_id,
                "mode": mode,
                "duration_seconds": int(duration),
                "error": str(e)
            }
    
    def _check_duplicate_runs(self, workflow_id: int) -> tuple:
        """Check if workflow has active runs."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM workflow_runs 
            WHERE workflow_id = %s AND status = 'running'
        """, (workflow_id,))
        row = cursor.fetchone()
        count = row['cnt'] if row else 0
        cursor.close()
        return count > 0, count
    
    def _check_rate_limit(self, workflow_id: int, min_interval: int = 60) -> tuple:
        """Check if workflow was run too recently."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT EXTRACT(EPOCH FROM (NOW() - MAX(i.created_at)))::int as seconds_ago
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            WHERE a.script_file_path LIKE '%%workflow_executor%%'
              AND i.input::text LIKE %s
              AND i.status = 'completed'
              AND i.created_at > NOW() - INTERVAL '5 minutes'
        """, (f'%"workflow_id": {workflow_id}%',))
        row = cursor.fetchone()
        cursor.close()
        
        if row and row['seconds_ago'] is not None:
            return row['seconds_ago'] < min_interval, row['seconds_ago']
        return False, 999


# Standard execution pattern
if __name__ == '__main__':
    actor = WorkflowExecutorActor()
    actor.run()
