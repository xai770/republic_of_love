#!/usr/bin/env python3
"""
Test the validator on specific test postings
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

# Just validate the 3 test postings
test_posting_ids = [1933, 1934, 1935]

print("=" * 70)
print("TESTING VALIDATOR ON TEST POSTINGS")
print("=" * 70)
print()

conn = psycopg2.connect(
    dbname='turing',
    user='base_admin',
    password='base_yoga_secure_2025',
    host='localhost',
    cursor_factory=RealDictCursor
)
cur = conn.cursor()

# Show before state
print("BEFORE VALIDATION:")
cur.execute("""
    SELECT posting_id, external_job_id, LEFT(job_title, 40) as title, posting_status
    FROM postings
    WHERE posting_id = ANY(%s)
    ORDER BY posting_id
""", (test_posting_ids,))

for row in cur.fetchall():
    print(f"  {row['posting_id']}: {row['external_job_id']:10} - {row['title']:40} [{row['posting_status']}]")

print()
print("Running validator on these 3 test postings...")
print()

# Run validator on just these IDs
import subprocess
for pid in test_posting_ids:
    result = subprocess.run(
        ['python3', 'tools/validate_job_status.py', '--posting-id', str(pid), '--verbose'],
        capture_output=True,
        text=True,
        timeout=30
    )
    # Extract the key line
    for line in result.stdout.split('\n'):
        if 'ACTIVE:' in line or 'EXPIRED:' in line or 'ERROR:' in line:
            print(line)

print()
print("=" * 70)
print("AFTER VALIDATION:")
print("=" * 70)

cur.execute("""
    SELECT posting_id, external_job_id, LEFT(job_title, 40) as title, posting_status
    FROM postings
    WHERE posting_id = ANY(%s)
    ORDER BY posting_id
""", (test_posting_ids,))

for row in cur.fetchall():
    status_icon = "✅" if row['posting_status'] == 'active' else "❌"
    print(f"  {status_icon} {row['posting_id']}: {row['external_job_id']:10} - {row['title']:40} [{row['posting_status']}]")

print()
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("Expected:")
print("  1933: EXPIRED (bogus Workday URL)")
print("  1934: EXPIRED (bogus API job ID)")
print("  1935: ACTIVE (real Workday job)")
print()

conn.close()
