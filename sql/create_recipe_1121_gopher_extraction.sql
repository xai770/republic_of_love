-- Recipe 1121: Gopher Skill Extraction to SkillBridge
-- ======================================================
-- Purpose: Extract skills from job postings using skill_gopher
--          and import hierarchical taxonomy to skill_hierarchy
-- Input: postings.extracted_summary (from Recipe 1120)
-- Output: skill_hierarchy + postings.skill_keywords
-- Date: 2025-10-28

BEGIN;

-- ============================================
-- 1. Create Canonical
-- ============================================

INSERT INTO canonicals (
  canonical_code,
  facet_id,
  capability_description,
  prompt,
  response,
  enabled
) VALUES (
  'gopher_skill_extraction',
  'dynatax_skills',
  'Extract skills from job description and build hierarchical taxonomy using autonomous gopher agent',
  $$Job Description:
{job_description}

Extract all technical and soft skills, then build a hierarchical skill taxonomy.$$,
  $$Hierarchy:
ROOT/TECHNICAL_SKILLS/PYTHON
ROOT/TECHNICAL_SKILLS/SQL
ROOT/SOFT_SKILLS/COMMUNICATION$$,
  TRUE
) ON CONFLICT (canonical_code) DO UPDATE SET
  capability_description = EXCLUDED.capability_description,
  updated_at = NOW();

-- ============================================
-- 2. Create Recipe
-- ============================================

INSERT INTO recipes (
  recipe_id,
  recipe_name,
  recipe_description,
  max_total_session_runs,
  enabled
) VALUES (
  1121,
  'Gopher Skill Extraction',
  'Extract skills from job postings using skill_gopher autonomous agent and import to SkillBridge hierarchy',
  100,
  TRUE
) ON CONFLICT (recipe_id) DO UPDATE SET
  recipe_name = EXCLUDED.recipe_name,
  recipe_description = EXCLUDED.recipe_description,
  updated_at = NOW();

-- ============================================
-- 3. Create Session
-- ============================================

INSERT INTO sessions (
  session_id,
  canonical_code,
  session_name,
  session_description,
  actor_id,
  context_strategy,
  max_instruction_runs,
  enabled
) VALUES (
  9121,
  'gopher_skill_extraction',
  'Gopher Extraction Pipeline',
  'Complete skill extraction and hierarchy building using gopher + import to SkillBridge',
  'phi3:latest',  -- Primary coordinator
  'isolated',
  20,
  TRUE
) ON CONFLICT (session_id) DO UPDATE SET
  session_name = EXCLUDED.session_name,
  session_description = EXCLUDED.session_description,
  updated_at = NOW();

-- ============================================
-- 4. Register Session Actors (Helpers)
-- ============================================

-- Primary actor
INSERT INTO session_actors (session_id, actor_id, actor_role, enabled)
VALUES (9121, 'phi3:latest', 'primary', TRUE)
ON CONFLICT (session_id, actor_id) DO UPDATE SET
  actor_role = EXCLUDED.actor_role,
  enabled = EXCLUDED.enabled;

-- Helper: skill_gopher
INSERT INTO session_actors (session_id, actor_id, actor_role, enabled)
VALUES (9121, 'skill_gopher', 'helper', TRUE)
ON CONFLICT (session_id, actor_id) DO UPDATE SET
  actor_role = EXCLUDED.actor_role,
  enabled = EXCLUDED.enabled;

-- ============================================
-- 5. Create Instructions
-- ============================================

-- Instruction 1: Get job summary from postings table
INSERT INTO instructions (
  instruction_id,
  session_id,
  step_number,
  step_description,
  delegate_actor_id,  -- NULL = use session primary (phi3)
  prompt_template,
  enabled
) VALUES (
  91211,
  9121,
  1,
  'Fetch extracted summary from postings',
  NULL,  -- phi3 executes this
  $$You are a data retriever. Extract the job summary for job_id: {{job_id}}

The extracted_summary field from the postings table contains:
{{extracted_summary}}

If the summary is empty or NULL, use the raw job_description instead:
{{job_description}}

Return ONLY the job description text, no additional commentary.$$,
  TRUE
) ON CONFLICT (instruction_id) DO UPDATE SET
  prompt_template = EXCLUDED.prompt_template,
  updated_at = NOW();

-- Instruction 2: Extract key skills (phi3 preprocessing)
INSERT INTO instructions (
  instruction_id,
  session_id,
  step_number,
  step_description,
  delegate_actor_id,
  prompt_template,
  enabled
) VALUES (
  91212,
  9121,
  2,
  'Extract key skills and requirements',
  NULL,  -- phi3
  $$You are a skill extraction expert. Analyze this job description and extract ALL skills mentioned:

{{PREVIOUS_RESPONSE}}

List each skill on a separate line. Include:
- Technical skills (programming languages, tools, frameworks)
- Soft skills (communication, leadership, teamwork)
- Domain knowledge (industry expertise, certifications)
- Methodologies (Agile, DevOps, etc.)

Format: One skill per line, no bullets or numbers.$$,
  TRUE
) ON CONFLICT (instruction_id) DO UPDATE SET
  prompt_template = EXCLUDED.prompt_template,
  updated_at = NOW();

