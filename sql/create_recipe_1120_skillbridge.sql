-- Recipe 1120: SkillBridge Skills Extraction
-- Created: 2025-10-25
-- Purpose: Extract and categorize job skills using multi-model hierarchical taxonomy

-- ============================================================================
-- STEP 1: Create Facet
-- ============================================================================

INSERT INTO facets (facet_id, parent_id, short_description, remarks, enabled)
VALUES (
    'dynatax_skills',
    NULL,
    'SkillBridge: Skills extraction and taxonomy building',
    'Extracts skills from job postings and builds hierarchical taxonomies (CATEGORY/SUBCATEGORY/TERM paths) for candidate matching',
    true
)
ON CONFLICT (facet_id) DO NOTHING;

-- ============================================================================
-- STEP 2: Create Canonicals (3 phases)
-- ============================================================================

-- Canonical 1: Soft Skills Detection (olmo2:7b)
INSERT INTO canonicals (canonical_code, facet_id, capability_description, prompt, response, enabled)
VALUES (
    'sb_extract_soft_skills',
    'dynatax_skills',
    'Extract soft skills from job posting using olmo2:7b for perfect binary classification',
    'I''m building SkillBridge - a system to extract and categorize job skills. Here''s a job posting:

{job_posting_text}

Which of these are soft skills vs technical skills? Just give me your gut reaction.',
    'Expected format:

**Technical Skills:**
- [list]

**Soft Skills:**
- [list]',
    true
)
ON CONFLICT (canonical_code) DO UPDATE SET
    prompt = EXCLUDED.prompt,
    response = EXCLUDED.response,
    updated_at = CURRENT_TIMESTAMP;

-- Canonical 2: Technical Skills Extraction (phi3:latest)
INSERT INTO canonicals (canonical_code, facet_id, capability_description, prompt, response, enabled)
VALUES (
    'sb_extract_technical_skills',
    'dynatax_skills',
    'Extract technical skills in strict hierarchical format using phi3:latest for perfect format compliance',
    '+++SKILLBRIDGE EXTRACTION+++

Task: Extract skills from job posting and categorize using hierarchical paths.

Input:
{job_posting_text}

Output format (use EXACTLY):
+++OUTPUT START+++
TECHNICAL/WEB_FUNDAMENTALS/HTML
TECHNICAL/WEB_FUNDAMENTALS/CSS
TECHNICAL/PROGRAMMING/JavaScript
TECHNICAL/FRAMEWORK/React
TECHNICAL/VERSION_CONTROL/Git
+++OUTPUT END+++

Rules:
1. Extract ONLY skills explicitly mentioned
2. Use path format: CATEGORY/SUBCATEGORY/TERM
3. One skill per line
4. No elaboration

Execute.',
    'Expected: +++OUTPUT START+++ block with hierarchical paths, one per line',
    true
)
ON CONFLICT (canonical_code) DO UPDATE SET
    prompt = EXCLUDED.prompt,
    response = EXCLUDED.response,
    updated_at = CURRENT_TIMESTAMP;

-- Canonical 3: Final Taxonomy Assembly (llama3.2:latest)
INSERT INTO canonicals (canonical_code, facet_id, capability_description, prompt, response, enabled)
VALUES (
    'sb_assemble_taxonomy',
    'dynatax_skills',
    'Combine soft and technical skills into final taxonomy using llama3.2:latest for balanced output',
    'Hey! I need help organizing skills from this job posting into a final hierarchy.

Job posting:
{job_posting_text}

Soft skills identified:
{soft_skills_from_session_1}

Technical skills identified:
{technical_skills_from_session_2}

Please combine these into a clean hierarchical taxonomy using this format:
CATEGORY/SUBCATEGORY/SKILL_NAME

Output format:
+++OUTPUT START+++
[your categorizations here, one per line]
+++OUTPUT END+++

Thanks!',
    'Expected: +++OUTPUT START+++ block with complete taxonomy',
    true
)
ON CONFLICT (canonical_code) DO UPDATE SET
    prompt = EXCLUDED.prompt,
    response = EXCLUDED.response,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- STEP 3: Create Actors (AI models)
