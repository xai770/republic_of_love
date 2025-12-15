#!/usr/bin/env python3
"""
Workflow Health Check - Run via cron every 5 minutes.

Monitors workflow health and detects stuck/dead processes.
Based on Sandy's proposal, approved by Arden (2025-11-30).

Checks:
  1. No interactions completed in 30 min → Runner may be dead
  2. Ollama unresponsive for 15 min → Model crashed/hung
  3. 3+ consecutive failures → Systematic bug
  4. GPU < 5% for 5 min → No AI work happening
  5. Interactions stuck in 'running' > 10 min → Timeout not working
  6. Disk space < 1GB → Logs filling up

Usage:
    python3 scripts/health_check.py           # Check only, report issues
    python3 scripts/health_check.py --fix     # Auto-fix recoverable issues
    python3 scripts/health_check.py --quiet   # Only output if issues found
    
Cron entry (every 5 minutes):
    */5 * * * * cd /home/xai/Documents/ty_wave && python3 scripts/health_check.py >> logs/health.log 2>&1

Author: Sandy (ℶ)
Date: 2025-11-30
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

# Thresholds (approved by Arden)
NO_PROGRESS_THRESHOLD_MIN = 30
OLLAMA_TIMEOUT_MIN = 15
CONSECUTIVE_FAILURES_THRESHOLD = 3
LOW_GPU_THRESHOLD_PCT = 5
STUCK_RUNNING_THRESHOLD_MIN = 10
DISK_SPACE_THRESHOLD_GB = 1


def get_db_connection():
    """Get database connection from environment."""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )


def check_interactions_progress(conn) -> List[str]:
    """Alert if no completions in 30 minutes."""
    issues = []
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check for any completions in the last 30 minutes
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM interactions
        WHERE status = 'completed'
          AND updated_at > NOW() - INTERVAL '%s minutes'
    """, (NO_PROGRESS_THRESHOLD_MIN,))
    
    result = cursor.fetchone()
    
    # Also check if there's pending work
    cursor.execute("""
        SELECT COUNT(*) as pending
        FROM interactions
        WHERE status = 'pending'
    """)
    pending = cursor.fetchone()['pending']
    
    if result['count'] == 0 and pending > 0:
        issues.append(f"⚠️  NO PROGRESS: No interactions completed in {NO_PROGRESS_THRESHOLD_MIN} min ({pending} pending)")
    
    return issues


