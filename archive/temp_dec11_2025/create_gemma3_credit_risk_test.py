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

print("Creating recipe to test gemma3:1b extraction on Credit Risk job...")

# Step 1: Create recipe
cursor.execute("""
INSERT INTO recipes (canonical_code, enabled, review_notes)
VALUES (?, ?, ?)
""", (
    'test_gemma3_credit_risk',
    1,
    'Test gemma3:1b extraction quality on Credit Risk Modelling job posting (job64659.json)'
))

recipe_id = cursor.lastrowid
print(f"✅ Recipe ID: {recipe_id}")

# Step 2: Create session for gemma3:1b
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

session_id = cursor.lastrowid
print(f"✅ Session ID: {session_id} - gemma3:1b")

# Step 3: Create instruction with concise description template
instruction_text = """Create a concise job description summary using EXACTLY this format:

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
    session_id,
    1,
    'Extract concise description from Credit Risk job',
    instruction_text,
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

print(f"\n🎯 Recipe setup complete!")
print(f"Recipe: {recipe_id} (test_gemma3_credit_risk)")
print(f"Session: {session_id} (gemma3:1b)")
print(f"Recipe Run: {recipe_run_id} (PENDING)")
print(f"\n🚀 Execute with: python3 recipe_run_test_runner_v31.py --max-runs 1")