-- ============================================================================

-- Actor 1: olmo2:7b
INSERT INTO actors (actor_id, actor_type, url, enabled)
VALUES (
    'olmo2:7b',
    'ai_model',
    'ollama://olmo2:7b',
    true
)
ON CONFLICT (actor_id) DO NOTHING;

-- Actor 2: phi3:latest
INSERT INTO actors (actor_id, actor_type, url, enabled)
VALUES (
    'phi3:latest',
    'ai_model',
    'ollama://phi3:latest',
    true
)
ON CONFLICT (actor_id) DO NOTHING;

-- Actor 3: llama3.2:latest
INSERT INTO actors (actor_id, actor_type, url, enabled)
VALUES (
    'llama3.2:latest',
    'ai_model',
    'ollama://llama3.2:latest',
    true
)
ON CONFLICT (actor_id) DO NOTHING;

-- ============================================================================
-- STEP 4: Create Sessions (3 models)
-- ============================================================================

-- Session 1: Soft skills extraction (olmo2:7b)
INSERT INTO sessions (session_name, canonical_code, actor_id, session_description, max_instruction_runs, enabled)
SELECT 'sb_soft_skills_olmo', 'sb_extract_soft_skills', 'olmo2:7b', 
       'Extract soft skills using olmo2:7b (excellent soft skills detection, EQ 10/10)', 5, true
WHERE NOT EXISTS (SELECT 1 FROM sessions WHERE session_name = 'sb_soft_skills_olmo');

-- Session 2: Technical skills extraction (phi3:latest)
INSERT INTO sessions (session_name, canonical_code, actor_id, session_description, max_instruction_runs, enabled)
SELECT 'sb_technical_skills_phi3', 'sb_extract_technical_skills', 'phi3:latest',
       'Extract technical skills using phi3:latest (perfect format compliance, EQ 5/10)', 5, true
WHERE NOT EXISTS (SELECT 1 FROM sessions WHERE session_name = 'sb_technical_skills_phi3');

-- Session 3: Final taxonomy assembly (llama3.2:latest)
INSERT INTO sessions (session_name, canonical_code, actor_id, session_description, max_instruction_runs, enabled)
SELECT 'sb_taxonomy_llama', 'sb_assemble_taxonomy', 'llama3.2:latest',
       'Assemble final taxonomy using llama3.2:latest (balanced output, proven production reliability)', 5, true
WHERE NOT EXISTS (SELECT 1 FROM sessions WHERE session_name = 'sb_taxonomy_llama');

-- ============================================================================
-- STEP 5: Create Recipe
-- ============================================================================

INSERT INTO recipes (recipe_id, recipe_name, recipe_description, recipe_version, max_total_session_runs, enabled)
VALUES (
    1120,
    'SkillBridge Skills Extraction',
    'Extract and categorize job skills using multi-model hierarchical taxonomy approach. Phase 1: olmo2 identifies soft skills. Phase 2: phi3 extracts technical skills with strict formatting. Phase 3: llama3.2 assembles final taxonomy.',
    1,
    100,
    true
)
ON CONFLICT (recipe_id) DO UPDATE SET
    recipe_name = EXCLUDED.recipe_name,
    recipe_description = EXCLUDED.recipe_description,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- STEP 6: Link Sessions to Recipe
-- ============================================================================

-- Session 1: Soft skills extraction (always runs first)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order, execute_condition, on_success_action, on_failure_action, max_retry_attempts)
SELECT
    1120,
    session_id,
    1,
    'always',
    'continue',
    'stop',
    1
FROM sessions WHERE session_name = 'sb_soft_skills_olmo';

-- Session 2: Technical skills extraction (runs after Session 1 succeeds)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order, execute_condition, on_success_action, on_failure_action, max_retry_attempts)
SELECT
    1120,
    session_id,
    2,
    'on_success',
    'continue',
    'stop',
    2
FROM sessions WHERE session_name = 'sb_technical_skills_phi3';

-- Session 3: Final taxonomy assembly (runs after Session 2 succeeds)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order, execute_condition, on_success_action, on_failure_action, max_retry_attempts)
SELECT
    1120,
    session_id,
    3,
    'on_success',
    'stop',
    'stop',
    1
