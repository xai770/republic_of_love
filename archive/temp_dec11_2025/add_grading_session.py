"""
Add a new grading session to existing joke generation recipes

This script adds a grading session to the og_generate_and_grade_joke recipes that:
- Uses {step1_response} to access the original generated joke
- Grades with a specified grader model
- Can be run without regenerating jokes (reuses existing data)

Usage:
    python3 temp/add_grading_session.py --grader granite3.1-moe:3b --session-number 4
"""

import sqlite3
import sys
import argparse

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


def add_grading_session(canonical_code='og_generate_and_grade_joke', 
                        grader_actor='llama3.2:latest',
                        session_number=3,
                        session_name=None):
    """Add a grading session to all recipes in the canonical"""
    
    if session_name is None:
        # Generate default name based on grader
        grader_short = grader_actor.split(':')[0].replace('.', '')
        session_name = f'regrade_joke_{grader_short}'
    
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
        print(f"Adding Session {session_number}: '{session_name}' with grader: {grader_actor}")
        
        sessions_added = 0
        
        for recipe_id, canon in recipes:
            # Check if session already exists
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE recipe_id = ? AND session_number = ?
            """, (recipe_id, session_number))
            
            if cursor.fetchone():
                print(f"  Recipe {recipe_id}: Session {session_number} already exists, skipping")
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
            
            # Create the grading session
            cursor.execute("""
                INSERT INTO sessions (
                    recipe_id, session_number, session_name, session_description,
                    actor_id, depends_on_session_id, context_strategy
                )
                VALUES (?, ?, ?, ?, ?, ?, 'none')
            """, (recipe_id, session_number, session_name, 
                  f'Grade joke using {grader_actor}', grader_actor, session1_id))
            
            session_id = cursor.lastrowid
            
            # Create instruction for the grading session
            cursor.execute("""
                INSERT INTO instructions (
                    session_id, step_number, step_description, 
                    prompt_template, timeout_seconds
                )
                VALUES (?, 1, ?, ?, 30)
            """, (session_id, f'Grade joke with {grader_actor}', GRADING_PROMPT))
            
            sessions_added += 1
            print(f"  ✅ Recipe {recipe_id}: Added Session {session_number} (session_id={session_id})")
        
        conn.commit()
        print(f"\n✅ Successfully added {sessions_added} grading sessions!")
        print(f"\nNext steps:")
        print(f"1. Reset recipe_runs to PENDING (or let runner handle it)")
        print(f"2. Run the test runner - it will skip Sessions 1-{session_number-1} and execute Session {session_number}")
        
        return sessions_added
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


def check_session_status(session_number):
    """Check how many recipe_runs need the specified session"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get all existing recipe_runs for the canonical
        cursor.execute("""
            SELECT recipe_run_id, recipe_id, status
            FROM recipe_runs
            WHERE recipe_id IN (
                SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke'
            )
            ORDER BY recipe_run_id
        """)
        
        all_runs = cursor.fetchall()
        print(f"Found {len(all_runs)} total recipe_runs")
        
        # Count how many need the session
        runs_needing_session = 0
        runs_completed_session = 0
        
        for recipe_run_id, recipe_id, status in all_runs:
            # Check if this session exists for this recipe
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE recipe_id = ? AND session_number = ?
            """, (recipe_id, session_number))
            
            if not cursor.fetchone():
                continue  # Recipe doesn't have this session
            
            # Check if session has been run for this recipe_run
            cursor.execute("""
                SELECT status FROM session_runs
                WHERE recipe_run_id = ? AND session_number = ?
            """, (recipe_run_id, session_number))
            
            result = cursor.fetchone()
            if result:
                if result[0] == 'SUCCESS':
                    runs_completed_session += 1
            else:
                runs_needing_session += 1
        
        print(f"\n📊 Session {session_number} Status:")
        print(f"   ✅ Completed: {runs_completed_session}")
        print(f"   ⏳ Pending: {runs_needing_session}")
        
        if runs_needing_session > 0:
            print(f"\n💡 Ready to run Session {session_number} for {runs_needing_session} recipe_runs")
        else:
            print(f"\n🎉 All recipe_runs have completed Session {session_number}!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Add grading session to joke generation recipes')
    parser.add_argument('--grader', required=True, help='Actor to use for grading (e.g., granite3.1-moe:3b)')
    parser.add_argument('--session-number', type=int, default=4, help='Session number to create (default: 4)')
    parser.add_argument('--session-name', help='Custom session name (default: auto-generated from grader)')
    parser.add_argument('--check', action='store_true', help='Just check status, don\'t add sessions')
    
    args = parser.parse_args()
    
    if args.check:
        print(f"🔍 Checking Session {args.session_number} status...")
        check_session_status(args.session_number)
    else:
        print(f"🚀 Adding Session {args.session_number} with grader: {args.grader}")
        sessions_added = add_grading_session(
            grader_actor=args.grader,
            session_number=args.session_number,
            session_name=args.session_name
        )
        print("\n" + "="*70)
        check_session_status(args.session_number)
