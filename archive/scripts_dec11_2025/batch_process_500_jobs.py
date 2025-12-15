#!/usr/bin/env python3
"""
Batch Process 500 Jobs - Workflow 3001
========================================

This script fetches and processes up to 500 jobs through the complete pipeline:
1. Fetch from Deutsche Bank API (with validation filters)
2. Validate job description quality (defense-in-depth layer 2)
3. Extract summary
4. Grade (dual graders in parallel)
5. Improve if needed
6. Create ticket if issues found
7. Format standardization
8. Save to database
9. Extract skills
10. IHL analysis (Analyst → Skeptic → HR Expert)

Features:
- Defense-in-depth validation (job fetcher + validation conversation)
- Progress tracking with ETA
- Checkpoint recovery (resume from crashes)
- Statistics reporting
- Resource monitoring

Usage:
    # Fetch and process up to 500 jobs
    python3 scripts/batch_process_500_jobs.py
    
    # Resume from crash
    python3 scripts/batch_process_500_jobs.py --resume
    
    # Dry run (show what would happen)
    python3 scripts/batch_process_500_jobs.py --dry-run

Expected Duration:
    - ~3-4 hours for 500 jobs (assuming 80-90% valid)
    - Invalid jobs stop at validation (0.3s vs 30s)

Author: Arden (for review by Sandy)
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
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class BatchProcessor:
    """Batch process multiple jobs through Workflow 3001."""
    
    def __init__(self, max_jobs: int = 500, dry_run: bool = False, resume: bool = False):
        """
        Initialize batch processor.
        
        Args:
            max_jobs: Maximum number of jobs to fetch/process
            dry_run: If True, show plan but don't execute
            resume: If True, resume from incomplete workflow runs
        """
        self.max_jobs = max_jobs
        self.dry_run = dry_run
        self.resume = resume
        self.conn = get_connection()
        
        # Statistics
        self.stats = {
            'jobs_fetched': 0,
            'jobs_validated': 0,
            'jobs_rejected': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'total_duration': 0,
            'avg_duration_per_job': 0
        }
        
    def get_incomplete_runs(self) -> List[int]:
        """Find workflow runs that didn't complete."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT workflow_run_id, posting_id, started_at
            FROM workflow_runs
            WHERE workflow_id = 3001
              AND status = 'running'
              AND started_at > NOW() - INTERVAL '24 hours'
            ORDER BY started_at DESC
        """)
        
        runs = cursor.fetchall()
        return [{'workflow_run_id': r[0], 'posting_id': r[1], 'started_at': r[2]} for r in runs]
    
    def resume_incomplete_runs(self):
        """Resume processing from incomplete runs."""
        incomplete = self.get_incomplete_runs()
        
        if not incomplete:
            print("✅ No incomplete runs found")
            return
        
        print(f"\n{'='*80}")
        print(f"RESUMING {len(incomplete)} INCOMPLETE RUNS")
        print(f"{'='*80}\n")
        
        for idx, run in enumerate(incomplete, 1):
            print(f"[{idx}/{len(incomplete)}] Resuming run {run['workflow_run_id']} (posting {run['posting_id']})")
            
            if self.dry_run:
                print(f"  [DRY RUN] Would resume from last checkpoint")
                continue
            
            try:
                start_time = time.time()
                runner = WaveRunner(self.conn, workflow_run_id=run['workflow_run_id'])
                result = runner.run(max_iterations=100)
                duration = time.time() - start_time
                
                if result['status'] == 'completed':
                    self.stats['jobs_completed'] += 1
                    print(f"  ✅ Completed in {duration:.1f}s")
                else:
                    self.stats['jobs_failed'] += 1
                    print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.stats['jobs_failed'] += 1
                print(f"  ❌ Error: {e}")
    
    def fetch_jobs(self) -> List[int]:
        """
        Fetch jobs from Deutsche Bank API.
        
        Returns:
            List of staging_ids created
        """
        print(f"\n{'='*80}")
        print(f"STEP 1: FETCH JOBS FROM API")
        print(f"{'='*80}\n")
        
        print(f"Parameters:")
        print(f"  max_jobs: {self.max_jobs}")
        print(f"  skip_rate_limit: true")
        print(f"  Defense layer 1: Job fetcher validates before staging insert")
        print()
        
        if self.dry_run:
            print(f"[DRY RUN] Would fetch up to {self.max_jobs} jobs")
            print(f"[DRY RUN] Job fetcher would skip:")
            print(f"  - NULL job_description")
            print(f"  - job_description < 100 characters")
            print(f"  - NULL job_title")
            return []
        
        # Start workflow from Job Fetcher
        result = start_workflow(
            self.conn,
            workflow_id=3001,
            posting_id=None,
            start_conversation_id=9144,  # Job Fetcher
            params={
                "max_jobs": self.max_jobs,
                "skip_rate_limit": True,
                "search_text": ""
            }
        )
        
        workflow_run_id = result['workflow_run_id']
        print(f"✅ Workflow initialized: run_id={workflow_run_id}")
        print(f"   Starting Job Fetcher...\n")
        
        # Run fetcher
        start_time = time.time()
        runner = WaveRunner(self.conn, workflow_run_id=workflow_run_id)
        wave_result = runner.run(max_iterations=1)
        duration = time.time() - start_time
        
        # Get staging_ids from workflow state
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT state->'staging_ids' as staging_ids
            FROM workflow_runs
            WHERE workflow_run_id = %s
        """, (workflow_run_id,))
        
        row = cursor.fetchone()
        if row and row['staging_ids']:
            staging_ids = row['staging_ids']
            self.stats['jobs_fetched'] = len(staging_ids)
            
            print(f"\n✅ Fetched {len(staging_ids)} jobs in {duration:.1f}s")
            print(f"   Staging IDs: {staging_ids[:10]}{'...' if len(staging_ids) > 10 else ''}")
            return staging_ids
        else:
            print(f"\n⚠️  No jobs fetched (API may have returned 0 results)")
            return []
    
    def process_jobs(self, staging_ids: Optional[List[int]] = None):
        """
        Process jobs through full pipeline.
        
        Args:
            staging_ids: List of staging IDs to process (if None, get from recent fetch)
        """
        print(f"\n{'='*80}")
        print(f"STEP 2: PROCESS JOBS THROUGH PIPELINE")
        print(f"{'='*80}\n")
        
        # Get posting_ids from staging
        cursor = self.conn.cursor()
        
        if staging_ids:
            # Convert staging_ids to posting_ids
            cursor.execute("""
                SELECT posting_id 
                FROM postings 
                WHERE posting_id IN (
                    SELECT posting_id FROM postings_staging WHERE staging_id = ANY(%s)
                )
            """, (staging_ids,))
        else:
            # Get recent unprocessed postings
            cursor.execute("""
                SELECT posting_id 
                FROM postings 
                WHERE posting_id NOT IN (
                    SELECT DISTINCT posting_id 
                    FROM workflow_runs 
                    WHERE workflow_id = 3001 AND status = 'completed'
                )
                ORDER BY first_seen_at DESC
                LIMIT %s
            """, (self.max_jobs,))
        
        posting_ids = [row['posting_id'] for row in cursor.fetchall()]
        
        if not posting_ids:
            print(f"⚠️  No postings to process")
            return
        
        print(f"Found {len(posting_ids)} postings to process")
        print(f"Pipeline: Validate → Extract → Grade → Improve → Ticket → Format → Save → Skills → IHL")
        print()
        
        if self.dry_run:
            print(f"[DRY RUN] Would process {len(posting_ids)} postings")
            print(f"[DRY RUN] Defense layer 2: Validation conversation at step 2")
            print(f"[DRY RUN] Estimated duration: {len(posting_ids) * 30 / 3600:.1f} hours (if all valid)")
            return
        
        # Process each posting
        start_batch = time.time()
        
        for idx, posting_id in enumerate(posting_ids, 1):
            print(f"\n[{idx}/{len(posting_ids)}] Processing posting {posting_id}")
            print(f"-" * 80)
            
            try:
                # Start workflow for this posting
                result = start_workflow(
                    self.conn,
                    workflow_id=3001,
                    posting_id=posting_id
                )
                
                workflow_run_id = result['workflow_run_id']
                
                # Run workflow
                start_time = time.time()
                runner = WaveRunner(self.conn, workflow_run_id=workflow_run_id)
                wave_result = runner.run(max_iterations=100)
                duration = time.time() - start_time
                
                # Check result
                if wave_result['status'] == 'completed':
                    # Check if stopped at validation
                    cursor.execute("""
                        SELECT COUNT(*) FROM interactions
                        WHERE workflow_run_id = %s AND conversation_id = 9193
                          AND output LIKE '%%[NO_DESCRIPTION]%%' OR output LIKE '%%[TOO_SHORT]%%'
                    """, (workflow_run_id,))
                    
                    if cursor.fetchone()[0] > 0:
                        self.stats['jobs_rejected'] += 1
                        print(f"  ⚠️  Rejected at validation (invalid description) - {duration:.1f}s")
                    else:
                        self.stats['jobs_completed'] += 1
                        print(f"  ✅ Completed - {duration:.1f}s")
                else:
                    self.stats['jobs_failed'] += 1
                    print(f"  ❌ Failed: {wave_result.get('error', 'Unknown error')} - {duration:.1f}s")
                
                # Update stats
                self.stats['total_duration'] += duration
                
                # Calculate ETA
                completed = self.stats['jobs_completed'] + self.stats['jobs_rejected'] + self.stats['jobs_failed']
                if completed > 0:
                    avg_duration = self.stats['total_duration'] / completed
                    remaining = len(posting_ids) - idx
                    eta_seconds = remaining * avg_duration
                    eta = timedelta(seconds=int(eta_seconds))
                    
                    print(f"  Progress: {idx}/{len(posting_ids)} ({idx/len(posting_ids)*100:.1f}%)")
                    print(f"  ETA: {eta} ({avg_duration:.1f}s avg per job)")
                
            except Exception as e:
                self.stats['jobs_failed'] += 1
                print(f"  ❌ Error: {e}")
        
        # Final stats
        total_batch_duration = time.time() - start_batch
        print(f"\n{'='*80}")
        print(f"BATCH PROCESSING COMPLETE")
        print(f"{'='*80}\n")
        print(f"Duration: {timedelta(seconds=int(total_batch_duration))}")
        print(f"Completed: {self.stats['jobs_completed']}")
        print(f"Rejected (validation): {self.stats['jobs_rejected']}")
        print(f"Failed: {self.stats['jobs_failed']}")
        print(f"Average: {total_batch_duration / len(posting_ids):.1f}s per job")
        print()
    
    def run(self):
        """Execute batch processing."""
        print(f"\n{'='*80}")
        print(f"BATCH PROCESS 500 JOBS - WORKFLOW 3001")
        print(f"{'='*80}")
        print(f"Started: {datetime.now()}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        print(f"Max jobs: {self.max_jobs}")
        print()
        
        if self.resume:
            # Resume incomplete runs first
            self.resume_incomplete_runs()
        
        # Fetch new jobs
        staging_ids = self.fetch_jobs()
        
        # Process jobs
        self.process_jobs(staging_ids)
        
        print(f"\n{'='*80}")
        print(f"FINAL STATISTICS")
        print(f"{'='*80}")
        print(f"Jobs fetched: {self.stats['jobs_fetched']}")
        print(f"Jobs completed: {self.stats['jobs_completed']}")
        print(f"Jobs rejected (validation): {self.stats['jobs_rejected']}")
        print(f"Jobs failed: {self.stats['jobs_failed']}")
        print(f"Total duration: {timedelta(seconds=int(self.stats['total_duration']))}")
        print(f"Finished: {datetime.now()}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch process up to 500 jobs through Workflow 3001"
    )
    parser.add_argument(
        '--max-jobs',
        type=int,
        default=500,
        help='Maximum number of jobs to fetch/process (default: 500)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would happen without executing'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume incomplete workflow runs first'
    )
    
    args = parser.parse_args()
    
    processor = BatchProcessor(
        max_jobs=args.max_jobs,
        dry_run=args.dry_run,
        resume=args.resume
    )
    
    try:
        processor.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("Run with --resume to continue from last checkpoint")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