FROM sessions WHERE session_name = 'sb_taxonomy_llama';

-- ============================================================================
-- STEP 7: Create Instructions for Each Session
-- ============================================================================

-- Instructions for Session 1: sb_soft_skills_olmo
-- Step 1: Send job posting and ask for soft skills
INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, expected_pattern, validation_rules, is_terminal, enabled)
SELECT
    session_id,
    1,
    'Ask olmo2:7b to identify soft vs technical skills',
    'I''m building SkillBridge - a system to extract and categorize job skills. Here''s a job posting:

{job_posting_text}

Which of these are soft skills vs technical skills? Just give me your gut reaction.',
    60,
    '\*\*Soft Skills:\*\*',
    '{"must_contain": ["Soft Skills", "Technical Skills"]}',
    true,
    true
FROM sessions WHERE session_name = 'sb_soft_skills_olmo';

-- Instructions for Session 2: sb_technical_skills_phi3
-- Step 1: Send strict extraction command
INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, expected_pattern, validation_rules, is_terminal, enabled)
SELECT
    session_id,
    1,
    'Command phi3 to extract technical skills in strict format',
    '+++SKILLBRIDGE EXTRACTION+++

Task: Extract skills from job posting and categorize using hierarchical paths.

Input:
{job_posting_text}

Output format (use EXACTLY):
+++OUTPUT START+++
TECHNICAL/WEB_FUNDAMENTALS/HTML
TECHNICAL/WEB_FUNDAMENTALS/CSS
TECHNICAL/PROGRAMMING/JavaScript
TECHNICAL/FRAMEWORK/React
TECHNICAL/VERSION_CONTROL/Git
+++OUTPUT END+++

Rules:
1. Extract ONLY skills explicitly mentioned
2. Use path format: CATEGORY/SUBCATEGORY/TERM
3. One skill per line
4. No elaboration

Execute.',
    60,
    '\+\+\+OUTPUT START\+\+\+',
    '{"must_contain": ["+++OUTPUT START+++", "+++OUTPUT END+++"]}',
    true,
    true
FROM sessions WHERE session_name = 'sb_technical_skills_phi3';

-- Instructions for Session 3: sb_taxonomy_llama
-- Step 1: Ask llama3.2 to combine results
INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, expected_pattern, validation_rules, is_terminal, enabled)
SELECT
    session_id,
    1,
    'Ask llama3.2 to assemble final taxonomy from previous sessions',
    'Hey! I need help organizing skills from this job posting into a final hierarchy.

Job posting:
{job_posting_text}

Soft skills identified:
{soft_skills_from_session_1}

Technical skills identified:
{technical_skills_from_session_2}

Please combine these into a clean hierarchical taxonomy using this format:
CATEGORY/SUBCATEGORY/SKILL_NAME

Output format:
+++OUTPUT START+++
[your categorizations here, one per line]
+++OUTPUT END+++

Thanks!',
    60,
    '\+\+\+OUTPUT START\+\+\+',
    '{"must_contain": ["+++OUTPUT START+++", "+++OUTPUT END+++"]}',
    true,
    true
FROM sessions WHERE session_name = 'sb_taxonomy_llama';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check recipe structure
SELECT 
    r.recipe_name,
    rs.execution_order,
    s.session_name,
    a.actor_id,
    c.canonical_code,
    rs.execute_condition,
    rs.on_success_action
FROM recipes r
JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
JOIN sessions s ON rs.session_id = s.session_id
JOIN actors a ON s.actor_id = a.actor_id
JOIN canonicals c ON s.canonical_code = c.canonical_code
WHERE r.recipe_id = 1120
ORDER BY rs.execution_order;

-- Check instructions
SELECT 
    s.session_name,
    i.step_number,
    i.step_description,
    i.timeout_seconds,
    i.is_terminal
FROM sessions s
JOIN instructions i ON s.session_id = i.session_id
WHERE s.session_name IN ('sb_soft_skills_olmo', 'sb_technical_skills_phi3', 'sb_taxonomy_llama')
ORDER BY s.session_name, i.step_number;
