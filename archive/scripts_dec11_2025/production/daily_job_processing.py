#!/usr/bin/env python3
"""
Daily Job Processing Pipeline
==============================
Runs the complete job processing workflow:
1. Fetch new jobs from API (Workflow 3001)
2. Discover pending jobs
3. Process each job: extract skills + save (Workflow 1121)

Usage:
    python3 scripts/daily_job_processing.py [--dry-run] [--max-jobs N]
"""

import sys
import os
import time
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow_executor import WorkflowExecutor
from core.turing_orchestrator import TuringOrchestrator
from core.database import get_connection


def print_banner(text):
    """Print a formatted banner"""
    print()
    print('═' * 80)
    print(f'  {text}')
    print('═' * 80)
    print()


def step_1_fetch_jobs(dry_run=False):
    """Step 1: Fetch new jobs from API"""
    print_banner('STEP 1: FETCH NEW JOBS')
    
    if dry_run:
        print('🔍 DRY RUN: Would execute Workflow 3001 (Job Fetch)')
        return {'status': 'skipped', 'jobs_fetched': 0}
    
    executor = WorkflowExecutor()
    start = time.time()
    
    print('🚀 Executing Workflow 3001: Daily Job Fetch...')
    result = executor.execute_workflow(3001, {})
    elapsed = time.time() - start
    
    print(f'✅ Fetch completed in {elapsed:.1f}s')
    print(f'   Status: {result["status"]}')
    
    # Parse output to get job count
    # The fetch script outputs JSON with jobs_fetched count
    return result


def step_2_discover_pending(dry_run=False):
    """Step 2: Discover pending jobs"""
    print_banner('STEP 2: DISCOVER PENDING JOBS')
    
    orchestrator = TuringOrchestrator(verbose=False)
    pending = orchestrator.discover_pending_tasks()
    
    print(f'📋 Found {len(pending)} pending jobs:')
    for task in pending[:10]:  # Show first 10
        print(f'   • {task}')
    
    if len(pending) > 10:
        print(f'   ... and {len(pending) - 10} more')
    
    return pending


def step_3_process_jobs(max_jobs=None, dry_run=False):
    """Step 3: Process pending jobs"""
    print_banner('STEP 3: PROCESS JOBS (Extract + Save Skills)')
    
    if dry_run:
        print(f'🔍 DRY RUN: Would process up to {max_jobs or "all"} jobs')
        return {'tasks_processed': 0, 'success_count': 0}
    
    orchestrator = TuringOrchestrator(verbose=False)
    start = time.time()
    
    print(f'🚀 Processing jobs (max: {max_jobs or "unlimited"})...')
    results = orchestrator.process_pending_tasks(
        max_tasks=max_jobs or 1000, 
        dry_run=False
    )
    elapsed = time.time() - start
    
    print()
    print(f'✅ Processing completed in {elapsed:.1f}s ({elapsed/60:.1f} min)')
    print(f'   Jobs processed: {results["tasks_processed"]}')
    print(f'   Successful: {results["success_count"]}')
    print(f'   Failed: {results["tasks_processed"] - results["success_count"]}')
    print(f'   Success rate: {100*results["success_count"]//max(results["tasks_processed"],1)}%')
    print(f'   Avg time per job: {elapsed/max(results["tasks_processed"],1):.1f}s')
    
    return results


def get_database_stats():
    """Get current database statistics"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_jobs,
            COUNT(CASE WHEN posting_status = 'active' THEN 1 END) as active_jobs,
            COUNT(job_description) as has_description
        FROM postings
    """)
    posting_stats = cur.fetchone()
    
    cur.execute("""
        SELECT 
            COUNT(DISTINCT posting_id) as jobs_with_skills,
            COUNT(*) as total_skills
        FROM job_skills
        WHERE extracted_by = 'workflow_2001'
    """)
    skill_stats = cur.fetchone()
    
    return {
        'total_jobs': posting_stats['total_jobs'],
        'active_jobs': posting_stats['active_jobs'],
        'has_description': posting_stats['has_description'],
        'jobs_with_skills': skill_stats['jobs_with_skills'],
        'total_skills': skill_stats['total_skills']
    }


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Run daily job processing pipeline')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--max-jobs', type=int, help='Maximum number of jobs to process')
    parser.add_argument('--skip-fetch', action='store_true', help='Skip job fetching step')
    
    args = parser.parse_args()
    
    # Print header
    print()
    print('╔' + '═' * 78 + '╗')
    print('║' + '  DAILY JOB PROCESSING PIPELINE'.center(78) + '║')
    print('║' + f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'.center(78) + '║')
    print('╚' + '═' * 78 + '╝')
    
    if args.dry_run:
        print()
        print('🔍 DRY RUN MODE - No changes will be made')
    
    # Get initial stats
    print_banner('INITIAL DATABASE STATUS')
    initial_stats = get_database_stats()
    print(f'   Total jobs: {initial_stats["total_jobs"]}')
    print(f'   Active jobs: {initial_stats["active_jobs"]}')
    print(f'   Jobs with descriptions: {initial_stats["has_description"]}')
    print(f'   Jobs with skills: {initial_stats["jobs_with_skills"]}')
    print(f'   Total skills saved: {initial_stats["total_skills"]}')
    
    # Execute pipeline
    overall_start = time.time()
    
    try:
        # Step 1: Fetch jobs
        if not args.skip_fetch:
            fetch_result = step_1_fetch_jobs(dry_run=args.dry_run)
        else:
            print_banner('STEP 1: FETCH (SKIPPED)')
        
        # Step 2: Discover pending
        pending = step_2_discover_pending(dry_run=args.dry_run)
        
        # Step 3: Process jobs
        if len(pending) > 0 or args.dry_run:
            process_result = step_3_process_jobs(
                max_jobs=args.max_jobs, 
                dry_run=args.dry_run
            )
        else:
            print_banner('STEP 3: PROCESS (SKIPPED - No pending jobs)')
            process_result = {'tasks_processed': 0, 'success_count': 0}
        
        # Get final stats
        print_banner('FINAL DATABASE STATUS')
        final_stats = get_database_stats()
        print(f'   Total jobs: {final_stats["total_jobs"]} (+{final_stats["total_jobs"] - initial_stats["total_jobs"]})')
        print(f'   Active jobs: {final_stats["active_jobs"]} (+{final_stats["active_jobs"] - initial_stats["active_jobs"]})')
        print(f'   Jobs with skills: {final_stats["jobs_with_skills"]} (+{final_stats["jobs_with_skills"] - initial_stats["jobs_with_skills"]})')
        print(f'   Total skills saved: {final_stats["total_skills"]} (+{final_stats["total_skills"] - initial_stats["total_skills"]})')
        
        # Summary
        overall_elapsed = time.time() - overall_start
        print()
        print('╔' + '═' * 78 + '╗')
        print('║' + '  PIPELINE COMPLETE'.center(78) + '║')
        print('╚' + '═' * 78 + '╝')
        print()
        print(f'   Total time: {overall_elapsed:.1f}s ({overall_elapsed/60:.1f} min)')
        if not args.dry_run and 'tasks_processed' in process_result:
            print(f'   Jobs processed: {process_result["tasks_processed"]}')
            print(f'   Success rate: {100*process_result["success_count"]//max(process_result["tasks_processed"],1) if process_result["tasks_processed"] > 0 else 0}%')
        print()
        print('✅ Pipeline completed successfully!')
        print()
        
    except Exception as e:
        print()
        print('❌ ERROR:', str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
