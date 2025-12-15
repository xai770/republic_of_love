-- Add Session 8 to Recipe 1114: Save extracted summary to postings table
-- This persists the formatted output from Session 7 to the database

BEGIN;

-- 1. Create canonical for saving summary
INSERT INTO canonicals (
  canonical_code,
  facet_id,
  capability_description,
  prompt,
  response,
  enabled
) VALUES (
  'save_extracted_summary',
  'dynatax_skills',
  'Save formatted job summary to postings.extracted_summary field',
  'Save this summary to database: {{PREVIOUS_RESPONSE}}',
  'Summary saved successfully',
  TRUE
) ON CONFLICT (canonical_code) DO UPDATE SET
  capability_description = EXCLUDED.capability_description,
  updated_at = NOW();

-- 2. Create session for saving
INSERT INTO sessions (
  session_id,
  canonical_code,
  session_name,
  session_description,
  actor_id,
  context_strategy,
  enabled
) VALUES (
  3345,
  'save_extracted_summary',
  'Save Summary to Database',
  'Persist formatted summary to postings.extracted_summary',
  'phi3:latest',  -- Doesn't matter, we'll use a script actor
  'inherit_previous',
  TRUE
) ON CONFLICT (session_id) DO UPDATE SET
  session_name = EXCLUDED.session_name,
  updated_at = NOW();

-- 3. Create instruction (this will need a database script actor)
INSERT INTO instructions (
  instruction_id,
  session_id,
  step_number,
  step_description,
  delegate_actor_id,
  prompt_template,
  enabled
) VALUES (
  3346,
  3345,
  1,
  'Update postings.extracted_summary',
  NULL,  -- Will need to create a script actor for this
  $$UPDATE postings 
SET extracted_summary = '{{PREVIOUS_RESPONSE}}',
    summary_extracted_at = NOW(),
    summary_extraction_status = 'completed'
WHERE job_id = '{{job_id}}';$$,
  TRUE
) ON CONFLICT (instruction_id) DO UPDATE SET
  prompt_template = EXCLUDED.prompt_template,
  updated_at = NOW();

-- 4. Link to Recipe 1114 as Session 8
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order)
VALUES (1114, 3345, 8)
ON CONFLICT (recipe_id, execution_order) DO UPDATE SET
  session_id = EXCLUDED.session_id;

COMMIT;

-- Verify
SELECT 
  rs.execution_order,
  s.session_name,
  i.step_description
FROM recipe_sessions rs
JOIN sessions s USING (session_id)
LEFT JOIN instructions i USING (session_id)
WHERE rs.recipe_id = 1114
ORDER BY rs.execution_order, i.step_number;
