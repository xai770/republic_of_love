#!/usr/bin/env python3
"""
Create qwen2.5:7b Grader Test Recipe
=====================================

Full validation of qwen2.5:7b as grader with llama3.2:1b extractor.
Compare results against gemma2:latest baseline.

Recipe Structure:
- Session A: llama3.2:1b extraction (known to be inconsistent)
- Session B: qwen2.5:7b grading (candidate grader)

Test with same 5 variations as Recipe 1111
"""

import sqlite3

DB_PATH = "/home/xai/Documents/ty_learn/data/llmcore.db"

def create_qwen_grader_test():
    """Create test recipe with qwen2.5:7b as grader"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Recipe
    cursor.execute("""
        INSERT INTO recipes (canonical_code, enabled, review_notes)
        VALUES ('test_qwen25_grader_full', 
                1,
                'Full test: llama3.2:1b → qwen2.5:7b grader validation')
    """)
    recipe_id = cursor.lastrowid
    print(f"✅ Created Recipe {recipe_id}: test_qwen25_grader_full")
    
    # Session A: llama3.2:1b extractor (same as Recipe 1111)
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
        ) VALUES (?, 1, 'session_a_llama32_extract',
                  0, 1, NULL,
                  'isolated', 'llama3.2:1b', 1)
    """, (recipe_id,))
    session_a_id = cursor.lastrowid
    print(f"✅ Created Session A ({session_a_id}): llama3.2:1b extraction")
    
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled,
            expected_pattern, is_terminal
        ) VALUES (?, 1, 'Extract job description',
                  ?, 60, 1, NULL, 0)
    """, (session_a_id, extraction_prompt))
    instruction_a_id = cursor.lastrowid
    print(f"   Instruction {instruction_a_id}: Extraction prompt")
    
    # Session B: qwen2.5:7b grader
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
    
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 2, 'session_b_qwen25_validate',
                  0, 2, ?,
                  'isolated', 'qwen2.5:7b', 1)
    """, (recipe_id, session_a_id))
    session_b_id = cursor.lastrowid
    print(f"✅ Created Session B ({session_b_id}): qwen2.5:7b validation")
    
    cursor.execute("""
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled,
            expected_pattern, is_terminal
        ) VALUES (?, 1, 'Grade extraction with qwen2.5:7b',
                  ?, 60, 1, NULL, 0)
    """, (session_b_id, grading_prompt))
    instruction_b_id = cursor.lastrowid
    print(f"   Instruction {instruction_b_id}: qwen2.5:7b grading prompt")
    
    # Use same 5 variations as Recipe 1111 (149-151, 152, 153)
    variation_ids = [149, 150, 151, 152, 153]
    
    print(f"\n✅ Creating recipe_runs for {len(variation_ids)} variations")
    
    recipe_run_ids = []
    for idx, variation_id in enumerate(variation_ids, 1):
        cursor.execute("""
            INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
            VALUES (?, ?, 8, 'PENDING')
        """, (recipe_id, variation_id))
        recipe_run_id = cursor.lastrowid
        recipe_run_ids.append(recipe_run_id)
        print(f"   Recipe Run {recipe_run_id}: variation {variation_id}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ QWEN2.5:7B GRADER TEST RECIPE CREATED")
    print(f"{'='*70}")
    print(f"Recipe ID: {recipe_id}")
    print(f"Session A: llama3.2:1b (ID {session_a_id}) - extraction")
    print(f"Session B: qwen2.5:7b (ID {session_b_id}) - grading")
    print(f"Recipe Runs: {recipe_run_ids}")
    print(f"\nTest Plan:")
    print(f"  1. Run: python3 recipe_run_test_runner_v32.py --max-runs 5")
    print(f"  2. Compare qwen2.5:7b results vs gemma2:latest (Recipe 1111)")
    print(f"\nExpected: qwen2.5:7b should catch bad extractions like gemma2 did")
    print(f"{'='*70}")

if __name__ == "__main__":
    create_qwen_grader_test()
