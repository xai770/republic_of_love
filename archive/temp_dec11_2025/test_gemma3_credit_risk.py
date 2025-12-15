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

# Get current max IDs
cursor.execute("SELECT COALESCE(MAX(recipe_id), 0) FROM recipes")
recipe_id = cursor.fetchone()[0] + 1

cursor.execute("SELECT COALESCE(MAX(batch_id), 0) FROM batches")
batch_id = cursor.fetchone()[0] + 1

cursor.execute("SELECT COALESCE(MAX(variation_id), 0) FROM variations")
variation_id = cursor.fetchone()[0] + 1

cursor.execute("SELECT COALESCE(MAX(session_id), 0) FROM sessions")
session_id = cursor.fetchone()[0] + 1

cursor.execute("SELECT COALESCE(MAX(instruction_id), 0) FROM instructions")
instruction_id = cursor.fetchone()[0] + 1

cursor.execute("SELECT COALESCE(MAX(recipe_run_id), 0) FROM recipe_runs")
recipe_run_id = cursor.fetchone()[0] + 1

print(f"Creating recipe {recipe_id}: test_gemma3_credit_risk_extraction")

# Create recipe
cursor.execute("""
INSERT INTO recipes (recipe_id, name, description, created_at, enabled, total_sessions, actor_id)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    recipe_id,
    "test_gemma3_credit_risk_extraction",
    "Test gemma3:1b extraction on Credit Risk Modelling job posting",
    datetime.now().isoformat(),
    1,
    1,
    "gemma3:1b"
))

# Create batch
cursor.execute("""
INSERT INTO batches (batch_id, batch_name, created_at)
VALUES (?, ?, ?)
""", (batch_id, f"credit_risk_extraction_test_{datetime.now().strftime('%Y%m%d')}", datetime.now().isoformat()))

# Create variation with the job posting
cursor.execute("""
INSERT INTO variations (variation_id, param_1, created_at)
VALUES (?, ?, ?)
""", (variation_id, job_content, datetime.now().isoformat()))

# Create session
cursor.execute("""
INSERT INTO sessions (session_id, session_name, actor_id, context_mode, reason)
VALUES (?, ?, ?, ?, ?)
""", (
    session_id,
    "gemma3_extract_credit_risk",
    "gemma3:1b", 
    "isolated",
    "Test gemma3:1b concise description extraction on Credit Risk Modelling role"
))

# Create instruction with concise description template
instruction_text = """Create a concise job description summary using EXACTLY this format:

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

Important: Use ONLY information directly stated in the posting. Do not add, interpret, or invent any details."""

cursor.execute("""
INSERT INTO instructions (instruction_id, step_number, instruction_text, created_at, session_id)
VALUES (?, ?, ?, ?, ?)
""", (instruction_id, 1, instruction_text, datetime.now().isoformat(), session_id))

# Create recipe run
cursor.execute("""
INSERT INTO recipe_runs (recipe_run_id, recipe_id, variation_id, batch_id, status)
VALUES (?, ?, ?, ?, ?)
""", (recipe_run_id, recipe_id, variation_id, batch_id, 'PENDING'))

conn.commit()
conn.close()

print(f"✅ Created recipe {recipe_id} with:")
print(f"   - Recipe run {recipe_run_id}")
print(f"   - Session {session_id}: gemma3_extract_credit_risk")
print(f"   - Batch {batch_id}")
print(f"   - Variation {variation_id} with Credit Risk job posting")
print(f"\nExecute with: python3 recipe_run_test_runner_v31.py --max-runs 1")