#!/usr/bin/env python3
"""
watchdog_wf3007.py - Self-healing WF3007 monitor

Watches the workflow and automatically restarts if stuck.
Checks every 30 seconds. If no progress in 2 minutes, kills and restarts.

Usage:
    python tools/watchdog_wf3007.py
"""

import subprocess
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.database import get_connection_raw, return_connection
import psycopg2

def get_trace_count():
    """Get current trace count."""
    conn = get_connection_raw()
    cur = conn.cursor(cursor_factory=psycopg2.extensions.cursor)
    cur.execute("SELECT COUNT(*) FROM wf3007_traces WHERE phase = 'wf3007_turing'")
    count = cur.fetchone()[0]
    return_connection(conn)
    return count

def get_remaining():
    """Get remaining skills to process."""
    conn = get_connection_raw()
    cur = conn.cursor(cursor_factory=psycopg2.extensions.cursor)
    cur.execute("""
        SELECT COUNT(*) FROM v_orphan_skills vos 
        WHERE vos.canonical_name NOT LIKE 'atomic_skill_%' 
        AND NOT EXISTS (
            SELECT 1 FROM wf3007_traces t 
            WHERE t.verbose_skill_name = vos.canonical_name 
            AND t.phase = 'wf3007_turing'
        )
    """)
    count = cur.fetchone()[0]
    return_connection(conn)
    return count

def get_gpu_util():
    """Get GPU utilization."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        return int(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        return -1

def is_process_running():
    """Check if wf3007 process is running."""
    result = subprocess.run(['pgrep', '-f', 'run_wf3007'], capture_output=True)
    return result.returncode == 0

def kill_process():
    """Kill wf3007 process."""
    subprocess.run(['pkill', '-f', 'run_wf3007'], capture_output=True)
    time.sleep(2)

def start_process(runs):
    """Start wf3007 process."""
    log_file = f"/home/xai/Documents/ty_learn/logs/wf3007_watchdog_{datetime.now().strftime('%H%M%S')}.log"
    cmd = f"cd /home/xai/Documents/ty_learn && source venv/bin/activate && nohup /home/xai/Documents/ty_learn/venv/bin/python scripts/run_wf3007.py --runs {runs} > {log_file} 2>&1 &"
    subprocess.run(cmd, shell=True, executable='/bin/bash')
    time.sleep(3)

def main():
    print("=" * 50)
    print("  WF3007 Watchdog - Self-Healing Monitor")
    print("=" * 50)
    print("Checking every 30s. Auto-restart if stuck for 2min.")
    print("Press Ctrl+C to stop.\n")
    
    last_count = get_trace_count()
    last_progress_time = time.time()
    stuck_threshold = 120  # 2 minutes
    
    try:
        while True:
            now = datetime.now().strftime('%H:%M:%S')
            count = get_trace_count()
            remaining = get_remaining()
            gpu = get_gpu_util()
            running = is_process_running()
            
            # Check progress
            if count > last_count:
                last_count = count
                last_progress_time = time.time()
                status = "🟢 WORKING"
            elif running:
                stuck_for = int(time.time() - last_progress_time)
                if stuck_for > stuck_threshold:
                    status = f"🔴 STUCK ({stuck_for}s) - RESTARTING!"
                else:
                    status = f"🟡 IDLE ({stuck_for}s)"
            else:
                status = "🔴 STOPPED"
            
            # Print status
            rate = (count - last_count) / 30 if count > last_count else 0
            print(f"[{now}] {status}")
            print(f"  Traces: {count}/5846 ({100*count/5846:.1f}%) | Remaining: {remaining} | GPU: {gpu}%")
            
            # Check if done
            if remaining == 0:
                print("\n🎉 COMPLETE! All skills processed.")
                break
            
            # Auto-restart if stuck
            stuck_for = int(time.time() - last_progress_time)
            if stuck_for > stuck_threshold or not running:
                print(f"\n⚠️  {'Process died' if not running else 'Stuck for >2min'}. Restarting...")
                kill_process()
                start_process(remaining)
                last_progress_time = time.time()
                print(f"  ✅ Restarted with {remaining} remaining\n")
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\nWatchdog stopped. Process still running in background.")

if __name__ == '__main__':
    main()
