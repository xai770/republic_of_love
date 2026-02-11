#!/usr/bin/env python3
"""
Complete Run Actor
==================
Marks a Pipeline V2 run as complete and removes the posting from the queue.

This is the terminal step of any workflow using the new queue/runs architecture.
It should be the LAST step in the workflow chain.

Responsibilities:
1. Update runs.completed_at for the current run_id
2. Delete the queue entry for this run_id
3. Log success

Input:
{
    "posting_id": 12345,
    "workflow_run_id": 99,
    "interaction_id": 888,
    "run_id": 542  // May be null for legacy runs
}

Output:
{
    "status": "success",
    "run_id": 542,
    "posting_id": 12345,
    "completed_at": "2025-12-11T10:30:00Z"
}
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.script_actor_template import ScriptActorBase
from datetime import datetime, timezone


class CompleteRunActor(ScriptActorBase):
    """Mark run as complete and clean up queue"""
    
    def process(self):
        """
        Complete the run and remove from queue.
        
        If run_id is None (legacy interaction), just returns success without
        touching runs/queue tables.
        """
        posting_id = self.input_data.get('posting_id')
        interaction_id = self.input_data.get('interaction_id')
        run_id = self.input_data.get('run_id')
        
        if not posting_id:
            return {
                "status": "error",
                "error": "Missing posting_id"
            }
        
        # Legacy path: no run_id means this is a pre-V2 workflow run
        if not run_id:
            return {
                "status": "success",
                "message": "No run_id - legacy workflow, skipping run completion",
                "posting_id": posting_id
            }
        
        cursor = self.db_conn.cursor()
        completed_at = datetime.now(timezone.utc)
        
        try:
            # 1. Mark run as completed
            cursor.execute("""
                UPDATE runs
                SET completed_at = %s
                WHERE run_id = %s
                RETURNING run_id
            """, (completed_at, run_id))
            
            updated_run = cursor.fetchone()
            if not updated_run:
                # run_id doesn't exist - might be orphaned, just warn
                self.db_conn.rollback()
                return {
                    "status": "warning",
                    "message": f"Run {run_id} not found in runs table",
                    "posting_id": posting_id,
                    "run_id": run_id
                }
            
            # 2. Delete from queue (ephemeral - successful jobs get deleted)
            cursor.execute("""
                DELETE FROM queue
                WHERE run_id = %s
                RETURNING queue_id
            """, (run_id,))
            
            deleted_queue = cursor.fetchone()
            queue_id = deleted_queue['queue_id'] if deleted_queue else None
            
            self.db_conn.commit()
            
            return {
                "status": "success",
                "run_id": run_id,
                "posting_id": posting_id,
                "completed_at": completed_at.isoformat(),
                "queue_deleted": queue_id is not None,
                "queue_id": queue_id
            }
            
        except Exception as e:
            self.db_conn.rollback()
            return {
                "status": "error",
                "error": str(e),
                "run_id": run_id,
                "posting_id": posting_id
            }


if __name__ == '__main__':
    actor = CompleteRunActor()
    actor.run()
