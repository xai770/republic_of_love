#!/usr/bin/env python3
"""
Example: Run Workflow 3001 (Complete Job Processing Pipeline)

This script runs the complete job processing pipeline:
1. Fetch jobs from Deutsche Bank API (if --fetch or no posting exists)
2. Validate job descriptions
3. Extract summaries, grade, improve
4. Extract skills
5. Calculate IHL scores
6. (Optional) Run WF3005 to resolve unmatched skills (--with-registry)

NOTE: --with-taxonomy is deprecated, use --with-registry instead.
      WF3002 is deprecated in favor of WF3005 (Entity Registry - Skill Maintenance).

Usage:
    # Fetch new jobs and process them
    python scripts/prod/run_workflow_3001.py --fetch --max-jobs 1
    
    # Process a specific posting
    python scripts/prod/run_workflow_3001.py --posting-id 176
    
    # Full pipeline with skill registry maintenance
    python scripts/prod/run_workflow_3001.py --fetch --max-jobs 100 --with-registry
"""

import sys
import os
import argparse
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Setup paths - go up two levels from scripts/test to project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner

# Conversation shortcuts for starting at different points
CONVERSATION_MAP = {
    'fetch': 9144,      # Fetch Jobs from Deutsche Bank API
    'validate': 9193,   # Validate Job Description
    'extract': 3335,    # Extract job summary (AI)
    'grade': 3336,      # Grade with gemma2 (AI)
    'improve': 3338,    # Improve summary (AI)
    'format': 3341,     # Format Standardization (AI)
    'skills': 9121,     # Extract skills (AI)
    'ihl': 9161,        # IHL scoring chain (AI)
}


def run_registry_maintenance(conn, max_skills: int = 50) -> dict:
    """
    Run WF3005 - Entity Registry - Skill Maintenance.
    
    This resolves unmatched skills by:
    1. TRIAGE: ALIAS/NEW/SPLIT/SKIP decision
    2. CATEGORIZE: Assign to parent domain
    3. DEBATE: Multi-model verification
    4. SAVE: Record to registry_decisions
    
    NOTE: This replaced WF3002 as of 2025-12-08.
    
    Returns:
        dict with resolved/remaining counts
    """
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check orphan count in entities
    cursor.execute("""
        SELECT COUNT(*) as cnt 
        FROM entities e
        WHERE e.entity_type = 'skill' AND e.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er 
              WHERE er.entity_id = e.entity_id AND er.relationship = 'child_of'
          )
    """)
    before_count = cursor.fetchone()['cnt']
    
    if before_count == 0:
        print("\n✅ No orphan skills to process!")
        return {'resolved': 0, 'remaining': 0}
    
    print(f"\n🔧 Running Entity Registry - Skill Maintenance (WF3005)")
    print(f"   Orphan skills: {before_count}")
    print(f"   Processing in batches of 25...")
    
    # Start WF3005
    result = start_workflow(
        conn,
        workflow_id=3005,
        posting_id=None,
        start_conversation_id=9229,  # entity_orphan_fetcher
        params={'max_skills': max_skills}
    )
    
    print(f"   workflow_run_id: {result['workflow_run_id']}")
    
    # Run wave
    runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
    wave_result = runner.run(max_iterations=500)
    
    # Check results
    cursor.execute("""
        SELECT COUNT(*) as cnt 
        FROM entities e
        WHERE e.entity_type = 'skill' AND e.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er 
              WHERE er.entity_id = e.entity_id AND er.relationship = 'child_of'
          )
    """)
    after_count = cursor.fetchone()['cnt']
    resolved = before_count - after_count
    
    print(f"\n📊 Registry Maintenance Results:")
    print(f"   Skills categorized: {resolved}")
    print(f"   Remaining orphans: {after_count}")
    
    return {'resolved': resolved, 'remaining': after_count}


