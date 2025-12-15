#!/usr/bin/env python3
"""
Test job fetcher with description fetching - small batch of 3 jobs
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_wave')

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os
from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner

# Load .env credentials
load_dotenv()

# Connect to database
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    cursor_factory=psycopg2.extras.RealDictCursor
)

# Start workflow with max_jobs=3 parameter
print("Starting workflow 3001 with conversation 9144 (Job Fetcher)...")
print("Fetching 3 jobs with full descriptions...")

start_params = {
    'skip_rate_limit': True,
    'max_jobs': 3  # Only fetch 3 jobs for testing
}

result = start_workflow(
    conn,
    workflow_id=3001,
    posting_id=176,
    start_conversation_id=9144,
    params=start_params
)

print(f"✅ Workflow run: {result['workflow_run_id']}")
print(f"✅ Seed interaction: {result['seed_interaction_id']}")

# Run with trace enabled
runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
runner_result = runner.run(
    max_interactions=1,
    trace=True,
    trace_file=f'reports/trace_3jobs_run_{result["workflow_run_id"]}.md'
)

print(f"\n{'='*60}")
print(f"Duration: {runner_result['duration']:.1f}s")
print(f"Interactions completed: {runner_result['interactions_completed']}")

# Show interaction results
for interaction in runner_result['interactions']:
    output_size = len(str(interaction.get('output', '')))
    print(f"✅ Interaction {interaction['interaction_id']}: "
          f"Status: {interaction['status']}, "
          f"Output: {output_size} chars")

print(f"\n📊 Trace report: reports/trace_3jobs_run_{result['workflow_run_id']}.md")
print(f"{'='*60}\n")

conn.close()
