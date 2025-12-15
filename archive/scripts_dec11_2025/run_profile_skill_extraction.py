#!/usr/bin/env python3
"""
Run Profile Skill Extraction (WF1122) for a specific profile.

Usage:
    python3 scripts/run_profile_skill_extraction.py --profile-id 1

This creates a workflow_run and seed interaction, then runs the workflow.
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()


def run_profile_skill_extraction(profile_id: int, dry_run: bool = False):
    """Run WF1122 for a profile."""
    
    WORKFLOW_ID = 1122
    FIRST_CONVERSATION_ID = 9204  # profile_skill_summary
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # 1. Get profile data
        cursor.execute("""
            SELECT profile_id, full_name, profile_raw_text, skills_extraction_status
            FROM profiles
            WHERE profile_id = %s
        """, (profile_id,))
        
        profile = cursor.fetchone()
        if not profile:
            print(f"❌ Profile {profile_id} not found")
            return False
        
        print(f"📋 Profile: {profile['full_name']} (ID: {profile_id})")
        print(f"   Text length: {len(profile['profile_raw_text'] or '')} chars")
        print(f"   Current extraction status: {profile['skills_extraction_status']}")
        
        if not profile['profile_raw_text']:
            print("❌ No profile_raw_text available")
            return False
        
        # 2. Get first conversation info
        cursor.execute("""
            SELECT 
                c.conversation_id,
                c.actor_id,
                a.actor_type,
                a.actor_name
            FROM conversations c
            JOIN actors a ON c.actor_id = a.actor_id
            WHERE c.conversation_id = %s
        """, (FIRST_CONVERSATION_ID,))
        
        first_conv = cursor.fetchone()
        if not first_conv:
            print(f"❌ Conversation {FIRST_CONVERSATION_ID} not found")
            return False
        
        print(f"   First step: {first_conv['actor_name']} ({first_conv['actor_type']})")
        
        # 3. Get prompt template
        cursor.execute("""
            SELECT prompt_template
            FROM instructions
            WHERE conversation_id = %s
              AND enabled = TRUE
            LIMIT 1
        """, (FIRST_CONVERSATION_ID,))
        
        instruction = cursor.fetchone()
        if not instruction:
            print(f"❌ No instruction found for conversation {FIRST_CONVERSATION_ID}")
            return False
        
        # 4. Build prompt with profile text
        prompt = instruction['prompt_template'].replace(
            '{profile_raw_text}', 
            profile['profile_raw_text']
        )
        
        seed_input = {
            'prompt': prompt,
            'profile_id': profile_id
        }
        
        if dry_run:
            print("\n🔍 DRY RUN - Would create:")
            print(f"   Workflow run for WF{WORKFLOW_ID}")
            print(f"   Seed interaction for conv {FIRST_CONVERSATION_ID}")
            print(f"   Prompt length: {len(prompt)} chars")
            return True
        
        # 5. Create workflow_run
        cursor.execute("""
            INSERT INTO workflow_runs (
                workflow_id, 
                status, 
                environment,
                metadata
            )
            VALUES (%s, 'running', 'dev', %s)
            RETURNING workflow_run_id
        """, (WORKFLOW_ID, json.dumps({'profile_id': profile_id})))
        
        workflow_run_id = cursor.fetchone()['workflow_run_id']
        print(f"\n✅ Created workflow_run {workflow_run_id}")
        
        # 6. Create seed interaction
        cursor.execute("""
            INSERT INTO interactions (
                workflow_run_id,
                conversation_id,
                actor_id,
                actor_type,
                status,
                execution_order,
                input,
                input_interaction_ids
            ) VALUES (
                %s, %s, %s, %s,
                'pending',
                1,
                %s::jsonb,
                ARRAY[]::INT[]
            )
            RETURNING interaction_id
        """, (
            workflow_run_id,
            first_conv['conversation_id'],
            first_conv['actor_id'],
            first_conv['actor_type'],
            json.dumps(seed_input)
        ))
        
        seed_interaction_id = cursor.fetchone()['interaction_id']
        print(f"✅ Created seed interaction {seed_interaction_id}")
        
        # 7. Link workflow_run to seed interaction
        cursor.execute("""
            UPDATE workflow_runs 
            SET seed_interaction_id = %s
            WHERE workflow_run_id = %s
        """, (seed_interaction_id, workflow_run_id))
        
        conn.commit()
        
        # 8. Run the workflow
        print(f"\n🚀 Running WaveRunner for workflow_run {workflow_run_id}...")
        
        from core.wave_runner.runner import WaveRunner
        
        runner = WaveRunner(
            db_conn=conn,
            global_batch=True,
            workflow_id=WORKFLOW_ID,
            runner_id=f'profile_skill_{profile_id}'
        )
        
        stats = runner.run(max_iterations=10)  # Should complete in few iterations
        
        print("\n" + "=" * 50)
        print("✅ WORKFLOW COMPLETE")
        print(f"   Completed: {stats['interactions_completed']}")
        print(f"   Failed: {stats['interactions_failed']}")
        print(f"   Duration: {stats['duration_ms'] / 1000:.1f}s")
        
        # 9. Check results
        cursor.execute("""
            SELECT COUNT(*) as skill_count
            FROM profile_skills
            WHERE profile_id = %s
        """, (profile_id,))
        
        skill_count = cursor.fetchone()['skill_count']
        print(f"\n📊 Skills saved for profile {profile_id}: {skill_count}")
        
        if skill_count > 0:
            cursor.execute("""
                SELECT sa.skill_alias, ps.proficiency_level
                FROM profile_skills ps
                JOIN skill_aliases sa ON ps.skill_id = sa.skill_id
                WHERE ps.profile_id = %s
                ORDER BY sa.skill_alias
                LIMIT 10
            """, (profile_id,))
            
            print("\nSample skills:")
            for row in cursor.fetchall():
                print(f"   - {row['skill_alias']} [{row['proficiency_level']}]")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Run Profile Skill Extraction (WF1122) for a profile'
    )
    parser.add_argument('--profile-id', type=int, required=True,
                        help='Profile ID to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    success = run_profile_skill_extraction(args.profile_id, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
