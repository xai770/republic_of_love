#!/usr/bin/env python3
"""
Check if the retried jobs now have extracted_summary
"""
import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'database': 'base_yoga'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("📊 Checking status of retried jobs:")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            job_id,
            job_title,
            LENGTH(extracted_summary) as summary_length,
            summary_extraction_status
        FROM postings
        WHERE job_id IN ('59428', '64727')
    """)
    
    for row in cursor.fetchall():
        job_id, title, length, status = row
        if length and length > 0:
            print(f"✅ Job {job_id}: {title[:50]}...")
            print(f"   Summary: {length:,} chars, Status: {status}")
        else:
            print(f"❌ Job {job_id}: {title[:50]}...")
            print(f"   Summary: NULL")
    
    print("\n" + "="*80)
    print("📊 Overall database status:")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN extracted_summary IS NOT NULL THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN extracted_summary IS NULL THEN 1 ELSE 0 END) as pending
        FROM postings
        WHERE enabled = TRUE AND job_description IS NOT NULL
    """)
    
    total, completed, pending = cursor.fetchone()
    pct = (completed / total * 100) if total > 0 else 0
    
    print(f"Total jobs: {total}")
    print(f"✅ With summaries: {completed} ({pct:.1f}%)")
    print(f"⏳ Without summaries: {pending} ({(pending/total*100):.1f}%)")
    
    if pending == 0:
        print("\n🎉 ALL JOBS COMPLETE! Every job now has extracted_summary.")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
