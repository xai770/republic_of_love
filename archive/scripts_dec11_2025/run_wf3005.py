#!/usr/bin/env python3
"""
WF3005 - Skill Registry Maintenance Runner

Properly starts WF3005 by:
1. Creating seed interaction via start_workflow()
2. Running WaveRunner to process all steps

Usage:
    python3 scripts/run_wf3005.py           # One run
    python3 scripts/run_wf3005.py --runs 3  # Three consecutive runs
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
import time
from datetime import datetime
from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection


def run_wf3005_once(run_number: int = 1):
    """Run WF3005 once."""
    conn = get_connection()
    
    try:
        print(f"\n{'='*70}")
        print(f"🚀 WF3005 Run #{run_number} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        
        # Start workflow with seed interaction
        result = start_workflow(
            conn,
            workflow_id=3005,
            posting_id=None  # No posting - this is entity workflow
        )
        
        print(f"   Workflow run ID: {result['workflow_run_id']}")
        print(f"   Seed interaction: {result['seed_interaction_id']}")
        print(f"   First step: {result['first_conversation_name']}")
        
        # Run Wave Runner
        runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
        wave_result = runner.run(max_iterations=100)
        
        print(f"\n✅ Run #{run_number} Complete!")
        print(f"   Interactions: {wave_result['interactions_completed']} completed, {wave_result['interactions_failed']} failed")
        print(f"   Duration: {wave_result['duration_ms']/1000:.1f}s")
        
        return {
            'run_number': run_number,
            'workflow_run_id': result['workflow_run_id'],
            'completed': wave_result['interactions_completed'],
            'failed': wave_result['interactions_failed'],
            'duration_ms': wave_result['duration_ms']
        }
        
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Run WF3005 Skill Registry Maintenance')
    parser.add_argument('--runs', type=int, default=1, help='Number of consecutive runs')
    args = parser.parse_args()
    
    print("="*70)
    print("WF3005 - SKILL REGISTRY MAINTENANCE")
    print(f"Planned runs: {args.runs}")
    print("="*70)
    
    results = []
    start_time = time.time()
    
    for i in range(args.runs):
        try:
            result = run_wf3005_once(run_number=i+1)
            results.append(result)
            
            # Short pause between runs
            if i < args.runs - 1:
                print("\n⏳ Pausing 2s before next run...")
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Error on run {i+1}: {e}")
            results.append({'run_number': i+1, 'error': str(e)})
    
    total_duration = time.time() - start_time
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total time: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"Successful runs: {sum(1 for r in results if 'error' not in r)}/{args.runs}")
    
    print("\nRun Details:")
    for r in results:
        if 'error' in r:
            print(f"  Run {r['run_number']}: ❌ {r['error']}")
        else:
            print(f"  Run {r['run_number']}: ✅ WR={r['workflow_run_id']}, {r['completed']} interactions, {r['duration_ms']/1000:.1f}s")


if __name__ == '__main__':
    main()
