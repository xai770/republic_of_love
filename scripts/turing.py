#!/usr/bin/env python3
"""
Turing Workflow Engine - Live Dashboard
========================================

Monitors workflow progress using interaction data (the source of truth).

Usage:
    python scripts/turing.py              # Live dashboard
    python scripts/turing.py --status     # Show status once and exit
    python scripts/turing.py --kill       # Stop daemon

Author: Sandy (refactored Dec 13 2025)
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

import psycopg2

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

REFRESH_INTERVAL = 60  # 1 minute for active monitoring
DAEMON_LOCK_FILE = project_root / '.turing_daemon.lock'
DAEMON_LOG = project_root / 'logs' / 'turing_daemon.out'

# ANSI colors
RESET, BOLD, DIM = '\033[0m', '\033[1m', '\033[2m'
GREEN, YELLOW, RED, CYAN = '\033[32m', '\033[33m', '\033[31m', '\033[36m'
CLEAR = '\033[2J\033[H'

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE QUERIES - All metrics from interactions table
# ═══════════════════════════════════════════════════════════════════════════════

def get_conn():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST')
    )


def get_pipeline_status(cur):
    """Get real-time pipeline status from interactions."""
    # Running interactions
    cur.execute("""
        SELECT a.actor_name, COUNT(*), 
               EXTRACT(EPOCH FROM (NOW() - MIN(i.started_at))) as oldest_secs
        FROM interactions i
        JOIN actors a ON i.actor_id = a.actor_id
        WHERE i.status = 'running'
        GROUP BY a.actor_name ORDER BY COUNT(*) DESC
    """)
    running = [{'actor': r[0][:15], 'count': r[1], 'secs': r[2] or 0} for r in cur.fetchall()]
    
    # Pending interactions (ready to run)
    cur.execute("""
        SELECT a.actor_name, a.actor_type, COUNT(*)
        FROM interactions i
        JOIN actors a ON i.actor_id = a.actor_id
        LEFT JOIN interactions p ON i.parent_interaction_id = p.interaction_id
        WHERE i.status = 'pending' AND i.enabled AND NOT i.invalidated
          AND (i.parent_interaction_id IS NULL OR p.status = 'completed')
        GROUP BY a.actor_name, a.actor_type ORDER BY COUNT(*) DESC LIMIT 5
    """)
    pending = [{'actor': r[0][:15], 'type': r[1], 'count': r[2]} for r in cur.fetchall()]
    
    # Completions in last 5 minutes
    cur.execute("""
        SELECT a.actor_name, COUNT(*)
        FROM interactions i JOIN actors a ON i.actor_id = a.actor_id
        WHERE i.status = 'completed' AND i.completed_at > NOW() - INTERVAL '5 minutes'
        GROUP BY a.actor_name ORDER BY COUNT(*) DESC LIMIT 3
    """)
    recent = [{'actor': r[0][:15], 'count': r[1]} for r in cur.fetchall()]
    
    return {
        'running': running, 'pending': pending, 'recent': recent,
        'total_running': sum(r['count'] for r in running),
        'total_pending': sum(p['count'] for p in pending),
    }


def get_skill_progress(cur):
    """Get WF3005 skill processing progress."""
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'processing') as processing,
            COUNT(*) FILTER (WHERE status IN ('approved','rejected','merged')) as done
        FROM entities_pending
    """)
    row = cur.fetchone()
    return {'pending': row[0], 'processing': row[1], 'done': row[2], 
            'total': row[0] + row[1] + row[2]}


def get_interaction_progress(cur):
    """Get interaction queue progress - shows work draining in real-time."""
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'running') as running,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) as total
        FROM interactions
        WHERE workflow_run_id IN (
            SELECT workflow_run_id FROM workflow_runs WHERE status = 'running'
        )
    """)
    row = cur.fetchone()
    return {
        'pending': row[0] or 0, 
        'running': row[1] or 0, 
        'completed': row[2] or 0,
        'failed': row[3] or 0,
        'total': row[4] or 0
    }


def get_throughput(cur):
    """Get interaction completion rates."""
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE completed_at > NOW() - INTERVAL '5 minutes') as last_5m,
            COUNT(*) FILTER (WHERE completed_at > NOW() - INTERVAL '60 minutes') as last_1h
        FROM interactions WHERE status = 'completed'
    """)
    row = cur.fetchone()
    rate_5m = (row[0] or 0) * 12  # Extrapolate to hourly
    rate_1h = row[1] or 0
    return {'rate_5m': rate_5m, 'rate_1h': rate_1h, 'count_5m': row[0], 'count_1h': row[1]}


