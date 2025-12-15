-- Unified Test Results Monitoring Queries
-- ========================================
-- SQL statements for hourly test suite monitoring and analysis

-- 1. HOURLY SUMMARY VIEW
-- Quick overview of the most recent test session
SELECT 
    session_id,
    COUNT(*) as total_tests,
    SUM(is_correct) as total_correct,
    ROUND(AVG(is_correct) * 100, 1) as overall_accuracy_pct,
    COUNT(DISTINCT model_name) as models_tested,
    COUNT(DISTINCT test_type) as test_types,
    MIN(executed_at) as session_start,
    MAX(executed_at) as session_end,
    ROUND(AVG(latency_seconds), 2) as avg_latency_sec
FROM unified_test_results 
WHERE session_id = (
    SELECT session_id 
    FROM unified_test_results 
    ORDER BY created_at DESC 
    LIMIT 1
)
GROUP BY session_id;

-- 2. MODEL PERFORMANCE RANKINGS (Latest Session)
-- Rank all models by performance in the most recent test
SELECT 
    RANK() OVER (ORDER BY AVG(is_correct) DESC, AVG(latency_seconds) ASC) as rank,
    model_name,
    COUNT(*) as total_tests,
    SUM(is_correct) as correct_tests,
    ROUND(AVG(is_correct) * 100, 1) as accuracy_pct,
    ROUND(AVG(latency_seconds), 2) as avg_latency_sec,
    SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as error_count
FROM unified_test_results 
WHERE session_id = (
    SELECT session_id 
    FROM unified_test_results 
    ORDER BY created_at DESC 
    LIMIT 1
)
GROUP BY model_name
ORDER BY rank;

-- 3. TEST TYPE COMPARISON (Latest Session) 
-- Compare performance across different test types
SELECT 
    test_type,
    COUNT(*) as total_tests,
    SUM(is_correct) as correct_tests,
    ROUND(AVG(is_correct) * 100, 1) as accuracy_pct,
    ROUND(AVG(latency_seconds), 2) as avg_latency_sec,
    MIN(difficulty_level) as min_difficulty,
    MAX(difficulty_level) as max_difficulty
FROM unified_test_results 
WHERE session_id = (
    SELECT session_id 
    FROM unified_test_results 
    ORDER BY created_at DESC 
    LIMIT 1
)
GROUP BY test_type
ORDER BY accuracy_pct DESC;

-- 4. DIFFICULTY GRADIENT ANALYSIS (Latest Session)
-- Shows capability drop-off by difficulty level
SELECT 
    test_type,
    difficulty_level,
    COUNT(*) as total_tests,
    SUM(is_correct) as correct_tests,
    ROUND(AVG(is_correct) * 100, 1) as accuracy_pct,
    ROUND(AVG(latency_seconds), 2) as avg_latency_sec
FROM unified_test_results 
WHERE session_id = (
    SELECT session_id 
    FROM unified_test_results 
    ORDER BY created_at DESC 
    LIMIT 1
)
GROUP BY test_type, difficulty_level
ORDER BY test_type, difficulty_level;

-- 5. PRODUCTION MONITORING DASHBOARD
-- Key metrics for production monitoring
SELECT 
    'LATEST SESSION SUMMARY' as metric_type,
    session_id as value,
    '' as details,
    MAX(executed_at) as timestamp
FROM unified_test_results 
WHERE session_id = (SELECT session_id FROM unified_test_results ORDER BY created_at DESC LIMIT 1)

UNION ALL

SELECT 
    'OVERALL ACCURACY',
    ROUND(AVG(is_correct) * 100, 1) || '%',
    'Latest session',
    MAX(executed_at)
FROM unified_test_results 
WHERE session_id = (SELECT session_id FROM unified_test_results ORDER BY created_at DESC LIMIT 1)

UNION ALL

SELECT 
    'BEST MODEL',
    model_name,
    ROUND(AVG(is_correct) * 100, 1) || '% accuracy',
    MAX(executed_at)
FROM unified_test_results 
WHERE session_id = (SELECT session_id FROM unified_test_results ORDER BY created_at DESC LIMIT 1)
GROUP BY model_name
ORDER BY AVG(is_correct) DESC
LIMIT 1

