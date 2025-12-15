#!/usr/bin/env python3

import sqlite3
import json
from datetime import datetime

# Read the credit risk job posting
with open('/home/xai/Documents/ty_learn/data/postings_backup_20250728/job64659.json', 'r') as f:
    job_data = json.load(f)

job_content = job_data['job_content']['description']

# Connect to database
conn = sqlite3.connect('/home/xai/Documents/ty_learn/data/llmcore.db')
cursor = conn.cursor()

print("Creating 2-session recipe: gemma3:1b extract → gemma2:9b grade")

# Step 1: Create recipe
cursor.execute("""
INSERT INTO recipes (canonical_code, enabled, review_notes)
VALUES (?, ?, ?)
""", (
    'test_gemma3_extract_gemma2_grade',
    1,
    'Test full pipeline: gemma3:1b extraction + gemma2:9b validation on Credit Risk job'
))

recipe_id = cursor.lastrowid
print(f"✅ Recipe ID: {recipe_id}")

# Step 2: Create Session 1 - gemma3:1b extraction
cursor.execute("""
INSERT INTO sessions (
    recipe_id, 
    session_number, 
    session_name, 
    maintain_llm_context, 
    execution_order, 
    actor_id, 
    enabled
)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    recipe_id,
    1,
    'gemma3_extract_credit_risk',
    0,  # isolated context
    1,  # execution order
    'gemma3:1b',
    1   # enabled
))

session1_id = cursor.lastrowid
print(f"✅ Session 1 ID: {session1_id} - gemma3:1b (extract)")

# Step 3: Create Session 2 - gemma2:9b grading
cursor.execute("""
INSERT INTO sessions (
    recipe_id, 
    session_number, 
    session_name, 
    maintain_llm_context, 
    execution_order, 
    depends_on_session_id,
    actor_id, 
    enabled
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    recipe_id,
    2,
    'gemma2_grade_extraction',
    0,  # isolated context
    2,  # execution order
    session1_id,  # depends on session 1
    'gemma2:9b',
    1   # enabled
))

session2_id = cursor.lastrowid
print(f"✅ Session 2 ID: {session2_id} - gemma2:9b (grade) - depends on session {session1_id}")

# Step 4: Create Instruction 1 - gemma3:1b extraction
extraction_instruction = """Create a concise job description summary for this job posting:

{variations_param_1}

Use EXACTLY this format:

===OUTPUT TEMPLATE===
**Role:** [Exact job title from posting]
**Company:** [Company name]
**Location:** [Location]

**Key Responsibilities:**
• [Responsibility 1]
• [Responsibility 2]  
• [Responsibility 3]

**Requirements:**
• [Requirement 1]
• [Requirement 2]
• [Requirement 3]

**Details:**
• Employment: [Full-time/Part-time]
• Experience: [Years/Level mentioned]
• Contact: [Recruiter info if available]
===END TEMPLATE===

Important: Use ONLY information directly stated in the posting. Do not add, interpret, or invent any details."""

cursor.execute("""
INSERT INTO instructions (
    session_id, 
    step_number, 
    step_description, 
    prompt_template, 
    enabled
)
VALUES (?, ?, ?, ?, ?)
""", (
    session1_id,
    1,
    'Extract concise description from Credit Risk job',
    extraction_instruction,
    1
))

instruction1_id = cursor.lastrowid
print(f"✅ Instruction 1 ID: {instruction1_id} - extraction")

# Step 5: Create Instruction 2 - gemma2:9b grading
# This instruction needs to reference the output from Session 1
grading_instruction = """# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **posting summary** created by another AI:

--- start posting summary ---
{session_1_output}
--- end posting summary ---

## 3. Grade this posting summary by applying the following criteria:

### ✅ PASS if ALL of these are met:
- Correct role extraction (should match original posting exactly)
- Accurate key responsibilities (match original posting)
- Complete requirements (no missing key qualifications)
- Proper template format with ===OUTPUT TEMPLATE=== markers
- No hallucinated/invented information not in original

### ❌ FAIL if ANY of these issues:
- Wrong role extraction or interpretation
- Missing key requirements or responsibilities  
- Hallucinated skills/requirements not in original
- Poor formatting or missing template markers
- Invented information not stated in posting

## 4. Output your response

### Response Format
[PASS] or [FAIL]
[Detailed explanation of your decision, citing specific examples]

IMPORTANT: Start with [PASS] or [FAIL] in square brackets!"""

cursor.execute("""
INSERT INTO instructions (
    session_id, 
    step_number, 
    step_description, 
    prompt_template, 
    enabled
)
VALUES (?, ?, ?, ?, ?)
""", (
    session2_id,
    1,
    'Grade the extracted description quality',
    grading_instruction,
    1
))

instruction2_id = cursor.lastrowid
print(f"✅ Instruction 2 ID: {instruction2_id} - grading")

# Step 6: Create variation with the job posting
cursor.execute("""
INSERT INTO variations (recipe_id, variations_param_1, enabled)
VALUES (?, ?, ?)
""", (
    recipe_id,
    job_content,
    1
))

variation_id = cursor.lastrowid
print(f"✅ Variation ID: {variation_id}")

# Step 7: Create recipe run
cursor.execute("""
INSERT INTO recipe_runs (
    recipe_id, 
    variation_id, 
    batch_id, 
    status, 
    total_steps
)
VALUES (?, ?, ?, ?, ?)
""", (
    recipe_id,
    variation_id,
    1,  # batch_id
    'PENDING',
    2   # total_steps (2 sessions)
))

recipe_run_id = cursor.lastrowid
print(f"✅ Recipe Run ID: {recipe_run_id}")

conn.commit()
conn.close()

print(f"\n🎯 2-Session Recipe setup complete!")
print(f"Recipe: {recipe_id} (test_gemma3_extract_gemma2_grade)")
print(f"Session 1: {session1_id} (gemma3:1b extract)")
print(f"Session 2: {session2_id} (gemma2:9b grade - depends on session 1)")
print(f"Recipe Run: {recipe_run_id} (PENDING)")
print(f"\n🚀 Execute with: python3 recipe_run_test_runner_v31.py --max-runs 1")
print(f"\nThis will test the full pipeline: extraction → validation")