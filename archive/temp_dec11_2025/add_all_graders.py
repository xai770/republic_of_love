#!/usr/bin/env python3
"""
Add grading sessions for all non-specialist models
Excludes: codegemma:2b, codegemma:latest, qwen2.5vl:latest
Already tested: gemma3:1b (S2), llama3.2:latest (S3), granite3.1-moe:3b (S4), llama3.2:1b (S5)
"""

import sqlite3
import sys

DB_PATH = '/home/xai/Documents/ty_learn/data/llmcore.db'

# Models to test as graders (excluding specialists and already tested)
GRADERS_TO_ADD = [
    'dolphin3:8b',
    'dolphin3:latest',
    'gemma2:latest',
    'gemma3:4b',
    'gemma3n:e2b',
    'gemma3n:latest',
    'mistral-nemo:12b',
    'mistral:latest',
    'olmo2:latest',
    'phi3:3.8b',
    'phi3:latest',
    'phi4-mini:latest',
    'qwen2.5:7b',
    'qwen3:0.6b',
    'qwen3:1.7b',
    'qwen3:4b',
]

def add_grading_sessions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all joke generation recipes
    cursor.execute("""
        SELECT recipe_id FROM recipes 
        WHERE canonical_code = 'og_generate_and_grade_joke'
        ORDER BY recipe_id
    """)
    recipe_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"🚀 Adding grading sessions for {len(GRADERS_TO_ADD)} models")
    print(f"Found {len(recipe_ids)} recipes for 'og_generate_and_grade_joke'")
    
    session_number = 6  # Starting from Session 6
    total_added = 0
    
    for grader_model in GRADERS_TO_ADD:
        session_name = f"regrade_joke_{grader_model.replace(':', '_').replace('.', '_')}"
        print(f"\n📝 Session {session_number}: {grader_model}")
        
        for recipe_id in recipe_ids:
            # Get Session 1 (joke generation) for this recipe to set dependency
            cursor.execute("""
                SELECT session_id FROM sessions 
                WHERE recipe_id = ? AND session_number = 1
            """, (recipe_id,))
            session1_result = cursor.fetchone()
            
            if not session1_result:
                print(f"  ⚠️  Recipe {recipe_id}: No Session 1 found, skipping")
                continue
                
            session1_id = session1_result[0]
            
            # Add the grading session
            cursor.execute("""
                INSERT INTO sessions (
                    recipe_id, session_number, session_name, 
                    actor_id, depends_on_session_id, context_strategy,
                    maintain_llm_context
                ) VALUES (?, ?, ?, ?, ?, 'none', 0)
            """, (recipe_id, session_number, session_name, grader_model, session1_id))
            
            new_session_id = cursor.lastrowid
            
            # Add the grading instruction
            cursor.execute("""
                INSERT INTO instructions (
                    session_id, step_number, prompt_template, timeout_seconds
                ) VALUES (?, 1, ?, 60)
            """, (new_session_id, f"""Read the following joke and rate its quality:

{{step1_response}}

Answer these three questions:
1. Is this actually a joke? (YES/NO)
2. Rate the quality: EXCELLENT, GOOD, MEDIOCRE, or BAD
3. Why did you give this rating?

Format your response EXACTLY like this:
IS_JOKE: [YES/NO]
QUALITY: [EXCELLENT/GOOD/MEDIOCRE/BAD]
REASON: [Your explanation]"""))
            
            total_added += 1
        
        print(f"  ✅ Added Session {session_number} to {len(recipe_ids)} recipes")
        session_number += 1
    
    conn.commit()
    
    # Verify and show summary
    cursor.execute("""
        SELECT session_number, actor_id, COUNT(*) as count
        FROM sessions 
        WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke')
        AND session_number >= 6
        GROUP BY session_number, actor_id
        ORDER BY session_number
    """)
    
    print("\n" + "="*70)
    print("✅ Successfully added grading sessions!")
    print("="*70)
    print("\nSession Summary:")
    for row in cursor.fetchall():
        print(f"  Session {row[0]}: {row[1]} ({row[2]} recipes)")
    
    # Check total recipe_runs
    cursor.execute("""
        SELECT COUNT(*) FROM recipe_runs 
        WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke')
    """)
    total_runs = cursor.fetchone()[0]
    
    print(f"\n📊 Total recipe_runs: {total_runs}")
    print(f"💡 Ready to grade {total_runs} jokes with {len(GRADERS_TO_ADD)} new graders!")
    print(f"⏱️  Estimated time: ~{len(GRADERS_TO_ADD) * 10} minutes at 1.5s/joke")
    
    conn.close()

if __name__ == '__main__':
    try:
        add_grading_sessions()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
