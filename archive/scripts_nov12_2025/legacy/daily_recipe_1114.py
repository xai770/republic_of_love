#!/usr/bin/env python3
"""
Daily Recipe 1114 Runner - Extract summaries for all jobs with NULL extracted_summary

This script is designed to run daily (via cron) to process new job postings.

Features:
- Processes ONLY jobs where extracted_summary IS NULL (source of truth)
- Production mode (1 batch per job, saves to postings.extracted_summary)
- Checkpoint/resume capability (can be stopped and resumed)
- Progress tracking with ETA
- Error handling and logging
- Dry-run mode for testing

Usage:
    # Normal run (production mode)
    python3 scripts/daily_recipe_1114.py
    
    # Dry run (see what would be processed)
    python3 scripts/daily_recipe_1114.py --dry-run
    
    # Limit processing (useful for testing)
    python3 scripts/daily_recipe_1114.py --limit 10

Cron setup (runs daily at 2 AM):
    0 2 * * * cd /home/xai/Documents/ty_learn && python3 scripts/daily_recipe_1114.py >> logs/recipe_1114_daily.log 2>&1
"""
import psycopg2
import psycopg2.extras
import subprocess
import sys
import time
import argparse
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'database': 'base_yoga'
}

RECIPE_ID = 1114
EXECUTION_MODE = 'production'
TARGET_BATCH_COUNT = 1

