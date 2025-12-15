#!/usr/bin/env python3
"""
Daily Run Summary - What Happened Today?

A single-glance dashboard showing:
- Which workflows ran
- How many interactions
- Success/failure rates
- Key metrics by workflow

Usage:
    python tools/daily_summary.py              # Today
    python tools/daily_summary.py --yesterday  # Yesterday
    python tools/daily_summary.py --days 7     # Last 7 days

Author: Arden
Date: December 9, 2025
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

# Add project root to path (go up two directories from tools/monitoring/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database import get_connection


def get_workflow_summary(conn, start_date, end_date):
    """Get summary of workflow runs."""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            w.workflow_name,
            w.workflow_id,
            COUNT(DISTINCT wr.workflow_run_id) as runs,
            COUNT(DISTINCT CASE WHEN wr.status = 'completed' THEN wr.workflow_run_id END) as completed,
            COUNT(DISTINCT CASE WHEN wr.status = 'failed' THEN wr.workflow_run_id END) as failed,
            COUNT(i.interaction_id) as interactions,
            MIN(i.created_at) as first_run,
            MAX(i.created_at) as last_run
        FROM workflows w
        LEFT JOIN workflow_runs wr ON w.workflow_id = wr.workflow_id
        LEFT JOIN interactions i ON wr.workflow_run_id = i.workflow_run_id
        WHERE i.created_at BETWEEN %s AND %s
        GROUP BY w.workflow_name, w.workflow_id
        ORDER BY interactions DESC
    """, (start_date, end_date))
    
    return cur.fetchall()


def get_interaction_summary(conn, start_date, end_date):
    """Get interaction counts by status."""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT status, COUNT(*) as cnt
        FROM interactions
        WHERE created_at BETWEEN %s AND %s
        GROUP BY status
        ORDER BY cnt DESC
    """, (start_date, end_date))
    
    return {row['status']: row['cnt'] for row in cur.fetchall()}


def get_cron_jobs(conn, start_date, end_date):
    """Check if scheduled jobs ran."""
    cur = conn.cursor()
    
    # Check entity_sync log
    jobs = {}
    
    # Check WF3005 runs
    cur.execute("""
        SELECT COUNT(DISTINCT workflow_run_id) as runs
        FROM workflow_runs
        WHERE workflow_id = 3005
        AND started_at BETWEEN %s AND %s
    """, (start_date, end_date))
    row = cur.fetchone()
    jobs['entity_registry_sync'] = row['runs'] if row else 0
    
    # Check WF3001 runs
    cur.execute("""
        SELECT COUNT(DISTINCT workflow_run_id) as runs
        FROM workflow_runs
        WHERE workflow_id = 3001
        AND started_at BETWEEN %s AND %s
    """, (start_date, end_date))
    row = cur.fetchone()
    jobs['posting_pipeline'] = row['runs'] if row else 0
    
    return jobs


def get_key_metrics(conn, start_date, end_date):
    """Get key business metrics."""
    cur = conn.cursor()
    metrics = {}
    
    # posting_skills coverage
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(entity_id) as with_entity
        FROM posting_skills
    """)
    row = cur.fetchone()
    if row:
        metrics['skill_coverage'] = f"{row['with_entity']}/{row['total']} ({row['with_entity']*100/row['total']:.1f}%)" if row['total'] > 0 else "N/A"
    
    # Pending skills
    cur.execute("SELECT COUNT(*) as cnt FROM entities_pending WHERE status = 'pending'")
    metrics['pending_skills'] = cur.fetchone()['cnt']
    
    # New entities today
    cur.execute("""
        SELECT COUNT(*) as cnt FROM entities 
        WHERE created_at BETWEEN %s AND %s
    """, (start_date, end_date))
    metrics['new_entities'] = cur.fetchone()['cnt']
    
    return metrics


def print_summary(start_date, end_date, workflows, interactions, cron_jobs, metrics):
    """Print the summary dashboard."""
    total_interactions = sum(interactions.values())
    completed = interactions.get('completed', 0)
    failed = interactions.get('failed', 0)
    
    print("=" * 70)
    print(f"  📊 DAILY RUN SUMMARY")
    print(f"  {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("=" * 70)
    print()
    
    # Health indicator
    if failed == 0 and total_interactions > 0:
        health = "🟢 HEALTHY"
    elif failed > 0 and failed < total_interactions * 0.1:
        health = "🟡 MINOR ISSUES"
    elif failed > 0:
        health = "🔴 NEEDS ATTENTION"
    else:
        health = "⚪ NO ACTIVITY"
    
    print(f"  Status: {health}")
    print()
    
    # Interactions summary
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  INTERACTIONS                                               │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Total:      {total_interactions:>6}                                       │")
    print(f"  │  Completed:  {completed:>6}  ✅                                  │")
    print(f"  │  Failed:     {failed:>6}  {'❌' if failed > 0 else '✅'}                                  │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()
    
    # Workflows
    print("  WORKFLOWS:")
    print("  " + "-" * 66)
    print(f"  {'Workflow':<40} {'Runs':>6} {'Done':>6} {'Fail':>6}")
    print("  " + "-" * 66)
    for wf in workflows:
        name = wf['workflow_name'][:38] if len(wf['workflow_name']) > 38 else wf['workflow_name']
        status = "✅" if wf['failed'] == 0 else "❌"
        print(f"  {name:<40} {wf['runs']:>6} {wf['completed']:>6} {wf['failed']:>5}{status}")
    print()
    
    # Scheduled Jobs
    print("  SCHEDULED JOBS:")
    print("  " + "-" * 66)
    for job, runs in cron_jobs.items():
        status = "✅ Ran" if runs > 0 else "⚠️ Did not run"
        print(f"  {job:<40} {status}")
    print()
    
    # Key Metrics
    print("  KEY METRICS:")
    print("  " + "-" * 66)
    for metric, value in metrics.items():
        print(f"  {metric:<40} {value}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Daily Run Summary')
    parser.add_argument('--yesterday', action='store_true', help='Show yesterday')
    parser.add_argument('--days', type=int, default=1, help='Number of days to look back')
    
    args = parser.parse_args()
    
    # Calculate date range
    now = datetime.now()
    if args.yesterday:
        end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)
    else:
        end_date = now
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=args.days - 1)
    
    conn = get_connection()
    
    try:
        workflows = get_workflow_summary(conn, start_date, end_date)
        interactions = get_interaction_summary(conn, start_date, end_date)
        cron_jobs = get_cron_jobs(conn, start_date, end_date)
        metrics = get_key_metrics(conn, start_date, end_date)
        
        print_summary(start_date, end_date, workflows, interactions, cron_jobs, metrics)
        
    finally:
        conn.close()


if __name__ == '__main__':
    main()
