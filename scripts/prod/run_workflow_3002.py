#!/usr/bin/env python3
"""
Test Runner for Workflow 3002 - Skill Taxonomy Maintenance

Usage:
    # Test with 5 skills
    python3 scripts/prod/run_workflow_3002.py --max-skills 5
    
    # Process a specific skill
    python3 scripts/prod/run_workflow_3002.py --skill-name "Security Practices"

Author: Sandy
Date: December 4, 2025
"""

import sys
import os
import argparse
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Setup paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner


def run_workflow(max_skills: int = 10, skill_name: str = None, max_iterations: int = 50):
    """Run workflow 3002 for skill taxonomy maintenance."""
    
    load_dotenv()
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="turing",
        user="base_admin",
        password="base_yoga_secure_2025"
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Check current state
        cursor.execute("""
            SELECT COUNT(*) as unmatched 
            FROM posting_skills 
            WHERE skill_id IS NULL
              AND raw_skill_name IS NOT NULL
        """)
        unmatched = cursor.fetchone()['unmatched']
        print(f"📊 Unmatched skills before: {unmatched}")
        
        if unmatched == 0:
            print("✅ No unmatched skills to process!")
            return
        
        # Start workflow 3002
        print(f"🚀 Starting Workflow 3002: Skill Taxonomy Maintenance")
        print(f"   Max skills: {max_skills}")
        
        # Pass parameters via workflow starter
        result = start_workflow(
            conn,
            workflow_id=3002,
            posting_id=None,  # Not posting-centric
            start_conversation_id=9201,  # Fetch Unmatched Skills
            params={'max_skills': max_skills, 'min_occurrences': 1}
        )
        
        print(f"   workflow_run_id: {result['workflow_run_id']}")
        print(f"   seed_interaction_id: {result['seed_interaction_id']}")
        
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
        
        # Check results
        cursor.execute("""
            SELECT COUNT(*) as unmatched 
            FROM posting_skills 
            WHERE skill_id IS NULL
              AND raw_skill_name IS NOT NULL
        """)
        unmatched_after = cursor.fetchone()['unmatched']
        resolved = unmatched - unmatched_after
        
        print(f"\n📊 Results:")
        print(f"   Skills resolved: {resolved}")
        print(f"   Remaining unmatched: {unmatched_after}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Run Workflow 3002: Skill Taxonomy Maintenance')
    parser.add_argument('--max-skills', type=int, default=10,
                        help='Maximum number of skills to process (default: 10)')
    parser.add_argument('--skill-name', type=str,
                        help='Process a specific skill by name')
    parser.add_argument('--max-iterations', type=int, default=50,
                        help='Maximum Wave Runner iterations (default: 50)')
    
    args = parser.parse_args()
    
    run_workflow(
        max_skills=args.max_skills,
        skill_name=args.skill_name,
        max_iterations=args.max_iterations
    )


if __name__ == '__main__':
    main()