def get_latency(cur):
    """Get actor latency stats (last hour)."""
    cur.execute("""
        SELECT a.actor_name, COUNT(*),
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p50,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p95
        FROM interactions i JOIN actors a ON i.actor_id = a.actor_id
        WHERE i.completed_at > NOW() - INTERVAL '1 hour' AND i.started_at IS NOT NULL
        GROUP BY a.actor_name ORDER BY COUNT(*) DESC LIMIT 3
    """)
    return [{'actor': r[0][:12], 'n': r[1], 'p50': r[2] or 0, 'p95': r[3] or 0} for r in cur.fetchall()]


def get_skill_kpis(cur):
    """Get skill-level KPIs for the dashboard."""
    result = {}
    
    # 1. Skills completed per hour (1h and 5m extrapolated)
    cur.execute("""
        SELECT 
            COUNT(DISTINCT ep.pending_id) FILTER (
                WHERE ep.processed_at > NOW() - INTERVAL '1 hour'
            ) as skills_1h,
            COUNT(DISTINCT ep.pending_id) FILTER (
                WHERE ep.processed_at > NOW() - INTERVAL '5 minutes'
            ) as skills_5m
        FROM entities_pending ep
        WHERE ep.status IN ('approved', 'rejected', 'merged')
    """)
    row = cur.fetchone()
    result['skills_1h'] = row[0] or 0
    result['skills_5m'] = row[1] or 0
    result['skills_hr_rate'] = (row[1] or 0) * 12  # Extrapolate 5m to hourly
    
    # 2. Avg interactions per skill (ratio based - skills are batch processed)
    cur.execute("""
        SELECT 
            (SELECT COUNT(*) FROM interactions WHERE completed_at > NOW() - INTERVAL '24 hours') as interactions_24h,
            (SELECT COUNT(*) FROM entities_pending WHERE processed_at > NOW() - INTERVAL '24 hours' 
                AND status IN ('approved', 'rejected', 'merged')) as skills_24h
    """)
    row = cur.fetchone()
    interactions_24h, skills_24h = row[0] or 0, row[1] or 0
    if skills_24h > 0:
        result['avg_interactions_per_skill'] = round(interactions_24h / skills_24h, 2)
    else:
        result['avg_interactions_per_skill'] = 4.0  # Default fallback
    
    # 3. Time per interaction (p50, p95) - since skills are batched
    cur.execute("""
        SELECT 
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at))) as p50,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at))) as p95,
            COUNT(*) as n
        FROM interactions
        WHERE completed_at > NOW() - INTERVAL '24 hours'
          AND started_at IS NOT NULL AND completed_at IS NOT NULL
    """)
    row = cur.fetchone()
    result['skill_time_p50'] = row[0] or 0
    result['skill_time_p95'] = row[1] or 0
    result['skill_time_n'] = row[2] or 0
    
    # 4. Model utilization (% of last hour models were busy)
    cur.execute("""
        SELECT a.actor_name,
            SUM(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) / 3600.0 * 100 as pct_busy
        FROM interactions i
        JOIN actors a ON i.actor_id = a.actor_id
        WHERE i.completed_at > NOW() - INTERVAL '1 hour'
          AND i.started_at IS NOT NULL
          AND a.actor_type = 'ai_model'
        GROUP BY a.actor_name
        ORDER BY pct_busy DESC
        LIMIT 3
    """)
    result['model_utilization'] = [{'actor': r[0][:12], 'pct': r[1] or 0} for r in cur.fetchall()]
    
    # 5. Throughput trend (compare last 30m to previous 30m)
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE completed_at > NOW() - INTERVAL '30 minutes') as recent,
            COUNT(*) FILTER (WHERE completed_at BETWEEN NOW() - INTERVAL '60 minutes' AND NOW() - INTERVAL '30 minutes') as previous
        FROM interactions
        WHERE status = 'completed' AND completed_at > NOW() - INTERVAL '60 minutes'
    """)
    row = cur.fetchone()
    recent, previous = row[0] or 0, row[1] or 0
    if previous > 0:
        trend_pct = ((recent - previous) / previous) * 100
        result['trend'] = '↑' if trend_pct > 10 else ('↓' if trend_pct < -10 else '→')
        result['trend_pct'] = trend_pct
    else:
        result['trend'] = '→'
        result['trend_pct'] = 0
    result['trend_recent'] = recent
    result['trend_previous'] = previous
    
    return result


def get_batch_start(cur):
    """Get when current batch started (oldest pending queue entry)."""
    cur.execute("SELECT MIN(created_at) FROM queue WHERE status IN ('pending','processing')")
    row = cur.fetchone()
    return row[0] if row else None


def get_instruction_breakdown(cur):
    """Get interaction counts grouped by instruction name."""
    cur.execute("""
        SELECT 
            COALESCE(ins.instruction_name, '(no instruction)') as instruction,
            a.actor_name,
            COUNT(*) FILTER (WHERE i.status = 'pending') as pending,
            COUNT(*) FILTER (WHERE i.status = 'running') as running,
            COUNT(*) FILTER (WHERE i.status = 'completed' AND i.completed_at > NOW() - INTERVAL '1 hour') as done_1h
        FROM interactions i
        JOIN actors a ON i.actor_id = a.actor_id
        LEFT JOIN instructions ins ON i.instruction_id = ins.instruction_id
        GROUP BY ins.instruction_name, a.actor_name
        HAVING COUNT(*) FILTER (WHERE i.status IN ('pending', 'running')) > 0 
            OR COUNT(*) FILTER (WHERE i.completed_at > NOW() - INTERVAL '1 hour') > 0
        ORDER BY pending DESC, done_1h DESC
        LIMIT 8
    """)
    return [{'instruction': r[0][:25], 'actor': r[1][:12], 'pending': r[2], 'running': r[3], 'done_1h': r[4]} 
            for r in cur.fetchall()]


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def fmt_time(dt):
    """Format datetime as 'Xs ago'."""
    if not dt: return "—"
    dt = dt.replace(tzinfo=None) if dt.tzinfo else dt
    secs = (datetime.now() - dt).total_seconds()
    if secs < 60: return f"{secs:.0f}s"
    if secs < 3600: return f"{secs/60:.0f}m"
    return f"{secs/3600:.1f}h"


def fmt_duration(secs, expected=120):
    """Format seconds as duration. Shows elapsed time, with warning if over expected."""
    secs = abs(secs) if secs else 0  # Handle negative/None
    if secs < 60: 
        return f"{secs:.0f}s"
    if secs < 3600: 
        mins = secs / 60
        suffix = "!" if secs > expected else ""
        return f"{mins:.0f}m{suffix}"
    return f"{secs/3600:.1f}h!"


def get_recent_logs(n=5):
    """Get the last n lines from today's daemon log."""
    from datetime import date
    log_dir = Path(__file__).parent.parent / 'logs'
    today = date.today().strftime('%Y%m%d')
    log_file = log_dir / f'turing_daemon_{today}.log'
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        # Strip newlines and return last n non-empty lines
        return [l.strip() for l in lines if l.strip()][-n:]
    except Exception:
        return []


