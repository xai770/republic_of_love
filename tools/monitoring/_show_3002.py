#!/usr/bin/env python3
"""
Workflow 3002 Taxonomy Maintenance Dashboard

Shows progress of skill taxonomy maintenance:
- Pending skills in queue
- Classification decisions (ALIAS/NEW/SPLIT/SKIP)
- Skills created/mapped
- Phosphor activity bars

Run: python3 tools/_show_3002.py --once
     python3 tools/_show_3002.py  # Continuous refresh
"""

from dotenv import load_dotenv, find_dotenv
import os
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv(find_dotenv())

# Workflow 3002 conversation steps
WORKFLOW_STEPS = [
    (9201, "Fetch Unmatched Skills", "unmatched_skills_fetcher", "script"),
    (9202, "Classify Unmatched Skill", "qwen2.5:7b", "ai_model"),
    (9203, "Apply Taxonomy Decision", "skill_taxonomy_saver", "script"),
]

# ANSI colors (reuse from _show_3001.py)
PHOSPHOR_COLORS = [
    '\033[38;5;196m', '\033[38;5;202m', '\033[38;5;208m', '\033[38;5;214m',
    '\033[38;5;220m', '\033[38;5;226m', '\033[38;5;190m', '\033[38;5;154m',
    '\033[38;5;118m', '\033[38;5;82m', '\033[38;5;46m', '\033[38;5;42m',
    '\033[38;5;43m', '\033[38;5;49m', '\033[38;5;51m', '\033[38;5;45m',
    '\033[38;5;39m', '\033[38;5;33m', '\033[38;5;63m', '\033[38;5;57m',
    '\033[38;5;93m', '\033[38;5;97m', '\033[38;5;240m', '\033[38;5;236m',
]
RESET_COLOR = '\033[0m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
BOLD = '\033[1m'


def get_conn():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )


def get_pending_stats(conn):
    """Get skills_pending_taxonomy status counts."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            review_status,
            COUNT(*) as cnt,
            SUM(occurrences) as total_occurrences
        FROM skills_pending_taxonomy
        GROUP BY review_status
        ORDER BY COUNT(*) DESC
    """)
    
    stats = {}
    for status, cnt, occurrences in cursor.fetchall():
        stats[status] = {'count': cnt, 'occurrences': occurrences or 0}
    
    return stats


def get_recent_taxonomy_changes(conn, hours=24):
    """Get recently created skills and aliases."""
    cursor = conn.cursor()
    
    # New skills created
    cursor.execute("""
        SELECT skill_name, display_name, created_at
        FROM skill_aliases
        WHERE created_by = 'wf3002_taxonomy_saver'
          AND created_at >= NOW() - INTERVAL '%s hours'
        ORDER BY created_at DESC
        LIMIT 10
    """, (hours,))
    new_skills = cursor.fetchall()
    
    # Count by hour
    cursor.execute("""
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as cnt
        FROM skill_aliases
        WHERE created_by = 'wf3002_taxonomy_saver'
          AND created_at >= NOW() - INTERVAL '%s hours'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour DESC
    """, (hours,))
    hourly_stats = cursor.fetchall()
    
    return {'new_skills': new_skills, 'hourly': hourly_stats}


def get_step_stats(conn):
    """Get interaction stats per workflow step."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            conversation_id,
            status,
            COUNT(*) as cnt
        FROM interactions
        WHERE conversation_id IN %s
          AND workflow_run_id IN (
              SELECT workflow_run_id FROM workflow_runs 
              WHERE workflow_id = 3002 
              AND created_at >= NOW() - INTERVAL '24 hours'
          )
        GROUP BY conversation_id, status
    """, (tuple([step[0] for step in WORKFLOW_STEPS]),))
    
    stats = defaultdict(lambda: defaultdict(int))
    for conv_id, status, cnt in cursor.fetchall():
        stats[conv_id][status] = cnt
    
    return stats


