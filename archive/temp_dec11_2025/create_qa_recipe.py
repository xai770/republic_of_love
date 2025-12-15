#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/llmcore.db')
cursor = conn.cursor()

# Read the job posting
with open('temp/job50571_raw_text.txt', 'r') as f:
    job_text = f.read()

# Create recipe
canonical_code = "qa_concise_description_top5"
review_notes = "QA test: Compare top 5 models for concise job description quality"

cursor.execute("INSERT INTO recipes (canonical_code, review_notes, enabled) VALUES (?, ?, 1)", 
               (canonical_code, review_notes))
recipe_id = cursor.lastrowid
print(f"✅ Recipe {recipe_id}: {canonical_code}")

# Top 5 models for QA
qa_models = [
    ('phi3:latest', 'Perfect template, 3.7s'),
    ('gemma3:1b', 'Production baseline, 3.5s'),
    ('phi4-mini:latest', 'Perfect template, 6.0s'),
    ('dolphin3:latest', 'Usable format, 3.9s'),
    ('llama3.2:latest', 'Usable format, 4.4s')
]

# Create sessions
session_ids = []
for i, (model, desc) in enumerate(qa_models, 1):
    cursor.execute("""
    INSERT INTO sessions (recipe_id, session_number, actor_id, session_name, session_description, enabled)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (recipe_id, i, model, f"qa_{model.replace(':', '_')}", desc))
    session_ids.append((cursor.lastrowid, model))
    print(f"   Session {i}: {model}")

# Create prompt
output_template = """===OUTPUT TEMPLATE===
ROLE: [fill in the job title/role in 1-2 words]
KEY_RESPONSIBILITIES: [fill in 2-3 core responsibilities, one per line with bullet points]
REQUIREMENTS: [fill in 3-5 key requirements, one per line with bullet points]
===END TEMPLATE==="""

prompt_template = f"""You are analyzing a job posting to create a concise, structured description.

JOB POSTING:
{job_text}

Your task: Extract and organize the key information into this template format:

{output_template}

CRITICAL INSTRUCTIONS:
- Return ONLY the filled template
- Use the EXACT template structure shown above
- Keep ROLE concise (1-2 words)
- List only CORE responsibilities (2-3 items)
- List only KEY requirements (3-5 items)
- NO commentary, NO explanations, NO meta-text
- Start directly with ===OUTPUT TEMPLATE==="""

# Create instructions
for session_id, actor_id in session_ids:
    cursor.execute("""
    INSERT INTO instructions (session_id, step_number, step_description, prompt_template, enabled)
    VALUES (?, 1, 'Extract concise description', ?, 1)
    """, (session_id, prompt_template))
print(f"✅ Created {len(session_ids)} instructions")

# Create variation
cursor.execute("INSERT INTO variations (recipe_id, variations_param_1, enabled) VALUES (?, ?, 1)",
               (recipe_id, "job50571_qa_top5"))
variation_id = cursor.lastrowid
print(f"✅ Variation {variation_id}: job50571_qa_top5")

# Create recipe_run (batch_id is required)
cursor.execute("INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status) VALUES (?, ?, 1, 'PENDING')",
               (recipe_id, variation_id))
recipe_run_id = cursor.lastrowid
print(f"✅ Recipe_run {recipe_run_id}: PENDING")

conn.commit()
conn.close()

print("\n" + "="*60)
print("QA TEST READY")
print("="*60)
print(f"Recipe: {recipe_id} | Run: {recipe_run_id}")
print("\n🚀 python3 recipe_run_test_runner_v31.py --max-runs 1")
