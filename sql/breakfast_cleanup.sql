-- ============================================================================
-- BREAKFAST DATABASE CLEANUP SQL
-- ============================================================================
-- Direct SQL approach for morning database cleanup

-- STEP 1: Drop backup and redundant tables
-- Note: Using IF EXISTS to avoid errors

DROP TABLE IF EXISTS tests_old_redundant;
DROP TABLE IF EXISTS tests_backup_20250925;
DROP TABLE IF EXISTS test_runs_backup_20250925;
DROP TABLE IF EXISTS tests_history_backup;
DROP TABLE IF EXISTS tests_backup_20250925_190419;
DROP TABLE IF EXISTS tests_gradient_backup_20250925_190419;
DROP TABLE IF EXISTS test_results_backup_20250925_190419;
DROP TABLE IF EXISTS tests_backup_20250925_190441;
DROP TABLE IF EXISTS tests_gradient_backup_20250925_190441;
DROP TABLE IF EXISTS test_results_backup_20250925_190441;
DROP TABLE IF EXISTS tests_backup_20250925_190509;
DROP TABLE IF EXISTS tests_gradient_backup_20250925_190509;
DROP TABLE IF EXISTS test_results_backup_20250925_190509;

-- STEP 2: Drop prompt_templates table
DROP TABLE IF EXISTS prompt_templates;

-- STEP 3: Disable all canonicals, then enable only our two targets
UPDATE canonicals SET enabled = 0;

UPDATE canonicals 
SET enabled = 1 
WHERE canonical_code IN ('ce_char_extract', 'ff_reverse_exact');

-- STEP 4: Remove old ff_reverse_exact_14 canonical and all its data

-- First, delete test_results via test_parameters for ff_reverse_exact_14 tests
DELETE FROM test_results 
WHERE param_id IN (
    SELECT tp.param_id 
    FROM test_parameters tp
    JOIN tests t ON tp.test_id = t.test_id
    WHERE t.canonical_code = 'ff_reverse_exact_14'
);

-- Delete test_parameters for ff_reverse_exact_14 tests
DELETE FROM test_parameters 
WHERE test_id IN (
    SELECT test_id FROM tests 
    WHERE canonical_code = 'ff_reverse_exact_14'
);

-- Delete tests for ff_reverse_exact_14
DELETE FROM tests WHERE canonical_code = 'ff_reverse_exact_14';

-- Delete the canonical itself
DELETE FROM canonicals WHERE canonical_code = 'ff_reverse_exact_14';

-- STEP 5: Verification queries
SELECT '=== CLEANUP VERIFICATION ===' as status;

SELECT 'Enabled Canonicals:' as check_type;
SELECT canonical_code, canonical_name, enabled 
FROM canonicals 
WHERE enabled = 1
ORDER BY canonical_code;

SELECT 'Test Summary:' as check_type;
SELECT 
    t.canonical_code,
    COUNT(DISTINCT t.test_id) as tests,
    COUNT(DISTINCT tp.param_id) as parameters
FROM tests t
LEFT JOIN test_parameters tp ON t.test_id = tp.test_id
WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_exact')
GROUP BY t.canonical_code;

SELECT 'Remaining Cleanup Items:' as check_type;
SELECT name as remaining_table
FROM sqlite_master 
WHERE type='table' 
AND (name LIKE '%backup%' OR name LIKE '%redundant%' OR name = 'prompt_templates');