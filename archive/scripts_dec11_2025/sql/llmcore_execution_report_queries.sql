-- LLMCore Execution Report SQL Queries
-- Comprehensive analysis of models, canonicals, and test results

-- =================================================================
-- SECTION 1: OVERVIEW STATISTICS
-- =================================================================

-- Basic execution summary
SELECT 
    'EXECUTION OVERVIEW' as report_section,
    COUNT(*) as total_tests_defined,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tests,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tests,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_tests,
    ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate_percent,
    ROUND(AVG(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END), 2) as avg_latency_seconds
FROM tests;

-- Models tested
SELECT 
    'MODELS TESTED' as report_section,
    processing_model_name as model_name,
    COUNT(*) as total_tests,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate,
    ROUND(AVG(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END), 2) as avg_latency_sec,
    ROUND(MIN(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END), 2) as min_latency_sec,
    ROUND(MAX(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END), 2) as max_latency_sec
FROM tests 
GROUP BY processing_model_name
ORDER BY success_rate DESC, avg_latency_sec ASC;

-- Canonicals tested
SELECT 
    'CANONICALS TESTED' as report_section,
    canonical_code,
    capability_description,
    COUNT(*) as total_tests,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate,
    ROUND(AVG(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END), 2) as avg_latency_sec
FROM tests 
GROUP BY canonical_code, capability_description
ORDER BY success_rate DESC, avg_latency_sec ASC;

-- =================================================================
-- SECTION 2: DETAILED TEST RESULTS
-- =================================================================

-- Complete test execution details
SELECT 
    'DETAILED TEST RESULTS' as report_section,
    t.test_id,
    t.canonical_code,
    t.processing_model_name,
    t.capability_description,
    t.status,
    t.processing_latency_canonicaal as latency_seconds,
    t.executed_at,
    SUBSTR(t.processing_instructions, 1, 100) || '...' as instructions_preview,
    SUBSTR(t.processing_payload_canonical, 1, 100) || '...' as payload_preview,
    CASE 
        WHEN LENGTH(t.processing_received_response_canonical) > 0 THEN 'Response received'
        ELSE 'No response'
    END as response_status,
    LENGTH(t.processing_received_response_canonical) as response_length_chars
FROM tests t
ORDER BY t.executed_at DESC, t.test_id;

-- =================================================================
-- SECTION 3: FULL EXECUTION DETAILS (for completed tests)
-- =================================================================

-- Complete execution data for successful tests
SELECT 
    'FULL EXECUTION DATA - COMPLETED TESTS' as report_section,
    '===========================================' as separator,
    'TEST ID: ' || t.test_id as test_identifier,
    'CANONICAL: ' || t.canonical_code as canonical_info,
    'MODEL: ' || t.processing_model_name as model_info,
    'CAPABILITY: ' || t.capability_description as capability_info,
    'LATENCY: ' || t.processing_latency_canonicaal || ' seconds' as performance_info,
    'EXECUTED: ' || t.executed_at as execution_time,
    '' as blank_line_1,
    '--- PROCESSING INSTRUCTIONS ---' as instructions_header,
    t.processing_instructions as full_instructions,
    '' as blank_line_2,
    '--- PAYLOAD ---' as payload_header,
    t.processing_payload_canonical as full_payload,
    '' as blank_line_3,
    '--- RECEIVED RESPONSE ---' as response_header,
    t.processing_received_response_canonical as full_response,
    '' as blank_line_4,
    '--- QA INSTRUCTIONS ---' as qa_instructions_header,
    COALESCE(t.qa_instructions, 'No QA instructions recorded') as qa_instructions_content,
    '' as blank_line_5,
    '--- QA RESPONSE ---' as qa_response_header,
    COALESCE(t.qa_received_response, 'No QA response recorded') as qa_response_content,
    '' as blank_line_6,
    '--- SCORING ---' as scoring_header,
    COALESCE(t.qa_scoring, 'No scoring recorded') as scoring_content,
    '' as blank_line_7,
    '===========================================' as separator_end
FROM tests t
WHERE t.status = 'completed'
ORDER BY t.canonical_code, t.processing_model_name;

-- =================================================================
-- SECTION 4: PERFORMANCE ANALYSIS
-- =================================================================

-- Performance breakdown by model and canonical
SELECT 
    'PERFORMANCE MATRIX' as report_section,
    processing_model_name,
    canonical_code,
    status,
    processing_latency_canonicaal as latency_seconds,
    CASE 
        WHEN processing_latency_canonicaal <= 10 THEN 'Fast'
        WHEN processing_latency_canonicaal <= 20 THEN 'Medium' 
        WHEN processing_latency_canonicaal <= 30 THEN 'Slow'
        ELSE 'Very Slow'
    END as performance_category,
    executed_at
FROM tests
ORDER BY processing_model_name, canonical_code;

-- Model ranking by performance
SELECT 
    'MODEL PERFORMANCE RANKING' as report_section,
    processing_model_name,
    COUNT(*) as total_tests,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tests,
    ROUND(AVG(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END), 2) as avg_latency,
    ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate,
    CASE 
        WHEN COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) >= 95 AND 
             AVG(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END) <= 15 THEN 'EXCELLENT'
        WHEN COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) >= 85 AND 
             AVG(CASE WHEN status = 'completed' THEN processing_latency_canonicaal END) <= 30 THEN 'GOOD'
        WHEN COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) >= 70 THEN 'FAIR'
        ELSE 'POOR'
    END as performance_rating
FROM tests
GROUP BY processing_model_name
ORDER BY success_rate DESC, avg_latency ASC;

-- =================================================================
-- SECTION 5: FAILURE ANALYSIS
-- =================================================================

-- Failed tests analysis
SELECT 
    'FAILURE ANALYSIS' as report_section,
    canonical_code,
    processing_model_name,
    status,
    review_notes,
    executed_at,
    COALESCE(processing_latency_canonicaal, 0) as attempted_latency
FROM tests
WHERE status != 'completed'
ORDER BY canonical_code, processing_model_name;

-- =================================================================
-- SECTION 6: FACET ANALYSIS
-- =================================================================

-- Facet performance analysis
SELECT 
    'FACET PERFORMANCE' as report_section,
    f.facet_id,
    f.facet_name,
    f.facet_description,
    COUNT(t.test_id) as tests_run,
    COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed,
    ROUND(COUNT(CASE WHEN t.status = 'completed' THEN 1 END) * 100.0 / COUNT(t.test_id), 2) as success_rate,
    ROUND(AVG(CASE WHEN t.status = 'completed' THEN t.processing_latency_canonicaal END), 2) as avg_latency
FROM facets f
LEFT JOIN tests t ON f.facet_id = t.facet_id
WHERE t.test_id IS NOT NULL
GROUP BY f.facet_id, f.facet_name, f.facet_description
ORDER BY success_rate DESC, avg_latency ASC;