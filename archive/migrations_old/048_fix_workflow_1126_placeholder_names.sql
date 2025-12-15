-- Migration 048: Fix Workflow 1126 placeholder naming
-- Issue: Prompts use {session_r1_output} but prompt_renderer expects {session_1_output}
-- Solution: Update all prompts to use the correct naming convention
-- Date: 2025-11-04

BEGIN;

-- Update extraction prompt (no session outputs needed, only document_text)
-- No changes needed for instruction 3362

-- Update validation prompt: session_r1_output → session_1_output
UPDATE instructions
SET prompt_template = REPLACE(prompt_template, '{session_r1_output}', '{session_1_output}')
WHERE instruction_id = 3363;

-- Update import prompt: session_r1_output → session_1_output, session_r2_output → session_2_output
UPDATE instructions
SET prompt_template = REPLACE(
    REPLACE(prompt_template, '{session_r1_output}', '{session_1_output}'),
    '{session_r2_output}', '{session_2_output}'
)
WHERE instruction_id = 3364;

-- Update error report prompt: session_r1/r2/r3 → session_1/2/3
UPDATE instructions
SET prompt_template = REPLACE(
    REPLACE(
        REPLACE(prompt_template, '{session_r1_output}', '{session_1_output}'),
        '{session_r2_output}', '{session_2_output}'
    ),
    '{session_r3_output}', '{session_3_output}'
)
WHERE instruction_id = 3365;

-- Verify placeholders are fixed
SELECT 
    instruction_id,
    instruction_name,
    CASE 
        WHEN prompt_template LIKE '%{session_r%' THEN '❌ Still has session_rN'
        WHEN prompt_template LIKE '%{session_%' THEN '✅ Has session_N'
        ELSE '⚪ No session placeholders'
    END as placeholder_status
FROM instructions
WHERE conversation_id IN (
    SELECT conversation_id 
    FROM workflow_conversations 
    WHERE workflow_id = 1126
)
ORDER BY instruction_id;

COMMIT;

-- Migration complete!
-- Next: Test with: python3 runners/workflow_1126_runner.py --file "docs/Gershon Pollatschek Projects.md" --dry-run
