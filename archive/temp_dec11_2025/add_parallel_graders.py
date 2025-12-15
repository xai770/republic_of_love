#!/usr/bin/env python3
"""
Add Parallel Grader Sessions to Recipe 1111
============================================

Add 3 more grading sessions (Session C, D, E) to compare graders:
- Session C: mistral:latest (4.4GB)
- Session D: qwen2.5:7b (4.7GB)  
- Session E: dolphin3:8b (4.9GB)

All depend on Session A (llama3.2:1b extraction)
"""

import sqlite3

DB_PATH = "/home/xai/Documents/ty_learn/data/llmcore.db"

def add_parallel_graders():
    """Add 3 more grading sessions to Recipe 1111"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    recipe_id = 1111
    session_a_id = 626  # llama3.2:1b extractor
    
    grading_prompt = """# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{session_1_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning."""
    
    graders = [
        ('mistral:latest', 'session_c_mistral_validate', 3),
        ('qwen2.5:7b', 'session_d_qwen25_validate', 4),
        ('dolphin3:8b', 'session_e_dolphin3_validate', 5)
    ]
    
    session_ids = []
    
    for actor_id, session_name, session_number in graders:
        # Create session
        cursor.execute("""
            INSERT INTO sessions (
                recipe_id, session_number, session_name,
                maintain_llm_context, execution_order, depends_on_session_id,
                context_strategy, actor_id, enabled
            ) VALUES (?, ?, ?,
                      0, ?, ?,
                      'isolated', ?, 1)
        """, (recipe_id, session_number, session_name, 
              session_number, session_a_id, actor_id))
        
        session_id = cursor.lastrowid
        session_ids.append((session_id, actor_id, session_name))
        print(f"✅ Created Session {session_number} ({session_id}): {actor_id} - {session_name}")
        
        # Create instruction for this session
        cursor.execute("""
            INSERT INTO instructions (
                session_id, step_number, step_description,
                prompt_template, timeout_seconds, enabled,
                expected_pattern, is_terminal
            ) VALUES (?, 1, ?,
                      ?, 60, 1, NULL, 0)
        """, (session_id, f'Grade extraction with {actor_id}', grading_prompt))
        
        instruction_id = cursor.lastrowid
        print(f"   Instruction {instruction_id}: Grading prompt")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ ADDED 3 PARALLEL GRADERS TO RECIPE 1111")
    print(f"{'='*70}")
    print(f"Recipe 1111 now has 5 sessions:")
    print(f"  Session A (626): llama3.2:1b - extraction")
    print(f"  Session B (627): gemma2:latest - grading")
    for session_id, actor_id, session_name in session_ids:
        print(f"  Session ({session_id}): {actor_id} - grading")
    print(f"\nAll graders receive the same extraction from Session A")
    print(f"\nNext: Reset recipe_runs to PENDING and re-run")
    print(f"  sqlite3 data/llmcore.db \"UPDATE recipe_runs SET status = 'PENDING' WHERE recipe_id = 1111;\"")
    print(f"  python3 recipe_run_test_runner_v32.py --max-runs 5")
    print(f"{'='*70}")

if __name__ == "__main__":
    add_parallel_graders()
