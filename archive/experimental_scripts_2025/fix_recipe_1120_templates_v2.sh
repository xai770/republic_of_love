#!/bin/bash
# Fix Recipe 1120 templates to use variations_param_1

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'
-- Update all instructions to use {variations_param_1}
UPDATE instructions
SET prompt_template = REPLACE(prompt_template, '{param_1}', '{variations_param_1}')
WHERE session_id IN (
    SELECT session_id FROM sessions 
    WHERE session_name IN ('sb_soft_skills_olmo', 'sb_technical_skills_phi3', 'sb_taxonomy_llama')
);

-- Verify
SELECT s.session_name, i.step_number, 
       CASE 
           WHEN i.prompt_template LIKE '%{variations_param_1}%' THEN '✅ Uses variations_param_1'
           ELSE '❌ Wrong placeholder'
       END as status
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name IN ('sb_soft_skills_olmo', 'sb_technical_skills_phi3', 'sb_taxonomy_llama');

SQL