def render(pipeline, skills, throughput, latency, batch_start, daemon_pid, instructions, skill_kpis, interaction_progress=None, recent_logs=None):
    """Render the dashboard."""
    W = 70
    now = datetime.now().strftime('%H:%M:%S')
    
    # Uptime
    if batch_start:
        bs = batch_start.replace(tzinfo=None) if batch_start.tzinfo else batch_start
        uptime = datetime.now() - bs
        uptime_str = f"{int(uptime.total_seconds()/3600)}h {int((uptime.total_seconds()%3600)/60)}m"
    else:
        uptime_str = "—"
    
    # ETA calculation based on throughput
    skills_remaining = skills['pending'] + skills['processing']
    rate = throughput['rate_5m'] if throughput['rate_5m'] > 0 else throughput['rate_1h']
    # Use actual avg interactions per skill (measured), not assumed 4
    avg_interactions = skill_kpis.get('avg_interactions_per_skill', 4.0)
    # hours = (skills × avg_interactions) / rate
    if rate > 0 and skills_remaining > 0:
        eta_hours = (skills_remaining * avg_interactions) / rate
        eta_time = datetime.now() + timedelta(hours=eta_hours)
        eta_str = f"~{eta_time.strftime('%b %d %H:%M')}" if eta_hours > 1 else f"~{eta_hours*60:.0f}m"
    elif skills_remaining == 0:
        eta_str = "✅ Complete"
    else:
        eta_str = "calculating..."
    
    # Status
    status = '🟢 OK' if pipeline['total_running'] > 0 else ('🟡 IDLE' if pipeline['total_pending'] > 0 else '⚪ DONE')
    
    lines = [
        f"{'═'*W}",
        f"  TURING WORKFLOW ENGINE                                    {now}",
        f"{'═'*W}",
        f"  Status: {status}    Uptime: {uptime_str}    ETA: {GREEN}{eta_str}{RESET}",
        f"{'─'*W}",
        f"  SKILLS",
        f"    Done: {GREEN}{skills['done']:,}{RESET}  Processing: {YELLOW}{skills['processing']:,}{RESET}  Pending: {skills['pending']:,}",
        f"    Progress: {100*skills['done']/skills['total']:.0f}% ({skills['done']:,}/{skills['total']:,})",
        f"{'─'*W}",
    ]
    
    # Interaction queue progress (shows work draining)
    if interaction_progress and interaction_progress['total'] > 0:
        ip = interaction_progress
        done = ip['completed'] + ip['failed']
        remaining = ip['pending'] + ip['running']
        pct = 100 * done / ip['total'] if ip['total'] > 0 else 0
        lines.extend([
            f"  INTERACTIONS (active workflows)",
            f"    Done: {GREEN}{done:,}{RESET}  Running: {YELLOW}{ip['running']:,}{RESET}  Pending: {ip['pending']:,}  Failed: {RED if ip['failed'] > 0 else DIM}{ip['failed']:,}{RESET}",
            f"    Progress: {pct:.0f}% ({done:,}/{ip['total']:,})  Remaining: {remaining:,}",
            f"{'─'*W}",
        ])
    
    lines.extend([
        f"  THROUGHPUT",
        f"    Last 5m: {throughput['count_5m']} interactions ({throughput['rate_5m']:.0f}/hr extrapolated)",
        f"    Last 1h: {throughput['count_1h']} interactions ({throughput['rate_1h']:.0f}/hr)",
        f"{'─'*W}",
    ])
    
    # Pipeline status
    lines.append(f"  PIPELINE")
    if pipeline['running']:
        items = ', '.join(f"{r['actor']}×{r['count']}({fmt_duration(r['secs'])})" for r in pipeline['running'][:3])
        lines.append(f"    {GREEN}▶ Running ({pipeline['total_running']}): {items}{RESET}")
    else:
        lines.append(f"    {DIM}▶ Running (0){RESET}")
    
    if pipeline['pending']:
        items = ', '.join(f"{p['actor']}×{p['count']}" for p in pipeline['pending'][:3])
        lines.append(f"    {YELLOW}◉ Queued ({pipeline['total_pending']}): {items}{RESET}")
    else:
        lines.append(f"    {DIM}◉ Queued (0){RESET}")
    
    if pipeline['recent']:
        total = sum(r['count'] for r in pipeline['recent'])
        items = ', '.join(f"{r['actor']}×{r['count']}" for r in pipeline['recent'][:2])
        lines.append(f"    {CYAN}✓ Done (5m): {total} - {items}{RESET}")
    
    lines.append(f"{'─'*W}")
    
    # Instructions breakdown
    if instructions:
        lines.append(f"  INSTRUCTIONS                            pend  run  done/hr")
        for ins in instructions[:6]:
            pend_color = YELLOW if ins['pending'] > 0 else DIM
            run_color = GREEN if ins['running'] > 0 else DIM
            lines.append(f"    {ins['instruction']:<25} {ins['actor']:<12} {pend_color}{ins['pending']:>4}{RESET} {run_color}{ins['running']:>4}{RESET} {CYAN}{ins['done_1h']:>4}{RESET}")
        lines.append(f"{'─'*W}")
    
    # Latency
    if latency:
        lines.append(f"  LATENCY (1hr)")
        for s in latency[:2]:
            lines.append(f"    {DIM}{s['actor']:<12} p50={s['p50']:>5.1f}s  p95={s['p95']:>5.1f}s  n={s['n']}{RESET}")
        lines.append(f"{'─'*W}")
    
    # Skill Metrics (new KPIs)
    lines.append(f"  SKILL METRICS")
    # Skills/hour
    skill_rate = skill_kpis.get('skills_hr_rate', 0)
    skills_1h = skill_kpis.get('skills_1h', 0)
    lines.append(f"    Skills/hr: {GREEN}{skill_rate:.0f}{RESET} (extrapolated)  Actual 1h: {skills_1h}")
    # Avg interactions per skill
    avg_int = skill_kpis.get('avg_interactions_per_skill', 4.0)
    lines.append(f"    Avg interactions/skill: {avg_int:.1f}  (used in ETA calc)")
    # Time per interaction (renamed from skill since skills are batched)
    p50 = skill_kpis.get('skill_time_p50', 0)
    p95 = skill_kpis.get('skill_time_p95', 0)
    n = skill_kpis.get('skill_time_n', 0)
    if n > 0:
        lines.append(f"    Time/interaction (24h): p50={p50:.0f}s  p95={p95:.0f}s  (n={n})")
    # Model utilization
    util = skill_kpis.get('model_utilization', [])
    if util:
        util_str = '  '.join(f"{u['actor']}:{u['pct']:.0f}%" for u in util[:3])
        lines.append(f"    Model util (1h): {util_str}")
    # Throughput trend
    trend = skill_kpis.get('trend', '→')
    trend_pct = skill_kpis.get('trend_pct', 0)
    trend_color = GREEN if trend == '↑' else (RED if trend == '↓' else DIM)
    lines.append(f"    Trend (30m vs prev 30m): {trend_color}{trend} {trend_pct:+.0f}%{RESET}")
    lines.append(f"{'─'*W}")
    
    # Recent log entries
    if recent_logs:
        lines.append(f"  RECENT LOG")
        for log_line in recent_logs[-5:]:
            # Truncate to fit width, strip timestamp prefix if too long
            display = log_line[:W-4] if len(log_line) > W-4 else log_line
            lines.append(f"    {DIM}{display}{RESET}")
        lines.append(f"{'─'*W}")
    
    # Daemon status
    if daemon_pid:
        lines.append(f"  {GREEN}● Daemon running (PID {daemon_pid}){RESET}")
    else:
        lines.append(f"  {RED}○ Daemon stopped{RESET} - run 'python scripts/turing.py' to start")
    
    lines.append(f"{'═'*W}")
    
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# DAEMON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_daemon_pid():
    """Check if daemon is running, return PID or None."""
    if DAEMON_LOCK_FILE.exists():
        try:
            with open(DAEMON_LOCK_FILE) as f:
                pid = int(f.readline().strip())
            os.kill(pid, 0)  # Check if alive
            return pid
        except (ValueError, OSError, ProcessLookupError):
            pass
    return None


