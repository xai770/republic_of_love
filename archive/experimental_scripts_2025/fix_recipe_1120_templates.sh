#!/bin/bash
# Fix Recipe 1120 templates to use param_1

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'
-- Update all instructions to use {param_1} instead of {job_posting_text}
UPDATE instructions
SET prompt_template = REPLACE(prompt_template, '{job_posting_text}', '{param_1}')
WHERE session_id IN (
    SELECT session_id FROM sessions 
    WHERE session_name IN ('sb_soft_skills_olmo', 'sb_technical_skills_phi3', 'sb_taxonomy_llama')
);

-- Verify
SELECT s.session_name, i.step_number, 
       CASE 
           WHEN i.prompt_template LIKE '%{param_1}%' THEN '✅ Uses param_1'
           WHEN i.prompt_template LIKE '%{job_posting_text}%' THEN '❌ Still uses job_posting_text'
           ELSE '⚠️  No placeholder found'
       END as status
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name IN ('sb_soft_skills_olmo', 'sb_technical_skills_phi3', 'sb_taxonomy_llama');

SQL
