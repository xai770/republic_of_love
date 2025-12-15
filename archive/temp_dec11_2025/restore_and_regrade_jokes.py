"""
Restore joke data from CSV and add llama3.2:latest regrading

This script:
1. Reads joke_review_20251021.csv with all the original jokes
2. Recreates session_runs and instruction_runs for Sessions 1 & 2 (with SUCCESS status)
3. Keeps recipe_runs as PENDING so Session 3 will execute
4. Session 3 will use {step1_response} from the restored Session 1 data

Usage:
    python3 temp/restore_and_regrade_jokes.py
"""

import sqlite3
import csv
import sys
from datetime import datetime

DB_PATH = '/home/xai/Documents/ty_learn/data/llmcore.db'
CSV_PATH = '/home/xai/Documents/ty_learn/reports/joke_review_20251021.csv'


def restore_joke_data():
    """Restore joke data from CSV back into database"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("📖 Reading joke data from CSV...")
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            jokes_data = list(reader)
        
        print(f"   Found {len(jokes_data)} jokes in CSV")
        
        restored_count = 0
        skipped_count = 0
        
        for row in jokes_data:
            recipe_run_id = int(row['recipe_run_id'])
            comedian = row['comedian']
            topic = row['topic']
            batch_id = int(row['batch_id'])
            joke = row['joke']
            gen_time_ms = int(row['gen_time_ms'])
            grade_response = f"IS_JOKE: {row['is_joke']}\nQUALITY: {row['quality']}\nREASON: {row['reason']}"
            grade_time_ms = int(row['grade_time_ms'])
            
            # Get recipe_id for this recipe_run
            cursor.execute("SELECT recipe_id FROM recipe_runs WHERE recipe_run_id = ?", (recipe_run_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"   ⚠️  Recipe run {recipe_run_id} not found, skipping")
                skipped_count += 1
                continue
            
            recipe_id = result[0]
            
            # Get session IDs for this recipe
            cursor.execute("""
                SELECT session_id, session_number FROM sessions 
                WHERE recipe_id = ? AND session_number IN (1, 2)
                ORDER BY session_number
            """, (recipe_id,))
            
            sessions = cursor.fetchall()
            if len(sessions) != 2:
                print(f"   ⚠️  Recipe {recipe_id} doesn't have sessions 1 & 2, skipping")
                skipped_count += 1
                continue
            
            session1_id = sessions[0][0]
            session2_id = sessions[1][0]
            
            # Check if session_runs already exist
            cursor.execute("""
                SELECT session_run_id FROM session_runs 
                WHERE recipe_run_id = ? AND session_number IN (1, 2)
            """, (recipe_run_id,))
            
            if cursor.fetchall():
                skipped_count += 1
                continue  # Already restored
            
            # Create session_run for Session 1 (generation)
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO session_runs (recipe_run_id, session_id, session_number, started_at, completed_at, status)
                VALUES (?, ?, 1, ?, ?, 'SUCCESS')
            """, (recipe_run_id, session1_id, timestamp, timestamp))
            
            session1_run_id = cursor.lastrowid
            
            # Get instruction_id for session 1
            cursor.execute("SELECT instruction_id FROM instructions WHERE session_id = ? AND step_number = 1", (session1_id,))
            instruction1_id = cursor.fetchone()[0]
            
            # Create instruction_run for Session 1 (the joke)
            cursor.execute("""
                INSERT INTO instruction_runs (
                    session_run_id, recipe_run_id, instruction_id, step_number,
                    prompt_rendered, response_received, latency_ms, status, timestamp
                )
                VALUES (?, ?, ?, 1, '', ?, ?, 'SUCCESS', ?)
            """, (session1_run_id, recipe_run_id, instruction1_id, joke, gen_time_ms, timestamp))
            
            # Create session_run for Session 2 (grading)
            cursor.execute("""
                INSERT INTO session_runs (recipe_run_id, session_id, session_number, started_at, completed_at, status)
                VALUES (?, ?, 2, ?, ?, 'SUCCESS')
            """, (recipe_run_id, session2_id, timestamp, timestamp))
            
            session2_run_id = cursor.lastrowid
            
            # Get instruction_id for session 2
            cursor.execute("SELECT instruction_id FROM instructions WHERE session_id = ? AND step_number = 1", (session2_id,))
            instruction2_id = cursor.fetchone()[0]
            
            # Create instruction_run for Session 2 (the grade)
            cursor.execute("""
                INSERT INTO instruction_runs (
                    session_run_id, recipe_run_id, instruction_id, step_number,
                    prompt_rendered, response_received, latency_ms, status, timestamp
                )
                VALUES (?, ?, ?, 1, '', ?, ?, 'SUCCESS', ?)
            """, (session2_run_id, recipe_run_id, instruction2_id, grade_response, grade_time_ms, timestamp))
            
            restored_count += 1
            
            if restored_count % 50 == 0:
                print(f"   Restored {restored_count} jokes...")
        
        conn.commit()
        
        print(f"\n✅ Successfully restored {restored_count} jokes!")
        print(f"   Skipped {skipped_count} (already exist or missing recipe data)")
        
        # Verify restoration
        cursor.execute("""
            SELECT COUNT(*) FROM session_runs sr
            JOIN recipe_runs rr ON sr.recipe_run_id = rr.recipe_run_id
            JOIN recipes r ON rr.recipe_id = r.recipe_id
            WHERE r.canonical_code = 'og_generate_and_grade_joke'
                AND sr.session_number IN (1, 2)
                AND sr.status = 'SUCCESS'
        """)
        
        total_restored = cursor.fetchone()[0]
        print(f"\n📊 Total session_runs (Sessions 1 & 2): {total_restored}")
        print(f"   Expected: {restored_count * 2} (2 sessions per joke)")
        
        # Check recipe_runs status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM recipe_runs 
            WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke')
            GROUP BY status
        """)
        
        print(f"\n📋 Recipe runs status:")
        for status, count in cursor.fetchall():
            print(f"   {status}: {count}")
        
        print(f"\n💡 Next step: Run the test runner to execute Session 3 (llama3.2:latest regrading)")
        print(f"   Command: python3 recipe_run_test_runner_v31.py")
        print(f"\n   The runner will:")
        print(f"   - ✅ Skip Session 1 (already SUCCESS)")
        print(f"   - ✅ Skip Session 2 (already SUCCESS)")
        print(f"   - 🚀 Execute Session 3 (new llama3.2:latest grading)")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    restore_joke_data()