def start_daemon():
    """Start daemon if not running."""
    if get_daemon_pid():
        return False  # Already running
    
    DAEMON_LOG.parent.mkdir(exist_ok=True)
    with open(DAEMON_LOG, 'a') as log:
        subprocess.Popen(
            ['python3', 'scripts/turing_daemon.py'],
            stdout=log, stderr=log, cwd=project_root, start_new_session=True
        )
    time.sleep(2)
    return True


def stop_daemon():
    """Stop daemon gracefully."""
    result = subprocess.run(
        ['python3', 'scripts/turing_daemon.py', '--stop'],
        capture_output=True, text=True, cwd=project_root
    )
    if result.returncode != 0:
        subprocess.run(['pkill', '-f', 'turing_daemon.py'], capture_output=True)
        time.sleep(1)
        subprocess.run(['pkill', '-9', '-f', 'turing_daemon.py'], capture_output=True)
    DAEMON_LOCK_FILE.unlink(missing_ok=True)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def show_status():
    """Show status once and exit."""
    conn = get_conn()
    cur = conn.cursor()
    
    pipeline = get_pipeline_status(cur)
    skills = get_skill_progress(cur)
    throughput = get_throughput(cur)
    latency = get_latency(cur)
    batch_start = get_batch_start(cur)
    daemon_pid = get_daemon_pid()
    instructions = get_instruction_breakdown(cur)
    skill_kpis = get_skill_kpis(cur)
    interaction_progress = get_interaction_progress(cur)
    recent_logs = get_recent_logs(5)
    
    print(render(pipeline, skills, throughput, latency, batch_start, daemon_pid, instructions, skill_kpis, interaction_progress, recent_logs))
    conn.close()


