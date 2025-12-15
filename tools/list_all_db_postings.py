#!/usr/bin/env python3
"""
Standalone script to list ALL available job postings from Deutsche Bank careers.
Fetches from the Workday API at https://careers.db.com/

Usage:
    python3 tools/list_all_db_postings.py              # List all jobs
    python3 tools/list_all_db_postings.py --json       # Output as JSON
    python3 tools/list_all_db_postings.py --csv        # Output as CSV
    python3 tools/list_all_db_postings.py --count      # Just show count
"""

import requests
import json
import argparse
import sys
from datetime import datetime


# Deutsche Bank Workday API
API_URL = 'https://db.wd3.myworkdayjobs.com/wday/cxs/db/DBWebSite/jobs'

# API enforces max 20 jobs per request
MAX_PER_REQUEST = 20


def fetch_all_jobs(verbose: bool = False) -> list:
    """
    Fetch all job postings from Deutsche Bank Workday API.
    
    Returns:
        List of job posting dicts
    """
    all_jobs = []
    offset = 0
    total = None
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print("Connecting to API...", file=sys.stderr, flush=True)
    
    while True:
        payload = {
            "appliedFacets": {},
            "limit": MAX_PER_REQUEST,
            "offset": offset,
            "searchText": ""
        }
        
        try:
            print(f"  Request offset={offset}...", file=sys.stderr, end='', flush=True)
            response = requests.post(
                API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=60  # Increased timeout
            )
            print(f" {response.status_code}", file=sys.stderr, flush=True)
            
            if response.status_code != 200:
                print(f"Error: API returned {response.status_code}", file=sys.stderr)
                print(f"Response: {response.text[:500]}", file=sys.stderr)
                break
            
            data = response.json()
            jobs = data.get('jobPostings', [])
            
            if total is None:
                total = data.get('total', 0)
                if verbose:
                    print(f"API reports {total} total jobs available", file=sys.stderr)
            
            if not jobs:
                break
            
            all_jobs.extend(jobs)
            
            if verbose:
                print(f"Fetched {len(all_jobs)}/{total} jobs...", file=sys.stderr)
            
            # Check if we've got all jobs
            if len(all_jobs) >= total or len(jobs) < MAX_PER_REQUEST:
                break
            
            offset += len(jobs)
            
        except requests.exceptions.Timeout:
            print("Error: Request timed out", file=sys.stderr)
            break
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}", file=sys.stderr)
            break
    
    return all_jobs


def format_job(job: dict) -> dict:
    """
    Format a job posting for output.
    """
    bullet_fields = job.get('bulletFields', [])
    job_id = bullet_fields[0] if bullet_fields else None
    
    return {
        'job_id': job_id,
        'title': job.get('title', ''),
        'location': job.get('locationsText', ''),
        'posted_on': job.get('postedOn', ''),
        'external_path': job.get('externalPath', ''),
        'url': f"https://db.wd3.myworkdayjobs.com/DBWebSite{job.get('externalPath', '')}"
    }


def output_table(jobs: list):
    """
    Print jobs as a formatted table.
    """
    # Header
    print(f"\n{'='*120}")
    print(f"{'Job ID':<15} {'Title':<50} {'Location':<35} {'Posted':<15}")
    print(f"{'='*120}")
    
    for job in jobs:
        formatted = format_job(job)
        title = formatted['title'][:48] + '..' if len(formatted['title']) > 50 else formatted['title']
        location = formatted['location'][:33] + '..' if len(formatted['location']) > 35 else formatted['location']
        job_id = formatted['job_id'] or 'N/A'
        
        print(f"{job_id:<15} {title:<50} {location:<35} {formatted['posted_on']:<15}")
    
    print(f"{'='*120}")
    print(f"Total: {len(jobs)} jobs")


def output_json(jobs: list):
    """
    Print jobs as JSON.
    """
    formatted = [format_job(job) for job in jobs]
    print(json.dumps({
        'fetched_at': datetime.now().isoformat(),
        'total': len(formatted),
        'jobs': formatted
    }, indent=2))


def output_csv(jobs: list):
    """
    Print jobs as CSV.
    """
    print("job_id,title,location,posted_on,url")
    for job in jobs:
        formatted = format_job(job)
        # Escape quotes in fields
        title = formatted['title'].replace('"', '""')
        location = formatted['location'].replace('"', '""')
        print(f'"{formatted["job_id"]}","{title}","{location}","{formatted["posted_on"]}","{formatted["url"]}"')


def main():
    parser = argparse.ArgumentParser(
        description='List all available Deutsche Bank job postings from careers.db.com'
    )
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--csv', action='store_true', help='Output as CSV')
    parser.add_argument('--count', action='store_true', help='Just show count')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress')
    
    args = parser.parse_args()
    
    # Always be verbose unless outputting structured data
    verbose = args.verbose or (not args.json and not args.csv and not args.count)
    
    if verbose and not args.count:
        print(f"Fetching all jobs from {API_URL}...", file=sys.stderr)
    
    jobs = fetch_all_jobs(verbose=verbose)
    
    if args.count:
        print(f"{len(jobs)}")
    elif args.json:
        output_json(jobs)
    elif args.csv:
        output_csv(jobs)
    else:
        output_table(jobs)
        
        # Show breakdown by location
        print("\n--- Location breakdown ---")
        locations = {}
        for job in jobs:
            loc = job.get('locationsText', 'Unknown')
            # Extract country/region from location
            if ',' in loc:
                loc = loc.split(',')[0].strip()
            locations[loc] = locations.get(loc, 0) + 1
        
        for loc, count in sorted(locations.items(), key=lambda x: -x[1])[:20]:
            print(f"  {loc}: {count}")
        
        if len(locations) > 20:
            print(f"  ... and {len(locations) - 20} more locations")


if __name__ == '__main__':
    main()
