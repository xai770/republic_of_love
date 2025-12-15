#!/usr/bin/env python3
"""
Re-run specific failed jobs with verbose output for debugging
"""
import subprocess
import sys

FAILED_JOBS = ['59428', '64727']

def run_job_verbose(job_id):
    """Run a single job with full output for debugging"""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUGGING JOB {job_id}")
    print(f"{'='*80}\n")
    
    cmd = [
        'python3', 
        'scripts/by_recipe_runner.py',
        '--recipe-id', '1114',
        '--job-id', job_id,
        '--execution-mode', 'testing',  # Use testing to allow re-runs
        '--target-batch-count', '5'
    ]
    
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        # Run without capturing output so we see everything
        result = subprocess.run(cmd, timeout=600)
        
        print(f"\n{'='*80}")
        if result.returncode == 0:
            print(f"✅ Job {job_id} completed successfully")
        else:
            print(f"❌ Job {job_id} failed with exit code {result.returncode}")
        print(f"{'='*80}\n")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"\n❌ Job {job_id} timed out (>10 minutes)")
        return False
    except Exception as e:
        print(f"\n❌ Job {job_id} exception: {e}")
        return False

def main():
    print("🔧 Re-running failed jobs with verbose output")
    print("="*80)
    print(f"Jobs to retry: {', '.join(FAILED_JOBS)}")
    print("="*80)
    
    results = {}
    for job_id in FAILED_JOBS:
        results[job_id] = run_job_verbose(job_id)
    
    # Summary
    print("\n" + "="*80)
    print("📊 RETRY SUMMARY")
    print("="*80)
    
    for job_id, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"Job {job_id}: {status}")
    
    success_count = sum(1 for s in results.values() if s)
    print(f"\nTotal: {success_count}/{len(FAILED_JOBS)} succeeded")
    print("="*80)

if __name__ == "__main__":
    main()
