#!/usr/bin/env python3
"""
Log workflow progress to CSV every 5 minutes
"""

import sys
import csv
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection, return_connection
from psycopg2.extras import RealDictCursor


def get_workflow_stats(workflow_id):
    """Get current workflow statistics"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get overall counts
    cursor.execute('''
        SELECT 
            COUNT(*) as total_postings,
            COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL AND LENGTH(extracted_summary) > 100) as has_summary,
            COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as has_skills,
            COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as has_ihl
        FROM postings
        WHERE enabled = TRUE AND job_description IS NOT NULL
    ''')
    totals = cursor.fetchone()
    
    # Get pipeline distribution
    cursor.execute('''
        WITH latest_checkpoints AS (
            SELECT DISTINCT ON (posting_id)
                posting_id,
                conversation_id,
                created_at
            FROM posting_state_checkpoints
            WHERE workflow_run_id IN (
                SELECT workflow_run_id 
                FROM workflow_runs 
                WHERE workflow_id = %s 
                  AND started_at > NOW() - INTERVAL '3 hours'
            )
            ORDER BY posting_id, created_at DESC
        )
        SELECT 
            wc.execution_order,
            COUNT(*) as posting_count
        FROM latest_checkpoints lc
        JOIN conversations c ON lc.conversation_id = c.conversation_id
        JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id AND wc.workflow_id = %s
        WHERE lc.created_at > NOW() - INTERVAL '3 hours'
        GROUP BY wc.execution_order
        ORDER BY wc.execution_order
    ''', (workflow_id, workflow_id))
    
    pipeline = {row['execution_order']: row['posting_count'] for row in cursor.fetchall()}
    
    # Get recent activity (last 5 minutes)
    cursor.execute('''
        SELECT COUNT(*) as checkpoint_count
        FROM posting_state_checkpoints
        WHERE created_at > NOW() - INTERVAL '5 minutes'
    ''')
    activity = cursor.fetchone()
    
    return_connection(conn)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'total_postings': totals['total_postings'],
        'summaries_saved': totals['has_summary'],
        'skills_extracted': totals['has_skills'],
        'ihl_scored': totals['has_ihl'],
        'step_2_count': pipeline.get(2, 0),
        'step_3_count': pipeline.get(3, 0),
        'step_4_count': pipeline.get(4, 0),
        'step_11_count': pipeline.get(11, 0),
        'step_16_count': pipeline.get(16, 0),
        'checkpoints_last_5min': activity['checkpoint_count']
    }


def log_to_csv(stats, csv_file):
    """Append stats to CSV file"""
    file_exists = Path(csv_file).exists()
    
    with open(csv_file, 'a', newline='') as f:
        fieldnames = [
            'timestamp', 'total_postings', 'summaries_saved', 'skills_extracted', 'ihl_scored',
            'step_2_count', 'step_3_count', 'step_4_count', 'step_11_count', 'step_16_count',
            'checkpoints_last_5min'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(stats)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Log workflow progress to CSV')
    parser.add_argument('--workflow', type=int, default=3001, help='Workflow ID')
    parser.add_argument('--output', type=str, default='logs/workflow_progress.csv', help='Output CSV file')
    parser.add_argument('--interval', type=int, default=300, help='Log interval in seconds (default 300 = 5 minutes)')
    parser.add_argument('--once', action='store_true', help='Log once and exit')
    
    args = parser.parse_args()
    
    # Ensure logs directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    if args.once:
        stats = get_workflow_stats(args.workflow)
        log_to_csv(stats, args.output)
        print(f"Logged stats to {args.output}")
        print(f"  Summaries: {stats['summaries_saved']}/{stats['total_postings']}")
        print(f"  Step 3 queue: {stats['step_3_count']}")
        print(f"  Activity (5min): {stats['checkpoints_last_5min']} checkpoints")
    else:
        print(f"Logging workflow {args.workflow} progress to {args.output}")
        print(f"Interval: {args.interval} seconds ({args.interval//60} minutes)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                stats = get_workflow_stats(args.workflow)
                log_to_csv(stats, args.output)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] Summaries: {stats['summaries_saved']:4}/{stats['total_postings']} | "
                      f"Step 3: {stats['step_3_count']:4} | "
                      f"Activity: {stats['checkpoints_last_5min']:4} checkpoints/5min")
                
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\nLogging stopped.")


if __name__ == '__main__':
    main()
