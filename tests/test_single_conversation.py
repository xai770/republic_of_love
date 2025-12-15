#!/usr/bin/env python3
"""
Test single conversation in isolation
Usage: python3 tests/test_single_conversation.py [conversation_id]
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get conversation_id from command line (default: 3335 = Extract)
conversation_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3335
skip_rate_limit = '--skip-rate-limit' in sys.argv

# Connect using .env credentials
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    cursor_factory=psycopg2.extras.RealDictCursor
)

# Get conversation name
cur = conn.cursor()
cur.execute("SELECT conversation_name FROM conversations WHERE conversation_id = %s", (conversation_id,))
conv = cur.fetchone()
print(f"🎯 Testing conversation {conversation_id}: {conv['conversation_name']}")

# Start workflow from this conversation
start_params = {'skip_rate_limit': True} if skip_rate_limit else None
result = start_workflow(
    conn,
    workflow_id=3001,
    posting_id=176,
    start_conversation_id=conversation_id,
    params=start_params
)

print(f"✅ Workflow run: {result['workflow_run_id']}")
print(f"✅ Seed interaction: {result['seed_interaction_id']}")

# Run ONLY 1 interaction
print("\n⚡ Executing 1 interaction...")
runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
runner_result = runner.run(
    max_interactions=1,  # ← STOP after 1 interaction
    trace=True,
    trace_file=f'reports/trace_conv_{conversation_id}_run_{result["workflow_run_id"]}.md'
)

print(f"\n📊 Result:")
print(f"   Completed: {runner_result['interactions_completed']}")
print(f"   Failed: {runner_result['interactions_failed']}")
print(f"   Duration: {runner_result.get('duration_ms', 0) / 1000:.1f}s")
print(f"\n📄 Trace report: reports/trace_conv_{conversation_id}_run_{result['workflow_run_id']}.md")

# Show interaction result
cur.execute("""
    SELECT 
        i.interaction_id,
        c.conversation_name,
        i.status,
        LENGTH(i.output::text) as output_len,
        i.output->>'status' as status_flag
    FROM interactions i
    JOIN conversations c ON i.conversation_id = c.conversation_id
    WHERE i.workflow_run_id = %s
    ORDER BY i.created_at DESC
    LIMIT 1
""", (result['workflow_run_id'],))

inter = cur.fetchone()
if inter:
    print(f"\n✅ Interaction {inter['interaction_id']}:")
    print(f"   Status: {inter['status']}")
    print(f"   Output: {inter['output_len']} chars")
    if inter['status_flag']:
        print(f"   Flag: {inter['status_flag']}")

conn.close()
print("\n✨ Test complete!")
