# Recipe 1114: self_healing_dual_grader

**Enabled:** True
**Created:** 2025-10-22 16:09:51
**Updated:** 2025-10-29 15:24:42.898643

## Description

Multi-stage job posting extraction with self-correction using multiple LLMs for extraction, grading, improvement, and formatting

## Documentation

See docs/RECIPE_1114_COMPLETE.md for full documentation.

## Quick Summary
- **Purpose:** Extract job summaries and skills with dual grading quality control
- **Sessions:** 9 (summary extraction + dual grading + skill extraction + taxonomy mapping)
- **Performance:** ~2.5 min/job, 100% success rate
- **Bilingual:** German → English translation for skill taxonomy matching
- **Self-Healing:** Dual graders with automatic improvement loop

## Usage
```bash
# Process single job
python3 scripts/by_recipe_runner.py --recipe-id 1114 --job-id YOUR_JOB_ID

# Daily automation
python3 scripts/daily_recipe_1114.py
```

## Database Fields Updated
- `postings.extracted_summary` - Formatted job summary
- `postings.skill_keywords` - JSON array of taxonomy-matched skills

**Full Documentation:** docs/RECIPE_1114_COMPLETE.md

## Metadata

- **Total Sessions:** 9
- **Max Session Runs:** 100

## Sessions

### Session 1: session_a_gemma3_extract

- **Actor:** `gemma3:1b`
- **Session ID:** 3335
- **On Success:** continue
- **On Failure:** stop

**Description:** Extract job summary

#### Instructions

**Step 1: Extract with gemma3:1b**

- **Instruction ID:** 3328
- **Timeout:** 60s
- **Enabled:** True

**Prompt Template:**
```
Create a concise job description summary for this job posting:

{variations_param_1}

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information.
```

---

### Session 2: session_b_gemma2_grade

- **Actor:** `gemma2:latest`
- **Session ID:** 3336
- **On Success:** continue
- **On Failure:** stop

**Description:** Grade extraction with gemma2

#### Instructions

**Step 1: Grade with gemma2:latest**

- **Instruction ID:** 3329
- **Timeout:** 60s
- **Enabled:** True

**Prompt Template:**
```
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{session_1_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
```

---

### Session 3: session_c_qwen25_grade

- **Actor:** `qwen2.5:7b`
- **Session ID:** 3337
- **On Success:** continue
- **On Failure:** stop

**Description:** Second opinion grading

#### Instructions

**Step 1: Grade with qwen2.5:7b**

- **Instruction ID:** 3330
- **Timeout:** 60s
- **Enabled:** True

**Prompt Template:**
```
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{session_1_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
```

#### Branching Rules

- **Priority 10:** If matches `\[PASS\]` → Session 3341 - Both graders passed - skip improvement, go directly to format
- **Priority 10:** If matches `\[FAIL\]` → Session 3338 - Grading failed - go to improvement session
- **Priority 0:** If matches `*` → Session 3340 - Unexpected output format - create error ticket

---

### Session 4: session_d_qwen25_improve

- **Actor:** `qwen2.5:7b`
- **Session ID:** 3338
- **On Success:** continue
- **On Failure:** retry

**Description:** Improve extraction based on feedback

#### Instructions

**Step 1: Improve extraction based on previous grade**

- **Instruction ID:** 3331
- **Timeout:** 90s
- **Enabled:** True

**Prompt Template:**
```
# Your Task: Improve the job summary based on previous feedback

## Previous Grading Result:
{session_3_output}

## Original Job Posting:
{variations_param_1}

## Current Summary (that received feedback):
{session_1_output}

## Instructions:

**IF** the previous grading result starts with "[PASS]":
- Simply return the current summary unchanged
- Do NOT modify anything

**IF** the previous grading result starts with "[FAIL]":
- Read the feedback carefully
- Create an IMPROVED version of the summary that addresses ALL issues mentioned
- Use the same ===OUTPUT TEMPLATE=== format
- Extract ONLY from the original posting
- Fix completeness issues, accuracy problems, and formatting errors

Return ONLY the improved summary (or unchanged summary if [PASS]). No explanations.
```

---

### Session 5: session_e_qwen25_regrade

- **Actor:** `qwen2.5:7b`
- **Session ID:** 3339
- **On Success:** continue
- **On Failure:** stop

**Description:** Re-grade improved version

#### Instructions

**Step 1: Re-grade the improved version**

- **Instruction ID:** 3332
- **Timeout:** 60s
- **Enabled:** True

**Prompt Template:**
```
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** (this is the improved version):

--- start summary ---
{session_4_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
```

#### Branching Rules

- **Priority 10:** If matches `\[PASS\]` → Session 3341 - Improvement successful - format the improved version
- **Priority 10:** If matches `\[FAIL\]` → Session 3340 - Still failing after improvement - create error ticket
- **Priority 0:** If matches `*` → Session 3340 - Unexpected output format - create error ticket

