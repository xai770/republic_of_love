#!/usr/bin/env python3
"""
Database Update Script - Execute SQL UPDATE statements
Usage: python3 db_update.py --job-id JOB_ID --summary "SUMMARY TEXT"
       OR via JSON: echo '{"job_id": "123", "summary": "text"}' | python3 db_update.py --json-input
"""

import sys
import json
import argparse
import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

def update_posting_summary(job_id, summary):
    """Update postings.extracted_summary for given job_id"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE postings 
                SET extracted_summary = %s,
                    summary_extracted_at = NOW(),
                    summary_extraction_status = 'completed'
                WHERE job_id = %s
                RETURNING job_id, LENGTH(extracted_summary) as summary_length
            """, (summary, job_id))
            
            result = cur.fetchone()
            conn.commit()
            
            if result:
                return {
                    'status': 'success',
                    'job_id': result[0],
                    'summary_length': result[1],
                    'message': f'Updated job {result[0]} with {result[1]} char summary'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Job {job_id} not found'
                }
    except Exception as e:
        conn.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Update posting summary in database')
    parser.add_argument('--json-input', action='store_true', help='Read JSON from stdin')
    parser.add_argument('--job-id', type=str, help='Job ID to update')
    parser.add_argument('--summary', type=str, help='Summary text to save')
    
    args = parser.parse_args()
    
    if args.json_input:
        # JSON mode for universal executor
        input_data = json.load(sys.stdin)
        job_id = input_data.get('job_id')
        summary = input_data.get('summary') or input_data.get('PREVIOUS_RESPONSE')
    else:
        # Command line mode
        job_id = args.job_id
        summary = args.summary
    
    if not job_id or not summary:
        print(json.dumps({
            'status': 'error',
            'message': 'Missing job_id or summary'
        }))
        sys.exit(1)
    
    result = update_posting_summary(job_id, summary)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result['status'] == 'success' else 1)

if __name__ == '__main__':
    main()