def get_phosphor_completions(conn, bucket_minutes=5, num_buckets=24):
    """Get completions bucketed by time for rainbow fade effect."""
    cursor = conn.cursor()
    now = datetime.now()
    
    phosphor = defaultdict(lambda: [0] * num_buckets)
    
    for bucket_idx in range(num_buckets):
        start_offset = bucket_idx * bucket_minutes
        end_offset = (bucket_idx + 1) * bucket_minutes
        
        start_time = now - timedelta(minutes=end_offset)
        end_time = now - timedelta(minutes=start_offset)
        
        cursor.execute("""
            SELECT 
                conversation_id,
                COUNT(*) as cnt
            FROM interactions
            WHERE conversation_id IN %s
              AND status = 'completed'
              AND updated_at >= %s
              AND updated_at < %s
            GROUP BY conversation_id
        """, (tuple([step[0] for step in WORKFLOW_STEPS]), start_time, end_time))
        
        for conv_id, cnt in cursor.fetchall():
            phosphor[conv_id][bucket_idx] = cnt
    
    return phosphor


def get_workflow_run_stats(conn):
    """Get recent workflow run statistics."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            workflow_run_id,
            status,
            started_at,
            EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - started_at)) as duration_sec,
            (metadata->>'max_skills')::int as max_skills
        FROM workflow_runs
        WHERE workflow_id = 3002
        ORDER BY workflow_run_id DESC
        LIMIT 5
    """)
    
    return cursor.fetchall()


def format_phosphor_bar(phosphor_buckets, width=16):
    """Create a rainbow time-fade bar."""
    total = sum(phosphor_buckets)
    if total == 0:
        return " " * (width + 5)
    
    bar_chars = []
    buckets_per_char = len(phosphor_buckets) / width
    
    for char_idx in range(width):
        start_bucket = int(char_idx * buckets_per_char)
        end_bucket = int((char_idx + 1) * buckets_per_char)
        bucket_sum = sum(phosphor_buckets[start_bucket:end_bucket])
        
        if bucket_sum > 0:
            color = PHOSPHOR_COLORS[min(start_bucket, len(PHOSPHOR_COLORS) - 1)]
            bar_chars.append(f"{color}█{RESET_COLOR}")
        else:
            bar_chars.append(" ")
    
    return f"+{total:3d} {' '.join(bar_chars)}"


