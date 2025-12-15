#!/usr/bin/env python3
"""
Posting Validator Monitor - Watch validation progress in real-time.

Usage:
    python tools/monitoring/_show_validator.py [--once]
"""

import os
import sys
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()


def get_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'base_yoga_secure_2025'),
        cursor_factory=RealDictCursor
    )


def show_status():
    conn = get_conn()
    cursor = conn.cursor()
    
    # Get total active postings
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM postings 
        WHERE source = 'deutsche_bank' AND invalidated = false
    """)
    total = cursor.fetchone()['total']
    
    # Get latest validator interaction (parent only - exclude child interactions)
    cursor.execute("""
        SELECT i.interaction_id, i.workflow_run_id, i.status,
               i.output->'data'->>'total_checked' as checked,
               i.output->'data'->>'still_live' as live,
               i.output->'data'->>'removed_count' as removed,
               i.output->'data'->>'errors' as errors,
               i.output->'data'->>'dry_run' as dry_run,
               i.output->'data'->>'invalidated' as invalidated,
               i.created_at,
               i.completed_at,
               EXTRACT(EPOCH FROM (COALESCE(i.completed_at, NOW()) - i.created_at)) as duration_sec
        FROM interactions i
        WHERE i.conversation_id = 9247  -- validate_postings
          AND i.parent_interaction_id IS NULL  -- Only parent/batch interactions
        ORDER BY i.interaction_id DESC
        LIMIT 1
    """)
    latest = cursor.fetchone()
    
    # Check if process is running
    cursor.execute("""
        SELECT COUNT(*) as running
        FROM interactions 
        WHERE conversation_id = 9247 AND status = 'running'
    """)
    is_running = cursor.fetchone()['running'] > 0
    
    # Get invalidation history (last 7 days)
    cursor.execute("""
        SELECT DATE(invalidated_at) as date, COUNT(*) as cnt
        FROM postings
        WHERE invalidated = true 
          AND invalidated_at > NOW() - INTERVAL '7 days'
        GROUP BY DATE(invalidated_at)
        ORDER BY date DESC
    """)
    history = cursor.fetchall()
    
    # Display
    print("=" * 60)
    print("POSTING VALIDATOR MONITOR")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print(f"📊 POSTINGS:")
    print(f"   Active postings: {total:,}")
    print()
    
    if latest:
        status_icon = "🔄" if latest['status'] == 'running' else ("✅" if latest['status'] == 'completed' else "❌")
        print(f"📋 LATEST RUN: {status_icon} {latest['status'].upper()}")
        print(f"   Interaction: {latest['interaction_id']} (workflow_run {latest['workflow_run_id']})")
        print(f"   Started: {latest['created_at'].strftime('%Y-%m-%d %H:%M:%S') if latest['created_at'] else 'N/A'}")
        
        if latest['status'] == 'completed':
            print(f"   Completed: {latest['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if latest['completed_at'] else 'N/A'}")
            duration = latest['duration_sec'] or 0
            print(f"   Duration: {duration/60:.1f} min")
            print()
            print(f"   Results:")
            print(f"     Checked:     {latest['checked'] or 0}")
            print(f"     Still live:  {latest['live'] or 0}")
            print(f"     Removed:     {latest['removed'] or 0}")
            print(f"     Errors:      {latest['errors'] or 0}")
            print(f"     Invalidated: {latest['invalidated'] or 0}")
            if latest['dry_run'] == 'true':
                print(f"     ⚠️  DRY RUN - no changes made")
        elif latest['status'] == 'running':
            duration = float(latest['duration_sec'] or 0)
            
            # Get ACTUAL progress by counting child interactions
            cursor.execute("""
                SELECT COUNT(*) as checked
                FROM interactions
                WHERE parent_interaction_id = %s
            """, (latest['interaction_id'],))
            actual_checked = cursor.fetchone()['checked']
            
            pct = min(100, 100 * actual_checked / total) if total > 0 else 0
            # Estimate remaining based on actual rate
            if actual_checked > 0:
                rate = duration / actual_checked  # seconds per posting
                eta_sec = max(0, (total - actual_checked) * rate)
            else:
                eta_sec = total * 1.1  # Initial estimate
            
            bar_width = 40
            filled = int(bar_width * pct / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            
            print(f"   Duration: {duration/60:.1f} min")
            print()
            print(f"   Progress (actual from child interactions):")
            print(f"     [{bar}] {pct:.0f}%")
            print(f"     {actual_checked:,} / {total:,} postings")
            print(f"     ETA: ~{eta_sec/60:.1f} min remaining")
    else:
        print("   No validation runs found")
    
    if history:
        print()
        print(f"📅 INVALIDATION HISTORY (7 days):")
        for row in history:
            print(f"   {row['date']}: {row['cnt']} postings invalidated")
    
    conn.close()
    
    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Posting Validator Monitor')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=10, help='Refresh interval (default: 10s)')
    args = parser.parse_args()
    
    if args.once:
        show_status()
    else:
        while True:
            print("\033[2J\033[H", end="")  # Clear screen
            show_status()
            print(f"⏱️  Refreshing every {args.interval}s... (Ctrl+C to stop)")
            time.sleep(args.interval)


if __name__ == '__main__':
    main()
