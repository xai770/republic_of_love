#!/usr/bin/env python3
"""
Batch Job Skills Extraction - Run workflow 1121 on missing postings
====================================================================

Identifies postings with no extracted skills and runs workflow 1121 on them.
"""

import sys
import subprocess
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection

def get_postings_needing_extraction():
    """Get list of posting IDs with no extracted skills"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        WITH postings_with_skills AS (
            SELECT DISTINCT posting_id
            FROM job_skills
        )
        SELECT p.posting_id, p.job_title
        FROM postings p
        LEFT JOIN postings_with_skills pws ON p.posting_id = pws.posting_id
        WHERE pws.posting_id IS NULL
        ORDER BY p.posting_id
    """)
    
    postings = cursor.fetchall()
    conn.close()
    return postings

def run_workflow_1121(posting_id, job_title):
    """Run workflow 1121 for a single posting"""
    print(f"\n{'='*60}")
    print(f"🔄 Extracting skills from posting {posting_id}")
    print(f"📝 {job_title[:50]}...")
    print(f"{'='*60}")
    
    cmd = [
        'python3',
        'runners/workflow_1121_runner.py',
        '--posting-id', str(posting_id)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 min timeout per job
        )
        
        if result.returncode == 0:
            print(f"✅ SUCCESS: Posting {posting_id} extracted")
            return True
        else:
            print(f"❌ FAILED: Posting {posting_id}")
            print(f"Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: Posting {posting_id} took too long")
        return False
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False

def main():
    """Main batch extraction runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch extract skills from postings')
    parser.add_argument('--auto-confirm', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    print("="*60)
    print("Batch Job Skills Extraction - Workflow 1121")
    print("="*60)
    
    # Get postings needing extraction
    print("\n🔍 Finding postings with no extracted skills...")
    postings = get_postings_needing_extraction()
    
    if not postings:
        print("✅ All postings already have skills extracted!")
        return
    
    print(f"📊 Found {len(postings)} postings needing extraction\n")
    
    # Ask for confirmation unless auto-confirmed
    if not args.auto_confirm:
        response = input(f"Run workflow 1121 on {len(postings)} postings? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    
    # Process each posting
    success_count = 0
    failed_count = 0
    start_time = time.time()
    
    for i, posting in enumerate(postings, 1):
        posting_id = posting['posting_id']
        job_title = posting['job_title'] or 'Untitled'
        
        print(f"\n[{i}/{len(postings)}] Processing posting {posting_id}...")
        
        if run_workflow_1121(posting_id, job_title):
            success_count += 1
        else:
            failed_count += 1
        
        # Brief pause between extractions
        if i < len(postings):
            time.sleep(2)
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("📊 BATCH EXTRACTION SUMMARY")
    print("="*60)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⏱️  Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"📈 Success rate: {success_count/len(postings)*100:.1f}%")
    print("="*60)

if __name__ == '__main__':
    main()
