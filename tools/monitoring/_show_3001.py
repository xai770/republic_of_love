#!/usr/bin/env python3
"""
Workflow 3001 Flowchart Progress Dashboard

Shows the complete workflow flowchart with actual progress numbers:
- How many postings have reached each step
- Status breakdown (pending/running/completed/failed)
- Delta: completions in the last 10 minutes with mini progress bar
"""

from dotenv import load_dotenv, find_dotenv
import os
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv(find_dotenv())

# Workflow 3001 conversation mapping (in execution order)
# IDs from database: SELECT conversation_id, conversation_name FROM conversations WHERE ...
# Note: "Check if X Exists" steps removed - runner auto-skips completed interactions
WORKFLOW_STEPS = [
    # Step 1: Fetch & Validate
    (9144, "Fetch Jobs from Deutsche Bank API", "db_job_fetcher", "script"),
    (9193, "Validate Job Description", "check_description", "script"),
    
    # Step 2: Summary Pipeline (auto-skips if already done)
    (3335, "session_a_qwen25_extract", "qwen2.5:7b", "ai_model"),
    (3336, "session_b_mistral_grade", "mistral:latest", "ai_model"),
    (3337, "session_c_qwen25_grade", "qwen2.5:7b", "ai_model"),
    (3338, "session_d_qwen25_improve", "qwen2.5:7b", "ai_model"),      # Conditional
    (3339, "session_e_qwen25_regrade", "qwen2.5:7b", "ai_model"),      # Conditional
    (3340, "session_f_create_ticket", "qwen2.5:7b", "ai_model"),       # Conditional
    (3341, "Format Standardization", "qwen2.5:7b", "ai_model"),
    (9168, "Save Summary", "summary_saver", "script"),
    
    # Step 3: Skills Pipeline (auto-skips if already done)
    (9121, "Hybrid Job Skills Extraction", "qwen2.5:7b", "ai_model"),
    (9197, "Save Posting Skills", "postingskill_save", "script"),
    
    # Step 4: IHL Pipeline (auto-skips if already done)
    (9161, "IHL Analyst - Find Red Flags", "qwen2.5:7b", "ai_model"),
    (9162, "IHL Skeptic - Challenge Analyst", "mistral:latest", "ai_model"),
    (9163, "IHL HR Expert - Final Verdict", "qwen2.5:7b", "ai_model"),
    (9194, "Save IHL Score and Category", "ihl_score_saver", "script"),
]

# Conditional steps: only run for some postings, don't estimate ETA for remaining
CONDITIONAL_STEPS = {3338, 3339, 3340}

def get_conn():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )

def get_step_stats(conn):
    """Get status counts for each conversation step (unique postings only)."""
    cursor = conn.cursor()
    
    # Count UNIQUE postings per conversation_id and status
    # Uses DISTINCT ON to count each posting only once per step
    # Takes the "best" status for each posting (completed > running > pending > failed)
    # IMPORTANT: Only count non-invalidated interactions!
    cursor.execute("""
        WITH ranked_interactions AS (
            SELECT 
                conversation_id,
                posting_id,
                status,
                ROW_NUMBER() OVER (
                    PARTITION BY conversation_id, posting_id 
                    ORDER BY 
                        CASE status 
                            WHEN 'completed' THEN 1 
                            WHEN 'running' THEN 2 
                            WHEN 'pending' THEN 3 
                            ELSE 4 
                        END
                ) as rn
            FROM interactions
            WHERE conversation_id IN %s
              AND posting_id IS NOT NULL
              AND invalidated = false
        )
        SELECT 
            conversation_id,
            status,
            COUNT(*) as cnt
        FROM ranked_interactions
        WHERE rn = 1
        GROUP BY conversation_id, status
    """, (tuple([step[0] for step in WORKFLOW_STEPS]),))
    
    # Build nested dict: {conv_id: {status: count}}
    stats = defaultdict(lambda: defaultdict(int))
    for conv_id, status, cnt in cursor.fetchall():
        stats[conv_id][status] = cnt
    
    return stats


