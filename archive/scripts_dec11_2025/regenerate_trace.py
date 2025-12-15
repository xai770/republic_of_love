#!/usr/bin/env python3
"""
Regenerate trace report for completed workflow run
Uses WaveRunner's built-in trace generation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from dotenv import load_dotenv
from core.wave_runner.runner import WaveRunner

load_dotenv()

def regenerate_trace(workflow_run_id: int):
    """Regenerate trace for a completed run"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
    trace_file = f"reports/trace_run_{workflow_run_id}.md"
    
    # The runner's trace generation requires trace_data which is collected during run
    # We need to manually generate from database
    from datetime import datetime
    from core.wave_runner.trace_reporter import generate_trace_report
    
    cursor = conn.cursor()
    
    # Get workflow run details
    cursor.execute("""
        SELECT wr.workflow_id, wr.posting_id, wr.status, wr.started_at, wr.completed_at,
               w.workflow_name
        FROM workflow_runs wr
        JOIN workflows w ON wr.workflow_id = w.workflow_id
        WHERE wr.workflow_run_id = %s
    """, (workflow_run_id,))
    
    run_info = cursor.fetchone()
    if not run_info:
        print(f"❌ Workflow run {workflow_run_id} not found")
        conn.close()
        return
    
    workflow_id, posting_id, status, started_at, completed_at, workflow_name = run_info
    
    # Get all interactions
    cursor.execute("""
        SELECT i.interaction_id, i.conversation_id, c.conversation_name,
               i.status, i.created_at, i.completed_at,
               EXTRACT(EPOCH FROM (i.completed_at - i.created_at)) as duration,
               i.input, i.output, a.actor_name, a.actor_type
        FROM interactions i
        JOIN conversations c ON i.conversation_id = c.conversation_id
        JOIN actors a ON c.actor_id = a.actor_id
        WHERE i.workflow_run_id = %s
          AND i.status = 'completed'
        ORDER BY i.interaction_id
    """, (workflow_run_id,))
    
    interactions = cursor.fetchall()
    
    # Build trace_data in the format WaveRunner uses
    trace_data = []
    for row in interactions:
        (interaction_id, conversation_id, conversation_name, status, created_at, 
         completed_at, duration, input_data, output_data, actor_name, actor_type) = row
        
        trace_entry = {
            'interaction_id': interaction_id,
            'conversation_id': conversation_id,
            'conversation_name': conversation_name,
            'status': status,
            'created_at': created_at,
            'completed_at': completed_at,
            'duration': duration or 0,
            'actor_name': actor_name,
            'actor_type': actor_type,
            'input': input_data,
            'output': output_data,
            'parent_interaction_ids': [],  # Not tracked in DB currently
            'branch_taken': None,
            'context': {
                'workflow_id': workflow_id,
                'workflow_name': workflow_name,
                'posting_id': posting_id
            }
        }
        trace_data.append(trace_entry)
    
    # Calculate stats
    total_duration = completed_at - started_at if completed_at else None
    stats = {
        'total_interactions': len(interactions),
        'interactions_completed': len(interactions),
        'interactions_failed': 0,
        'duration_ms': total_duration.total_seconds() * 1000 if total_duration else 0,
        'duration_seconds': total_duration.total_seconds() if total_duration else 0
    }
    
    # Generate trace
    generate_trace_report(
        trace_data=trace_data,
        stats=stats,
        start_time=started_at,
        trace_file=trace_file,
        workflow_run_id=workflow_run_id,
        posting_id=posting_id
    )
    
    print(f"✅ Trace report generated: {trace_file}")
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/regenerate_trace.py <workflow_run_id>")
        sys.exit(1)
    
    workflow_run_id = int(sys.argv[1])
    regenerate_trace(workflow_run_id)
