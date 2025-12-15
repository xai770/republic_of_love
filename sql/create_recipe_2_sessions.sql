-- Recipe 2: Profile Skill Extraction (CORRECTED for actual schema)
-- Purpose: Extract and map skills from candidate profiles
-- Parallel to Recipe 1114 for job postings

-- Recipe already created (ID 1122), now create sessions

-- ============================================================================
-- Step 1: Create Session 1 - Extract Profile Summary
-- ============================================================================

INSERT INTO sessions (
    session_name,
    session_description,
    canonical_code,
    actor_id,
    enabled
) VALUES (
    'r2_extract_profile_summary',
    'Extract professional summary from candidate profile/CV',
    'taxonomy_skill_extraction',  -- Reuse same canonical as Recipe 1114
    'gemma2:2b',
    TRUE
);

-- Add instruction for Session 1
INSERT INTO instructions (
    session_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    enabled
) SELECT
    session_id,
    1,
    'Extract professional summary from profile',
    '# Task: Extract Professional Summary from Profile

You are analyzing a candidate profile/CV. Extract a clean, structured professional summary.

## Input
{profile_raw_text}

## Instructions
1. Extract core information:
   - Professional identity (current role, specialization)
   - Years of experience and career level
   - Key domains/industries worked in
   - Core competencies and strengths
   - Notable achievements or impact
   
2. Structure:
   - Start with current role and identity
   - List key domains/expertise areas
   - Highlight significant achievements
   - Note career trajectory (progression, industries)

3. Format as bullet points for clarity

## Output
Return ONLY the professional summary in this format:

**Professional Identity:** [Current role/specialization]

**Experience Level:** [Years] years, [Level: entry/junior/mid/senior/lead/executive]

**Core Domains:**
- [Domain 1]
- [Domain 2]
- [Domain 3]

**Key Competencies:**
- [Competency 1]
- [Competency 2]
- [Competency 3]

**Notable Achievements:**
- [Achievement 1]
- [Achievement 2]

**Career Trajectory:** [Brief summary of career progression]',
    300,
    TRUE
FROM sessions 
WHERE session_name = 'r2_extract_profile_summary';

-- ============================================================================
-- Step 2: Create Session 2 - Extract Raw Skills
-- ============================================================================

INSERT INTO sessions (
    session_name,
    session_description,
    canonical_code,
    actor_id,
    enabled
) VALUES (
    'r2_extract_skills',
    'Extract raw skills from profile summary and work history',
    'taxonomy_skill_extraction',
    'qwen2.5:7b',
    TRUE
);

-- Add instruction for Session 2
INSERT INTO instructions (
    session_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    enabled
) SELECT
    session_id,
    1,
    'Extract skills from profile',
    '# Task: Extract Skills from Profile

You are analyzing a candidate profile. Extract ALL skills mentioned or implied.

## Input Summary
{session_1_output}

## Full Profile Text
{profile_raw_text}

## Instructions
1. Review both the summary and full profile text
2. Extract technical skills (programming languages, tools, platforms)
3. Extract domain skills (SAM, compliance, project management, etc.)
4. Extract soft skills (leadership, communication, etc.)
5. Include skills from:
   - Explicitly mentioned tools/technologies
   - Work responsibilities (e.g., "managed team" → Leadership)
   - Achievements (e.g., "negotiated contracts" → Negotiation)
   - Industry context (e.g., "banking" → Financial Services)

## Guidelines
- Extract 10-30 skills
- Use specific names (e.g., "Python" not "programming")
- Include both technical and soft skills
- Extract in original language (German or English)
- Avoid duplicates
- Infer reasonable skills from context

## Output
Return ONLY a JSON array of extracted skills:

["skill1", "skill2", "skill3", ...]

Example:
["SAP", "Contract Management", "Leadership", "Python", "Software Compliance", "Project Management", "Stakeholder Management"]',
    300,
    TRUE
FROM sessions 
WHERE session_name = 'r2_extract_skills';

-- ============================================================================
-- Step 3: Create Session 3 - Map to Taxonomy (REUSE from Recipe 1114)
-- ============================================================================

-- We can actually reuse Session 9 from Recipe 1114!
-- It's the SAME mapping logic, just different input source

INSERT INTO sessions (
    session_name,
    session_description,
    canonical_code,
    actor_id,
    enabled
) VALUES (
    'r2_map_to_taxonomy',
    'Translate skills to English and map to canonical job taxonomy',
    'taxonomy_skill_extraction',
    'qwen2.5:7b',
    TRUE
);

-- Copy the SAME instruction from Recipe 1114 Session 9
INSERT INTO instructions (
    session_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    enabled
) SELECT
    s.session_id,
    1,
    'Map extracted skills to taxonomy',
    i.prompt_template,  -- Copy from Recipe 1114 Session 9
    300,
    TRUE
FROM sessions s
CROSS JOIN LATERAL (
    SELECT i.prompt_template
    FROM instructions i
    JOIN sessions s2 ON i.session_id = s2.session_id
    WHERE s2.session_name = 'r1114_map_to_taxonomy'
    LIMIT 1
) i
WHERE s.session_name = 'r2_map_to_taxonomy';

-- ============================================================================
-- Step 4: Link Sessions to Recipe
-- ============================================================================

-- Session 1: Extract Summary (execution_order = 1)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order)
SELECT 
    r.recipe_id,
    s.session_id,
    1
FROM recipes r
CROSS JOIN sessions s
WHERE r.recipe_name = 'profile_skill_extraction'
  AND s.session_name = 'r2_extract_profile_summary';

-- Session 2: Extract Skills (execution_order = 2)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order)
SELECT 
    r.recipe_id,
    s.session_id,
    2
FROM recipes r
CROSS JOIN sessions s
WHERE r.recipe_name = 'profile_skill_extraction'
  AND s.session_name = 'r2_extract_skills';

-- Session 3: Map to Taxonomy (execution_order = 3)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order)
SELECT 
    r.recipe_id,
    s.session_id,
    3
FROM recipes r
CROSS JOIN sessions s
WHERE r.recipe_name = 'profile_skill_extraction'
  AND s.session_name = 'r2_map_to_taxonomy';

-- ============================================================================
-- Verification
-- ============================================================================

SELECT 'Recipe 2 sessions created successfully!' as status;

-- Show recipe details
SELECT 
    r.recipe_id,
    r.recipe_name,
    r.recipe_description,
    COUNT(rs.session_id) as session_count
FROM recipes r
LEFT JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
WHERE r.recipe_name = 'profile_skill_extraction'
GROUP BY r.recipe_id, r.recipe_name, r.recipe_description;

-- Show sessions
SELECT 
    rs.execution_order,
    s.session_name,
    s.actor_id,
    s.session_description
FROM recipe_sessions rs
JOIN sessions s ON rs.session_id = s.session_id
JOIN recipes r ON rs.recipe_id = r.recipe_id
WHERE r.recipe_name = 'profile_skill_extraction'
ORDER BY rs.execution_order;