def get_phosphor_completions(conn, bucket_minutes=5, num_buckets=24):
    """
    Get completions bucketed by time for rainbow fade effect.
    Recent activity glows bright, older fades through the spectrum.
    
    Default: 24 buckets × 5 min = 2 hours of history
    Returns: {conv_id: [count_0_5min, count_5_10min, count_10_15min, ...]}
    """
    cursor = conn.cursor()
    now = datetime.now()
    
    # Build buckets
    phosphor = defaultdict(lambda: [0] * num_buckets)
    
    for bucket_idx in range(num_buckets):
        start_offset = bucket_idx * bucket_minutes
        end_offset = (bucket_idx + 1) * bucket_minutes
        
        start_time = now - timedelta(minutes=end_offset)
        end_time = now - timedelta(minutes=start_offset)
        
        cursor.execute("""
            SELECT 
                conversation_id,
                COUNT(DISTINCT posting_id) as cnt
            FROM interactions
            WHERE conversation_id IN %s
              AND posting_id IS NOT NULL
              AND status = 'completed'
              AND invalidated = false
              AND updated_at >= %s
              AND updated_at < %s
            GROUP BY conversation_id
        """, (tuple([step[0] for step in WORKFLOW_STEPS]), start_time, end_time))
        
        for conv_id, cnt in cursor.fetchall():
            phosphor[conv_id][bucket_idx] = cnt
    
    return phosphor


def get_avg_latency(conn):
    """Get average processing time in seconds per conversation step."""
    cursor = conn.cursor()
    
    # Calculate avg processing time from started_at to completed_at (last 24h for relevance)
    cursor.execute("""
        SELECT 
            conversation_id,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_seconds,
            COUNT(*) as sample_size
        FROM interactions
        WHERE conversation_id IN %s
          AND status = 'completed'
          AND invalidated = false
          AND started_at IS NOT NULL
          AND completed_at IS NOT NULL
          AND completed_at > started_at
          AND created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY conversation_id
    """, (tuple([step[0] for step in WORKFLOW_STEPS]),))
    
    latencies = {}
    for conv_id, avg_sec, sample_size in cursor.fetchall():
        if avg_sec and sample_size >= 3:  # Need at least 3 samples
            latencies[conv_id] = avg_sec
    
    return latencies

def get_posting_counts(conn):
    """Get total postings and their completion status."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE invalidated = false) as active,
            COUNT(extracted_summary) as has_summary,
            COUNT(skill_keywords) as has_skills,
            COUNT(ihl_score) as has_ihl
        FROM postings
        WHERE source = 'deutsche_bank'
    """)
    
    row = cursor.fetchone()
    return {
        'total': row[0],
        'active': row[1],
        'has_summary': row[2],
        'has_skills': row[3],
        'has_ihl': row[4]
    }

def format_progress_bar(completed, total, width=30):
    """Create a visual progress bar."""
    if total == 0:
        return "[" + " " * width + "] 0%"
    
    pct = completed / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct*100:.0f}%"


# ANSI color codes for rainbow time-fade effect
# 24 colors spanning 2 hours: hot (recent) → cool (older) → dim (ancient)
# Like a thermal camera view of activity over time
PHOSPHOR_COLORS = [
    # HOT - Recent activity (0-30 min) - Reds/Oranges/Yellows
    '\033[38;5;196m',  # Bright red (0-5 min) - just happened!
    '\033[38;5;202m',  # Orange-red (5-10 min)
    '\033[38;5;208m',  # Orange (10-15 min)
    '\033[38;5;214m',  # Light orange (15-20 min)
    '\033[38;5;220m',  # Gold (20-25 min)
    '\033[38;5;226m',  # Yellow (25-30 min)
    # WARM - Recent-ish (30-60 min) - Greens
    '\033[38;5;190m',  # Yellow-green (30-35 min)
    '\033[38;5;154m',  # Lime (35-40 min)
    '\033[38;5;118m',  # Bright green (40-45 min)
    '\033[38;5;82m',   # Green (45-50 min)
    '\033[38;5;46m',   # Pure green (50-55 min)
    '\033[38;5;42m',   # Sea green (55-60 min)
    # COOL - Older (60-90 min) - Cyans/Blues
    '\033[38;5;43m',   # Cyan-green (60-65 min)
    '\033[38;5;49m',   # Cyan (65-70 min)
    '\033[38;5;51m',   # Bright cyan (70-75 min)
    '\033[38;5;45m',   # Sky blue (75-80 min)
    '\033[38;5;39m',   # Light blue (80-85 min)
    '\033[38;5;33m',   # Blue (85-90 min)
    # COLD - Ancient (90-120 min) - Purples/Grays
    '\033[38;5;63m',   # Blue-purple (90-95 min)
    '\033[38;5;57m',   # Purple (95-100 min)
    '\033[38;5;93m',   # Violet (100-105 min)
    '\033[38;5;97m',   # Dim purple (105-110 min)
    '\033[38;5;240m',  # Dark gray (110-115 min)
    '\033[38;5;236m',  # Almost gone (115-120 min)
]
RESET_COLOR = '\033[0m'