def get_pending_postings(limit=None):
    """
    Get postings that need extracted_summary OR skill_keywords generated.
    
    Uses extracted_summary IS NULL OR skill_keywords IS NULL as source of truth.
    Recipe 1114 now handles BOTH summary extraction AND skill extraction.
    """
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)
    cursor = conn.cursor()
    
    query = """
        SELECT 
            p.job_id,
            p.job_title,
            p.organization_name,
            p.updated_at,
            LENGTH(p.job_description) as desc_length,
            p.extracted_summary IS NULL as needs_summary,
            (p.skill_keywords IS NULL OR p.skill_keywords = '[]'::jsonb) as needs_skills
        FROM postings p
        WHERE p.enabled = TRUE
          AND p.job_description IS NOT NULL
          AND (p.extracted_summary IS NULL  -- Needs summary
               OR p.skill_keywords IS NULL  -- Needs skills
               OR p.skill_keywords = '[]'::jsonb)  -- Has empty skills array
        ORDER BY p.updated_at DESC  -- Process newest first
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    postings = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return postings

def get_stats():
    """Get processing statistics for both summaries and skills"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN extracted_summary IS NOT NULL THEN 1 ELSE 0 END) as has_summary,
            SUM(CASE WHEN skill_keywords IS NOT NULL AND skill_keywords != '[]'::jsonb THEN 1 ELSE 0 END) as has_skills,
            SUM(CASE WHEN extracted_summary IS NOT NULL AND skill_keywords IS NOT NULL AND skill_keywords != '[]'::jsonb THEN 1 ELSE 0 END) as has_both,
            SUM(CASE WHEN extracted_summary IS NULL OR skill_keywords IS NULL OR skill_keywords = '[]'::jsonb THEN 1 ELSE 0 END) as needs_processing
        FROM postings
        WHERE enabled = TRUE
          AND job_description IS NOT NULL
    """)
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return {
        'total': result[0],
        'has_summary': result[1],
        'has_skills': result[2],
        'has_both': result[3],
        'needs_processing': result[4]
    }

def process_posting(job_id, dry_run=False, retry_attempt=1, max_retries=2):
    """Process a single posting with Recipe 1114.
    
    Args:
        job_id: The job posting ID to process
        dry_run: If True, only simulate processing
        retry_attempt: Current attempt number (1-based)
        max_retries: Maximum number of attempts (default 2 = try once, retry once if failed)
    """
    if dry_run:
        print(f"  [DRY RUN] Would process job {job_id}")
        return True, "dry_run"
    
    try:
        # Call by_recipe_runner.py with Recipe 1114
        cmd = [
            'python3', 'scripts/by_recipe_runner.py',
            '--recipe-id', '1114',
            '--job-id', str(job_id),
            '--execution-mode', 'production',
            '--target-batch-count', '1'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per job
        )
        
        if result.returncode == 0:
            # Verify the summary was actually saved
            if verify_save(job_id):
                if retry_attempt > 1:
                    print(f"    ✓ Succeeded on retry attempt {retry_attempt}")
                return True, "success"
            else:
                error_msg = "save_failed"
        else:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        
        # If we failed and have retries left, try again
        if retry_attempt < max_retries:
            print(f"    ⚠ Attempt {retry_attempt} failed: {error_msg}")
            print(f"    🔄 Retrying (attempt {retry_attempt + 1}/{max_retries})...")
            time.sleep(2)  # Brief pause before retry
            return process_posting(job_id, dry_run, retry_attempt + 1, max_retries)
        else:
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = "timeout"
        if retry_attempt < max_retries:
            print(f"    ⚠ Attempt {retry_attempt} timed out")
            print(f"    🔄 Retrying (attempt {retry_attempt + 1}/{max_retries})...")
            time.sleep(2)
            return process_posting(job_id, dry_run, retry_attempt + 1, max_retries)
        else:
            return False, error_msg
    except Exception as e:
        error_msg = str(e)
        if retry_attempt < max_retries:
            print(f"    ⚠ Attempt {retry_attempt} failed with exception: {error_msg}")
            print(f"    🔄 Retrying (attempt {retry_attempt + 1}/{max_retries})...")
            time.sleep(2)
            return process_posting(job_id, dry_run, retry_attempt + 1, max_retries)
        else:
            return False, error_msg

def verify_save(job_id):
    """Verify that extracted_summary was actually saved"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            extracted_summary IS NOT NULL as has_summary,
            LENGTH(extracted_summary) as summary_length
        FROM postings
        WHERE job_id = %s
    """, (job_id,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if result and result[0]:
        return True, result[1]
    else:
        return False, 0

def main():
    parser = argparse.ArgumentParser(description='Daily Recipe 1114 runner for job summary extraction')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without actually running')
    parser.add_argument('--limit', type=int, help='Limit number of jobs to process (useful for testing)')
    parser.add_argument('--quiet', action='store_true', help='Minimal output (for cron logs)')
    
    args = parser.parse_args()
    
    # Header
    if not args.quiet:
        print("="*80)
        print(f"📅 Daily Recipe 1114 Runner - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if args.dry_run:
            print("🔍 DRY RUN MODE - No actual processing")
        print("="*80)
    
    # Get current statistics
    stats = get_stats()
    pending = get_pending_postings(limit=args.limit)
    
    if not args.quiet:
        print(f"\n📊 Database Status:")
        print(f"   Total jobs: {stats['total']:,}")
        print(f"   ✅ Complete (summary + skills): {stats['has_both']:,} ({stats['has_both']/stats['total']*100:.1f}%)")
        print(f"   📝 Has summary only: {stats['has_summary'] - stats['has_both']:,}")
        print(f"   🔤 Has skills only: {stats['has_skills'] - stats['has_both']:,}")
        print(f"   ⏳ Needs processing: {stats['needs_processing']:,} ({stats['needs_processing']/stats['total']*100:.1f}%)")
        
        if args.limit:
            print(f"\n⚠️  Processing limited to {args.limit} jobs")
        
        print(f"\n🎯 Will process: {len(pending)} job(s)")
    
    if not pending:
        if not args.quiet:
            print("\n✅ No jobs need processing. All jobs have summary + skills!")
        return 0
    
    if not args.quiet:
        print(f"\n⏱️  Estimated time: {len(pending) * 2.5:.1f} minutes (avg 2.5 min/job)")
        if not args.dry_run:
            print("\n💡 Press Ctrl+C to stop safely. Resume by running again.\n")
    
    # Process each posting
    start_time = time.time()
    success_count = 0
    error_count = 0
    errors = []
    
    try:
        for idx, posting in enumerate(pending, 1):
            job_id = posting['job_id']
            title = posting['job_title']
            org = posting['organization_name']
            desc_len = posting['desc_length']
            
            if not args.quiet:
                print(f"\n[{idx}/{len(pending)}] Job {job_id}")
                print(f"  Title: {title[:60]}...")
                print(f"  Org: {org}")
                print(f"  Length: {desc_len:,} chars")
                print(f"  Updated: {posting['updated_at']}")
            
            posting_start = time.time()
            success, message = process_posting(job_id, dry_run=args.dry_run)
            duration = time.time() - posting_start
            
            if success and not args.dry_run:
                # Verify the summary was actually saved
                saved, summary_len = verify_save(job_id)
                if saved:
                    if not args.quiet:
                        print(f"  ✅ Success ({duration:.1f}s) - Saved {summary_len:,} chars")
                    success_count += 1
                else:
                    if not args.quiet:
                        print(f"  ⚠️  Recipe succeeded but summary not saved!")
                    error_count += 1
                    errors.append((job_id, "Summary not saved after successful recipe run"))
            elif success and args.dry_run:
                success_count += 1
                if not args.quiet:
                    print(f"  🔍 Would process")
            else:
                if not args.quiet:
                    print(f"  ❌ Failed: {message}")
                error_count += 1
                errors.append((job_id, message))
            
            # Show progress
            if not args.quiet:
                progress = (idx / len(pending)) * 100
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining = (len(pending) - idx) * avg_time
                
                print(f"  📊 Progress: {progress:.1f}% | Avg: {avg_time:.1f}s/job | ETA: {remaining/60:.1f} min")
            
    except KeyboardInterrupt:
        print("\n\n⏸️  Interrupted by user")
        print(f"✅ Successfully processed: {success_count}")
        print(f"❌ Errors: {error_count}")
        print(f"\n💾 All progress saved. Run again to resume.")
        sys.exit(0)
    
    # Final summary
    print("\n" + "="*80)
    print("📊 DAILY RUN COMPLETE")
    print("="*80)
    
    if args.dry_run:
        print(f"🔍 Dry run - would have processed {len(pending)} jobs")
    else:
        print(f"✅ Successful: {success_count}/{len(pending)}")
        print(f"❌ Failed: {error_count}/{len(pending)}")
        print(f"⏱️  Total time: {(time.time() - start_time)/60:.1f} minutes")
        
        if errors and not args.quiet:
            print(f"\n❌ Errors ({len(errors)}):")
            for job_id, error_msg in errors[:10]:  # Show first 10
                print(f"   Job {job_id}: {error_msg}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more")
        
        # Update stats
        final_stats = get_stats()
        print(f"\n📈 Final Status:")
        print(f"   ✅ With summaries: {final_stats['completed']:,}/{final_stats['total']:,} ({final_stats['completed']/final_stats['total']*100:.1f}%)")
        print(f"   ⏳ Without summaries: {final_stats['pending']:,}/{final_stats['total']:,} ({final_stats['pending']/final_stats['total']*100:.1f}%)")
    
    print("="*80)
    
    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