UNION ALL

SELECT 
    'WORST MODEL',
    model_name,
    ROUND(AVG(is_correct) * 100, 1) || '% accuracy',
    MAX(executed_at)
FROM unified_test_results 
WHERE session_id = (SELECT session_id FROM unified_test_results ORDER BY created_at DESC LIMIT 1)
GROUP BY model_name
ORDER BY AVG(is_correct) ASC
LIMIT 1

UNION ALL

SELECT 
    'TOTAL TESTS EXECUTED',
    COUNT(*),
    'Across ' || COUNT(DISTINCT model_name) || ' models',
    MAX(executed_at)
FROM unified_test_results 
WHERE session_id = (SELECT session_id FROM unified_test_results ORDER BY created_at DESC LIMIT 1);

-- 6. TRENDING ANALYSIS (Last 5 Sessions)
-- Track performance trends over recent sessions
SELECT 
    session_id,
    COUNT(*) as total_tests,
    ROUND(AVG(is_correct) * 100, 1) as accuracy_pct,
    ROUND(AVG(latency_seconds), 2) as avg_latency_sec,
    MIN(executed_at) as session_time,
    -- Performance trend indicators
    LAG(ROUND(AVG(is_correct) * 100, 1)) OVER (ORDER BY MIN(executed_at)) as prev_accuracy,
    ROUND(AVG(is_correct) * 100, 1) - LAG(ROUND(AVG(is_correct) * 100, 1)) OVER (ORDER BY MIN(executed_at)) as accuracy_change
FROM unified_test_results 
WHERE session_id IN (
    SELECT DISTINCT session_id 
    FROM unified_test_results 
    ORDER BY created_at DESC 
    LIMIT 5
)
GROUP BY session_id
ORDER BY MIN(executed_at) DESC;

-- 7. MODEL CAPABILITY MATRIX (Latest Session)
-- Show which models excel at which test types
SELECT 
    model_name,
    MAX(CASE WHEN test_type = 'strawberry' THEN ROUND(AVG(is_correct) * 100, 1) END) as strawberry_accuracy,
    MAX(CASE WHEN test_type = 'reverse' THEN ROUND(AVG(is_correct) * 100, 1) END) as reverse_accuracy,
    -- Calculate capability score (weighted average)
    ROUND(
        (COALESCE(MAX(CASE WHEN test_type = 'strawberry' THEN AVG(is_correct) END), 0) + 
         COALESCE(MAX(CASE WHEN test_type = 'reverse' THEN AVG(is_correct) END), 0)) * 50, 1
    ) as combined_capability_score
FROM unified_test_results 
WHERE session_id = (
    SELECT session_id 
    FROM unified_test_results 
    ORDER BY created_at DESC 
    LIMIT 1
)
GROUP BY model_name
ORDER BY combined_capability_score DESC;

-- 8. HOURLY MONITORING CRON QUERY
-- Single query for automated hourly monitoring alerts
-- Use this in your cron job for quick health checks
WITH latest_session AS (
    SELECT session_id
    FROM unified_test_results 
    ORDER BY created_at DESC 
    LIMIT 1
),
session_stats AS (
    SELECT 
        session_id,
        COUNT(*) as total_tests,
        ROUND(AVG(is_correct) * 100, 1) as accuracy,
        COUNT(DISTINCT model_name) as models,
        SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as errors,
        MAX(executed_at) as completed_at
    FROM unified_test_results r
    JOIN latest_session l ON r.session_id = l.session_id
    GROUP BY r.session_id
)
SELECT 
    session_id as "Session_ID",
    total_tests as "Total_Tests", 
    accuracy || '%' as "Accuracy",
    models as "Models_Tested",
    errors as "Errors",
    completed_at as "Completed_At",
    CASE 
        WHEN accuracy >= 40 AND errors = 0 THEN '✅ HEALTHY'
        WHEN accuracy >= 30 AND errors <= 5 THEN '⚠️ WARNING' 
        ELSE '🚨 ALERT'
    END as "Status"
FROM session_stats;