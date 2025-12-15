#!/usr/bin/env python3
"""
Create grader validation recipe using llama3.2:latest instead of olmo2
Test if llama3.2 can detect flaws that olmo2 missed
"""
import sqlite3
import sys
sys.path.append('/home/xai/Documents/ty_learn/temp')
from test_descriptions import TEST_CASES

conn = sqlite3.connect('data/llmcore.db')
cursor = conn.cursor()

# Read original job posting
with open('temp/job50571_raw_text.txt', 'r') as f:
    job_text = f.read()

# Create recipe for llama3.2 grader validation
canonical_code = "test_grader_validation_llama32"
review_notes = "Test llama3.2:latest as grader with improved prompt (compare vs olmo2's 14.3% accuracy)"

cursor.execute("INSERT INTO recipes (canonical_code, review_notes, enabled) VALUES (?, ?, 1)",
               (canonical_code, review_notes))
recipe_id = cursor.lastrowid
print(f"✅ Recipe {recipe_id}: {canonical_code}")

# Use the same improved prompt that failed with olmo2
improved_prompt = """# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **posting summary**:

--- start posting summary ---
{variations_param_2}
--- end posting summary ---

## 3. Grade this posting summary by applying the following criteria:

### ✅ PASS if ALL of these are met:
- Correct role extraction (should be "Senior Consultant", not other titles)
- Accurate responsibilities (strategy projects, client interaction, project management)
- Complete requirements (degree, experience, skills, language fluency)
- Proper template format with markers
- No hallucinated/invented information
- Appropriate length (concise but complete)

### ❌ FAIL if ANY of these issues:
- Wrong role (Data Scientist, Engagement Manager, etc.)
- Missing key requirements or responsibilities
- Hallucinated technical skills (Python, SQL, AWS, Docker not in original)
- Poor formatting (missing template structure)
- Too verbose (excessive detail) or too brief (missing information)
- Invented information not in original job posting

## 4. Output your response

### Response Format
[PASS] or [FAIL]
[Explanation]

IMPORTANT!!!: Enclose both responses in square brackets! 
### Response Example (DO NOT COPY CONTENTS!)

[PASS] 
[The summary correctly identifies the role as "Senior Consultant". It accurately captures key responsibilities like strategy work, client interaction, and project management. The requirements section correctly notes the need for a degree, experience, and language fluency. The summary is concise, well-formatted, and doesn't invent any information.]

[FAIL]
[The role is incorrectly listed as "Data Scientist" when the original posting clearly states "Senior Consultant". This is a critical error in role extraction.]

End of instructions.
*Thank you for your help!*"""

# Create one session per test case with llama3.2:latest
session_ids = []
for i, test_case in enumerate(TEST_CASES, 1):
    session_name = f"llama32_grade_{test_case['name']}"
    session_desc = f"llama3.2 grades: {test_case['expected_grade']} - {test_case['reason']}"
    
    cursor.execute("""
    INSERT INTO sessions (recipe_id, session_number, actor_id, session_name, session_description, enabled)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (recipe_id, i, 'llama3.2:latest', session_name, session_desc))
    
    session_id = cursor.lastrowid
    session_ids.append((session_id, test_case))
    print(f"   Session {i}: {test_case['name']} → Expected {test_case['expected_grade']}")

# Create instructions for each session
for session_id, test_case in session_ids:
    cursor.execute("""
    INSERT INTO instructions (session_id, step_number, step_description, prompt_template, enabled)
    VALUES (?, 1, ?, ?, 1)
    """, (session_id, f"llama3.2 grade {test_case['name']}", improved_prompt))

print(f"\n✅ Created {len(session_ids)} grading instructions for llama3.2:latest")

# Create variations (same as olmo2 test for fair comparison)
variation_ids = []
for i, test_case in enumerate(TEST_CASES, 1):
    cursor.execute("""
    INSERT INTO variations (recipe_id, variations_param_1, variations_param_2, enabled)
    VALUES (?, ?, ?, 1)
    """, (recipe_id, job_text, test_case['description']))
    
    variation_id = cursor.lastrowid
    variation_ids.append(variation_id)
    print(f"   Variation {variation_id}: {test_case['name']}")

print(f"\n✅ Created {len(variation_ids)} variations (identical to olmo2 test)")

# Create recipe_runs for each variation
recipe_run_ids = []
for i, (variation_id, test_case) in enumerate(zip(variation_ids, TEST_CASES), 1):
    cursor.execute("""
    INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
    VALUES (?, ?, ?, 'PENDING')
    """, (recipe_id, variation_id, i))
    
    recipe_run_id = cursor.lastrowid
    recipe_run_ids.append(recipe_run_id)
    print(f"   Recipe_run {recipe_run_id}: {test_case['name']} (batch {i})")

conn.commit()
conn.close()

print("\n" + "="*70)
print("LLAMA3.2 GRADER VALIDATION TEST READY")
print("="*70)
print(f"Recipe: {recipe_id} | Runs: {min(recipe_run_ids)}-{max(recipe_run_ids)}")
print(f"Model: llama3.2:latest (QA champion runner-up)")
print(f"Sessions: {len(TEST_CASES)} (same test cases as olmo2)")
print(f"Prompt: Identical improved prompt with variable substitution")

print("\nTest cases:")
for i, case in enumerate(TEST_CASES, 1):
    print(f"   {i}. {case['name']:30s} → Expected {case['expected_grade']}")

print(f"\nExpected: llama3.2 should perform BETTER than olmo2's 14.3% accuracy")
print(f"Key test: Will llama3.2 detect 'Data Scientist' vs 'Senior Consultant'?")
print(f"Key test: Will llama3.2 catch hallucinated Python/SQL skills?")
print("\n🚀 python3 recipe_run_test_runner_v31.py --max-runs 7")