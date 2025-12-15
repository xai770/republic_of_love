-- Migration 049: Clarify validation [PASS]/[FAIL] logic for WARNING status
-- Issue: gemma2 outputs [WARNING] but branching only recognizes [PASS] or [FAIL]
-- Solution: Update prompt to output [PASS] for WARNING status (can still import)
-- Date: 2025-11-04

BEGIN;

UPDATE instructions
SET prompt_template = REPLACE(
    prompt_template,
    E'After your validation report, output:\n- [PASS] if all required fields are present and valid\n- [FAIL] if any critical errors found',
    E'After your validation report, output:\n- [PASS] if all required fields are present (WARNING status is acceptable for import)\n- [FAIL] if any critical errors found (validation_status = FAIL)'
)
WHERE instruction_id = 3363;

-- Verify update
SELECT 
    instruction_id,
    instruction_name,
    CASE 
        WHEN prompt_template LIKE '%WARNING status is acceptable%' THEN '✅ Updated'
        ELSE '❌ Not updated'
    END as status
FROM instructions
WHERE instruction_id = 3363;

COMMIT;
