#!/usr/bin/env python3
import subprocess
import json
import sys
import time
sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection

URL = 'https://db.wd3.myworkdayjobs.com/wday/cxs/db/DBWebSite/jobs'

def fetch_page(offset, limit=100, retry=3):
    """Fetch via curl subprocess. Retry on 400 errors with delay."""
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    for attempt in range(retry):
        cmd = f'curl -s -X POST "{URL}" -H "Content-Type: application/json" -H "User-Agent: {ua}" -d \'{{"limit":{limit},"offset":{offset}}}\''
        print(f"DEBUG CMD: {cmd[:150]}...")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"DEBUG OUT: {result.stdout[:100]}...")
        try:
            data = json.loads(result.stdout)
            if 'errorCode' in data:
                time.sleep(2)  # Rate limited, wait
                continue
            return data
        except Exception:
            time.sleep(1)
    return {'total': 0, 'jobPostings': []}

print("Fetching from Workday...")
data = fetch_page(0, 100)
total = data.get('total', 0)
print(f"Total online: {total}")

all_ids = set()
for job in data.get('jobPostings', []):
    rid = job.get('bulletFields', [None])[0]
    if rid:
        all_ids.add(rid)

offset = 100
while offset < total:
    time.sleep(0.5)  # Rate limit protection
    d = fetch_page(offset, 100)
    for job in d.get('jobPostings', []):
        rid = job.get('bulletFields', [None])[0]
        if rid:
            all_ids.add(rid)
    print(f"  {min(offset+100, total)}/{total} - {len(all_ids)} IDs")
    offset += 100

print(f"\nTotal unique online: {len(all_ids)}")

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT external_id, invalidated FROM postings WHERE external_id IS NOT NULL")
    rows = cur.fetchall()
    
    db_all = set(r['external_id'] for r in rows)
    marked_invalid = set(r['external_id'] for r in rows if r['invalidated'])
    
    overlap = db_all & all_ids
    gone = db_all - all_ids
    new = all_ids - db_all
    false_invalids = marked_invalid & all_ids
    
    print(f"\n{'='*50}")
    print("COMPARISON RESULTS")
    print(f"{'='*50}")
    print(f"DB total:              {len(db_all)}")
    print(f"Online (Workday):      {len(all_ids)}")
    print(f"Overlap (in both):     {len(overlap)}")
    print(f"Gone (DB only):        {len(gone)}")
    print(f"New (online only):     {len(new)}")
    print(f"False invalids:        {len(false_invalids)}")
