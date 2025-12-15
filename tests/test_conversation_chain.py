#!/usr/bin/env python3
"""
Test a chain of conversations in workflow 3001
Shows comprehensive trace with multiple interactions
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.wave_runner.database import DatabaseHelper
from dotenv import load_dotenv
import psycopg2

# Load environment
load_dotenv()

def test_chain():
    """Test conversation chain starting from specified conversation"""
    
    # Get optional command line args
    start_conv_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3335
    max_interactions = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    # Connect to database
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='turing',
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    db = DatabaseHelper(conn)
    
    # Get conversation name for display
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_name FROM conversations WHERE conversation_id = %s", (start_conv_id,))
    conv_name = cursor.fetchone()[0]
    cursor.close()
    
    # Prepare params - skip rate limit for testing
    params = {
        'skip_rate_limit': True,
        'max_jobs': 3  # Fetch only 3 jobs for faster testing
    }
    
    # Start workflow
    print(f"🎯 Testing conversation chain starting from: {conv_name} ({start_conv_id})")
    result = start_workflow(
        db_conn=conn,
        workflow_id=3001,
        posting_id=176,
        start_conversation_id=start_conv_id,
        params=params
    )
    
    workflow_run_id = result['workflow_run_id']
    seed_interaction_id = result['seed_interaction_id']
    
    print(f"✅ Workflow run: {workflow_run_id}")
    print(f"✅ Seed interaction: {seed_interaction_id}")
    
    # Run with specified max_interactions
    runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
    
    print(f"\n⚡ Executing chain (up to {max_interactions} interactions)...")
    runner_result = runner.run(
        max_interactions=max_interactions,
        trace=True,
        trace_file=f'reports/trace_chain_run_{workflow_run_id}.md'
    )
    
    print(f"📄 Trace report: reports/trace_chain_run_{workflow_run_id}.md")
    print(f"\n📊 Result:")
    print(f"   Completed: {runner_result['interactions_completed']}")
    print(f"   Failed: {runner_result['interactions_failed']}")
    print(f"   Duration: {runner_result['duration_ms'] / 1000:.1f}s")
    
    print(f"\n📄 Trace report: reports/trace_chain_run_{workflow_run_id}.md")
    print("\n✨ Test complete!")
    
    conn.close()

if __name__ == '__main__':
    test_chain()
