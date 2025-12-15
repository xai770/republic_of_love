#!/usr/bin/env python3
"""Quick test - extract ONE summary"""
import psycopg2
import subprocess
import time

conn = psycopg2.connect(
    host='localhost',
    user='base_admin',
    password='base_yoga_secure_2025',
    database='base_yoga'
)

# Get one small posting
cursor = conn.cursor()
cursor.execute("""
    SELECT job_id, job_description 
    FROM postings 
    WHERE LENGTH(job_description) < 1000 
    LIMIT 1
""")
row = cursor.fetchone()
job_id, description = row

print(f"Processing job {job_id}")
print(f"Length: {len(description)} chars\n")

# Extract
prompt = f"""Extract job summary. Use this format:

Role: [title]
Company: [name]
Location: [city]
Skills: [list]

POSTING:
{description}

SUMMARY:"""

print("Calling gemma3:1b...")
start = time.time()
result = subprocess.run(
    ['ollama', 'run', 'gemma3:1b'],
    input=prompt,
    capture_output=True,
    text=True,
    timeout=60
)
elapsed = time.time() - start

if result.returncode == 0:
    summary = result.stdout.strip()
    print(f"\n✅ SUCCESS ({elapsed:.1f}s)\n")
    print(summary)
    
    # Save
    cursor.execute(
        "UPDATE postings SET extracted_summary = %s, summary_extraction_status = 'success' WHERE job_id = %s",
        (summary, job_id)
    )
    conn.commit()
    print(f"\n💾 Saved to database")
else:
    print(f"❌ FAILED: {result.stderr}")

cursor.close()
conn.close()
