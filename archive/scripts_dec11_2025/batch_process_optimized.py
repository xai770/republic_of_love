#!/usr/bin/env python3
"""
Batch Process Jobs - Optimized with Parallel Execution
========================================================

Improvements over original:
1. Parallel processing (5 workers by default)
2. Wave batching integration (7-8x speedup)
3. Resource monitoring (GPU, DB connections, memory)
4. Better error recovery
5. Staged rollout option

Author: Sandy
Date: November 26, 2025
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection
import time
import argparse
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class ResourceMonitor:
    """Monitor system resources during batch processing."""
    
    @staticmethod
    def check_database_connections(conn) -> Dict[str, any]:
        """Check PostgreSQL connection pool status."""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_connections,
                    SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN state = 'idle' THEN 1 ELSE 0 END) as idle
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            total, active, idle = cursor.fetchone()
            return {
                'total': total or 0,
                'active': active or 0,
                'idle': idle or 0
            }
        except Exception as e:
            # Fallback if query fails
            return {'total': 1, 'active': 1, 'idle': 0, 'error': str(e)}
    
    @staticmethod
    def check_gpu_status() -> Optional[Dict[str, any]]:
        """Check GPU utilization (if nvidia-smi available)."""
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                gpu_util, mem_used, mem_total = result.stdout.strip().split(',')
                return {
                    'utilization': int(gpu_util),
                    'memory_used_mb': int(mem_used),
                    'memory_total_mb': int(mem_total),
                    'memory_pct': int(mem_used) / int(mem_total) * 100
                }
        except:
            pass
        return None
    
    @staticmethod
    def check_memory_usage() -> Dict[str, float]:
        """Check system memory usage."""
        mem = psutil.virtual_memory()
        return {
            'total_gb': mem.total / (1024**3),
            'available_gb': mem.available / (1024**3),
            'percent_used': mem.percent
        }


def process_single_posting(posting_id: int, workflow_id: int = 3001) -> Dict[str, any]:
    """
    Process a single posting through the workflow.
    
    Thread-safe - each thread gets its own database connection.
    
    Returns:
        Result dict with status, duration, workflow_run_id
    """
    conn = get_connection()
    start_time = time.time()
    
    try:
        # Start workflow
        result = start_workflow(
            conn,
            workflow_id=workflow_id,
            posting_id=posting_id
        )
        
        workflow_run_id = result['workflow_run_id']
        
        # Run workflow with wave batching enabled
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        wave_result = runner.run(max_iterations=100)
        
        duration = time.time() - start_time
        
        # Check if rejected at validation
        cursor = conn.cursor()
        cursor.execute("""
            SELECT output
            FROM interactions
            WHERE workflow_run_id = %s AND conversation_id = 9193
        """, (workflow_run_id,))
        
        validation_result = cursor.fetchone()
        if validation_result:
            output = validation_result[0]
            if '[NO_DESCRIPTION]' in str(output) or '[TOO_SHORT]' in str(output):
                return {
                    'posting_id': posting_id,
                    'status': 'rejected',
                    'reason': 'validation_failed',
                    'duration': duration,
                    'workflow_run_id': workflow_run_id
                }
        
        # Check completion status
        if wave_result['interactions_failed'] > 0:
            return {
                'posting_id': posting_id,
                'status': 'failed',
                'reason': 'interaction_failed',
                'duration': duration,
                'workflow_run_id': workflow_run_id,
                'failed_count': wave_result['interactions_failed']
            }
        
        return {
            'posting_id': posting_id,
            'status': 'completed',
            'duration': duration,
            'workflow_run_id': workflow_run_id,
            'interactions': wave_result['interactions_completed']
        }
        
    except Exception as e:
        duration = time.time() - start_time
        return {
            'posting_id': posting_id,
            'status': 'error',
            'reason': str(e),
            'duration': duration
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Batch process jobs with parallel execution')
    parser.add_argument('--max-jobs', type=int, default=500, help='Maximum jobs to process')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers')
    parser.add_argument('--dry-run', action='store_true', help='Show plan without executing')
    parser.add_argument('--test-size', type=int, help='Test with N jobs first (staged rollout)')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("OPTIMIZED BATCH PROCESSOR - WITH WAVE BATCHING")
    print("=" * 80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Max jobs: {args.max_jobs}")
    print(f"Parallel workers: {args.workers}")
    print(f"Wave batching: ✅ ENABLED (7-8x speedup)")
    
    # Check resources
    print(f"\n{'='*80}")
    print("RESOURCE CHECK")
    print("=" * 80)
    
    conn = get_connection()
    
    db_status = ResourceMonitor.check_database_connections(conn)
    print(f"\n📊 Database Connections:")
    print(f"   Total: {db_status['total']}, Active: {db_status['active']}, Idle: {db_status['idle']}")
    
    gpu_status = ResourceMonitor.check_gpu_status()
    if gpu_status:
        print(f"\n🎮 GPU Status:")
        print(f"   Utilization: {gpu_status['utilization']}%")
        print(f"   Memory: {gpu_status['memory_used_mb']:.0f}MB / {gpu_status['memory_total_mb']:.0f}MB ({gpu_status['memory_pct']:.1f}%)")
    else:
        print(f"\n⚠️  GPU monitoring unavailable (nvidia-smi not found)")
    
    mem_status = ResourceMonitor.check_memory_usage()
    print(f"\n💾 System Memory:")
    print(f"   Available: {mem_status['available_gb']:.1f}GB / {mem_status['total_gb']:.1f}GB ({100-mem_status['percent_used']:.1f}% free)")
    
    # Get postings to process
    print(f"\n{'='*80}")
    print("FETCHING POSTINGS")
    print("=" * 80)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT posting_id 
        FROM postings 
        WHERE posting_id NOT IN (
            SELECT DISTINCT posting_id 
            FROM workflow_runs 
            WHERE workflow_id = 3001 AND status = 'completed'
        )
        AND job_description IS NOT NULL
        AND LENGTH(job_description) >= 100
        ORDER BY first_seen_at DESC
        LIMIT %s
    """, (args.max_jobs,))
    
    rows = cursor.fetchall()
    posting_ids = [row[0] if isinstance(row, tuple) else row['posting_id'] for row in rows]
    
    print(f"\nFound {len(posting_ids)} postings ready to process")
    
    if len(posting_ids) == 0:
        print("⚠️  No postings available. Run job fetcher first.")
        return 1
    
    # Test mode for staged rollout
    if args.test_size and args.test_size < len(posting_ids):
        print(f"\n🧪 TEST MODE: Processing first {args.test_size} postings")
        posting_ids = posting_ids[:args.test_size]
    
    if args.dry_run:
        print(f"\n[DRY RUN] Would process {len(posting_ids)} postings with {args.workers} workers")
        print(f"[DRY RUN] Estimated duration: {len(posting_ids) / args.workers * 4 / 60:.1f} minutes (with wave batching)")
        print(f"[DRY RUN] Without batching would take: {len(posting_ids) * 30 / 3600:.1f} hours")
        return 0
    
    # Process with parallel workers
    print(f"\n{'='*80}")
    print(f"PROCESSING {len(posting_ids)} POSTINGS ({args.workers} WORKERS)")
    print("=" * 80)
    
    stats = {
        'completed': 0,
        'rejected': 0,
        'failed': 0,
        'error': 0,
        'total_duration': 0
    }
    
    start_batch = time.time()
    durations = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_posting = {
            executor.submit(process_single_posting, posting_id): posting_id 
            for posting_id in posting_ids
        }
        
        # Process results as they complete
        for idx, future in enumerate(as_completed(future_to_posting), 1):
            result = future.result()
            posting_id = future_to_posting[future]
            
            # Update stats
            stats[result['status']] += 1
            durations.append(result['duration'])
            stats['total_duration'] += result['duration']
            
            # Print progress
            avg_duration = sum(durations) / len(durations)
            eta_seconds = (len(posting_ids) - idx) * avg_duration / args.workers
            eta = timedelta(seconds=int(eta_seconds))
            
            status_emoji = {
                'completed': '✅',
                'rejected': '⚠️',
                'failed': '❌',
                'error': '🔥'
            }.get(result['status'], '❓')
            
            print(f"\n[{idx}/{len(posting_ids)}] Posting {posting_id}: {status_emoji} {result['status'].upper()} ({result['duration']:.1f}s)")
            print(f"   Progress: {idx/len(posting_ids)*100:.1f}% | Avg: {avg_duration:.1f}s/job | ETA: {eta}")
            
            if result['status'] == 'completed':
                print(f"   Interactions: {result.get('interactions', '?')}")
            elif result['status'] in ['rejected', 'failed', 'error']:
                print(f"   Reason: {result.get('reason', 'unknown')}")
    
    # Final summary
    total_time = time.time() - start_batch
    
    print(f"\n{'='*80}")
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)
    
    print(f"\n📊 Results:")
    print(f"   ✅ Completed: {stats['completed']}")
    print(f"   ⚠️  Rejected (validation): {stats['rejected']}")
    print(f"   ❌ Failed: {stats['failed']}")
    print(f"   🔥 Errors: {stats['error']}")
    print(f"   📈 Success rate: {stats['completed']/(len(posting_ids))*100:.1f}%")
    
    print(f"\n⏱️  Performance:")
    print(f"   Total time: {timedelta(seconds=int(total_time))}")
    print(f"   Average per job: {stats['total_duration']/len(posting_ids):.1f}s")
    print(f"   Throughput: {len(posting_ids)/total_time*60:.1f} jobs/minute")
    
    print(f"\n🎉 Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
