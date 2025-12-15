#!/usr/bin/env python3
"""
Live Activity Chart - Shows interaction state changes over time.

If bars are appearing = workflow is alive
If nothing for several minutes = might be stuck

Usage:
    python3 tools/activity_chart.py           # Live updating (default 30s)
    python3 tools/activity_chart.py --once    # Single snapshot
    python3 tools/activity_chart.py -i 10     # Update every 10 seconds
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()


def get_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )


def get_activity_data(conn, minutes=30):
    """Get interaction state changes grouped by minute."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get creations and completions per minute for the last N minutes
    cursor.execute("""
        WITH time_buckets AS (
            SELECT generate_series(
                date_trunc('minute', NOW() - INTERVAL '%s minutes'),
                date_trunc('minute', NOW()),
                INTERVAL '1 minute'
            ) AS minute
        ),
        created AS (
            SELECT 
                date_trunc('minute', created_at) AS minute,
                COUNT(*) AS created
            FROM interactions
            WHERE created_at > NOW() - INTERVAL '%s minutes'
            GROUP BY 1
        ),
        completed AS (
            SELECT 
                date_trunc('minute', updated_at) AS minute,
                COUNT(*) AS completed
            FROM interactions
            WHERE status = 'completed'
              AND updated_at > NOW() - INTERVAL '%s minutes'
            GROUP BY 1
        ),
        failed AS (
            SELECT 
                date_trunc('minute', updated_at) AS minute,
                COUNT(*) AS failed
            FROM interactions
            WHERE status = 'failed'
              AND updated_at > NOW() - INTERVAL '%s minutes'
            GROUP BY 1
        )
        SELECT 
            tb.minute,
            COALESCE(cr.created, 0) AS created,
            COALESCE(co.completed, 0) AS completed,
            COALESCE(f.failed, 0) AS failed
        FROM time_buckets tb
        LEFT JOIN created cr ON tb.minute = cr.minute
        LEFT JOIN completed co ON tb.minute = co.minute
        LEFT JOIN failed f ON tb.minute = f.minute
        ORDER BY tb.minute
    """, (minutes, minutes, minutes, minutes))
    
    return cursor.fetchall()


def get_current_status(conn):
    """Get current pipeline status."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'pending') AS pending,
            COUNT(*) FILTER (WHERE status = 'running') AS running,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed
        FROM interactions
    """)
    
    return cursor.fetchone()


def render_bar(value, max_val, width=40, char='█'):
    """Render a horizontal bar."""
    if max_val == 0:
        return ''
    bar_len = int((value / max_val) * width)
    return char * bar_len


def render_chart(data, width=50):
    """Render the activity chart."""
    if not data:
        return "No data"
    
    # Find max for scaling
    max_activity = max(
        max(row['created'] + row['completed'] + row['failed'] for row in data),
        1  # Prevent division by zero
    )
    
    lines = []
    
    for row in data:
        minute = row['minute']
        created = row['created']
        completed = row['completed']
        failed = row['failed']
        total = created + completed + failed
        
        # Time label (just HH:MM)
        time_str = minute.strftime('%H:%M')
        
        # Build composite bar: created=cyan, completed=green, failed=red
        bar_width = int((total / max_activity) * width) if max_activity > 0 else 0
        
        if total == 0:
            bar = '·'  # Show dot for zero activity
        else:
            # Proportional coloring
            c_len = int((created / total) * bar_width) if total > 0 else 0
            d_len = int((completed / total) * bar_width) if total > 0 else 0
            f_len = bar_width - c_len - d_len
            
            bar = (
                f"\033[96m{'▪' * c_len}\033[0m"  # Cyan for created
                f"\033[92m{'█' * d_len}\033[0m"  # Green for completed
                f"\033[91m{'▪' * f_len}\033[0m"  # Red for failed (if any)
            )
        
        # Count annotation
        counts = []
        if created > 0:
            counts.append(f"+{created}")
        if completed > 0:
            counts.append(f"✓{completed}")
        if failed > 0:
            counts.append(f"✗{failed}")
        count_str = ' '.join(counts) if counts else ''
        
        lines.append(f"{time_str} │{bar} {count_str}")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Live activity chart')
    parser.add_argument('--once', action='store_true', help='Single snapshot')
    parser.add_argument('-i', '--interval', type=int, default=30, help='Refresh interval (seconds)')
    parser.add_argument('-m', '--minutes', type=int, default=15, help='History to show (minutes)')
    args = parser.parse_args()
    
    while True:
        conn = get_connection()
        
        # Clear screen (unless --once)
        if not args.once:
            print('\033[2J\033[H', end='')
        
        # Header
        now = datetime.now().strftime('%H:%M:%S')
        print(f"📊 ACTIVITY CHART [{now}]")
        print(f"   Last {args.minutes} minutes │ \033[96m▪created\033[0m \033[92m█completed\033[0m \033[91m▪failed\033[0m")
        print("─" * 60)
        
        # Get and render data
        data = get_activity_data(conn, args.minutes)
        print(render_chart(data))
        
        # Summary line
        print("─" * 60)
        status = get_current_status(conn)
        
        # Calculate recent rate
        recent = [r for r in data[-5:] if r['completed'] > 0]  # Last 5 minutes
        rate = sum(r['completed'] for r in data[-5:]) / 5 if data else 0
        
        print(f"⚡ Rate: {rate:.1f}/min │ Pending: {status['pending']} │ Running: {status['running']}")
        
        # Health indicator
        last_3_min = data[-3:] if len(data) >= 3 else data
        total_recent = sum(r['created'] + r['completed'] for r in last_3_min)
        
        if total_recent == 0 and status['pending'] > 0:
            print(f"\n⚠️  NO ACTIVITY in last 3 minutes with {status['pending']} pending!")
        elif status['running'] == 0 and status['pending'] > 0:
            print(f"\n⚠️  Nothing running but {status['pending']} pending - runner may be dead")
        elif status['pending'] == 0:
            print(f"\n✅ All caught up! No pending work.")
        else:
            print(f"\n✅ Healthy - work is flowing")
        
        conn.close()
        
        if args.once:
            break
            
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
