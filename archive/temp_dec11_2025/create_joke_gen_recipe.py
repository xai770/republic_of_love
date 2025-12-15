#!/usr/bin/env python3
"""
Create 2-Step "Generate and Grade Joke" Recipe
==============================================
Session 1: Generate joke (actor varies - testing different joke tellers)
Session 2: Grade joke (actor: gemma3:1b - our best classifier)

Uses step output passing: {step1_response} in Session 2 gets joke from Session 1
"""

import sqlite3
from datetime import datetime

DB_PATH = '/home/xai/Documents/ty_learn/data/llmcore.db'
CANONICAL_CODE = 'og_generate_and_grade_joke'
GRADER_MODEL = 'gemma3:1b'  # Our fastest and most accurate classifier

JOKE_GENERATION_PROMPT = """Tell me a funny joke about {variations_param_1}.

Make it original and creative. The joke should be:
- Family-friendly
- Easy to understand
- Actually funny!

Just tell the joke, nothing else."""

JOKE_GRADING_PROMPT = """Read the following joke and rate its quality:

{step1_response}

Answer these three questions:
1. Is this actually a joke? Answer ONLY: YES or NO
2. If yes, rate its quality: BAD, MEDIOCRE, GOOD, or EXCELLENT
3. Briefly explain why (one sentence)

Format your answer exactly like this:
IS_JOKE: [YES or NO]
QUALITY: [BAD, MEDIOCRE, GOOD, or EXCELLENT]
REASON: [your one-sentence explanation]"""

def get_enabled_models(conn):
    """Get list of enabled AI models (excluding reasoning models)"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT actor_id 
        FROM actors 
        WHERE enabled = 1 
          AND actor_type = 'ai_model'
        ORDER BY actor_id
    """)
    return [row[0] for row in cursor.fetchall()]

def create_canonical(conn):
    """Create canonical if it doesn't exist"""
    cursor = conn.cursor()
    
    # Check if it exists first
    cursor.execute("SELECT canonical_code FROM canonicals WHERE canonical_code = ?", (CANONICAL_CODE,))
    if cursor.fetchone():
        print(f"   ✅ Canonical '{CANONICAL_CODE}' already exists")
        return
    
    # Create it (canonicals needs prompt and response fields)
    cursor.execute("""
        INSERT INTO canonicals (canonical_code, facet_id, capability_description, prompt, response, enabled)
        VALUES (?, 'og', 'Generate an original joke and have it graded for quality by our best classifier', 
                'Generate a joke and grade it', '', 1)
    """, (CANONICAL_CODE,))
    
    print(f"   ✅ Created canonical '{CANONICAL_CODE}'")

def create_variations(conn):
    """Create joke topic variations"""
    cursor = conn.cursor()
    
    # Get first recipe_id for this canonical (we'll create recipes first)
    cursor.execute("""
        SELECT MIN(recipe_id) FROM recipes WHERE canonical_code = ?
    """, (CANONICAL_CODE,))
    
    result = cursor.fetchone()
    if result and result[0]:
        # Variations already exist, return them
        cursor.execute("""
            SELECT variation_id, variations_param_1, difficulty_level
            FROM variations
            WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = ?)
            ORDER BY difficulty_level
        """, (CANONICAL_CODE,))
        return cursor.fetchall()
    
    # We'll create variations after the first recipe
    return None

def create_recipe_for_model(conn, joke_teller_model):
    """Create a 2-session recipe: joke generation + grading"""
    cursor = conn.cursor()
    
    # 1. Create recipe
    cursor.execute("""
        INSERT INTO recipes (canonical_code, recipe_version, enabled)
        VALUES (?, 1, 1)
    """, (CANONICAL_CODE,))
    
    recipe_id = cursor.lastrowid
    print(f"  ✅ Created recipe {recipe_id} for joke teller: {joke_teller_model}")
    
    # 2. Create Session 1: Generate joke
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order,
            context_strategy, actor_id, enabled
        )
        VALUES (?, 1, 'generate_joke', 0, 1, 'none', ?, 1)
    """, (recipe_id, joke_teller_model))
    
    session1_id = cursor.lastrowid
    print(f"     Created session 1 (generate_joke) with {joke_teller_model}")
    
    # 3. Create instruction for Session 1
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled, is_terminal
        )
        VALUES (?, 1, 'Generate a joke on the given topic', ?, 30, 1, 0)
    """, (session1_id, JOKE_GENERATION_PROMPT))
    
    # 4. Create Session 2: Grade joke (depends on Session 1)
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order,
            context_strategy, actor_id, enabled,
            depends_on_session_id
        )
        VALUES (?, 2, 'grade_joke', 0, 2, 'none', ?, 1, ?)
    """, (recipe_id, GRADER_MODEL, session1_id))
    
    session2_id = cursor.lastrowid
    print(f"     Created session 2 (grade_joke) with {GRADER_MODEL}")
    
    # 5. Create instruction for Session 2 (uses {step1_response})
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled, is_terminal
        )
        VALUES (?, 1, 'Grade the joke quality', ?, 30, 1, 1)
    """, (session2_id, JOKE_GRADING_PROMPT))
    
    print(f"     Created instructions for both sessions")
    
    return recipe_id

