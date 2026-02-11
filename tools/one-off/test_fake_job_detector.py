import os
#!/usr/bin/env python3
"""
Quick test of Fake Job Detector workflow
Manually runs the 3-actor dialogue
"""

import json
import subprocess
import sys

# Fetch posting #15 data
posting_id = 15

print(f"🔍 Testing Fake Job Detector on posting #{posting_id}...")
print()

# Get job description from database
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='turing',
    user='base_admin',
    password=os.getenv('DB_PASSWORD', '')
)
cursor = conn.cursor()

cursor.execute("""
    SELECT job_title, organization_name, job_description, skill_keywords
    FROM postings
    WHERE posting_id = %s
""", (posting_id,))

row = cursor.fetchone()
job_title, company, job_desc, skills = row

print(f"📋 Job: {job_title}")
print(f"🏢 Company: {company}")
print(f"📝 Description length: {len(job_desc)} chars")
print(f"🎯 Skills extracted: {len(skills) if skills else 0}")
print()

# Format skills for display
skills_text = json.dumps(skills, indent=2) if skills else "None"

# Step 1: Analyst
print("=" * 70)
print("🎤 TURN 1: ANALYST")
print("=" * 70)

analyst_prompt = f"""Job Description:
{job_desc}

Extracted Skills:
{skills_text}

You are a data-driven job market analyst. Analyze this job posting and identify RED FLAGS that suggest it may be "pre-wired" for a specific candidate.

Look for:
- Overly specific years of experience with rare skill combinations  
- Requirements for internal systems/tools
- Impossibly narrow candidate pool
- Geographic + industry + technical stack that rarely overlap

Provide:
1. List of red flags with evidence (quote the posting)
2. Estimated candidate pool size
3. Preliminary assessment (LOW/MEDIUM/HIGH suspicion)

Be specific and quote evidence."""

print("Calling ollama qwen2.5:7b...")
print()

# Call ollama
result = subprocess.run(
    ['ollama', 'run', 'qwen2.5:7b', analyst_prompt],
    capture_output=True,
    text=True,
    timeout=120
)

analyst_output = result.stdout
print(analyst_output)
print()

# Step 2: Skeptic  
print("=" * 70)
print("🎤 TURN 2: SKEPTIC")
print("=" * 70)

skeptic_prompt = f"""Job Description:
{job_desc}

Analyst's Assessment:
{analyst_output}

You are a skeptical investigator. Challenge the Analyst's findings.

For each red flag, ask:
- Is this actually uncommon or just standard for senior roles?
- Could this be legitimate business need?
- What industry/level is this? (Finance naturally has stricter requirements)

Provide counter-arguments and alternative explanations.

Final position: LIKELY FAKE / POSSIBLY LEGITIMATE / NEEDS MORE DATA"""

print("Calling ollama qwen2.5:7b...")
print()

result = subprocess.run(
    ['ollama', 'run', 'qwen2.5:7b', skeptic_prompt],
    capture_output=True,
    text=True,
    timeout=120
)

skeptic_output = result.stdout
print(skeptic_output)
print()

# Step 3: HR Expert
print("=" * 70)
print("🎤 TURN 3: HR EXPERT (FINAL VERDICT)")
print("=" * 70)

hr_prompt = f"""Job Description:
{job_desc}

Extracted Skills:
{skills_text}

Analyst's Red Flags:
{analyst_output}

Skeptic's Challenge:
{skeptic_output}

You are a seasoned HR expert with 20+ years experience. Make the FINAL VERDICT.

Score 1-10 scale:
- 1-3: GENUINE OPENING (selective but reasonable)
- 4-7: COMPLIANCE THEATER (suspicious but plausible)
- 8-10: PRE-WIRED / FAKE JOB (clearly describes one person's resume)

Provide:
1. Final verdict with confidence score
2. Most damning evidence
3. Candidate pool reality check
4. Recommendation for candidates: Apply / Caution / Skip

Be decisive."""

print("Calling ollama qwen2.5:7b...")
print()

result = subprocess.run(
    ['ollama', 'run', 'qwen2.5:7b', hr_prompt],
    capture_output=True,
    text=True,
    timeout=120
)

hr_output = result.stdout
print(hr_output)
print()

print("=" * 70)
print("✅ FAKE JOB DETECTOR COMPLETE")
print("=" * 70)

conn.close()
