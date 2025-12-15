# Job Requirements Extraction Experiment - REVISED
# Testing Actor Specialization with Production Prompts
# October 22, 2025 07:22

## Hypothesis
- Different actors have different extraction capabilities
- olmo2:latest excels at validation/judgment tasks
- Sequential validation (extract → validate) improves output quality
- Production prompt structure (bracket format) enforces compliance

## Test Job Posting
**Source:** job50571.json (Deutsche Bank)
**Title:** Senior Consultant (d/m/w) – Deutsche Bank Management Consulting
**Location:** Frankfurt, Deutschland
**Language:** English (with German section)

**Raw Description (9513 chars):**
Bilingual consultant role with clear requirements section. Contains marketing, benefits, responsibilities, AND actual requirements.

**Expected Requirements (Human Ground Truth):**

**EDUCATION:**
- Bachelor's/Master's degree (any field)
- Above-average academic performance

**EXPERIENCE:**
- Relevant professional experience in project management OR consulting
- Direct client contact and meeting management experience

**TECHNICAL SKILLS:**
- Project management
- Analytical skills
- Organizational talent

**SOFT SKILLS:**
- Teamwork
- Fluent German AND English (verhandlungssicher)
- Conflict management
- Persuasiveness
- Mentorship/training others

**BUSINESS SKILLS:**
- Strategic project work
- Stakeholder management (senior executives)
- Decision template preparation
- Best practices development

**What Should NOT Be Extracted:**
- Team description ("diverse backgrounds", "inclusive team")
- Job responsibilities ("You work on strategic projects")
- Benefits ("health check-ups", "pension plans", "Deutschlandticket")
- Company info ("Deutsche Bank Management Consulting")
- Contact details ("Nana Darko: +49 (0)175 - 6705312")
- Marketing language ("challenging tasks from day one")

---

## Experiment Design

### Recipe: extract_and_validate_job_requirements

**Session 1: Extraction (Multiple Actors Tested)**
- **Prompt Template (Adapted from production/v17 skill_extraction):**
```
# Skill Extraction Instructions

Extract job requirements from the following job posting and categorize them into the 5D Requirements Framework.

## Job Title
{job_title}

## Job Description
{job_description}

## Processing Instructions
DO NOT RETURN COMMENTARY, EXPLANATIONS OR OTHER ADDITIONS!
Format your response EXACTLY as shown below. Use square brackets for the output.
Example format:
[TECHNICAL: Python, SQL, Docker, AWS
BUSINESS: Financial Analysis, Risk Management
SOFT: Communication, Leadership, Problem Solving
EXPERIENCE: 3+ years software development, 2+ years business analysis
EDUCATION: Bachelor's degree in Computer Science, Finance certification]

## Required Output Format
Extract ONLY the requirements (what candidate must have). Do NOT include:
- Company descriptions
- Benefits offered
- Job responsibilities (what you will do)
- Contact information
- Marketing language

Categorize ALL requirements into exactly 5 categories:
- TECHNICAL: Programming languages, tools, software systems, technical skills
- BUSINESS: Domain knowledge, processes, methodologies, business functions
- SOFT: Communication, leadership, teamwork, interpersonal skills
- EXPERIENCE: Years required, specific backgrounds, levels, prior roles
- EDUCATION: Degrees, certifications, qualifications, academic requirements

## QA Check
Submit ONLY the categorized requirements in square brackets as shown in the example. Each category on its own line. Use comma-separated lists within each category.
```

**Test Actors for Session 1:**
1. llama3.2:latest (balanced, fast)
2. granite3.1-moe:3b (very fast, generous)
3. mistral:latest (mid-speed, quality focus)
4. qwen2.5:7b (slower, analytical)
5. olmo2:latest (our soft skills champion)

**Session 2: Validation (olmo2:latest only)**
- **Depends on:** Session 1 output
- **Prompt Template:**
```
# Extraction Validation Instructions

You are validating a requirements extraction task. Someone was asked to extract ONLY job requirements from a job posting and categorize them.

## What They Extracted:
{session_1_output}

## Your Task:
Determine if this output contains ONLY job requirements (qualifications and skills a candidate must have).

Check for these NON-requirements that should NOT be included:
- Company descriptions or history
- Benefits offered to employees
- Job responsibilities (what the person will DO in the role)
- Contact information
- Marketing language or promotional content
- Team descriptions

## Processing Instructions
DO NOT RETURN COMMENTARY, EXPLANATIONS OR OTHER ADDITIONS!
Format your response as [YES] or [NO].
Example: [YES]
Example: [NO]

## Decision Criteria:
- [YES] = Output contains ONLY requirements, properly categorized
- [NO] = Output contains ANY non-requirements, OR is improperly formatted

## QA Check
Submit ONLY [YES] or [NO] in square brackets. Nothing else.
```

**Session 3: Concise Description (olmo2:latest only)**
- **Purpose:** Human-readable summary for QA/review
- **Prompt Template:**
```
# Concise Description Generation

Create a brief, readable summary of this job posting. Focus on the KEY requirements and role purpose.

## Job Title
{job_title}

## Job Description
{job_description}

## Processing Instructions
DO NOT RETURN COMMENTARY, EXPLANATIONS OR OTHER ADDITIONS!
Format your response as a single paragraph in square brackets.
Maximum 300 characters.
Example: [Deutsche Bank seeks a Business Analyst for e-invoicing with 5+ years experience in financial processes, requiring SAP expertise and strong stakeholder management skills.]

## Content Guidelines:
- Include: Company name, role title, KEY requirements only
- Exclude: Benefits, full responsibilities list, marketing language
- Length: Maximum 300 characters
- Style: Concise, professional, factual

## QA Check
Submit ONLY the description in square brackets. Maximum 300 characters. One paragraph.
```

---

## Metrics to Collect

For each actor in Session 1:
1. **Latency** (how fast)
2. **Format compliance** (did they use brackets?)
3. **Requirement count** (how many items extracted)
4. **olmo2 validation** (did they pass [YES/NO]?)
5. **Human validation** (does it match our expected list?)

**Success criteria:**
- Actor extracts 5-7 requirements
- olmo2 says [YES]
- Human review confirms quality
- Total latency < 10 seconds (Session 1 + Session 2)

---

## Implementation Plan

1. **Create recipe in database** with proper canonical code
2. **Create Session 1 instruction** (extraction prompt)
3. **Create 5 sessions** (one per test actor)
4. **Run Session 1 for all actors**
5. **Create Session 2 instruction** (validation prompt)
6. **Create olmo2 validation session** (depends on each Session 1)
7. **Run Session 2 for all**
8. **Analyze results**

---

## Expected Outcomes

**Best Case:**
- One actor extracts cleanly (5-7 items, no fluff)
- olmo2 validates [YES]
- Fast (< 5s total)
- Human agrees with extraction

**Worst Case:**
- Actor includes marketing fluff
- olmo2 catches it, says [NO]
- Proves validation layer works!

**Learning:**
- Which actor is best at extraction
- Whether olmo2 can reliably validate
- If sequential validation catches errors
- Latency cost of validation step

---

## Next Steps After Results

If successful:
1. **Document winning actor** for extraction tasks
2. **Confirm olmo2** as validation specialist
3. **Create instruction version** for different job posting formats
4. **Build CV-to-requirements matching** next

If mixed results:
1. **Iterate on prompts** (add more examples)
2. **Test more actors**
3. **Add Session 3** (re-extraction if validation fails)

---

## Ready to Execute?

Waiting for your GO to:
1. Create the recipe in llmcore.db
2. Run the experiment
3. Generate comparison report

This will be BEAUTIFUL. 🎯
