#!/usr/bin/env python3
"""
monitor_alive.py - Is Turing Actually Working?

Quick system health check. Shows:
1. Is there an active process?
2. Is the GPU doing anything?
3. Are tickets being created?
4. What's the recent throughput?

Usage:
    python tools/monitor_alive.py          # One-shot check
    python tools/monitor_alive.py --watch  # Continuous monitoring
"""

import subprocess
import sys
import time
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_gpu_utilization():
    """Get current GPU utilization percentage."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,power.draw', 
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            return {
                'gpu_util': int(parts[0]),
                'mem_used': int(parts[1]),
                'mem_total': int(parts[2]),
                'power_w': float(parts[3])
            }
    except Exception:
        pass
    return None

def get_process_status():
    """Check if workflow processes are running."""
    try:
        result = subprocess.run(
            ['pgrep', '-af', 'python.*wf3007|python.*wave|python.*turing'],
            capture_output=True, text=True, timeout=5
        )
        processes = [line for line in result.stdout.strip().split('\n') if line]
        return processes
    except Exception:
        return []

def get_db_stats():
    """Get recent activity from database."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from core.database import get_connection_raw, return_connection
        import psycopg2
        conn = get_connection_raw()
        # Use regular cursor (not RealDictCursor) for tuple access
        cur = conn.cursor(cursor_factory=psycopg2.extensions.cursor)
        
        # Recent tickets (last 5 minutes)
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '5 minutes') as last_5min,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 minute') as last_1min,
                MAX(created_at) as last_ticket
            FROM tickets
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        row = cur.fetchone()
        tickets = {
            'last_5min': row[0],
            'last_1min': row[1],
            'last_time': row[2]
        }
        
        # WF3007 specific progress
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE extracted_atomics != '{NONE}') as extracted
            FROM wf3007_traces 
            WHERE phase = 'wf3007_turing'
        """)
        row = cur.fetchone()
        wf3007 = {'total': row[0], 'extracted': row[1]}
        
        # Remaining skills
        cur.execute("""
            SELECT COUNT(*) FROM v_orphan_skills vos 
            WHERE vos.canonical_name NOT LIKE 'atomic_skill_%' 
            AND NOT EXISTS (
                SELECT 1 FROM wf3007_traces t 
                WHERE t.verbose_skill_name = vos.canonical_name 
                AND t.phase = 'wf3007_turing'
            )
        """)
        remaining = cur.fetchone()[0]
        
        # Recent LLM latency
        cur.execute("""
            SELECT ROUND(AVG((output->>'latency_ms')::numeric)) as avg_latency
            FROM tickets 
            WHERE task_type_id = 9272 
            AND status = 'completed'
            AND created_at > NOW() - INTERVAL '5 minutes'
        """)
        latency = cur.fetchone()[0]
        
        return_connection(conn)
        return {
            'tickets': tickets,
            'wf3007': wf3007,
            'remaining': remaining,
            'latency_ms': latency
        }
    except Exception as e:
        return {'error': str(e)}

def print_status():
    """Print current system status."""
    now = datetime.now().strftime('%H:%M:%S')
    
    # GPU
    gpu = get_gpu_utilization()
    if gpu:
        gpu_status = f"GPU: {gpu['gpu_util']:3d}% | {gpu['mem_used']}/{gpu['mem_total']}MB | {gpu['power_w']:.0f}W"
        gpu_working = gpu['gpu_util'] > 5
    else:
        gpu_status = "GPU: unavailable"
        gpu_working = None
    
    # Processes
    procs = get_process_status()
    proc_status = f"Processes: {len(procs)}"
    
    # Database
    db = get_db_stats()
    if 'error' in db:
        db_status = f"DB Error: {db['error']}"
        db_working = False
    else:
        tickets = db['tickets']
        wf = db['wf3007']
        
        # Check if anything happened in last minute
        db_working = tickets['last_1min'] > 0
        
        if tickets['last_time']:
            ago = (datetime.now() - tickets['last_time'].replace(tzinfo=None)).total_seconds()
            time_ago = f"{int(ago)}s ago"
        else:
            time_ago = "never"
            
        db_status = f"Last: {time_ago} | 5min: {tickets['last_5min']} | WF3007: {wf['total']}/{wf['total']+db['remaining']} ({wf['extracted']} extracted)"
        
        if db['latency_ms']:
            db_status += f" | {db['latency_ms']}ms"
    
    # Overall status
    if gpu_working and db_working:
        status = "🟢 WORKING"
    elif gpu_working or db_working:
        status = "🟡 PARTIAL"
    elif len(procs) > 0:
        status = "🟡 PROCESS ALIVE (but idle)"
    else:
        status = "🔴 STOPPED"
    
    # Print
    print(f"\n[{now}] {status}")
    print(f"  {gpu_status}")
    print(f"  {proc_status}")
    print(f"  {db_status}")
    
    return gpu_working or db_working

def main():
    watch_mode = '--watch' in sys.argv or '-w' in sys.argv
    
    print("=" * 60)
    print("  Turing System Monitor")
    print("=" * 60)
    
    if watch_mode:
        print("Press Ctrl+C to stop")
        try:
            while True:
                print_status()
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        is_working = print_status()
        print()
        if not is_working:
            print("💡 To restart WF3007:")
            db = get_db_stats()
            if 'remaining' in db:
                print(f"   python scripts/run_wf3007.py --runs {db['remaining']}")

if __name__ == '__main__':
    main()
