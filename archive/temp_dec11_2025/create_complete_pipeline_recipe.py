#!/usr/bin/env python3

import sqlite3
import json
import os
from datetime import datetime

# Connect to database
conn = sqlite3.connect('/home/xai/Documents/ty_learn/data/llmcore.db')
cursor = conn.cursor()

print("=" * 70)
print("Creating Complete Extract + Validate Pipeline Recipe")
print("=" * 70)

# Step 1: Create recipe
print("\n📋 Step 1: Creating recipe...")
cursor.execute("""
INSERT INTO recipes (canonical_code, enabled, review_notes)
VALUES (?, ?, ?)
""", (
    'pipeline_extract_validate_5jobs',
    1,
    'Full pipeline: gemma3:1b extract + gemma2:latest validate on 5 job postings'
))
recipe_id = cursor.lastrowid
print(f"✅ Recipe ID: {recipe_id} (pipeline_extract_validate_5jobs)")

# Step 2: Create Session A - gemma3:1b extraction
print("\n📋 Step 2: Creating Session A (gemma3:1b extraction)...")
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
    'session_a_gemma3_extract',
    0,  # isolated context
    1,  # execution order
    'gemma3:1b',
    1   # enabled
))
session_a_id = cursor.lastrowid
print(f"✅ Session A ID: {session_a_id} (gemma3:1b)")

# Step 3: Create Instruction for Session A
print("\n📋 Step 3: Creating instruction for Session A...")
instruction_a = """Create a concise job description summary for this job posting:

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
    session_a_id,
    1,
    'Extract concise description',
    instruction_a,
    1
))
instruction_a_id = cursor.lastrowid
print(f"✅ Instruction A ID: {instruction_a_id}")

# Step 4: Extract descriptions from 5 JSONs and create variations
print("\n📋 Step 4: Creating variations from 5 job postings...")
postings_dir = '/home/xai/Documents/ty_learn/data/postings'

# Get first 5 JSON files
json_files = sorted([f for f in os.listdir(postings_dir) if f.endswith('.json')])[:5]

variation_ids = []
for idx, json_file in enumerate(json_files, 1):
    file_path = os.path.join(postings_dir, json_file)
    
    with open(file_path, 'r') as f:
        job_data = json.load(f)
    
    job_description = job_data.get('job_content', {}).get('description', '')
    
    if not job_description:
        print(f"⚠️  Skipping {json_file} - no description found")
        continue
    
    cursor.execute("""
    INSERT INTO variations (recipe_id, variations_param_1, enabled)
    VALUES (?, ?, ?)
    """, (
        recipe_id,
        job_description,
        1
    ))
    variation_id = cursor.lastrowid
    variation_ids.append(variation_id)
    print(f"✅ Variation {idx}: {json_file} (ID: {variation_id})")

print(f"\n📊 Created {len(variation_ids)} variations")

# Step 5: Create Session B - gemma2:latest grading
print("\n📋 Step 5: Creating Session B (gemma2:latest validation)...")
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
    'session_b_gemma2_validate',
    0,  # isolated context
    2,  # execution order
    session_a_id,  # depends on Session A
    'gemma2:latest',
    1   # enabled
))
session_b_id = cursor.lastrowid
print(f"✅ Session B ID: {session_b_id} (gemma2:latest) - depends on Session A")

# Step 6: Create Instruction for Session B
print("\n📋 Step 6: Creating instruction for Session B...")
instruction_b = """# Instructions: 
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
    session_b_id,
    1,
    'Validate extracted description',
    instruction_b,
    1
))
instruction_b_id = cursor.lastrowid
print(f"✅ Instruction B ID: {instruction_b_id}")

# Create recipe_runs for each variation
print("\n📋 Creating recipe_runs for each variation...")
recipe_run_ids = []
for idx, variation_id in enumerate(variation_ids, 1):
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
        idx,  # batch_id (1-5 for each variation)
        'PENDING',
        2   # 2 sessions (extract + validate)
    ))
    recipe_run_id = cursor.lastrowid
    recipe_run_ids.append(recipe_run_id)
    print(f"✅ Recipe Run {recipe_run_id}: Variation {variation_id}, Batch {idx}")

conn.commit()
conn.close()

print("\n" + "=" * 70)
print("🎯 Complete Pipeline Recipe Created!")
print("=" * 70)
print(f"Recipe ID: {recipe_id}")
print(f"Session A: {session_a_id} (gemma3:1b extract)")
print(f"Session B: {session_b_id} (gemma2:latest validate)")
print(f"Variations: {len(variation_ids)}")
print(f"Recipe Runs: {len(recipe_run_ids)}")
print("\n⚠️  NOTE: {session_1_output} in Session B instruction will NOT be auto-replaced")
print("    Runner v3.1 limitation - Session B will receive the placeholder as-is")
print("    To test with real output, use the manual embedding pattern from LLMCORE guide")
print("\n🚀 Execute with: python3 recipe_run_test_runner_v31.py --max-runs 5")
print("   This will run Session A only (extraction) for all 5 jobs")
print("   Session B will execute but won't have Session A output available")
print("=" * 70)