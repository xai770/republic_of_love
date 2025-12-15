#!/usr/bin/env python3
"""
Create Multi-Model Joke Classification Tests
============================================
Creates recipes, sessions, instructions, and recipe_runs for all enabled AI models
to test joke classification across 5 variations × 5 batches = 25 runs per model
"""

import sqlite3
from datetime import datetime

DB_PATH = '/home/xai/Documents/ty_learn/data/llmcore.db'
CANONICAL_CODE = 'ld_classify_joke_quality'

PROMPT_TEMPLATE = """Read the following text and determine if it is a joke:

{variations_param_1}

Answer these two questions:
1. Is this actually a joke? Answer ONLY: YES or NO
2. If yes, rate its quality: BAD, MEDIOCRE, GOOD, or EXCELLENT

Format your answer exactly like this:
IS_JOKE: [YES or NO]
QUALITY: [BAD, MEDIOCRE, GOOD, or EXCELLENT]"""

def get_enabled_ai_models(conn):
    """Get list of enabled AI models"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT actor_id 
        FROM actors 
        WHERE enabled = 1 
          AND actor_type = 'ai_model'
        ORDER BY actor_id
    """)
    return [row[0] for row in cursor.fetchall()]

def get_existing_recipe_actors(conn):
    """Get list of actors that already have recipes for this canonical"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT s.actor_id
        FROM recipes r
        JOIN sessions s ON r.recipe_id = s.recipe_id
        WHERE r.canonical_code = ?
    """, (CANONICAL_CODE,))
    return [row[0] for row in cursor.fetchall()]

def get_joke_variations(conn):
    """Get the 5 joke variation IDs"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT variation_id 
        FROM variations 
        WHERE recipe_id = (
            SELECT MIN(recipe_id) 
            FROM recipes 
            WHERE canonical_code = ?
        )
        ORDER BY difficulty_level
    """, (CANONICAL_CODE,))
    return [row[0] for row in cursor.fetchall()]

def create_recipe_for_model(conn, actor_id):
    """Create recipe, session, and instruction for a specific model"""
    cursor = conn.cursor()
    
    # 1. Create recipe
    cursor.execute("""
        INSERT INTO recipes (canonical_code, recipe_version, enabled)
        VALUES (?, 1, 1)
    """, (CANONICAL_CODE,))
    
    recipe_id = cursor.lastrowid
    print(f"  ✅ Created recipe {recipe_id} for {actor_id}")
    
    # 2. Create session
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name, 
            maintain_llm_context, execution_order, 
            context_strategy, actor_id, enabled
        )
        VALUES (?, 1, 'joke_classification', 0, 1, 'none', ?, 1)
    """, (recipe_id, actor_id))
    
    session_id = cursor.lastrowid
    print(f"     Created session {session_id}")
    
    # 3. Create instruction
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled, is_terminal
        )
        VALUES (?, 1, 'Classify if text is a joke and rate quality', ?, 30, 1, 1)
    """, (session_id, PROMPT_TEMPLATE))
    
    instruction_id = cursor.lastrowid
    print(f"     Created instruction {instruction_id}")
    
    return recipe_id

def create_recipe_runs(conn, recipe_id, variation_ids, num_batches=5):
    """Create recipe_runs for a recipe across all variations and batches"""
    cursor = conn.cursor()
    
    created_count = 0
    for variation_id in variation_ids:
        for batch_id in range(1, num_batches + 1):
            cursor.execute("""
                INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
                VALUES (?, ?, ?, 'PENDING')
            """, (recipe_id, variation_id, batch_id))
            created_count += 1
    
    print(f"     Created {created_count} recipe_runs (5 jokes × {num_batches} batches)")
    return created_count

def main():
    """Main execution"""
    print("=" * 70)
    print("🚀 Multi-Model Joke Classification Test Setup")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Get models and variations
        all_models = get_enabled_ai_models(conn)
        existing_actors = get_existing_recipe_actors(conn)
        variation_ids = get_joke_variations(conn)
        
        print(f"\n📊 Status:")
        print(f"  • Total enabled AI models: {len(all_models)}")
        print(f"  • Models with existing recipes: {len(existing_actors)}")
        print(f"  • Joke variations: {len(variation_ids)}")
        print(f"  • Models needing recipes: {len(all_models) - len(existing_actors)}")
        
        # Find models that need recipes
        models_to_create = [m for m in all_models if m not in existing_actors]
        
        if not models_to_create:
            print("\n✅ All models already have recipes!")
        else:
            print(f"\n🔨 Creating recipes for {len(models_to_create)} models...")
            print()
            
            total_recipe_runs = 0
            for actor_id in models_to_create:
                print(f"📝 {actor_id}")
                recipe_id = create_recipe_for_model(conn, actor_id)
                runs_created = create_recipe_runs(conn, recipe_id, variation_ids, num_batches=5)
                total_recipe_runs += runs_created
                print()
            
            conn.commit()
            
            print("=" * 70)
            print("✅ SETUP COMPLETE")
            print("=" * 70)
            print(f"  • New recipes created: {len(models_to_create)}")
            print(f"  • New recipe_runs created: {total_recipe_runs}")
            print(f"  • Total pending runs: {total_recipe_runs}")
            print()
            
        # Show summary
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM recipe_runs rr
            JOIN recipes r ON rr.recipe_id = r.recipe_id
            WHERE r.canonical_code = ?
              AND rr.status = 'PENDING'
        """, (CANONICAL_CODE,))
        
        total_pending = cursor.fetchone()[0]
        print(f"🎯 Ready to execute: {total_pending} pending recipe_runs")
        print()
        print("💡 Next step: Click 'RUN ALL PENDING TESTS' in the GUI!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