def run_monitor():
    """Run live monitoring dashboard."""
    stop_event = threading.Event()
    
    def handle_signal(signum, frame):
        stop_event.set()
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Start daemon if needed
    if start_daemon():
        print(f"{GREEN}✓ Started daemon{RESET}")
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        while not stop_event.is_set():
            pipeline = get_pipeline_status(cur)
            skills = get_skill_progress(cur)
            throughput = get_throughput(cur)
            latency = get_latency(cur)
            batch_start = get_batch_start(cur)
            daemon_pid = get_daemon_pid()
            instructions = get_instruction_breakdown(cur)
            skill_kpis = get_skill_kpis(cur)
            interaction_progress = get_interaction_progress(cur)
            recent_logs = get_recent_logs(5)
            
            print(CLEAR, end='')
            print(render(pipeline, skills, throughput, latency, batch_start, daemon_pid, instructions, skill_kpis, interaction_progress, recent_logs))
            print(f"{DIM}  Ctrl+C to exit. Daemon continues running.{RESET}")
            
            stop_event.wait(timeout=REFRESH_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()
        print(f"\n{GREEN}Monitor closed. Daemon still running.{RESET}")


def run_until_done():
    """Run dashboard until all pending skills are processed."""
    print(f"{GREEN}Running until all skills are processed...{RESET}")
    print(f"{DIM}Dashboard will exit when pending skills = 0. Ctrl+C to stop early.{RESET}\n")
    
    conn = get_conn()
    cur = conn.cursor()
    
    start_time = time.time()
    initial_pending = None
    
    try:
        while True:
            # Collect current state
            pipeline = get_pipeline_status(cur)
            skills = get_skill_progress(cur)
            throughput = get_throughput(cur)
            latency = get_latency(cur)
            batch_start = get_batch_start(cur)
            daemon_pid = get_daemon_pid()
            instructions = get_instruction_breakdown(cur)
            skill_kpis = get_skill_kpis(cur)
            interaction_progress = get_interaction_progress(cur)
            recent_logs = get_recent_logs(5)
            
            if initial_pending is None:
                initial_pending = skills['pending']
            
            # Check if done
            if skills['pending'] == 0 and skills['processing'] == 0:
                # Render final dashboard
                print(CLEAR, end='')
                print(render(pipeline, skills, throughput, latency, batch_start, daemon_pid, 
                            instructions, skill_kpis, interaction_progress, recent_logs))
                print(f"{GREEN}  ✓ ALL SKILLS PROCESSED!{RESET}")
                break
            
            # Calculate elapsed and progress
            elapsed = time.time() - start_time
            elapsed_str = f"{int(elapsed//3600)}h {int((elapsed%3600)//60)}m"
            skills_processed = initial_pending - skills['pending']
            
            # Render dashboard
            print(CLEAR, end='')
            print(render(pipeline, skills, throughput, latency, batch_start, daemon_pid, 
                        instructions, skill_kpis, interaction_progress, recent_logs))
            print(f"{YELLOW}  ⏳ Running until done | Elapsed: {elapsed_str} | Processed: {skills_processed}/{initial_pending} | Ctrl+C to stop{RESET}")
            
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        elapsed_str = f"{int(elapsed//3600)}h {int((elapsed%3600)//60)}m"
        print(f"\n{YELLOW}Stopped early after {elapsed_str}. Skills remaining: {skills['pending']} pending, {skills['processing']} processing.{RESET}")
    finally:
        conn.close()
    
    # Final summary
    elapsed = time.time() - start_time
    elapsed_str = f"{int(elapsed//3600)}h {int((elapsed%3600)//60)}m {int(elapsed%60)}s"
    print(f"\n{'═'*70}")
    print(f"  {GREEN}COMPLETION SUMMARY{RESET}")
    print(f"{'═'*70}")
    print(f"  Total time: {elapsed_str}")
    print(f"  Skills processed: {initial_pending - skills['pending'] if initial_pending else 'N/A'}")
    print(f"  Final status: Done={skills['done']} Processing={skills['processing']} Pending={skills['pending']}")
    print(f"{'═'*70}\n")


def run_cycle(duration_minutes=5):
    """Run dashboard for N minutes then exit for review."""
    print(f"{GREEN}Starting {duration_minutes}-minute monitoring cycle...{RESET}")
    print(f"{DIM}Dashboard will exit after {duration_minutes}m for review.{RESET}\n")
    
    conn = get_conn()
    cur = conn.cursor()
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    snapshots = []
    
    try:
        while time.time() < end_time:
            # Collect current state
            pipeline = get_pipeline_status(cur)
            skills = get_skill_progress(cur)
            throughput = get_throughput(cur)
            latency = get_latency(cur)
            batch_start = get_batch_start(cur)
            daemon_pid = get_daemon_pid()
            instructions = get_instruction_breakdown(cur)
            skill_kpis = get_skill_kpis(cur)
            interaction_progress = get_interaction_progress(cur)
            recent_logs = get_recent_logs(5)
            
            # Store snapshot for analysis
            snapshots.append({
                'time': datetime.now(),
                'throughput_5m': throughput['count_5m'],
                'running': pipeline['total_running'],
                'pending': pipeline['total_pending'],
                'interactions_remaining': interaction_progress['pending'] + interaction_progress['running'],
                'skills_done': skills['done'],
            })
            
            # Calculate time remaining
            elapsed = time.time() - start_time
            remaining = max(0, (duration_minutes * 60) - elapsed)
            remaining_str = f"{int(remaining//60)}m {int(remaining%60)}s"
            
            # Render dashboard
            print(CLEAR, end='')
            print(render(pipeline, skills, throughput, latency, batch_start, daemon_pid, 
                        instructions, skill_kpis, interaction_progress, recent_logs))
            print(f"{YELLOW}  ⏱ Cycle ends in {remaining_str} | Ctrl+C to end early{RESET}")
            
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Cycle ended early by user.{RESET}")
    finally:
        conn.close()
    
    # Analyze the cycle
    print(f"\n{'═'*70}")
    print(f"  CYCLE SUMMARY ({duration_minutes}m)")
    print(f"{'═'*70}")
    
    if len(snapshots) >= 2:
        first, last = snapshots[0], snapshots[-1]
        
        # Progress metrics
        interactions_processed = first['interactions_remaining'] - last['interactions_remaining']
        skills_completed = last['skills_done'] - first['skills_done']
        avg_throughput = sum(s['throughput_5m'] for s in snapshots) / len(snapshots)
        
        print(f"  Interactions processed: {GREEN}{interactions_processed:+d}{RESET}")
        print(f"  Skills completed: {GREEN}{skills_completed:+d}{RESET}")
        print(f"  Avg throughput (5m window): {avg_throughput:.1f}")
        print(f"  Remaining interactions: {last['interactions_remaining']}")
        
        # Anomaly detection
        anomalies = []
        
        if interactions_processed <= 0 and first['pending'] > 0:
            anomalies.append("⚠ Zero progress with pending work")
        
        if last['running'] == 0 and last['pending'] > 0:
            anomalies.append("⚠ No running interactions despite queue")
        
        zero_throughput_count = sum(1 for s in snapshots if s['throughput_5m'] == 0)
        if zero_throughput_count > len(snapshots) // 2:
            anomalies.append(f"⚠ Low activity ({zero_throughput_count}/{len(snapshots)} samples had 0 throughput)")
        
        if anomalies:
            print(f"\n  {RED}ANOMALIES DETECTED:{RESET}")
            for a in anomalies:
                print(f"    {RED}{a}{RESET}")
        else:
            print(f"\n  {GREEN}✓ No anomalies detected{RESET}")
    
    print(f"{'═'*70}")
    print(f"\n{DIM}Review complete. Run again with: python scripts/turing.py --cycle{RESET}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Turing Workflow Engine')
    parser.add_argument('--status', '-s', action='store_true', help='Show status and exit')
    parser.add_argument('--kill', '-k', action='store_true', help='Stop daemon')
    parser.add_argument('--cycle', '-c', type=int, nargs='?', const=5, metavar='MIN',
                        help='Run for N minutes then exit for review (default: 5)')
    parser.add_argument('--until-done', '-u', action='store_true',
                        help='Run until all pending skills are processed')
    args = parser.parse_args()
    
    if args.kill:
        stop_daemon()
        print(f"{GREEN}Daemon stopped.{RESET}")
    elif args.status:
        show_status()
    elif args.until_done:
        run_until_done()
    elif args.cycle:
        run_cycle(args.cycle)
    else:
        run_monitor()


if __name__ == '__main__':
    main()