def format_phosphor_bar(phosphor_buckets, max_total, width=16):
    """
    Create a rainbow time-fade bar showing activity over time.
    
    Uses ANSI colors for thermal effect:
    - Recent activity glows hot (red/orange)
    - Older activity cools (green/blue)
    - Ancient activity dims (purple/gray)
    """
    total = sum(phosphor_buckets)
    if max_total == 0 or total == 0:
        return " " * (width + 5)  # Empty space for alignment
    
    # Build the bar: each character represents proportional activity
    # Consolidate buckets to fit width, keeping color gradient
    bar_chars = []
    
    # Group buckets to fit in width (e.g., 24 buckets -> 16 chars = ~1.5 buckets per char)
    buckets_per_char = len(phosphor_buckets) / width
    
    for char_idx in range(width):
        # Which buckets contribute to this character?
        start_bucket = int(char_idx * buckets_per_char)
        end_bucket = int((char_idx + 1) * buckets_per_char)
        
        # Sum activity in these buckets
        bucket_sum = sum(phosphor_buckets[start_bucket:end_bucket])
        
        if bucket_sum > 0:
            # Use the color of the earliest bucket in this group
            color = PHOSPHOR_COLORS[min(start_bucket, len(PHOSPHOR_COLORS) - 1)]
            bar_chars.append(f"{color}█{RESET_COLOR}")
        else:
            bar_chars.append(" ")
    
    bar = "".join(bar_chars)
    
    return f"+{total:3d} {bar}"


def print_step(conv_id, name, actor, actor_type, stats, phosphor, latencies, total_postings, max_phosphor, step_num):
    """Print one workflow step with stats - all on one line."""
    pending = stats[conv_id].get('pending', 0)
    running = stats[conv_id].get('running', 0)
    completed = stats[conv_id].get('completed', 0)
    failed = stats[conv_id].get('failed', 0)
    phosphor_buckets = phosphor.get(conv_id, [0, 0, 0, 0])
    avg_sec = latencies.get(conv_id)
    
    # Check if this is a conditional step (not all postings flow through)
    is_conditional = conv_id in CONDITIONAL_STEPS
    
    # Calculate remaining work (not completed yet)
    remaining = total_postings - completed
    
    # Special case: Fetch step (conv 9144) - if postings exist, they were fetched
    if conv_id == 9144 and completed > 0:
        completed = total_postings
        remaining = 0
    
    # Icon based on actor type
    icon = "🤖" if actor_type == "ai_model" else "⚙️ "
    
    # Progress percentage - for conditional steps, don't show misleading percentage
    if is_conditional:
        # Conditional steps: show count only, not percentage (not all postings flow through)
        pct = "cond"  # Mark as conditional
    else:
        pct_value = 100*completed/total_postings if total_postings > 0 else 0
        pct = f"{pct_value:3.0f}%"
        
        # Green highlight for 100% complete (use rounded percentage to match display)
        if round(pct_value) >= 100:
            pct = f"\033[32m{pct}\033[0m"  # Green
    
    # Phosphor bar (CRT fade effect)
    phosphor_str = format_phosphor_bar(phosphor_buckets, max_phosphor)
    
    # Avg time formatting
    if avg_sec is not None:
        if avg_sec < 1:
            time_str = f"{avg_sec*1000:4.0f}ms"
        elif avg_sec < 60:
            time_str = f"{avg_sec:5.1f}s"
        else:
            time_str = f"{avg_sec/60:4.1f}m"
        
        # ETA for this step = avg_time * remaining
        # For conditional steps, don't calculate ETA (we don't know how many will flow through)
        if is_conditional:
            eta_str = "    —"  # Can't estimate ETA for conditional steps
        elif remaining > 0:
            eta_sec = avg_sec * remaining
            if eta_sec < 60:
                eta_str = f"{eta_sec:4.0f}s"
            elif eta_sec < 3600:
                eta_str = f"{eta_sec/60:4.1f}m"
            else:
                eta_str = f"{eta_sec/3600:4.1f}h"
        else:
            eta_str = "  done"
    else:
        time_str = "    —"
        eta_str = "    —"
    
    # Status summary (compact)
    status_parts = []
    if completed > 0:
        status_parts.append(f"✅{completed}")
    if running > 0:
        status_parts.append(f"🔄{running}")
    if pending > 0:
        status_parts.append(f"⏳{pending}")
    if failed > 0:
        status_parts.append(f"❌{failed}")
    status = " ".join(status_parts) if status_parts else "—"
    
    # Format: step_num | icon | name | actor | avg_time | eta | completed/total pct | phosphor bar | status
    # For conditional steps, show completed count without total (not all flow through)
    if is_conditional:
        progress_str = f"{completed:4d}      {pct}"
    else:
        progress_str = f"{completed:4d}/{total_postings:<4d} {pct}"
    
    print(f"{step_num:2d} {icon} {name:35s} | {actor:18s} | {time_str:>6s} | {eta_str:>6s} | {progress_str:15s} | {phosphor_str:17s} | {status}")

