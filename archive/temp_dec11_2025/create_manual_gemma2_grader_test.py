#!/usr/bin/env python3

import sqlite3
import json
from datetime import datetime

# Get the gemma3:1b output from the previous test
gemma3_output = """```
===OUTPUT TEMPLATE===
**Role:** Credit Risk Modelling – Risk Methodology Specialist in Group Strategic Analytics
**Company:** Group Strategic Analytics
**Location:** Frankfurt
**Job ID:** R0394362
**Type:** Regular
**Listed:** 2025-07-02

**Key Responsibilities:**
• Development, implementation, and maintenance of industry-leading internal models (PD, LGD, CCF) for credit portfolio risk assessment, adhering to regulatory requirements.
• Collaboration with business units (Business Lending, Risk, Finance), regulatory agencies, and the financial sector to build risk models reflecting Deutsche Bank's profile, ensuring compliance.
• Resolution of regulatory and internal findings related to credit risk parameter modeling.
• Collaboration with other business area specialists – Business Lending, Credit Risk Management, Finance, Capital Management, and Regulatory Affairs.
• Presentation of models to regulators.

**Requirements:**
• Strong academic background (Hochschulabschluss in Finanzmathematik, Statistik, Mathematik, Physik, or a similar field).
• Excellent academic performance.
• Significant experience in credit risk modeling (PD, LGD, CCF), strong credit risk knowledge, and familiarity with relevant regulations (e.g., EU Capital Requirements Regulations (CRR)).
• Practical, hands-on approach to modeling.
• Excellent analytical skills, statistical knowledge, and comfortable working with very large and complex datasets.
• Excellent communication skills in English (ideally German).

**Details:**
• Full-time position.
• Part-time position available.
• Compensation varies based on location.
• Benefits package includes a wide range of benefits covering all aspects of your professional and personal life.
• Emotional balance, positive attitude, and a supportive work environment.
• Fitness benefits: Counseling in difficult life situations, mental health awareness training.
• Excellent work-life balance: Flexible working options (e.g., part-time, hybrid working, job tandem), including support for career and personal growth.
• Socially connected: Collaboration with other professionals fosters new perspectives and boosts self-confidence.
• Diversity, equity, and inclusion initiatives.
• Strong emphasis on collaboration.

===END TEMPLATE==="""

# Read the original job posting
with open('/home/xai/Documents/ty_learn/data/postings_backup_20250728/job64659.json', 'r') as f:
    job_data = json.load(f)

job_content = job_data['job_content']['description']

# Connect to database
conn = sqlite3.connect('/home/xai/Documents/ty_learn/data/llmcore.db')
cursor = conn.cursor()

print("Creating manual grader test: gemma2:latest evaluating gemma3:1b output")

# Step 1: Create recipe
cursor.execute("""
INSERT INTO recipes (canonical_code, enabled, review_notes)
VALUES (?, ?, ?)
""", (
    'manual_gemma2_grade_gemma3',
    1,
    'Manual test: gemma2:latest grading actual gemma3:1b Credit Risk extraction'
))

recipe_id = cursor.lastrowid
print(f"✅ Recipe ID: {recipe_id}")

# Step 2: Create session for gemma2:latest grading
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
    'gemma2_grade_real_output',
    0,  # isolated context
    1,  # execution order
    'gemma2:latest',
    1   # enabled
))

session_id = cursor.lastrowid
print(f"✅ Session ID: {session_id} - gemma2:latest")

# Step 3: Create instruction with both job posting and actual gemma3:1b output
grading_instruction = f"""# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{{variations_param_1}}
--- end raw posting ---

## 2. Read the following **posting summary** created by gemma3:1b:

--- start posting summary ---
{gemma3_output}
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
    session_id,
    1,
    'Grade gemma3:1b Credit Risk extraction',
    grading_instruction,
    1
))

instruction_id = cursor.lastrowid
print(f"✅ Instruction ID: {instruction_id}")

# Step 4: Create variation with the job posting
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

# Step 5: Create recipe run
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
    1   # total_steps (1 session)
))

recipe_run_id = cursor.lastrowid
print(f"✅ Recipe Run ID: {recipe_run_id}")

conn.commit()
conn.close()

print(f"\n🎯 Manual grader test setup complete!")
print(f"Recipe: {recipe_id} (manual_gemma2_grade_gemma3)")
print(f"Session: {session_id} (gemma2:latest grading real gemma3:1b output)")
print(f"Recipe Run: {recipe_run_id} (PENDING)")
print(f"\n🚀 Execute with: python3 recipe_run_test_runner_v31.py --max-runs 1")
print(f"\nThis will test: Can gemma2:latest properly grade gemma3:1b's Credit Risk extraction?")