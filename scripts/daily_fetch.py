#!/usr/bin/env python3
"""Daily Job Fetch Script
Fetches all current jobs from Deutsche Bank and marks removed ones as invalidated.
"""

from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
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
print(f"🚀 DAILY JOB REVIEW - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70 + "\n")

# Fetch ALL jobs (max_jobs=2000 to be safe)
result = start_workflow(
    conn,
    workflow_id=3001,
    params={
        'skip_rate_limit': True,
        'max_jobs': 2000,
        'search_text': ''
    }
)

print(f"✅ Workflow run: {result['workflow_run_id']}")
print(f"Starting from: {result['first_conversation_name']}\n")

# Run just the job fetcher (1 interaction)
runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
runner.run(
    max_iterations=1, 
    trace=True, 
    trace_file=f"reports/trace_daily_run_{result['workflow_run_id']}.md"
)

print("\n" + "="*70)
print(f"📊 Job fetch completed!")
print(f"Trace: reports/trace_daily_run_{result['workflow_run_id']}.md")
print("="*70 + "\n")

conn.close()
