#!/usr/bin/env python3
"""
Check if Recipe 1114 saved extracted_summary for recent jobs
"""

import psycopg2
import psycopg2.extras

DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost',
    'port': '5432'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("📊 Recent jobs tested with Recipe 1114:")
    print("="*80)
    
    # First, get the most recently tested job
    cursor.execute("""
        SELECT job_id 
        FROM postings 
        WHERE job_id = '64654'  -- Most recent test
    """)
    
    job = cursor.fetchone()
    
    if job:
        cursor.execute("""
            SELECT 
                job_id,
                job_title,
                LENGTH(extracted_summary) as summary_length,
                summary_extraction_status,
                updated_at,
                SUBSTRING(extracted_summary FROM 1 FOR 200) as summary_preview
            FROM postings
            WHERE job_id = %s
        """, (job['job_id'],))
        
        result = cursor.fetchone()
        
        if result:
            status = "✅" if result['summary_length'] and result['summary_length'] > 0 else "❌"
            print(f"\n{status} Job {result['job_id']}")
            print(f"   Title: {result['job_title']}")
            print(f"   Summary Length: {result['summary_length'] or 0} chars")
            print(f"   Status: {result['summary_extraction_status'] or 'NULL'}")
            print(f"   Updated: {result['updated_at']}")
            
            if result['summary_preview']:
                print(f"\n   Preview:")
                print(f"   {result['summary_preview']}...")
        else:
            print("No result found for job 64657")
    else:
        print("Job 64657 not found")
    
    conn.close()

if __name__ == '__main__':
    main()