def print_dashboard():
    """Print the WF3002 monitoring dashboard."""
    conn = get_conn()
    
    pending_stats = get_pending_stats(conn)
    step_stats = get_step_stats(conn)
    phosphor = get_phosphor_completions(conn)
    taxonomy_changes = get_recent_taxonomy_changes(conn)
    workflow_runs = get_workflow_run_stats(conn)
    
    # Calculate totals
    pending = pending_stats.get('pending', {}).get('count', 0)
    approved = pending_stats.get('approved', {}).get('count', 0)
    rejected = pending_stats.get('rejected', {}).get('count', 0)
    duplicate = pending_stats.get('duplicate', {}).get('count', 0)
    total_skills = pending + approved + rejected + duplicate
    
    # Recent activity
    total_activity = sum(sum(buckets) for buckets in phosphor.values())
    recent_30m = sum(sum(buckets[:6]) for buckets in phosphor.values())
    
    # Rainbow legend
    legend = f"{PHOSPHOR_COLORS[0]}█{RESET_COLOR}now "
    legend += f"{PHOSPHOR_COLORS[6]}█{RESET_COLOR}30m "
    legend += f"{PHOSPHOR_COLORS[12]}█{RESET_COLOR}1h "
    legend += f"{PHOSPHOR_COLORS[23]}█{RESET_COLOR}2h"
    
    # Header
    print("=" * 100)
    print(f"{BOLD}WORKFLOW 3002: Skill Taxonomy Maintenance{RESET_COLOR}")
    print("=" * 100)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}    |    Rainbow: {legend}")
    
    # Queue Status
    print()
    print(f"📊 {BOLD}PENDING SKILLS QUEUE{RESET_COLOR}")
    print("─" * 100)
    
    pct_done = 100 * approved / total_skills if total_skills > 0 else 0
    bar_width = 40
    filled = int(bar_width * pct_done / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    print(f"   Total in Queue:     {total_skills:,}")
    print(f"   ⏳ Pending:          {pending:,} (waiting for review)")
    print(f"   ✅ Approved:         {GREEN}{approved:,}{RESET_COLOR} (added to taxonomy)")
    print(f"   ❌ Rejected:         {RED}{rejected:,}{RESET_COLOR} (not real skills)")
    print(f"   🔄 Duplicate:        {duplicate:,} (merged with existing)")
    print()
    print(f"   Progress: [{bar}] {pct_done:.1f}%")
    
    # Workflow Steps
    print()
    print(f"🔧 {BOLD}WORKFLOW STEPS (last 24h){RESET_COLOR}")
    print("─" * 100)
    print(f"{'#':>2} {'':2} {'Step Name':35s} | {'Actor':25s} | {'Completed':>10} | {'Running':>8} | {'Activity 2h':20s}")
    print("─" * 100)
    
    for i, (conv_id, name, actor, actor_type) in enumerate(WORKFLOW_STEPS):
        icon = "🤖" if actor_type == "ai_model" else "⚙️ "
        completed = step_stats[conv_id].get('completed', 0)
        running = step_stats[conv_id].get('running', 0)
        phos = format_phosphor_bar(phosphor.get(conv_id, [0]*24))
        
        print(f"{i+1:2d} {icon} {name:35s} | {actor:25s} | {completed:10,} | {running:8} | {phos}")
    
    # Recent Workflow Runs
    print()
    print(f"📜 {BOLD}RECENT WORKFLOW RUNS{RESET_COLOR}")
    print("─" * 100)
    print(f"{'Run ID':>10} | {'Status':>12} | {'Started':>20} | {'Duration':>10} | {'Max Skills':>10}")
    print("─" * 100)
    
    for run in workflow_runs:
        run_id, status, created, duration, max_skills = run
        duration_str = f"{duration:.0f}s" if duration else "—"
        max_skills_str = str(max_skills) if max_skills else "—"
        status_color = GREEN if status == 'completed' else (YELLOW if status == 'running' else '')
        print(f"{run_id:10} | {status_color}{status:>12}{RESET_COLOR} | {created.strftime('%Y-%m-%d %H:%M:%S'):>20} | {duration_str:>10} | {max_skills_str:>10}")
    
    # Recently Created Skills
    print()
    print(f"🆕 {BOLD}RECENTLY CREATED SKILLS{RESET_COLOR} (last 24h)")
    print("─" * 100)
    
    new_skills = taxonomy_changes['new_skills']
    if new_skills:
        for skill_name, display_name, created_at in new_skills[:10]:
            time_ago = datetime.now() - created_at.replace(tzinfo=None)
            if time_ago.seconds < 3600:
                ago_str = f"{time_ago.seconds // 60}m ago"
            else:
                ago_str = f"{time_ago.seconds // 3600}h ago"
            print(f"   {GREEN}+{RESET_COLOR} {display_name:50s} ({ago_str})")
    else:
        print("   (none in last 24h)")
    
    # Hourly breakdown
    hourly = taxonomy_changes['hourly']
    if hourly:
        print()
        total_new = sum(cnt for _, cnt in hourly)
        print(f"   Total new skills created: {GREEN}{total_new}{RESET_COLOR}")
    
    # Health check
    print()
    print("=" * 100)
    
    if pending == 0:
        health = f"✅ {GREEN}All skills processed!{RESET_COLOR}"
    elif recent_30m > 0:
        rate = recent_30m / 30
        eta_min = pending / rate if rate > 0 else 0
        if eta_min < 60:
            eta_str = f"{eta_min:.0f} min"
        else:
            eta_str = f"{eta_min/60:.1f} hours"
        health = f"✅ Healthy | Rate: {rate:.1f}/min | ETA: {eta_str}"
    else:
        health = f"⚠️  {YELLOW}No activity in last 30 min!{RESET_COLOR} | {pending:,} skills waiting"
    
    print(f"HEALTH: {health}    |    Activity (2h): {total_activity}    |    Activity (30m): {recent_30m}")
    print("=" * 100)
    
    conn.close()


if __name__ == '__main__':
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Workflow 3002 Taxonomy Dashboard')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=30, help='Refresh interval in seconds (default: 30)')
    args = parser.parse_args()
    
    if args.once:
        print_dashboard()
    else:
        while True:
            print("\033[2J\033[H", end="")  # Clear screen
            print_dashboard()
            print(f"\n⏱️  Refreshing every {args.interval}s... (Ctrl+C to stop)")
            time.sleep(args.interval)