-- Instruction 3: Build hierarchy with Gopher (DELEGATED!)
INSERT INTO instructions (
  instruction_id,
  session_id,
  step_number,
  step_description,
  delegate_actor_id,
  prompt_template,
  enabled
) VALUES (
  91213,
  9121,
  3,
  'Build skill hierarchy using autonomous gopher',
  'skill_gopher',  -- DELEGATE to gopher!
  $${{PREVIOUS_RESPONSE}}$$,  -- Pass extracted skills directly to gopher
  TRUE
) ON CONFLICT (instruction_id) DO UPDATE SET
  delegate_actor_id = EXCLUDED.delegate_actor_id,
  prompt_template = EXCLUDED.prompt_template,
  updated_at = NOW();

-- Instruction 4: Format gopher output for database import
INSERT INTO instructions (
  instruction_id,
  session_id,
  step_number,
  step_description,
  delegate_actor_id,
  prompt_template,
  enabled
) VALUES (
  91214,
  9121,
  4,
  'Parse and format hierarchy paths',
  NULL,  -- phi3
  $$You are a data formatter. Convert this JSON hierarchy to a clean list:

{{PREVIOUS_RESPONSE}}

Extract the "hierarchy" array and output each path on a new line.
Remove the ROOT/ prefix from each path.
Format as: CATEGORY/SUBCATEGORY/SKILL

Example:
TECHNICAL/PROGRAMMING/PYTHON
TECHNICAL/DATABASE/SQL
SOFT_SKILLS/COMMUNICATION

Output ONLY the formatted paths, nothing else.$$,
  TRUE
) ON CONFLICT (instruction_id) DO UPDATE SET
  prompt_template = EXCLUDED.prompt_template,
  updated_at = NOW();

-- Instruction 5: Extract final skill list for JSONB storage
INSERT INTO instructions (
  instruction_id,
  session_id,
  step_number,
  step_description,
  delegate_actor_id,
  prompt_template,
  enabled
) VALUES (
  91215,
  9121,
  5,
  'Create skill keywords array',
  NULL,  -- phi3
  $$From these hierarchy paths:

{{PREVIOUS_RESPONSE}}

Extract ONLY the leaf skills (the last part after the final slash).
Output as a JSON array.

Example input:
TECHNICAL/PROGRAMMING/PYTHON
TECHNICAL/DATABASE/SQL

Example output:
["python", "sql"]

Provide ONLY the JSON array, nothing else.$$,
  TRUE
) ON CONFLICT (instruction_id) DO UPDATE SET
  prompt_template = EXCLUDED.prompt_template,
  updated_at = NOW();

-- ============================================
-- 6. Link Session to Recipe
-- ============================================

INSERT INTO recipe_sessions (recipe_id, session_id, execution_order)
VALUES (1121, 9121, 1)
ON CONFLICT (recipe_id, execution_order) DO UPDATE SET
  session_id = EXCLUDED.session_id;

COMMIT;

-- ============================================
-- Verification Queries
-- ============================================

-- Show recipe structure
SELECT 
  r.recipe_id,
  r.recipe_name,
  s.session_id,
  s.session_name,
  s.actor_id as primary_actor,
  COUNT(i.instruction_id) as instruction_count
FROM recipes r
JOIN recipe_sessions rs USING (recipe_id)
JOIN sessions s USING (session_id)
LEFT JOIN instructions i USING (session_id)
WHERE r.recipe_id = 1121
GROUP BY r.recipe_id, r.recipe_name, s.session_id, s.session_name, s.actor_id;

-- Show session actors
SELECT 
  s.session_name,
  sa.actor_id,
  sa.actor_role,
  a.execution_type
FROM sessions s
JOIN session_actors sa USING (session_id)
JOIN actors a USING (actor_id)
WHERE s.session_id = 9121
ORDER BY CASE sa.actor_role WHEN 'primary' THEN 1 WHEN 'helper' THEN 2 END;

-- Show instruction flow with delegation
SELECT 
  i.instruction_id,
  i.step_number,
  i.step_description,
  COALESCE(i.delegate_actor_id, s.actor_id) as effective_actor,
  CASE WHEN i.delegate_actor_id IS NOT NULL THEN 'DELEGATED' ELSE 'PRIMARY' END as execution_mode
FROM instructions i
JOIN sessions s USING (session_id)
WHERE s.session_id = 9121
ORDER BY i.step_number;