def print_flowchart_dashboard():
    """Print the complete workflow flowchart with progress."""
    conn = get_conn()
    
    # Get data
    stats = get_step_stats(conn)
    phosphor = get_phosphor_completions(conn, bucket_minutes=5, num_buckets=24)  # 24 buckets × 5 min = 2 hour history
    latencies = get_avg_latency(conn)
    posting_counts = get_posting_counts(conn)
    
    # Find max phosphor bucket for scaling (use max of any single bucket)
    max_phosphor = 0
    for buckets in phosphor.values():
        max_phosphor = max(max_phosphor, max(buckets) if buckets else 0)
    
    # Calculate total activity (sum of all buckets)
    total_activity = sum(sum(buckets) for buckets in phosphor.values())
    
    # Calculate ETA by summing per-step ETAs (more accurate than rate extrapolation)
    # Each step's ETA = avg_latency * remaining_items
    # Skip conditional steps - they don't run for all postings
    total_eta_seconds = 0
    for conv_id, name, actor, actor_type in WORKFLOW_STEPS:
        # Skip conditional steps - can't estimate their remaining work
        if conv_id in CONDITIONAL_STEPS:
            continue
        completed = stats[conv_id].get('completed', 0)
        # Special case: Fetch step (conv 9144) - if any postings exist, fetch is done
        if conv_id == 9144 and posting_counts['active'] > 0:
            completed = posting_counts['active']
        remaining = max(0, posting_counts['active'] - completed)
        avg_sec = latencies.get(conv_id)
        if avg_sec and remaining > 0:
            total_eta_seconds += avg_sec * remaining
    
    if total_eta_seconds > 0:
        eta_minutes = total_eta_seconds / 60
        done_by = datetime.now() + timedelta(seconds=float(total_eta_seconds))
        done_by_str = done_by.strftime('%H:%M')
        if eta_minutes < 60:
            eta_str = f"\033[1m{eta_minutes:.0f} min\033[0m (done ~{done_by_str})"
        elif eta_minutes < 1440:
            eta_str = f"\033[1m{eta_minutes/60:.1f} hours\033[0m (done ~{done_by_str})"
        else:
            eta_str = f"\033[1m{eta_minutes/1440:.1f} days\033[0m"
    else:
        eta_str = "\033[1;32mdone ✅\033[0m"
    
    # Build rainbow legend (condensed - show key time markers)
    legend = f"{PHOSPHOR_COLORS[0]}█{RESET_COLOR}now "
    legend += f"{PHOSPHOR_COLORS[6]}█{RESET_COLOR}30m "
    legend += f"{PHOSPHOR_COLORS[12]}█{RESET_COLOR}1h "
    legend += f"{PHOSPHOR_COLORS[18]}█{RESET_COLOR}90m "
    legend += f"{PHOSPHOR_COLORS[23]}█{RESET_COLOR}2h"
    
    # Header
    print("=" * 140)
    print(f"WORKFLOW 3001: Complete Job Processing Pipeline                                                      ⏱️  ETA: {eta_str}")
    print("=" * 140)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}    |    Rainbow: {legend}")
    print()
    print(f"📊 POSTINGS OVERVIEW:")
    print(f"   Total Postings:     {posting_counts['total']:,}")
    print(f"   Active Postings:    {posting_counts['active']:,}")
    
    # Avoid division by zero when no active postings
    active = posting_counts['active'] if posting_counts['active'] > 0 else 1
    print(f"   With Summaries:     {posting_counts['has_summary']:,} ({100*posting_counts['has_summary']/active:.0f}%)")
    print(f"   With Skills:        {posting_counts['has_skills']:,} ({100*posting_counts['has_skills']/active:.0f}%)")
    print(f"   With IHL Scores:    {posting_counts['has_ihl']:,} ({100*posting_counts['has_ihl']/active:.0f}%)")
    
    print("\n" + "=" * 140)
    print("WORKFLOW FLOWCHART - STEP BY STEP PROGRESS")
    print("=" * 140)
    
    # Column headers
    header = f"{'#':>2} {'':2} {'Step Name':35s} | {'Actor':18s} | {'Avg':>6s} | {'ETA':>6s} | {'Progress':14s} | {'Activity 2h':21s} | Status"
    
    # Pipeline 1: Fetch & Validate
    print()
    print("📥 PIPELINE 1: FETCH & VALIDATE")
    print("─" * 140)
    print(header)
    print("─" * 140)
    
    for i in range(0, 2):
        conv_id, name, actor, actor_type = WORKFLOW_STEPS[i]
        print_step(conv_id, name, actor, actor_type, stats, phosphor, latencies, posting_counts['active'], max_phosphor, i+1)
    
    # Pipeline 2: Summary Generation (steps 2-9: indices 2-9)
    print()
    print("📝 PIPELINE 2: SUMMARY GENERATION")
    print("─" * 140)
    print(header)
    print("─" * 140)
    
    for i in range(2, 10):  # 8 steps: extract, 5 grading, format, save
        conv_id, name, actor, actor_type = WORKFLOW_STEPS[i]
        print_step(conv_id, name, actor, actor_type, stats, phosphor, latencies, posting_counts['active'], max_phosphor, i+1)
    
    # Pipeline 3: Skills Extraction (steps 10-11: indices 10-11)
    print()
    print("🎯 PIPELINE 3: SKILLS EXTRACTION")
    print("─" * 140)
    print(header)
    print("─" * 140)
    
    for i in range(10, 12):  # 2 steps: extract, save
        conv_id, name, actor, actor_type = WORKFLOW_STEPS[i]
        print_step(conv_id, name, actor, actor_type, stats, phosphor, latencies, posting_counts['active'], max_phosphor, i+1)
    
    # Pipeline 4: IHL Scoring (steps 12-15: indices 12-15)
    print()
    print("🔍 PIPELINE 4: IHL SCORING (Compliance Theater Detection)")
    print("─" * 140)
    print(header)
    print("─" * 140)
    
    for i in range(12, len(WORKFLOW_STEPS)):  # 4 steps: analyst, skeptic, expert, save
        conv_id, name, actor, actor_type = WORKFLOW_STEPS[i]
        print_step(conv_id, name, actor, actor_type, stats, phosphor, latencies, posting_counts['active'], max_phosphor, i+1)
    
    # Footer with total activity and health check
    remaining_work = calculate_remaining_work(stats, posting_counts['active'])
    recent_activity = sum(sum(buckets[:6]) for buckets in phosphor.values())  # Last 30 min (6 buckets × 5 min)
    very_recent = sum(sum(buckets[:2]) for buckets in phosphor.values())  # Last 10 min (2 buckets × 5 min)
    rate_per_min = recent_activity / 30 if recent_activity > 0 else 0
    
    # Health check
    total_running = sum(stats[conv_id].get('running', 0) for conv_id, _, _, _ in WORKFLOW_STEPS)
    total_pending = sum(stats[conv_id].get('pending', 0) for conv_id, _, _, _ in WORKFLOW_STEPS)
    
    if very_recent == 0 and remaining_work > 0:
        health = "  ⚠️  \033[33mNO ACTIVITY in last 10 min!\033[0m"
    elif total_running == 0 and total_pending > 0:
        health = f"  ⚠️  \033[33mNothing running but {total_pending} pending\033[0m"
    elif remaining_work == 0:
        health = "  ✅ \033[32mAll done!\033[0m"
    else:
        health = "  ✅ Healthy"
    
    print("\n" + "=" * 140)
    print(f"TOTAL ACTIVITY (last 2h): {total_activity} completions    |    Last 30 min: {recent_activity}    |    Remaining: {remaining_work}    |    Rate: {rate_per_min:.1f}/min{health}")
    print("=" * 140)
    
    conn.close()


def calculate_remaining_work(stats, total_postings):
    """Calculate total remaining step-completions needed."""
    remaining = 0
    for conv_id, name, actor, actor_type in WORKFLOW_STEPS:
        completed = stats[conv_id].get('completed', 0)
        remaining += max(0, total_postings - completed)
    return remaining

if __name__ == '__main__':
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Workflow 3001 Flowchart Dashboard')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=60, help='Refresh interval in seconds (default: 60)')
    args = parser.parse_args()
    
    if args.once:
        print_flowchart_dashboard()
    else:
        while True:
            # Clear screen
            print("\033[2J\033[H", end="")
            print_flowchart_dashboard()
            print(f"\n⏱️  Refreshing every {args.interval}s... (Ctrl+C to stop)")
            time.sleep(args.interval)
