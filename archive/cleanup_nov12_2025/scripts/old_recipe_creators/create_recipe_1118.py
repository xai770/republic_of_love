#!/usr/bin/env python3
"""
Create Recipe 1118: DynaTax Auto-Subdivision with Continuous Sessions

This recipe demonstrates multi-turn LLM conversations using Ollama's /api/chat endpoint
to maintain context across multiple prompts for intelligent category subdivision.
"""

import sqlite3
import sys

def create_recipe_1118():
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    try:
        print("🎨 Creating Recipe 1118: Auto-Subdivision with Continuous Sessions")
        print("=" * 70)
        print()
        
        # Create Recipe
        cursor.execute("""
            INSERT INTO recipes (recipe_id, canonical_code, review_notes)
            VALUES (1118, 'dynatax_auto_subdivide', 
            'Multi-turn conversation for intelligent category subdivision. Uses continuous Ollama chat sessions to: 1) Analyze terms and propose subdivisions, 2) Refine based on frequency data, 3) Categorize all terms into subcategories, 4) Execute database migration.')
        """)
        print("✓ Recipe 1118 created\n")
        
        # Session 1: Analyze and Propose
        cursor.execute("""
            INSERT INTO sessions (
                session_id, recipe_id, session_number, session_name, session_description,
                maintain_llm_context, execution_order, context_strategy, actor_id
            ) VALUES (
                2026, 1118, 1, 'Analyze & Propose',
                'Analyze category terms and propose subdivision structure',
                1, 1, 'continuous', 'phi3:latest'
            )
        """)
        
        # Session 2: Refine with Data
        cursor.execute("""
            INSERT INTO sessions (
                session_id, recipe_id, session_number, session_name, session_description,
                maintain_llm_context, execution_order, depends_on_session_id, context_strategy, actor_id
            ) VALUES (
                2027, 1118, 2, 'Refine Proposal',
                'Refine subdivision based on term usage frequency',
                1, 2, 2026, 'continuous', 'phi3:latest'
            )
        """)
        
        # Session 3: Categorize Terms
        cursor.execute("""
            INSERT INTO sessions (
                session_id, recipe_id, session_number, session_name, session_description,
                maintain_llm_context, execution_order, depends_on_session_id, context_strategy, actor_id
            ) VALUES (
                2028, 1118, 3, 'Categorize Terms',
                'Assign each term to final subcategories as JSON',
                1, 3, 2027, 'continuous', 'phi3:latest'
            )
        """)
        
        # Session 4: Execute Migration
        cursor.execute("""
            INSERT INTO sessions (
                session_id, recipe_id, session_number, session_name, session_description,
                maintain_llm_context, execution_order, depends_on_session_id, context_strategy, actor_id
            ) VALUES (
                2029, 1118, 4, 'Execute Migration',
                'Migrate terms to new subcategories in database',
                0, 4, 2028, 'isolated', 'dynatax_migrate_script'
            )
        """)
        
        print("✓ 4 Sessions created")
        print("  Session 2026: Analyze & Propose [continuous]")
        print("  Session 2027: Refine Proposal [continuous - remembers 2026]")
        print("  Session 2028: Categorize Terms [continuous - remembers 2026+2027]")
        print("  Session 2029: Execute Migration [isolated script]\n")
        
        # Instructions
        instructions = [
            (2155, 2026, 1, 'Analyze and propose subdivisions', """You are analyzing a taxonomy category that has too many terms.

CATEGORY: {category_name}
CURRENT TERMS ({term_count}): {term_list}

Analyze these terms and identify natural groupings or patterns. Consider:
- Functional similarity (what they do)
- Domain clusters (where they're used)  
- Skill level progression (beginner to advanced)
- Technology stack relationships

Propose 3-5 subcategory names that would meaningfully organize these terms. 
For each subcategory, explain the rationale briefly.

Format:
SUBCATEGORY_NAME: Brief rationale
SUBCATEGORY_NAME: Brief rationale
..."""),
            
            (2156, 2027, 2, 'Refine with frequency data', """Good analysis. Now I'll show you which terms are being used most frequently:

TERM FREQUENCY DATA:
{frequency_data}

Based on actual usage patterns, refine your subdivision proposal. Should any subcategories be:
- Merged (too similar)?
- Split further (too broad)?
- Renamed (clearer purpose)?

Provide your FINAL subdivision structure with 3-5 subcategories."""),
            
            (2157, 2028, 3, 'Categorize all terms', """Perfect. Now categorize each term into your proposed subcategories:

For each term in the original list, assign it to ONE subcategory.

Format as JSON:
{
  "SUBCATEGORY_1": ["term1", "term2", ...],
  "SUBCATEGORY_2": ["term3", "term4", ...],
  ...
}

Ensure ALL original terms are assigned.""")
        ]
        
        for inst_id, session_id, step, description, prompt in instructions:
            cursor.execute("""
                INSERT INTO instructions (
                    instruction_id, session_id, step_number, 
                    step_description, prompt_template
                ) VALUES (?, ?, ?, ?, ?)
            """, (inst_id, session_id, step, description, prompt))
        
        print("✓ 3 Instructions created\n")
        
        # Create migration script actor
        cursor.execute("""
            INSERT OR IGNORE INTO actors (actor_id, actor_type, url)
            VALUES ('dynatax_migrate_script', 'script', 'scripts/dynatax_migrate_subdivisions.py')
        """)
        
        print("✓ Actor 'dynatax_migrate_script' created\n")
        
        conn.commit()
        
        # Verify
        print("📊 Recipe 1118 Structure:\n")
        cursor.execute("""
            SELECT 
                s.session_number, 
                s.session_name, 
                s.actor_id, 
                s.context_strategy,
                s.maintain_llm_context,
                COUNT(i.instruction_id) as inst_count
            FROM sessions s
            LEFT JOIN instructions i ON s.session_id = i.session_id
            WHERE s.recipe_id = 1118
            GROUP BY s.session_id
            ORDER BY s.execution_order
        """)
        
        rows = cursor.fetchall()
        for num, name, actor, strategy, maintain, inst_count in rows:
            context = "✓" if maintain else " "
            insts = f"{inst_count} instruction(s)" if inst_count > 0 else "script"
            print(f"  {num}. {name:25} | {actor:25} | [{context}] {strategy:12} | {insts}")
        
        print("\n✅ Recipe 1118 created successfully!")
        print("\n🎯 Key Features:")
        print("   • Continuous context across 3 LLM sessions")
        print("   • Progressive refinement (propose → refine → categorize)")
        print("   • Uses Ollama /api/chat for conversation memory")
        print("   • Automatic database migration after categorization")
        
        return True
        
    except sqlite3.IntegrityError as e:
        print(f"❌ Recipe 1118 already exists or constraint violation: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Error creating recipe: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    success = create_recipe_1118()
    sys.exit(0 if success else 1)
