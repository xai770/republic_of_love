#!/usr/bin/env python3
"""
Batch Promote Staging → Postings
Promotes all validated staging records to the postings table.
"""

from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.actors.postings_staging_validator import PostingsStagingValidator
import psycopg2
import psycopg2.extras
from datetime import datetime

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    cursor_factory=psycopg2.extras.RealDictCursor
)

print("\n" + "="*70)
print(f"🔄 BATCH PROMOTE: Staging → Postings")
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

cur = conn.cursor()

# Get all unpromoted staging records
cur.execute("""
    SELECT staging_id, job_title
    FROM postings_staging
    WHERE promoted_to_posting_id IS NULL
    AND validation_status != 'failed'
    ORDER BY staging_id
""")

staging_records = cur.fetchall()
print(f"\n📥 Found {len(staging_records)} unpromoted staging records")

if not staging_records:
    print("✅ Nothing to promote!")
    conn.close()
    sys.exit(0)

# Prepare input for validator
staging_ids = [r['staging_id'] for r in staging_records]

print(f"\n🔧 Running validator...")

# Create validator instance
validator = PostingsStagingValidator()
validator.db_conn = conn
validator.input_data = {
    'staging_ids': staging_ids,
    'interaction_id': None  # Running standalone
}

# Run validation and promotion
result = validator.process()

print(f"\n📊 RESULTS:")
print(f"   Validated:  {result.get('validated', 0)}")
print(f"   Promoted:   {result.get('promoted', 0)}")
print(f"   Rejected:   {result.get('rejected', 0)}")

if result.get('posting_ids'):
    print(f"\n✅ Promoted posting IDs: {result['posting_ids'][:10]}...")
    if len(result['posting_ids']) > 10:
        print(f"   (and {len(result['posting_ids']) - 10} more)")

print("\n" + "="*70)
print("✅ Batch promotion complete!")
print("="*70 + "\n")

conn.close()