def create_variations_for_recipe(conn, recipe_id):
    """Create joke topic variations for a recipe"""
    cursor = conn.cursor()
    
    topics = [
        ('programming', 1),
        ('cats and dogs', 2),
        ('food and cooking', 3),
        ('science and technology', 4),
        ('anything you want - be creative!', 5)
    ]
    
    variation_ids = []
    for topic, difficulty in topics:
        cursor.execute("""
            INSERT INTO variations (recipe_id, variations_param_1, difficulty_level)
            VALUES (?, ?, ?)
        """, (recipe_id, topic, difficulty))
        variation_ids.append(cursor.lastrowid)
    
    print(f"     Created {len(variation_ids)} variations (joke topics)")
    return variation_ids

def create_recipe_runs(conn, recipe_id, variation_ids, num_batches=3):
    """Create recipe_runs for all variations and batches"""
    cursor = conn.cursor()
    
    created_count = 0
    for variation_id in variation_ids:
        for batch_id in range(1, num_batches + 1):
            cursor.execute("""
                INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
                VALUES (?, ?, ?, 'PENDING')
            """, (recipe_id, variation_id, batch_id))
            created_count += 1
    
    print(f"     Created {created_count} recipe_runs (5 topics × {num_batches} batches)")
    return created_count

def main():
    """Main execution"""
    print("=" * 70)
    print("🎭 2-Step Recipe: Generate Joke + Grade It")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Create canonical
        print("\n📝 Creating canonical...")
        create_canonical(conn)
        print(f"   Canonical code: {CANONICAL_CODE}")
        
        # Get enabled models
        models = get_enabled_models(conn)
        print(f"\n📊 Found {len(models)} enabled AI models")
        
        # Create recipes for each model
        print(f"\n🔨 Creating 2-session recipes for each model...")
        print(f"   Session 1: Generate joke (actor varies)")
        print(f"   Session 2: Grade joke (actor: {GRADER_MODEL})")
        print()
        
        total_recipe_runs = 0
        first_recipe_id = None
        
        for idx, model in enumerate(models):
            print(f"📝 Model {idx+1}/{len(models)}: {model}")
            recipe_id = create_recipe_for_model(conn, model)
            
            # Create variations for first recipe only
            if first_recipe_id is None:
                first_recipe_id = recipe_id
                variation_ids = create_variations_for_recipe(conn, recipe_id)
            else:
                # Reuse variations from first recipe
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT variation_id 
                    FROM variations 
                    WHERE recipe_id = ?
                    ORDER BY difficulty_level
                """, (first_recipe_id,))
                variation_ids = [row[0] for row in cursor.fetchall()]
            
            # Create recipe_runs (3 batches per topic)
            runs_created = create_recipe_runs(conn, recipe_id, variation_ids, num_batches=3)
            total_recipe_runs += runs_created
            print()
        
        conn.commit()
        
        print("=" * 70)
        print("✅ SETUP COMPLETE")
        print("=" * 70)
        print(f"  • Recipes created: {len(models)}")
        print(f"  • Joke topics: 5")
        print(f"  • Batches per topic: 3")
        print(f"  • Total recipe_runs: {total_recipe_runs}")
        print(f"  • Grader model: {GRADER_MODEL}")
        print()
        print("🎯 Ready to execute! Use GUI or run:")
        print("   python3 recipe_run_test_runner_v31.py")
        print()
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
