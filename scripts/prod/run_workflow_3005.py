#!/usr/bin/env python3
"""
Runner for Workflow 3005 - Hierarchy Consultation

Batch categorizes orphan skills using classifier + grader pattern.
All logic is in Turing (conversations, instructions). This script just starts the runner.

Usage:
    python3 scripts/prod/run_workflow_3005.py
    python3 scripts/prod/run_workflow_3005.py --max-iterations 100

Author: Sandy
Date: December 7, 2025
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
from core.wave_runner.actors.entity_registry_exporter import execute as export_registry


def _export_registry():
    """Export entity registry to INDEX.md"""
    load_dotenv()
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    result = export_registry({}, conn)
    conn.close()
    if result.get('status') == 'success':
        print(f"\n📄 Registry exported to: entity_registry/INDEX.md")
    else:
        print(f"\n⚠️  Export failed: {result.get('error')}")


def run_workflow(max_iterations: int = 50):
    """Run workflow 3005 for hierarchy consultation."""
    
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Check current orphan count - skills without 'is_a' relationship to a domain
        cursor.execute("""
            SELECT COUNT(*) as orphan_count
            FROM entities e
            WHERE e.entity_type = 'skill'
              AND e.status = 'active'
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relationships er 
                  WHERE er.entity_id = e.entity_id 
                  AND er.relationship = 'is_a'
              )
        """)
        orphan_count = cursor.fetchone()['orphan_count']
        print(f"📊 Orphan skills to process: {orphan_count}")
        
        if orphan_count == 0:
            print("✅ No orphan skills to process!")
            # Still export the registry
            _export_registry()
            return
        
        # Check existing decisions
        cursor.execute("""
            SELECT COUNT(*) as decision_count,
                   COUNT(*) FILTER (WHERE review_status = 'auto_approved') as auto_approved,
                   COUNT(*) FILTER (WHERE review_status = 'pending') as pending
            FROM registry_decisions
            WHERE decision_type = 'skill_domain_mapping'
        """)
        decisions = cursor.fetchone()
        print(f"   Existing decisions: {decisions['decision_count']} (auto: {decisions['auto_approved']}, pending: {decisions['pending']})")
        
        # Get first conversation
        cursor.execute("""
            SELECT conversation_id FROM conversations 
            WHERE canonical_name = 'w3005_c1_fetch'
        """)
        start_conv = cursor.fetchone()
        if not start_conv:
            print("❌ Error: Conversation w3005_c1_fetch not found!")
            return
        
        # Start workflow 3005
        print(f"\n🚀 Starting Workflow 3005: Hierarchy Consultation")
        print(f"   Max iterations: {max_iterations}")
        
        result = start_workflow(
            conn,
            workflow_id=3005,
            posting_id=None,  # Not posting-centric
            start_conversation_id=start_conv['conversation_id'],
            params={}
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
            SELECT COUNT(*) as decision_count,
                   COUNT(*) FILTER (WHERE review_status = 'auto_approved') as auto_approved,
                   COUNT(*) FILTER (WHERE review_status = 'pending') as pending
            FROM registry_decisions
            WHERE decision_type = 'assign'
        """)
        decisions_after = cursor.fetchone()
        new_decisions = decisions_after['decision_count'] - decisions['decision_count']
        
        print(f"\n📊 Results:")
        print(f"   New decisions: {new_decisions}")
        print(f"   Total auto-approved: {decisions_after['auto_approved']}")
        print(f"   Total pending QA: {decisions_after['pending']}")
        
        # Export registry at the end
        _export_registry()
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Run Workflow 3005: Hierarchy Consultation')
    parser.add_argument('--max-iterations', type=int, default=50,
                        help='Maximum Wave Runner iterations (default: 50)')
    
    args = parser.parse_args()
    run_workflow(max_iterations=args.max_iterations)


if __name__ == '__main__':
    main()
