#!/usr/bin/env python3

import sqlite3

conn = sqlite3.connect('/home/xai/Documents/ty_learn/data/llmcore.db')
cursor = conn.cursor()

print("Fixing instruction to include job posting via variable substitution...")

# Update the instruction to use variable substitution
fixed_instruction = """Create a concise job description summary for this job posting:

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
UPDATE instructions 
SET prompt_template = ?
WHERE instruction_id = 2104
""", (fixed_instruction,))

print(f"✅ Updated instruction 2104 with variable substitution")

# Now create a new recipe run (batch 2) since we can't rerun the same batch
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
    1106,  # recipe_id from previous
    141,   # variation_id from previous
    2,     # batch_id = 2 (new batch)
    'PENDING',
    1
))

recipe_run_id = cursor.lastrowid
print(f"✅ Created new recipe run {recipe_run_id} (batch 2)")

conn.commit()
conn.close()

print(f"\n🚀 Execute with: python3 recipe_run_test_runner_v31.py --max-runs 1")