def run_workflow(posting_id: int = None, start_from: str = None, max_iterations: int = 20,
                 fetch_jobs: bool = False, max_jobs: int = 1, resume: bool = False,
                 with_registry: bool = False, max_skills: int = 50):
    """Run workflow 3001 on a posting or fetch new jobs first."""
    
    # Load environment
    load_dotenv()
    
    # Connect to database
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="turing",
        user="base_admin",
        password="base_yoga_secure_2025"
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # If --resume flag, just process existing pending interactions
        if resume:
            cursor.execute("""
                SELECT COUNT(*) as pending 
                FROM interactions 
                WHERE status = 'pending' AND enabled = true AND invalidated = false
            """)
            pending = cursor.fetchone()['pending']
            
            if pending == 0:
                print("✅ No pending interactions to resume!")
                # Still run taxonomy if requested
                if with_registry:
                    run_registry_maintenance(conn, max_skills=max_skills)
                return
            
            print(f"🔄 Resuming {pending} pending interactions...")
            print("=" * 70)
            
            # Run WaveRunner in global_batch mode (processes ALL pending)
            runner = WaveRunner(conn, global_batch=True)
            wave_result = runner.run(max_iterations=max_iterations)
            
            print("\n" + "=" * 70)
            print("✅ Resume completed!")
            print(f"   Interactions completed: {wave_result['interactions_completed']}")
            print(f"   Interactions failed: {wave_result['interactions_failed']}")
            print(f"   Iterations: {wave_result['iterations']}")
            print(f"   Duration: {wave_result['duration_ms']/1000:.2f}s")
            
            # Run taxonomy maintenance if requested
            if with_registry:
                run_registry_maintenance(conn, max_skills=max_skills)
            return
        
        # If --fetch flag, run the fetcher first
        if fetch_jobs:
            print(f"🔄 Fetching up to {max_jobs} jobs from Deutsche Bank API...")
            
            # Start workflow at fetch conversation (9144)
            result = start_workflow(
                conn,
                workflow_id=3001,
                posting_id=None,  # No posting yet - we're fetching
                start_conversation_id=9144,
                params={'max_jobs': max_jobs, 'skip_rate_limit': True}
            )
            
            print(f"   workflow_run_id: {result['workflow_run_id']}")
            print(f"   seed_interaction_id: {result['seed_interaction_id']}")
            
            # Run the full workflow - fetch will fan out to all pending postings
            # The db_job_fetcher returns ALL postings needing processing (not just new ones)
            print(f"\n🌊 Running Wave Runner (max {max_iterations} iterations)...")
            print("=" * 70)
            
            runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
            wave_result = runner.run(max_iterations=max_iterations)
            
            print("\n" + "=" * 70)
            print("✅ Workflow execution completed!")
            print(f"   Interactions completed: {wave_result['interactions_completed']}")
            print(f"   Interactions failed: {wave_result['interactions_failed']}")
            print(f"   Iterations: {wave_result['iterations']}")
            print(f"   Duration: {wave_result['duration_ms']/1000:.2f}s")
            
            # Show summary of what was processed
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT posting_id) as postings_processed,
                    COUNT(*) as total_interactions
                FROM interactions
                WHERE workflow_run_id = %s
            """, (result['workflow_run_id'],))
            stats = cursor.fetchone()
            print(f"\n📊 Summary:")
            print(f"   Postings processed: {stats['postings_processed']}")
            print(f"   Total interactions: {stats['total_interactions']}")
            
            # Run taxonomy maintenance if requested
            if with_registry:
                run_registry_maintenance(conn, max_skills=max_skills)
            
            return  # Done - no need to process individual posting
            
        # Verify posting exists (only for --posting-id mode)
        if not posting_id:
            print("❌ No posting_id specified. Use --posting-id or --fetch")
            return
        
        cursor.execute("SELECT posting_id, posting_name FROM postings WHERE posting_id = %s", (posting_id,))
        posting = cursor.fetchone()
        if not posting:
            print(f"❌ Posting {posting_id} not found")
            return
        
        # Determine starting conversation
        start_conversation_id = None
        if start_from:
            if start_from not in CONVERSATION_MAP:
                print(f"❌ Unknown start point: {start_from}")
                print(f"   Available: {', '.join(CONVERSATION_MAP.keys())}")
                return
            start_conversation_id = CONVERSATION_MAP[start_from]
        elif not fetch_jobs:
            # If not fetching and no start_from, start at validate (skip fetch)
            start_conversation_id = CONVERSATION_MAP['validate']
        
        # Start workflow
        print(f"🚀 Starting workflow 3001 for posting {posting_id}...")
        if start_from:
            print(f"   Starting from: {start_from} (conversation {start_conversation_id})")
        
        result = start_workflow(
            conn,
            workflow_id=3001,
            posting_id=posting_id,
            start_conversation_id=start_conversation_id
        )
        
        print(f"\n✅ Workflow initialized!")
        print(f"   workflow_run_id: {result['workflow_run_id']}")
        print(f"   seed_interaction_id: {result['seed_interaction_id']}")
        print(f"   first_conversation: {result['first_conversation_name']}")
        
        # Run Wave Runner
        print(f"\n🌊 Running Wave Runner (max {max_iterations} iterations)...")
        print("=" * 70)
        
        runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
        wave_result = runner.run(max_iterations=max_iterations)
        
        print("\n" + "=" * 70)
        print("✅ Workflow execution completed!")
        print(f"   Interactions completed: {wave_result['interactions_completed']}")
        print(f"   Interactions failed: {wave_result['interactions_failed']}")
        print(f"   Iterations: {wave_result['iterations']}")
        print(f"   Duration: {wave_result['duration_ms']/1000:.2f}s")
        
        # Show summary
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM interactions
            WHERE workflow_run_id = %s
        """, (result['workflow_run_id'],))
        
        stats = cursor.fetchone()
        print(f"\n📊 Interaction Summary:")
        print(f"   Total: {stats['total']}")
        print(f"   Completed: {stats['completed']}")
        print(f"   Pending: {stats['pending']}")
        print(f"   Failed: {stats['failed']}")
        
        print(f"\n🔍 To view details:")
        print(f"   SELECT * FROM interactions WHERE workflow_run_id = {result['workflow_run_id']};")
        
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run workflow 3001 - Complete Job Processing Pipeline')
    parser.add_argument('--posting-id', type=int, help='Posting ID to process (optional if --fetch or --resume)')
    parser.add_argument('--fetch', action='store_true', help='Fetch new jobs from API first')
    parser.add_argument('--resume', action='store_true', help='Resume processing existing pending interactions')
    parser.add_argument('--max-jobs', type=int, default=1, help='Max jobs to fetch (default: 1)')
    parser.add_argument('--start-from', choices=list(CONVERSATION_MAP.keys()),
                       help='Start from specific step (default: validate, or fetch if --fetch)')
    parser.add_argument('--max-iterations', type=int, default=5000,
                       help='Maximum Wave Runner iterations (default: 5000)')
    parser.add_argument('--with-registry', action='store_true',
                       help='Run WF3005 Entity Registry skill maintenance after job processing')
    parser.add_argument('--max-skills', type=int, default=50,
                       help='Max skills to process in registry maintenance (default: 50)')
    
    args = parser.parse_args()
    
    # Default to --resume if no mode specified
    if not args.posting_id and not args.fetch and not args.resume:
        args.resume = True
    
    run_workflow(
        posting_id=args.posting_id,
        start_from=args.start_from,
        max_iterations=args.max_iterations,
        fetch_jobs=args.fetch,
        max_jobs=args.max_jobs,
        resume=args.resume,
        with_registry=args.with_registry,
        max_skills=args.max_skills
    )
