#!/usr/bin/env python3
"""
Create Dual-Grader Recipe: gemma2 + qwen2.5
============================================

Test both graders on the SAME extraction to see if they agree.

Recipe Structure:
- Session A: gemma3:1b extraction (consistent, good quality)
- Session B: gemma2:latest grading
- Session C: qwen2.5:7b grading

Both graders evaluate the same Session A output.
"""

import sqlite3

DB_PATH = "/home/xai/Documents/ty_learn/data/llmcore.db"

def create_dual_grader_recipe():
    """Create recipe with both graders evaluating same extraction"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Recipe
    cursor.execute("""
        INSERT INTO recipes (canonical_code, enabled, review_notes)
        VALUES ('dual_grader_gemma2_qwen25', 
                1,
                'Ensemble grading: gemma3:1b → (gemma2 + qwen2.5) both grade same output')
    """)
    recipe_id = cursor.lastrowid
    print(f"✅ Created Recipe {recipe_id}: dual_grader_gemma2_qwen25")
    
    # Session A: gemma3:1b extractor (proven champion)
    extraction_prompt = """Create a concise job description summary for this job posting:

{variations_param_1}

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information."""
    
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 1, 'session_a_gemma3_extract',
                  0, 1, NULL,
                  'isolated', 'gemma3:1b', 1)
    """, (recipe_id,))
    session_a_id = cursor.lastrowid
    print(f"✅ Created Session A ({session_a_id}): gemma3:1b extraction")
    
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled,
            expected_pattern, is_terminal
        ) VALUES (?, 1, 'Extract with gemma3:1b',
                  ?, 60, 1, NULL, 0)
    """, (session_a_id, extraction_prompt))
    instruction_a_id = cursor.lastrowid
    print(f"   Instruction {instruction_a_id}: Extraction prompt")
    
    # Grading prompt (same for both)
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
    
    # Session B: gemma2:latest grader
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 2, 'session_b_gemma2_grade',
                  0, 2, ?,
                  'isolated', 'gemma2:latest', 1)
    """, (recipe_id, session_a_id))
    session_b_id = cursor.lastrowid
    print(f"✅ Created Session B ({session_b_id}): gemma2:latest grading")
    
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled,
            expected_pattern, is_terminal
        ) VALUES (?, 1, 'Grade with gemma2:latest',
                  ?, 60, 1, NULL, 0)
    """, (session_b_id, grading_prompt))
    instruction_b_id = cursor.lastrowid
    print(f"   Instruction {instruction_b_id}: gemma2 grading prompt")
    
    # Session C: qwen2.5:7b grader
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 3, 'session_c_qwen25_grade',
                  0, 2, ?,
                  'isolated', 'qwen2.5:7b', 1)
    """, (recipe_id, session_a_id))
    session_c_id = cursor.lastrowid
    print(f"✅ Created Session C ({session_c_id}): qwen2.5:7b grading")
    
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled,
            expected_pattern, is_terminal
        ) VALUES (?, 1, 'Grade with qwen2.5:7b',
                  ?, 60, 1, NULL, 0)
    """, (session_c_id, grading_prompt))
    instruction_c_id = cursor.lastrowid
    print(f"   Instruction {instruction_c_id}: qwen2.5 grading prompt")
    
    # Use same 5 variations
    variation_ids = [149, 150, 151, 152, 153]
    
    print(f"\n✅ Creating recipe_runs for {len(variation_ids)} variations")
    
    recipe_run_ids = []
    for idx, variation_id in enumerate(variation_ids, 1):
        cursor.execute("""
            INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
            VALUES (?, ?, 9, 'PENDING')
        """, (recipe_id, variation_id))
        recipe_run_id = cursor.lastrowid
        recipe_run_ids.append(recipe_run_id)
        print(f"   Recipe Run {recipe_run_id}: variation {variation_id}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ DUAL-GRADER RECIPE CREATED")
    print(f"{'='*70}")
    print(f"Recipe ID: {recipe_id}")
    print(f"Session A: gemma3:1b (ID {session_a_id}) - extraction")
    print(f"Session B: gemma2:latest (ID {session_b_id}) - grading")
    print(f"Session C: qwen2.5:7b (ID {session_c_id}) - grading")
    print(f"Recipe Runs: {recipe_run_ids}")
    print(f"\nBoth graders will evaluate the SAME gemma3:1b extraction")
    print(f"\nNext: python3 recipe_run_test_runner_v32.py --max-runs 5")
    print(f"\nExpected: See where gemma2 and qwen2.5 agree/disagree on same input")
    print(f"{'='*70}")

if __name__ == "__main__":
    create_dual_grader_recipe()
