#!/usr/bin/env python3
"""
Continue Run 161 from Step 12 (Extract Skills)
===============================================

Run 161 stopped at step 11 (Check Skills Exist).
This script continues the workflow from step 12 to complete skills extraction.

Based on Arden's guidance:
- Don't test in isolation
- Extend existing Run 161 by one interaction
- Progressive validation (CRAWL methodology)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Database connection
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    print("=" * 80)
    print("CONTINUE RUN 161 - Step 12 (Extract Skills)")
    print("=" * 80)
    print()
    print("Workflow: 3001 (Complete Job Processing Pipeline)")
    print("Posting: 176 (Deutsche Bank - CA Intern)")
    print("Starting from: Conversation 3350 (r1114_extract_skills)")
    print()
    print("Expected outcome:")
    print("- State should gain 'extracted_skills' key")
    print("- Skills extracted from current_summary")
    print("- Ready to continue to step 16 (Check IHL Exists)")
    print()
    print("-" * 80)
    
    try:
        # Start workflow from conversation 3350 (extract_skills)
        result = start_workflow(
            db_conn=conn,
            workflow_id=3001,
            posting_id=176,
            start_conversation_id=3350  # r1114_extract_skills (step 12)
        )
        
        print(f"✅ Workflow run started: {result['workflow_run_id']}")
        print(f"   Seed interaction: {result['seed_interaction_id']}")
        print(f"   First conversation: {result['first_conversation_name']} ({result['first_conversation_id']})")
        print()
        
        # Create WaveRunner and execute
        runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
        print("🏃 Executing workflow...")
        print()
        
        # Run with trace enabled
        trace_file = f"reports/trace_run_{result['workflow_run_id']}.md"
        runner.run(
            max_iterations=10,
            trace=True,
            trace_file=trace_file
        )
        
        print()
        print("=" * 80)
        print("✅ EXECUTION COMPLETE")
        print("=" * 80)
        print()
        print(f"📄 Trace report: {trace_file}")
        print()
        print("Next steps:")
        print("1. Verify state has 'extracted_skills' key:")
        print("   ./scripts/q.sh \"SELECT jsonb_object_keys(state) FROM workflow_runs WHERE workflow_run_id = {}\";".format(result['workflow_run_id']))
        print()
        print("2. Check extracted skills content:")
        print("   ./scripts/q.sh \"SELECT state->'extracted_skills' FROM workflow_runs WHERE workflow_run_id = {}\";".format(result['workflow_run_id']))
        print()
        print("3. If successful, continue to step 16 (Check IHL Exists):")
        print("   python3 scripts/continue_to_step_16.py")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
