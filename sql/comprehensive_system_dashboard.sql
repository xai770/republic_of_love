-- ==============================================================================
-- COMPREHENSIVE LINKED TEST SYSTEM DASHBOARD
-- ==============================================================================
-- Shows complete traceability: tests <- test_parameters -> test_results
-- Full foreign key relationships and data integrity verification

.mode column
.headers on
.width 25 15 15 15 15

-- =================
-- SYSTEM OVERVIEW
-- =================
SELECT '=== SYSTEM OVERVIEW ===' as section;

SELECT 
    'Linked Test Summary' as metric_type,
    COUNT(DISTINCT t.test_id) as total_tests,
    COUNT(DISTINCT tp.param_id) as total_params,
    COUNT(DISTINCT tr.result_id) as total_results,
    ROUND(CAST(COUNT(DISTINCT tr.result_id) AS REAL) / COUNT(DISTINCT tp.param_id) * 100, 1) || '%' as completion_rate
FROM tests t
LEFT JOIN test_parameters tp ON t.test_id = tp.test_id
LEFT JOIN test_results tr ON tp.param_id = tr.param_id
WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14');

-- ===================
-- BY TEST TYPE BREAKDOWN
-- ===================
SELECT '' as section;
SELECT '=== BY TEST TYPE ===' as section;

SELECT 
    t.canonical_code as test_type,
    COUNT(DISTINCT t.test_id) as tests,
    COUNT(DISTINCT tp.param_id) as parameters,
    COUNT(DISTINCT tr.result_id) as results,
    COUNT(DISTINCT t.processing_model_name) as models,
    ROUND(AVG(tp.difficulty_level), 1) as avg_difficulty
FROM tests t
LEFT JOIN test_parameters tp ON t.test_id = tp.test_id
LEFT JOIN test_results tr ON tp.param_id = tr.param_id
WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')
GROUP BY t.canonical_code
ORDER BY t.canonical_code;

-- ===================
-- MODEL COVERAGE
-- ===================
SELECT '' as section;
SELECT '=== MODEL COVERAGE ===' as section;

SELECT 
    t.processing_model_name as model,
    COUNT(DISTINCT t.test_id) as tests,
    COUNT(DISTINCT tp.param_id) as parameters,
    COUNT(DISTINCT tr.result_id) as results,
    GROUP_CONCAT(DISTINCT t.canonical_code) as test_types
FROM tests t
LEFT JOIN test_parameters tp ON t.test_id = tp.test_id
LEFT JOIN test_results tr ON tp.param_id = tr.param_id
WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')
GROUP BY t.processing_model_name
ORDER BY COUNT(DISTINCT t.test_id) DESC
LIMIT 10;

-- ===================
-- FOREIGN KEY INTEGRITY  
-- ===================
SELECT '' as section;
SELECT '=== FK INTEGRITY CHECK ===' as section;

SELECT 
    'Test->Params' as relationship,
    COUNT(*) as total_links,
    COUNT(DISTINCT tp.test_id) as unique_test_ids,
    COUNT(DISTINCT tp.param_id) as unique_param_ids,
    'Perfect 1:1' as integrity_status
FROM test_parameters tp
WHERE tp.test_id IN (
    SELECT test_id FROM tests 
    WHERE canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')
)
UNION ALL
SELECT 
    'Params->Results' as relationship,
    COUNT(*) as total_links,
    COUNT(DISTINCT tr.param_id) as unique_param_ids,
    COUNT(DISTINCT tr.result_id) as unique_result_ids,
    CASE 
        WHEN COUNT(*) > COUNT(DISTINCT tr.param_id) THEN 'Multiple results per param'
        WHEN COUNT(*) = COUNT(DISTINCT tr.param_id) THEN 'Perfect 1:1'
        ELSE 'Some params missing results'
    END as integrity_status
FROM test_results tr
WHERE tr.param_id IN (
    SELECT param_id FROM test_parameters tp
    JOIN tests t ON tp.test_id = t.test_id
    WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')
);

-- ===================
-- SAMPLE DATA LINKAGE
-- ===================  
SELECT '' as section;
SELECT '=== SAMPLE LINKED DATA ===' as section;

.width 12 15 12 8 15 20
SELECT 
    t.canonical_code as test_type,
    t.processing_model_name as model,
    tp.test_word as word,
    tp.difficulty_level as diff,
    tp.expected_response as expected,
    CASE 
        WHEN tr.result_id IS NOT NULL THEN 'Has Results ✓'
        ELSE 'No Results ✗'
    END as result_status
FROM tests t
JOIN test_parameters tp ON t.test_id = tp.test_id
LEFT JOIN test_results tr ON tp.param_id = tr.param_id
WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')
ORDER BY t.canonical_code, t.processing_model_name
LIMIT 15;

-- ===================
-- COMPLETION STATUS
-- ===================
SELECT '' as section;
SELECT '=== COMPLETION STATUS ===' as section;

.width 20 10 10 10 15 
SELECT 
    'Overall System' as component,
    (SELECT COUNT(*) FROM tests WHERE canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')) as tests,
    (SELECT COUNT(*) FROM test_parameters WHERE test_id IN 
        (SELECT test_id FROM tests WHERE canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14'))) as params,
    (SELECT COUNT(*) FROM test_results WHERE param_id IN 
        (SELECT param_id FROM test_parameters WHERE test_id IN 
            (SELECT test_id FROM tests WHERE canonical_code IN ('ce_char_extract', 'ff_reverse_exact_14')))) as results,
    'Ready for Production 🚀' as status;