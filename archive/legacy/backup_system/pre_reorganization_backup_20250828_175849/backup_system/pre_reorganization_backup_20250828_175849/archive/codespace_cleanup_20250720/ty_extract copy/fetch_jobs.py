#!/usr/bin/env python3
"""
Fetch Jobs Runner
================

Simple runner to fetch jobs using the JobApiFetcher and save them to data directory.

Usage:
    python fetch_jobs.py            # Fetch 3 jobs (default)
    python fetch_jobs.py --jobs 10  # Fetch 10 jobs
    python fetch_jobs.py --force    # Force refetch existing jobs
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from job_api_fetcher_v6 import JobApiFetcher

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Fetch job postings from Deutsche Bank API"
    )
    
    parser.add_argument(
        '--jobs', '-j',
        type=int,
        default=3,
        help='Number of jobs to fetch (default: 3)'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force refetch existing jobs'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting job fetch: {args.jobs} jobs, force={args.force}")
    
    try:
        # Initialize fetcher
        fetcher = JobApiFetcher()
        
        # Fetch jobs
        jobs = fetcher.fetch_jobs(
            max_jobs=args.jobs,
            quick_mode=False,
            force_reprocess=args.force
        )
        
        logger.info(f"Successfully fetched {len(jobs)} jobs")
        
        # Show summary
        for job in jobs:
            job_content = job.get('job_content', {})
            print(f"✅ {job_content.get('title', 'Unknown Title')}")
        
    except Exception as e:
        logger.error(f"Error during job fetch: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
