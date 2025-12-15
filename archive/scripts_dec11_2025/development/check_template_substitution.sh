#!/bin/bash
# Check if templates still have unsubstituted placeholders

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'
\pset border 2

-- Check instruction_run 8 specifically
\echo '🔍 INSTRUCTION RUN 8 (Your Example):'
SELECT 
    ir.instruction_run_id,
    sr.recipe_run_id,
    i.instruction_id,
    CASE 
        WHEN ir.prompt_rendered LIKE '%{variations_%' THEN '❌ HAS UNSUBSTITUTED PLACEHOLDER'
        ELSE '✅ Clean'
    END as status,
    LEFT(ir.prompt_rendered, 300) as prompt_preview
FROM instruction_runs ir
JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
JOIN instructions i ON ir.instruction_id = i.instruction_id
WHERE ir.instruction_run_id = 8;

-- Check current Recipe 1120 instruction templates
\echo ''
\echo '📋 CURRENT RECIPE 1120 TEMPLATES:'
SELECT 
    s.session_name,
    i.step_number,
    CASE 
        WHEN i.prompt_template LIKE '%{variations_%' THEN '✅ Uses variations_param_1'
        WHEN i.prompt_template LIKE '%{param_1}%' THEN '⚠️  Uses param_1 (wrong)'
        WHEN i.prompt_template LIKE '%{job_posting_text}%' THEN '❌ Uses job_posting_text (wrong)'
        ELSE '⚠️  No placeholder?'
    END as template_status,
    CASE 
        WHEN i.prompt_template LIKE '%{session_%_output}%' THEN '✅ Uses session outputs'
        ELSE '⚠️  No session outputs'
    END as chaining_status
FROM sessions s
JOIN instructions i ON s.session_id = i.session_id
WHERE s.session_name IN ('sb_soft_skills_olmo', 'sb_technical_skills_phi3', 'sb_taxonomy_llama')
ORDER BY s.session_name, i.step_number;

SQL