---

### Session 6: session_f_create_ticket

- **Actor:** `qwen2.5:7b`
- **Session ID:** 3340
- **On Success:** continue
- **On Failure:** stop

**Description:** Create human review ticket

#### Instructions

**Step 1: Create ticket summary for human review**

- **Instruction ID:** 3333
- **Timeout:** 60s
- **Enabled:** True

**Prompt Template:**
```
# Create a ticket summary for human review

## Grading Results:
{session_3_output}

## Original Summary:
{session_1_output}

## Task:
Create a concise ticket for human review explaining:
1. What issues were found in the grading
2. What needs human attention
3. Any recommendations

Keep it brief and actionable.
```

---

### Session 7: Format Standardization

- **Actor:** `phi3:latest`
- **Session ID:** 3341
- **On Success:** continue
- **On Failure:** stop

**Description:** Standardize output format

#### Instructions

**Step 1: Standardize output format**

- **Instruction ID:** 3334
- **Timeout:** 300s
- **Enabled:** True

**Prompt Template:**
```
Clean this job posting summary by following these rules EXACTLY:

INPUT (use the best available summary - improved version if available, otherwise original):
{session_4_output?session_1_output}

RULES:
1. Remove ALL markdown code block markers (```, ```json, etc.)
2. Keep ONLY these section headers in this order:
   - **Role:**
   - **Company:**
   - **Location:**
   - **Job ID:**
   - **Key Responsibilities:**
   - **Requirements:**
   - **Details:**

3. Remove any "Type:", "Skills and Experience:", "Benefits:" sections - merge content into appropriate sections above
4. Format consistently:
   - Use "- " for all bullet points
   - Keep sections concise
   - No nested formatting
   - No extra blank lines between sections

5. Output PLAIN TEXT ONLY - no markdown wrappers

Return ONLY the cleaned version, nothing else.
```

---

### Session 8: r1114_extract_skills

- **Actor:** `qwen2.5:7b`
- **Session ID:** 3350
- **On Success:** continue
- **On Failure:** stop

**Description:** Extract raw skills from job summary (qwen2.5:7b)

#### Instructions

**Step 1: Extract all skills from job summary**

- **Instruction ID:** 3348
- **Timeout:** 300s
- **Enabled:** True

**Prompt Template:**
```
Extract ALL skills, technologies, and competencies mentioned in this job posting.

JOB SUMMARY:
{session_7_output}

TASK:
- List EVERY skill, tool, technology, or competency mentioned
- Include technical skills (Python, SQL, AWS, etc.)
- Include soft skills (leadership, communication, etc.)
- Include domain knowledge (finance, healthcare, etc.)
- Keep skills SHORT and ATOMIC (e.g., "SQL" not "Fundierte SQL Kenntnisse")
- Extract the core skill name, not full descriptions
- If text is in German, extract German skill names
- Return 5-20 skills typically

Return a simple JSON array of skills found:
["skill_1", "skill_2", "skill_3"]

Return ONLY the JSON array, no other text.
```

---

### Session 9: r1114_map_to_taxonomy

- **Actor:** `qwen2.5:7b`
- **Session ID:** 3351
- **On Success:** continue
- **On Failure:** stop

**Description:** Translate skills to English and map to taxonomy (qwen2.5:7b)

#### Instructions

**Step 1: Translate skills to English for taxonomy mapping**

- **Instruction ID:** 3349
- **Timeout:** 180s
- **Enabled:** True

**Prompt Template:**
```
Map these raw skills to our canonical taxonomy.

RAW SKILLS EXTRACTED:
{session_8_output}

TASK:
You have access to an interactive taxonomy query system. Ask questions like:
- LIST_DOMAINS - see all domain names
- GET_SKILLS domain_name - list skills in a domain  
- SEARCH query - find skills matching text
- CHECK skill_name - verify if skill exists

For each raw skill, find the best matching canonical skill.

When done, respond with:

MAPPED_SKILLS:
["Canonical_Skill_1", "Canonical_Skill_2", ...]

```

---

## Recent Executions

| Run ID | Status | Mode | Batch | Sessions | Started | Duration |
|--------|--------|------|-------|----------|---------|----------|
| 770 | RUNNING | testing | 1 | 1/9 | 2025-10-30 14:45 | 0.0s (15929) |
| 508 | SUCCESS | testing | 1 | 6/9 | 2025-10-29 15:05 | 102.7s (64255) |
| 507 | SUCCESS | testing | 1 | 4/7 | 2025-10-29 13:00 | 56.4s (64727) |
| 506 | SUCCESS | testing | 1 | 4/7 | 2025-10-29 12:59 | 83.4s (59428) |
| 505 | SUCCESS | production | 3 | 4/7 | 2025-10-29 12:23 | 49.3s (44162) |

---

*Generated by Recipe Report Tool on 2025-10-30 14:54:24*