def check_ollama_responsive() -> List[str]:
    """Alert if Ollama API not responding."""
    issues = []
    
    try:
        result = subprocess.run(
            ['curl', '-s', '-m', '5', 'http://localhost:11434/api/tags'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            issues.append(f"⚠️  OLLAMA DOWN: API not responding (curl failed)")
        elif 'models' not in result.stdout and 'error' in result.stdout.lower():
            issues.append(f"⚠️  OLLAMA ERROR: {result.stdout[:100]}")
            
    except subprocess.TimeoutExpired:
        issues.append(f"⚠️  OLLAMA TIMEOUT: API did not respond within 10 seconds")
    except Exception as e:
        issues.append(f"⚠️  OLLAMA CHECK FAILED: {e}")
    
    return issues


def check_consecutive_failures(conn) -> List[str]:
    """Alert if 3+ failures in a row."""
    issues = []
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get the last N interactions ordered by completion time
    cursor.execute("""
        SELECT status
        FROM interactions
        WHERE status IN ('completed', 'failed')
          AND updated_at > NOW() - INTERVAL '1 hour'
        ORDER BY updated_at DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    
    if results:
        # Count consecutive failures from the most recent
        consecutive_failures = 0
        for row in results:
            if row['status'] == 'failed':
                consecutive_failures += 1
            else:
                break
        
        if consecutive_failures >= CONSECUTIVE_FAILURES_THRESHOLD:
            issues.append(f"⚠️  FAILURE STREAK: {consecutive_failures} consecutive failures")
    
    return issues


def check_gpu_utilization() -> List[str]:
    """Alert if GPU < 5% (runner may be dead while pending work exists)."""
    issues = []
    
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            gpu_pct = int(result.stdout.strip().split()[0])
            
            # Only warn if GPU is low - we need to correlate with pending work
            if gpu_pct < LOW_GPU_THRESHOLD_PCT:
                # Check if there's pending work
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM interactions WHERE status = 'pending'")
                pending = cursor.fetchone()[0]
                conn.close()
                
                if pending > 0:
                    issues.append(f"⚠️  LOW GPU: {gpu_pct}% utilization with {pending} pending interactions")
                    
    except Exception as e:
        # Don't fail if nvidia-smi not available
        pass
    
    return issues


def check_stuck_running(conn, fix: bool = False) -> List[str]:
    """Mark interactions stuck in 'running' > 10min as failed."""
    issues = []
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT interaction_id, conversation_id, created_at,
               EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as stuck_minutes
        FROM interactions
        WHERE status = 'running'
          AND updated_at < NOW() - INTERVAL '%s minutes'
    """, (STUCK_RUNNING_THRESHOLD_MIN,))
    
    stuck = cursor.fetchall()
    
    if stuck:
        ids = [row['interaction_id'] for row in stuck]
        
        if fix:
            # Mark as failed so they can be retried
            cursor.execute("""
                UPDATE interactions
                SET status = 'failed',
                    output = jsonb_build_object(
                        'error', 'Health check: stuck in running state',
                        'stuck_at', NOW()
                    )
                WHERE interaction_id = ANY(%s)
            """, (ids,))
            conn.commit()
            issues.append(f"🔧 FIXED: Marked {len(stuck)} stuck interactions as failed: {ids}")
        else:
            issues.append(f"⚠️  STUCK RUNNING: {len(stuck)} interactions stuck > {STUCK_RUNNING_THRESHOLD_MIN} min: {ids}")
    
    return issues


def check_disk_space() -> List[str]:
    """Alert if < 1GB free on workspace partition."""
    issues = []
    
    try:
        result = subprocess.run(
            ['df', '-BG', '/home/xai/Documents/ty_wave'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                # Parse: Filesystem Size Used Avail Use% Mounted
                parts = lines[1].split()
                if len(parts) >= 4:
                    avail_gb = int(parts[3].replace('G', ''))
                    if avail_gb < DISK_SPACE_THRESHOLD_GB:
                        issues.append(f"⚠️  LOW DISK: Only {avail_gb}GB free")
                        
    except Exception as e:
        pass
    
    return issues


def check_runner_process() -> Tuple[bool, str]:
    """Check if a workflow runner process is active."""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        runners = []
        for line in result.stdout.split('\n'):
            # Skip health check itself
            if 'health_check' in line:
                continue
            # Look for wave-related Python processes
            if 'python' in line.lower():
                if any(x in line for x in ['run_batch', 'run_workflow', 'WaveRunner', 'wave_runner']):
                    parts = line.split()
                    if len(parts) > 1:
                        runners.append(parts[1])  # PID
        
        if runners:
            return True, f"PIDs: {', '.join(runners)}"
        
        return False, "No runner found"
        
    except Exception as e:
        return False, f"Error: {e}"


def send_notification(message: str):
    """Send desktop notification (if available)."""
    try:
        subprocess.run(
            ['notify-send', '-u', 'critical', 'Workflow Health Alert', message],
            timeout=5
        )
    except:
        pass  # Notification not critical


def main():
    parser = argparse.ArgumentParser(description='Workflow health check')
    parser.add_argument('--fix', action='store_true', help='Auto-fix recoverable issues')
    parser.add_argument('--quiet', action='store_true', help='Only output if issues found')
    parser.add_argument('--notify', action='store_true', help='Send desktop notification on issues')
    args = parser.parse_args()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_interactions_progress(conn))
    all_issues.extend(check_ollama_responsive())
    all_issues.extend(check_consecutive_failures(conn))
    all_issues.extend(check_gpu_utilization())
    all_issues.extend(check_stuck_running(conn, fix=args.fix))
    all_issues.extend(check_disk_space())
    
    # Check runner status (informational)
    runner_active, runner_info = check_runner_process()
    
    conn.close()
    
    # Output
    if all_issues:
        print(f"\n🏥 HEALTH CHECK [{timestamp}] - {len(all_issues)} issue(s)")
        print("-" * 50)
        for issue in all_issues:
            print(f"  {issue}")
        print(f"\n  Runner: {'✅ ' + runner_info if runner_active else '❌ ' + runner_info}")
        
        if args.notify:
            send_notification('\n'.join(all_issues))
            
    elif not args.quiet:
        print(f"✅ HEALTH CHECK [{timestamp}] - All healthy")
        print(f"   Runner: {'✅ ' + runner_info if runner_active else '⚪ ' + runner_info}")
    
    # Exit code: 0 if healthy, 1 if issues
    sys.exit(0 if not all_issues else 1)


if __name__ == '__main__':
    main()
