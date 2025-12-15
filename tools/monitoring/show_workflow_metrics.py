#!/usr/bin/env python3
"""
Show workflow step metrics for a completed or in-progress workflow run
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import timedelta
from core.database import get_connection, return_connection
from psycopg2.extras import RealDictCursor


def format_duration(seconds):
    """Format seconds as human-readable duration"""
    if seconds is None:
        return "N/A"
    return str(timedelta(seconds=int(seconds)))


def show_workflow_metrics(workflow_run_id=None, workflow_id=None, limit=1):
    """Show metrics for workflow run(s)"""
    
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # If no workflow_run_id, get recent runs for the workflow
        if workflow_run_id is None:
            if workflow_id is None:
                print("❌ Either workflow_run_id or workflow_id must be provided")
                return
            
            cursor.execute("""
                SELECT workflow_run_id, started_at, status
                FROM workflow_runs
                WHERE workflow_id = %s
                ORDER BY started_at DESC
                LIMIT %s
            """, (workflow_id, limit))
            
            runs = cursor.fetchall()
            if not runs:
                print(f"❌ No workflow runs found for workflow {workflow_id}")
                return
            
            print(f"\n📋 Recent Workflow Runs (workflow {workflow_id}):\n")
            for run in runs:
                print(f"  {run['workflow_run_id']}: {run['started_at']} - {run['status']}")
            
            workflow_run_id = runs[0]['workflow_run_id']
            print(f"\n📊 Showing metrics for most recent run: {workflow_run_id}\n")
        
        # Get step metrics
        cursor.execute("""
            SELECT 
                conversation_name,
                execution_order,
                duration_seconds,
                postings_processed,
                postings_succeeded,
                postings_failed,
                avg_time_per_posting,
                min_time_per_posting,
                max_time_per_posting,
                total_llm_calls,
                total_tokens_input,
                total_tokens_output,
                total_cost_usd,
                avg_latency_ms,
                status,
                started_at,
                completed_at
            FROM workflow_step_metrics
            WHERE workflow_run_id = %s
            ORDER BY execution_order, started_at
        """, (workflow_run_id,))
        
        metrics = cursor.fetchall()
        
        if not metrics:
            print(f"ℹ️  No step metrics found for workflow_run {workflow_run_id}")
            print("   (Metrics tracking may not have been enabled for this run)")
            return
        
        print(f"╔═══════════════════════════════════════════════════════════════════════════════╗")
        print(f"║  Workflow Run {workflow_run_id} - Step Performance Metrics")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════╝\n")
        
        total_duration = 0
        total_postings = 0
        total_cost = 0
        
        for idx, step in enumerate(metrics, 1):
            status_icon = "✅" if step['status'] == 'completed' else "⏳"
            
            print(f"{status_icon} Step {idx}: {step['conversation_name']}")
            print(f"   ⏱️  Duration: {format_duration(step['duration_seconds'])}")
            print(f"   📦 Postings: {step['postings_processed']} processed "
                  f"({step['postings_succeeded']} succeeded, {step['postings_failed']} failed)")
            
            if step['avg_time_per_posting']:
                print(f"   ⚡ Avg Time/Posting: {step['avg_time_per_posting']:.2f}s "
                      f"(min: {step['min_time_per_posting']:.2f}s, max: {step['max_time_per_posting']:.2f}s)")
            
            if step['total_llm_calls']:
                print(f"   🤖 LLM Calls: {step['total_llm_calls']} "
                      f"({step['total_tokens_input']:,} in, {step['total_tokens_output']:,} out)")
                print(f"   💰 Cost: ${step['total_cost_usd']:.4f} "
                      f"(avg latency: {step['avg_latency_ms']}ms)")
            
            print()
            
            # Accumulate totals
            if step['duration_seconds']:
                total_duration += step['duration_seconds']
            total_postings += step['postings_processed'] or 0
            total_cost += step['total_cost_usd'] or 0
        
        # Summary
        print("─" * 80)
        print(f"📈 Summary:")
        print(f"   Total Duration: {format_duration(total_duration)}")
        print(f"   Total Postings: {total_postings}")
        print(f"   Total Cost: ${total_cost:.4f}")
        if total_postings > 0:
            print(f"   Avg Cost/Posting: ${total_cost/total_postings:.4f}")
        print()
        
    finally:
        return_connection(conn)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Show workflow step metrics')
    parser.add_argument('--workflow-run-id', type=int, help='Specific workflow run ID')
    parser.add_argument('--workflow-id', type=int, help='Workflow ID (shows most recent run)')
    parser.add_argument('--limit', type=int, default=1, help='Number of recent runs to list')
    
    args = parser.parse_args()
    
    show_workflow_metrics(
        workflow_run_id=args.workflow_run_id,
        workflow_id=args.workflow_id,
        limit=args.limit
    )
