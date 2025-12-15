#!/bin/bash
# Fix Recipe 1120 Session 3 template to use session outputs

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'
-- Update Session 3 to use session_N_output format
UPDATE instructions
SET prompt_template = '
Hey! I need help organizing skills from this job posting into a final hierarchy.

Job posting:
{variations_param_1}

Soft skills identified:
{session_1_output}

Technical skills identified:
{session_2_output}

Please combine these into a clean hierarchical taxonomy using this format:
CATEGORY/SUBCATEGORY/SKILL_NAME

Output format:
+++OUTPUT START+++
[your categorizations here, one per line]
+++OUTPUT END+++

Thanks!'
WHERE session_id = (SELECT session_id FROM sessions WHERE session_name = 'sb_taxonomy_llama')
  AND step_number = 1;

-- Verify
SELECT 'Updated Session 3 template' as status;

SQL
