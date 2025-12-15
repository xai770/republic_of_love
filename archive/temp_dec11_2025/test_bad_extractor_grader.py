#!/usr/bin/env python3
"""
Test Bad Extractor + Good Grader Pipeline
==========================================

Purpose: Validate that gemma2:latest actually catches bad summaries

Strategy:
- Session A: phi3:3.8b (known to hallucinate/produce poor extractions)
- Session B: gemma2:latest (should catch errors and give [FAIL])

Expected Outcome:
- Session A: produces incomplete/hallucinated summaries
- Session B: catches problems and gives [FAIL] with specific critiques

If gemma2 gives [PASS] to phi3:3.8b output, we have a problem!
"""

import sqlite3
import json

DB_PATH = "/home/xai/Documents/ty_learn/data/llmcore.db"

def create_bad_extractor_test_recipe():
    """Create recipe with bad extractor to test grader validation"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Recipe
    cursor.execute("""
        INSERT INTO recipes (canonical_code, enabled, review_notes)
        VALUES ('test_bad_extractor_grader', 
                1,
                'Test pipeline: phi3:3.8b (bad) → gemma2:latest (should catch errors)')
    """)
    recipe_id = cursor.lastrowid
    print(f"✅ Created Recipe {recipe_id}: test_bad_extractor_grader")
    
    # Session A: Bad extractor (phi3:3.8b)
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 1, 'session_a_phi3_extract_BAD',
                  0, 1, NULL,
                  'isolated', 'phi3:3.8b', 1)
    """, (recipe_id,))
    session_a_id = cursor.lastrowid
    print(f"✅ Created Session A ({session_a_id}): phi3:3.8b extraction (expected to fail)")
    
    # Session A Instruction
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
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled,
            expected_pattern, is_terminal
        ) VALUES (?, 1, 'Extract job description (will likely fail)',
                  ?, 60, 1, NULL, 0)
    """, (session_a_id, extraction_prompt))
    instruction_a_id = cursor.lastrowid
    print(f"✅ Created Instruction {instruction_a_id}: phi3:3.8b extraction prompt")
    
    # Session B: Good grader (gemma2:latest) - should catch Session A's errors
    cursor.execute("""
        INSERT INTO sessions (
            recipe_id, session_number, session_name,
            maintain_llm_context, execution_order, depends_on_session_id,
            context_strategy, actor_id, enabled
        ) VALUES (?, 2, 'session_b_gemma2_validate',
                  0, 2, ?,
                  'isolated', 'gemma2:latest', 1)
    """, (recipe_id, session_a_id))
    session_b_id = cursor.lastrowid
    print(f"✅ Created Session B ({session_b_id}): gemma2:latest validation (should catch errors)")
    
    # Session B Instruction (grader with {session_1_output})
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
        INSERT INTO instructions (
            session_id, step_number, step_description,
            prompt_template, timeout_seconds, enabled,
            expected_pattern, is_terminal
        ) VALUES (?, 1, 'Grade extraction (should detect errors)',
                  ?, 60, 1, NULL, 0)
    """, (session_b_id, grading_prompt))
    instruction_b_id = cursor.lastrowid
    print(f"✅ Created Instruction {instruction_b_id}: gemma2:latest grading prompt")
    
    # Load 3 job postings for testing
    cursor.execute("""
        SELECT variation_id, variations_param_1
        FROM variations
        WHERE variation_id IN (149, 150, 151)
    """)
    
    variations = cursor.fetchall()
    print(f"\n✅ Using {len(variations)} existing variations")
    
    # Create recipe_runs
    recipe_run_ids = []
    for idx, (variation_id, posting) in enumerate(variations, 1):
        cursor.execute("""
            INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
            VALUES (?, ?, 7, 'PENDING')
        """, (recipe_id, variation_id))
        recipe_run_id = cursor.lastrowid
        recipe_run_ids.append(recipe_run_id)
        
        job_preview = posting[:60] + "..." if len(posting) > 60 else posting
        print(f"   Recipe Run {recipe_run_id}: {job_preview}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ TEST RECIPE CREATED")
    print(f"{'='*70}")
    print(f"Recipe ID: {recipe_id}")
    print(f"Session A: phi3:3.8b (ID {session_a_id}) - expected to produce bad summaries")
    print(f"Session B: gemma2:latest (ID {session_b_id}) - should catch errors")
    print(f"Recipe Runs: {recipe_run_ids}")
    print(f"\nNext: python3 recipe_run_test_runner_v32.py --max-runs 3")
    print(f"\nExpected: All Session B results should be [FAIL] if grader works properly")
    print(f"{'='*70}")

if __name__ == "__main__":
    create_bad_extractor_test_recipe()
