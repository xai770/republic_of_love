#!/usr/bin/env python3
"""
Create Recipe 1119: Job Posting Skill Graph Builder

Extracts skills from concise job descriptions and builds graph relationships:
- Job nodes (from Recipe 1114 output)
- Skill nodes (from term_dictionary) 
- Job-to-Skill edges (requirements)
- Skill co-occurrence tracking
- Graph queries for matching and analysis
"""

import sqlite3
import sys

def create_recipe_1119():
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    try:
        print("📊 Creating Recipe 1119: Job Posting Skill Graph Builder")
        print("=" * 70)
        print()
        
        # Create Recipe
        cursor.execute("""
            INSERT INTO recipes (recipe_id, canonical_code, review_notes)
            VALUES (1119, 'job_skill_graph', 
            'Extract skills from concise job descriptions and build graph relationships for matching and analysis')
        """)
        print("✓ Recipe 1119 created\n")
        
        # Session 1: Extract Skills (continuous - uses phi3:latest)
        cursor.execute("""
            INSERT INTO sessions (
                session_id, recipe_id, session_number, session_name, session_description,
                maintain_llm_context, execution_order, context_strategy, actor_id
            ) VALUES (
                2031, 1119, 1, 'Extract Skills',
                'Identify technical and business skills mentioned in job description',
                1, 1, 'continuous', 'phi3:latest'
            )
        """)
        
        # Session 2: Categorize Skills (continuous - remembers Session 1)
        cursor.execute("""
            INSERT INTO sessions (
                session_id, recipe_id, session_number, session_name, session_description,
                maintain_llm_context, execution_order, depends_on_session_id, context_strategy, actor_id
            ) VALUES (
                2032, 1119, 2, 'Categorize Skills',
                'Map extracted skills to DynaTax categories using term_dictionary',
                1, 2, 2031, 'continuous', 'phi3:latest'
            )
        """)
        
        # Session 3: Build Graph Edges (script)
        cursor.execute("""
            INSERT INTO sessions (
                session_id, recipe_id, session_number, session_name, session_description,
                maintain_llm_context, execution_order, depends_on_session_id, context_strategy, actor_id
            ) VALUES (
                2033, 1119, 3, 'Build Graph',
                'Create job-skill edges and update co-occurrence matrix',
                0, 3, 2032, 'isolated', 'graph_builder_script'
            )
        """)
        
        print("✓ 3 Sessions created")
        print("  Session 2031: Extract Skills [continuous]")
        print("  Session 2032: Categorize Skills [continuous - remembers 2031]")
        print("  Session 2033: Build Graph [isolated script]\n")
        
        # Instructions
        instructions = [
            (2159, 2031, 1, 'Identify skills', """Analyze this job description and extract ALL technical and business skills mentioned:

JOB DESCRIPTION:
{job_description}

Extract:
1. TECHNICAL SKILLS: Programming languages, tools, platforms, frameworks, databases
2. BUSINESS SKILLS: Domain knowledge, methodologies, processes
3. SOFT SKILLS: Leadership, communication, collaboration
4. EXPERIENCE: Years required, specific backgrounds
5. EDUCATION: Degrees, certifications

Return as JSON:
{
  "technical": ["Python", "AWS", "Docker", ...],
  "business": ["Agile", "Financial Analysis", ...],
  "soft": ["Leadership", "Communication", ...],
  "experience": ["10+ years", "Banking experience", ...],
  "education": ["Master's degree", "PMP certification", ...]
}"""),
            
            (2160, 2032, 2, 'Map to taxonomy', """Good! Now map these skills to our DynaTax categories.

EXTRACTED SKILLS:
{session_1_output}

AVAILABLE CATEGORIES:
{available_categories}

For each skill, find the best matching category. If no match exists, mark as "UNKNOWN".

Return as JSON:
{
  "mappings": [
    {"skill": "Python", "category": "BACKEND_DEVELOPMENT_AND_FRAMEWORKS", "confidence": "high"},
    {"skill": "AWS", "category": "CLOUD_COMPUTING_SERVICES_AND_AUTOMATION", "confidence": "high"},
    {"skill": "Financial Analysis", "category": "UNKNOWN", "confidence": "low"},
    ...
  ],
  "unknowns": ["Financial Analysis", "Basel III", ...]
}""")
        ]
        
        for inst_id, session_id, step, description, prompt in instructions:
            cursor.execute("""
                INSERT INTO instructions (
                    instruction_id, session_id, step_number, 
                    step_description, prompt_template
                ) VALUES (?, ?, ?, ?, ?)
            """, (inst_id, session_id, step, description, prompt))
        
        print("✓ 2 Instructions created\n")
        
        # Create graph builder script actor
        cursor.execute("""
            INSERT OR IGNORE INTO actors (actor_id, actor_type, url)
            VALUES ('graph_builder_script', 'script', 'scripts/build_job_skill_graph.py')
        """)
        
        print("✓ Actor 'graph_builder_script' created\n")
        
        conn.commit()
        
        # Verify
        print("📊 Recipe 1119 Structure:\n")
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
            WHERE s.recipe_id = 1119
            GROUP BY s.session_id
            ORDER BY s.execution_order
        """)
        
        rows = cursor.fetchall()
        for num, name, actor, strategy, maintain, inst_count in rows:
            context = "✓" if maintain else " "
            insts = f"{inst_count} instruction(s)" if inst_count > 0 else "script"
            print(f"  {num}. {name:25} | {actor:25} | [{context}] {strategy:12} | {insts}")
        
        print("\n✅ Recipe 1119 created successfully!")
        print("\n🎯 Next Steps:")
        print("   1. Create graph database tables (job_nodes, skill_nodes, job_skill_edges)")
        print("   2. Implement build_job_skill_graph.py script")
        print("   3. Test with concise job descriptions from Recipe 1114")
        print("   4. Build graph query API for matching and analysis")
        
        return True
        
    except sqlite3.IntegrityError as e:
        print(f"❌ Recipe 1119 already exists or constraint violation: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Error creating recipe: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    success = create_recipe_1119()
    sys.exit(0 if success else 1)
