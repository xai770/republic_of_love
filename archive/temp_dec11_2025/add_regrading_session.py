"""
Add Session 3 to existing joke generation recipes for regrading with better graders

This script adds a third session to the og_generate_and_grade_joke recipes that:
- Uses {step1_response} to access the original generated joke
- Grades with llama3.2:latest (recommended grader)
- Can be run without regenerating jokes (reuses existing data)

Usage:
    python3 temp/add_regrading_session.py
"""

import sqlite3
import sys

DB_PATH = '/home/xai/Documents/ty_learn/data/llmcore.db'

# Grading prompt (same as session 2, just different grader)
GRADING_PROMPT = """Read the following joke and rate its quality:

{step1_response}

Answer these three questions:
1. Is this actually a joke? (YES or NO)
2. How would you rate its quality? (EXCELLENT, GOOD, MEDIOCRE, or BAD)
3. Why? (Brief explanation)

Format your response exactly like this:
IS_JOKE: [YES or NO]
QUALITY: [EXCELLENT, GOOD, MEDIOCRE, or BAD]
REASON: [Your brief explanation]"""


def add_regrading_session(canonical_code='og_generate_and_grade_joke', 
                          grader_actor='llama3.2:latest',
                          session_name='regrade_joke_llama'):
    """Add session 3 to all recipes in the canonical for regrading"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get all recipes for this canonical
        cursor.execute("""
            SELECT recipe_id, canonical_code
            FROM recipes
            WHERE canonical_code = ?
        """, (canonical_code,))
        
        recipes = cursor.fetchall()
        
        if not recipes:
            print(f"❌ No recipes found for canonical '{canonical_code}'")
            return
        
        print(f"Found {len(recipes)} recipes for '{canonical_code}'")
        print(f"Adding Session 3: '{session_name}' with grader: {grader_actor}")
        
        sessions_added = 0
        
        for recipe_id, canon in recipes:
            # Check if session 3 already exists
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE recipe_id = ? AND session_number = 3
            """, (recipe_id,))
            
            if cursor.fetchone():
                print(f"  Recipe {recipe_id}: Session 3 already exists, skipping")
                continue
            
            # Get session_id for Session 1 (the depends_on_session_id)
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE recipe_id = ? AND session_number = 1
            """, (recipe_id,))
            
            session1_result = cursor.fetchone()
            if not session1_result:
                print(f"  Recipe {recipe_id}: Session 1 not found, skipping")
                continue
            
            session1_id = session1_result[0]
            
            # Create session 3
            cursor.execute("""
                INSERT INTO sessions (recipe_id, session_number, session_name, actor_id, depends_on_session_id)
                VALUES (?, 3, ?, ?, ?)
            """, (recipe_id, session_name, grader_actor, session1_id))
            
            session_id = cursor.lastrowid
            
            # Create instruction for session 3
            cursor.execute("""
                INSERT INTO instructions (
                    session_id, step_number, step_description, 
                    prompt_template, timeout_seconds
                )
                VALUES (?, 1, 'Regrade joke with better grader', ?, 30)
            """, (session_id, GRADING_PROMPT))
            
            sessions_added += 1
            print(f"  ✅ Recipe {recipe_id}: Added Session 3 (session_id={session_id})")
        
        conn.commit()
        print(f"\n✅ Successfully added {sessions_added} regrading sessions!")
        print(f"\nNext steps:")
        print(f"1. Create recipe_runs for the updated recipes")
        print(f"2. Run the test runner - it will execute Session 3 using existing joke data from Session 1")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


def create_recipe_runs_for_regrading():
    """Create recipe_runs for the regrading (reuses existing variations and batches)"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get all existing successful recipe_runs
        cursor.execute("""
            SELECT recipe_run_id, recipe_id, variation_id, batch_id
            FROM recipe_runs
            WHERE recipe_id IN (
                SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke'
            )
            AND status = 'SUCCESS'
            ORDER BY recipe_run_id
        """)
        
        existing_runs = cursor.fetchall()
        print(f"Found {len(existing_runs)} existing successful recipe_runs")
        
        # For each existing run, check if session 3 has been executed
        runs_needing_session3 = []
        
        for recipe_run_id, recipe_id, variation_id, batch_id in existing_runs:
            # Check if session 3 exists for this recipe
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE recipe_id = ? AND session_number = 3
            """, (recipe_id,))
            
            if not cursor.fetchone():
                continue  # Recipe doesn't have session 3 yet
            
            # Check if session 3 has been run for this recipe_run
            cursor.execute("""
                SELECT session_run_id FROM session_runs
                WHERE recipe_run_id = ? AND session_number = 3
            """, (recipe_run_id,))
            
            if not cursor.fetchone():
                runs_needing_session3.append(recipe_run_id)
        
        if runs_needing_session3:
            print(f"\n✅ {len(runs_needing_session3)} recipe_runs need Session 3 execution")
            print(f"   Recipe run IDs: {runs_needing_session3[:10]}..." if len(runs_needing_session3) > 10 else f"   Recipe run IDs: {runs_needing_session3}")
            print(f"\n💡 These recipe_runs already have status='SUCCESS' but need Session 3")
            print(f"   The runner will detect incomplete sessions and execute Session 3 automatically")
        else:
            print(f"\n✅ All recipe_runs have completed Session 3!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Add regrading session to joke generation recipes')
    parser.add_argument('--grader', default='llama3.2:latest', help='Actor to use for regrading')
    parser.add_argument('--check', action='store_true', help='Just check status, don\'t add sessions')
    
    args = parser.parse_args()
    
    if args.check:
        print("🔍 Checking regrading status...")
        create_recipe_runs_for_regrading()
    else:
        print(f"🚀 Adding regrading session with grader: {args.grader}")
        add_regrading_session(grader_actor=args.grader)
        print("\n" + "="*70)
        create_recipe_runs_for_regrading()
