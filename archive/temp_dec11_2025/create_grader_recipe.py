#!/usr/bin/env python3
"""
Create recipe to test olmo2:latest grading ability on concise descriptions
"""
import sqlite3
import sys
sys.path.append('/home/xai/Documents/ty_learn/temp')
from test_descriptions import TEST_CASES

conn = sqlite3.connect('data/llmcore.db')
cursor = conn.cursor()

# Read original job posting for context
with open('temp/job50571_raw_text.txt', 'r') as f:
    job_text = f.read()

# Create recipe for grader validation
canonical_code = "test_grader_validation_olmo2"
review_notes = "Test olmo2:latest ability to detect flaws in concise descriptions (7 test cases: 1 good, 6 flawed)"

cursor.execute("INSERT INTO recipes (canonical_code, review_notes, enabled) VALUES (?, ?, 1)",
               (canonical_code, review_notes))
recipe_id = cursor.lastrowid
print(f"✅ Recipe {recipe_id}: {canonical_code}")

# Create one session per test case (olmo2 grades each description)
session_ids = []
for i, test_case in enumerate(TEST_CASES, 1):
    session_name = f"grade_{test_case['name']}"
    session_desc = f"olmo2 grades: {test_case['expected_grade']} - {test_case['reason']}"
    
    cursor.execute("""
    INSERT INTO sessions (recipe_id, session_number, actor_id, session_name, session_description, enabled)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (recipe_id, i, 'olmo2:latest', session_name, session_desc))
    
    session_id = cursor.lastrowid
    session_ids.append((session_id, test_case))
    print(f"   Session {i}: {test_case['name']} → Expected {test_case['expected_grade']}")

# Create grading prompt for olmo2
grading_prompt_template = """You are a quality assurance specialist evaluating concise job descriptions.

ORIGINAL JOB POSTING:
{job_posting}

EXTRACTED DESCRIPTION TO EVALUATE:
{description}

Your task: Grade this extracted description as either PASS or FAIL.

GRADING CRITERIA:
✅ PASS if ALL of these are met:
- Correct role extraction (should be "Senior Consultant", not other titles)
- Accurate responsibilities (strategy projects, client interaction, project management)
- Complete requirements (degree, experience, skills, language fluency)
- Proper template format with markers
- No hallucinated/invented information
- Appropriate length (concise but complete)

❌ FAIL if ANY of these issues:
- Wrong role (Data Scientist, Engagement Manager, etc.)
- Missing key requirements or responsibilities
- Hallucinated technical skills (Python, SQL, AWS, Docker not in original)
- Poor formatting (missing template structure)
- Too verbose (excessive detail) or too brief (missing information)
- Invented information not in original job posting

RESPONSE FORMAT:
[PASS] or [FAIL]
Reason: [Brief explanation of why it passed or failed]

CRITICAL: Be strict but fair. Focus on accuracy and completeness."""

# Create instructions for each session
for session_id, test_case in session_ids:
    prompt = grading_prompt_template.format(
        job_posting=job_text,
        description=test_case['description']
    )
    
    cursor.execute("""
    INSERT INTO instructions (session_id, step_number, step_description, prompt_template, enabled)
    VALUES (?, 1, ?, ?, 1)
    """, (session_id, f"Grade {test_case['name']}", prompt))

print(f"\n✅ Created {len(session_ids)} grading instructions")

# Create variation
cursor.execute("INSERT INTO variations (recipe_id, variations_param_1, enabled) VALUES (?, ?, 1)",
               (recipe_id, "job50571_grader_validation"))
variation_id = cursor.lastrowid
print(f"✅ Variation {variation_id}: job50571_grader_validation")

# Create recipe_run
cursor.execute("INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status) VALUES (?, ?, 1, 'PENDING')",
               (recipe_id, variation_id))
recipe_run_id = cursor.lastrowid
print(f"✅ Recipe_run {recipe_run_id}: PENDING")

conn.commit()
conn.close()

print("\n" + "="*70)
print("GRADER VALIDATION TEST READY")
print("="*70)
print(f"Recipe: {recipe_id} | Run: {recipe_run_id}")
print(f"Sessions: {len(TEST_CASES)} (olmo2:latest grades each description)")
print("\nTest cases:")
for i, case in enumerate(TEST_CASES, 1):
    print(f"   {i}. {case['name']:30s} → Expected {case['expected_grade']}")

print(f"\nExpected results: 1 PASS, 6 FAIL")
print(f"We'll see if olmo2 is too strict (fails good ones) or too lenient (passes bad ones)")
print("\n🚀 python3 recipe_run_test_runner_v31.py --max-runs 1")