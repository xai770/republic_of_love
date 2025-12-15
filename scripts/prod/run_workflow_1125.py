#!/usr/bin/env python3
"""
WF1125: Multi-Agent Profile Career Deep Analysis

Runs 5 specialized expert agents in parallel to extract comprehensive skills:
- Technical Skills Extractor (with review step)
- Domain Expert
- Leadership Coach
- Creative Director
- Business Analyst

Then synthesizes all outputs and saves to profile_skills table.

Usage:
    python3 scripts/prod/run_workflow_1125.py --profile-id 1
    python3 scripts/prod/run_workflow_1125.py --profile-id 1 --dry-run
"""

import sys
import os
import argparse
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.wave_runner.runner import WaveRunner


def get_db_connection():
    """Get database connection."""
    load_dotenv()
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="turing",
        user="base_admin",
        password="base_yoga_secure_2025"
    )


def get_profile_text(conn, profile_id: int) -> str:
    """Fetch profile_raw_text from profiles table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT profile_raw_text 
            FROM profiles 
            WHERE profile_id = %s
        """, (profile_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Profile {profile_id} not found")
        return row[0]


# Parallel entry point conversations for WF1125
PARALLEL_CONVERSATIONS = [
    9208,  # Technical Skills Extractor
    9210,  # Domain Expert
    9211,  # Leadership Coach
    9212,  # Creative Director
    9213,  # Business Analyst
]


def create_parallel_seeds(conn, workflow_run_id: int, profile_id: int, profile_text: str):
    """Create seed interactions for all parallel entry points."""
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    seed_ids = []
    
    for conversation_id in PARALLEL_CONVERSATIONS:
        # Get conversation/actor info
        cursor.execute("""
            SELECT c.conversation_id, c.conversation_name, c.actor_id, a.actor_type
            FROM conversations c
            JOIN actors a ON c.actor_id = a.actor_id
            WHERE c.conversation_id = %s
        """, (conversation_id,))
        conv = cursor.fetchone()
        
        # Get prompt template
        cursor.execute("""
            SELECT prompt_template 
            FROM instructions 
            WHERE conversation_id = %s AND enabled = TRUE
            LIMIT 1
        """, (conversation_id,))
        instr = cursor.fetchone()
        
        # Build input - substitute placeholders
        prompt = instr['prompt_template'] if instr else 'Analyze the profile'
        prompt = prompt.replace('{profile_raw_text}', profile_text)
        prompt = prompt.replace('{profile_id}', str(profile_id))
        
        input_data = {
            'prompt': prompt,
            'params': {
                'profile_id': profile_id,
                'profile_raw_text': profile_text
            }
        }
        
        # Create seed interaction
        cursor.execute("""
            INSERT INTO interactions (
                posting_id,
                workflow_run_id,
                conversation_id,
                actor_id,
                actor_type,
                status,
                execution_order,
                input,
                input_interaction_ids
            ) VALUES (
                NULL, %s, %s, %s, %s,
                'pending',
                1,
                %s::jsonb,
                ARRAY[]::INT[]
            )
            RETURNING interaction_id
        """, (
            workflow_run_id,
            conv['conversation_id'],
            conv['actor_id'],
            conv['actor_type'],
            json.dumps(input_data)
        ))
        seed_id = cursor.fetchone()['interaction_id']
        seed_ids.append((conv['conversation_name'], seed_id))
        
    conn.commit()
    return seed_ids


def run_workflow_1125(profile_id: int, dry_run: bool = False, max_iterations: int = 50):
    """Run WF1125 for a specific profile."""
    
    print(f"\n{'='*60}")
    print(f"WF1125: Multi-Agent Profile Career Deep Analysis")
    print(f"Profile ID: {profile_id}")
    print(f"{'='*60}\n")
    
    # Get database connection
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Get profile text
        profile_text = get_profile_text(conn, profile_id)
        print(f"Profile text: {len(profile_text)} chars")
        
        if dry_run:
            print("\n[DRY RUN] Would run workflow with this profile text")
            print(f"First 500 chars:\n{profile_text[:500]}...")
            return
        
        # Create workflow_run manually with profile metadata
        metadata = json.dumps({'profile_id': profile_id})
        cursor.execute("""
            INSERT INTO workflow_runs (workflow_id, posting_id, status, environment, metadata)
            VALUES (1125, NULL, 'running', 'dev', %s::jsonb)
            RETURNING workflow_run_id
        """, (metadata,))
        workflow_run_id = cursor.fetchone()['workflow_run_id']
        conn.commit()
        
        print(f"Created workflow run: {workflow_run_id}")
        
        # Create all 5 parallel seed interactions
        print("\nCreating parallel seed interactions...")
        seed_ids = create_parallel_seeds(conn, workflow_run_id, profile_id, profile_text)
        for conv_name, seed_id in seed_ids:
            print(f"  - {seed_id}: {conv_name}")
        
        print("\nRunning experts in parallel (group 1)...")
        print("  - Technical Skills Extractor (mistral)")
        print("  - Domain Expert (qwen2.5)")
        print("  - Leadership Coach (mistral)")
        print("  - Creative Director (mistral)")
        print("  - Business Analyst (mistral)")
        print("\nThen: Tech Review → Synthesis → Save")
        print("\nThis will take ~5-6 minutes...\n")
        print("=" * 60)
        
        # Run the workflow
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        wave_result = runner.run(max_iterations=max_iterations)
        
        print("\n" + "=" * 60)
        print("✅ Workflow completed!")
        print(f"   Interactions completed: {wave_result['interactions_completed']}")
        print(f"   Interactions failed: {wave_result['interactions_failed']}")
        print(f"   Iterations: {wave_result['iterations']}")
        print(f"   Duration: {wave_result['duration_ms']/1000:.2f}s")
        
        # Show results summary
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM profile_skills 
            WHERE profile_id = %s
        """, (profile_id,))
        skill_count = cursor.fetchone()['cnt']
        print(f"\n📊 Skills in profile_skills: {skill_count}")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Run WF1125 Multi-Agent Skill Extraction')
    parser.add_argument('--profile-id', type=int, required=True, help='Profile ID to analyze')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run without executing')
    parser.add_argument('--max-iterations', type=int, default=50, help='Max WaveRunner iterations')
    
    args = parser.parse_args()
    
    run_workflow_1125(args.profile_id, args.dry_run, args.max_iterations)


if __name__ == '__main__':
    main()
