-- Update Recipe 1121 to use hybrid skills extraction
-- Old version will be automatically backed up by trigger to instructions_history

-- Step 1: Update Recipe description
UPDATE recipes 
SET recipe_description = 'Extract skills from job postings with importance (essential/critical/important/preferred), proficiency required (expert/advanced/intermediate/beginner), years required, and reasoning. Uses Qwen for intelligent hybrid skill analysis.'
WHERE recipe_id = 1121;

-- Step 2: Create new sessions for hybrid extraction
INSERT INTO sessions (session_id, canonical_code, session_name, session_description, actor_id, enabled)
VALUES 
  (1121001, 'job_summary_r1121', 'Job Summary Extraction', 'Extract comprehensive job description summary', 'qwen2.5:7b', TRUE),
  (1121002, 'job_hybrid_skills_r1121', 'Hybrid Skills Extraction', 'Extract skills with importance, proficiency, years, and reasoning', 'qwen2.5:7b', TRUE)
ON CONFLICT (session_id) DO UPDATE
SET session_name = EXCLUDED.session_name,
    session_description = EXCLUDED.session_description,
    actor_id = EXCLUDED.actor_id,
    enabled = EXCLUDED.enabled;

-- Step 3: Replace recipe_sessions links
DELETE FROM recipe_sessions WHERE recipe_id = 1121;
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order)
VALUES 
  (1121, 1121001, 1),
  (1121, 1121002, 2);

-- Step 4: Create new instructions (old ones will be backed up by trigger)
DELETE FROM instructions WHERE session_id IN (1121001, 1121002);

-- Session 1: Summary extraction
INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
VALUES (1121001, 1, 'Extract job summary', $$You are analyzing a job posting to extract a comprehensive summary.

**Job Posting:**
{job_description}

**Your Task:**
Extract a clear, comprehensive summary of this position including:
- Job title and level (junior/mid/senior/lead/principal)
- Key responsibilities and duties
- Required qualifications and experience
- Industry/domain context
- Team structure and reporting relationships
- Work environment details

**Output:**
Return ONLY the summary text (no JSON, no markdown, just plain text). Keep it concise but complete (200-500 words).
$$, 60, TRUE);

-- Session 2: Hybrid skills extraction
INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled)
VALUES (1121002, 1, 'Extract skills with hybrid metadata', $$You are a skills extraction expert for a talent matching system. Extract skills from this job posting with precise metadata.

**Job Summary:**
{summary}

**Original Job Posting:**
{job_description}

**Your Task:**
Extract EVERY skill requirement mentioned or implied in this job posting. For each skill, determine:

## Importance Levels:
- **essential** (90-100 weight): Absolutely required, deal-breaker if missing. Usually stated as "must have", "required", "essential"
- **critical** (65-89 weight): Very important but may have workarounds. Usually stated as "strong experience in", "proficient in"
- **important** (35-64 weight): Valued and expected. Usually in "responsibilities" or "you will" sections
- **preferred** (10-34 weight): Nice to have. Usually stated as "preferred", "nice to have", "bonus"

## Proficiency Levels:
- **expert**: Deep mastery, can teach others, handles edge cases. Usually for senior/lead roles or core technologies
- **advanced**: Strong working knowledge, handles most scenarios independently, 3-5 years typical
- **intermediate**: Working knowledge, needs some guidance, 1-3 years typical
- **beginner**: Basic familiarity, needs supervision, <1 year

## Years Required:
- Extract explicit year requirements ("5+ years", "3-5 years")
- If not stated, infer from job level: 
  * Junior: 0-2 years
  * Mid: 2-4 years
  * Senior: 5-8 years
  * Lead/Principal: 8+ years
- Essential skills usually require more years than preferred skills

## Weight Calculation:
Assign numeric weight based on importance:
- Essential: 90-100 (100 for THE core skill, 95 for other essentials, 90 for must-haves)
- Critical: 65-89 (85 for very critical, 75 for critical, 65 for important-critical)
- Important: 35-64 (60 for highly valued, 50 for standard, 35 for somewhat important)
- Preferred: 10-34 (30 for nice to have, 20 for bonus, 10 for optional)

**Output Format:**
Return a JSON array of skill objects. Each skill MUST have:
- skill: Technology, tool, framework, or competency (be specific - include versions if mentioned)
- importance: "essential", "critical", "important", or "preferred"
- weight: numeric 10-100 based on importance
- proficiency: "expert", "advanced", "intermediate", or "beginner"
- years_required: integer (0 if not required/specified)
- reasoning: Brief explanation (why this importance/proficiency, where mentioned in posting)

**Example:**
[
  {
    "skill": "Python",
    "importance": "essential",
    "weight": 100,
    "proficiency": "expert",
    "years_required": 5,
    "reasoning": "Core requirement stated as 'must have 5+ years Python', for senior role"
  },
  {
    "skill": "Docker",
    "importance": "critical",
    "weight": 75,
    "proficiency": "advanced",
    "years_required": 2,
    "reasoning": "Required for containerization tasks, stated in responsibilities"
  },
  {
    "skill": "GraphQL",
    "importance": "preferred",
    "weight": 25,
    "proficiency": "intermediate",
    "years_required": 0,
    "reasoning": "Nice to have for API development, mentioned as bonus"
  }
]

**Important:**
- Extract ALL skills mentioned (technical AND soft skills like leadership, communication)
- Be specific: "React 18" not just "JavaScript", "PostgreSQL 14" not just "SQL"
- Soft skills are usually important/preferred unless role is leadership (then critical/essential)
- Return ONLY valid JSON array, nothing else
$$, 120, TRUE);

SELECT 'Recipe 1121 updated to hybrid format! Old version backed up to instructions_history.' AS status;
