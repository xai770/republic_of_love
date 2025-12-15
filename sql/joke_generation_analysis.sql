-- ======================================================================
-- JOKE GENERATION ANALYSIS - STANDARDIZED REPORT
-- ======================================================================
-- Purpose: Analyze joke generation and grading performance across models
-- Dataset: og_generate_and_grade_joke canonical (2-session recipe)
-- Generated: 2025-10-21
-- ======================================================================

-- ======================================================================
-- SECTION 1: EXECUTIVE SUMMARY
-- ======================================================================
-- Overall statistics for the joke generation experiment

SELECT 
    '=== EXECUTIVE SUMMARY ===' as section;

SELECT
    COUNT(DISTINCT rr.recipe_run_id) as total_recipe_runs,
    SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_runs,
    SUM(CASE WHEN rr.status = 'FAILED' THEN 1 ELSE 0 END) as failed_runs,
    SUM(CASE WHEN rr.status = 'TIMEOUT' THEN 1 ELSE 0 END) as timeout_runs,
    ROUND(100.0 * SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate_pct,
    COUNT(DISTINCT r.recipe_id) as models_tested,
    COUNT(DISTINCT v.variations_param_1) as topics_tested,
    COUNT(DISTINCT rr.batch_id) as batches_per_topic
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
JOIN variations v ON rr.variation_id = v.variation_id
WHERE r.canonical_code = 'og_generate_and_grade_joke';

-- ======================================================================
-- SECTION 2: MODEL PERFORMANCE OVERVIEW
-- ======================================================================
-- Which models generate the best jokes according to gemma3:1b?

SELECT 
    '' as blank_line,
    '=== MODEL PERFORMANCE OVERVIEW ===' as section;

SELECT
    a.actor_id as model,
    COUNT(DISTINCT rr.recipe_run_id) as total_attempts,
    SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN rr.status = 'FAILED' THEN 1 ELSE 0 END) as failed,
    ROUND(100.0 * SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate_pct,
    ROUND(AVG(ir_gen.latency_ms), 0) as avg_generation_time_ms,
    ROUND(AVG(ir_grade.latency_ms), 0) as avg_grading_time_ms,
    ROUND(AVG(ir_gen.latency_ms + ir_grade.latency_ms), 0) as avg_total_time_ms
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
JOIN actors a ON s.actor_id = a.actor_id
LEFT JOIN session_runs sr_gen ON rr.recipe_run_id = sr_gen.recipe_run_id AND sr_gen.session_number = 1
LEFT JOIN instruction_runs ir_gen ON sr_gen.session_run_id = ir_gen.session_run_id
LEFT JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
LEFT JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
WHERE r.canonical_code = 'og_generate_and_grade_joke'
GROUP BY a.actor_id
ORDER BY success_rate_pct DESC, avg_generation_time_ms ASC;

-- ======================================================================
-- SECTION 3: JOKE QUALITY RATINGS BY MODEL
-- ======================================================================
-- Parse gemma3:1b's quality ratings from the grading responses

SELECT 
    '' as blank_line,
    '=== JOKE QUALITY RATINGS BY MODEL ===' as section;

WITH quality_ratings AS (
    SELECT
        a.actor_id as model,
        rr.recipe_run_id,
        ir_grade.response_received,
        -- Parse IS_JOKE field
        CASE 
            WHEN ir_grade.response_received LIKE '%IS_JOKE: YES%' THEN 'YES'
            WHEN ir_grade.response_received LIKE '%IS_JOKE: NO%' THEN 'NO'
            ELSE 'UNKNOWN'
        END as is_joke,
        -- Parse QUALITY field
        CASE 
            WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
            ELSE 'UNKNOWN'
        END as quality
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
    JOIN actors a ON s.actor_id = a.actor_id
    JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
    JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
        AND rr.status = 'SUCCESS'
)
SELECT
    model,
    COUNT(*) as total_jokes,
    SUM(CASE WHEN is_joke = 'YES' THEN 1 ELSE 0 END) as recognized_as_jokes,
    ROUND(100.0 * SUM(CASE WHEN is_joke = 'YES' THEN 1 ELSE 0 END) / COUNT(*), 1) as joke_recognition_pct,
    SUM(CASE WHEN quality = 'EXCELLENT' THEN 1 ELSE 0 END) as excellent_jokes,
    SUM(CASE WHEN quality = 'GOOD' THEN 1 ELSE 0 END) as good_jokes,
    SUM(CASE WHEN quality = 'MEDIOCRE' THEN 1 ELSE 0 END) as mediocre_jokes,
    SUM(CASE WHEN quality = 'BAD' THEN 1 ELSE 0 END) as bad_jokes,
    -- Calculate quality score (EXCELLENT=4, GOOD=3, MEDIOCRE=2, BAD=1)
    ROUND(AVG(
        CASE quality
            WHEN 'EXCELLENT' THEN 4
            WHEN 'GOOD' THEN 3
            WHEN 'MEDIOCRE' THEN 2
            WHEN 'BAD' THEN 1
            ELSE 0
        END
    ), 2) as avg_quality_score
FROM quality_ratings
GROUP BY model
ORDER BY avg_quality_score DESC, joke_recognition_pct DESC, total_jokes DESC;

-- ======================================================================
-- SECTION 4: TOPIC PERFORMANCE ANALYSIS
-- ======================================================================
-- Which topics produce the best jokes? Are some topics easier than others?

SELECT 
    '' as blank_line,
    '=== TOPIC PERFORMANCE ANALYSIS ===' as section;

WITH quality_ratings AS (
    SELECT
        v.variations_param_1 as topic,
        rr.recipe_run_id,
        CASE 
            WHEN ir_grade.response_received LIKE '%IS_JOKE: YES%' THEN 'YES'
            WHEN ir_grade.response_received LIKE '%IS_JOKE: NO%' THEN 'NO'
            ELSE 'UNKNOWN'
        END as is_joke,
        CASE 
            WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
            WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 3
            WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
            WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 1
            ELSE 0
        END as quality_score,
        ir_gen.latency_ms as generation_time
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN variations v ON rr.variation_id = v.variation_id
    JOIN session_runs sr_gen ON rr.recipe_run_id = sr_gen.recipe_run_id AND sr_gen.session_number = 1
    JOIN instruction_runs ir_gen ON sr_gen.session_run_id = ir_gen.session_run_id
    JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
    JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
        AND rr.status = 'SUCCESS'
)
SELECT
    topic,
    COUNT(*) as total_attempts,
    ROUND(100.0 * SUM(CASE WHEN is_joke = 'YES' THEN 1 ELSE 0 END) / COUNT(*), 1) as joke_recognition_pct,
    ROUND(AVG(quality_score), 2) as avg_quality_score,
    ROUND(AVG(generation_time), 0) as avg_generation_time_ms,
    MIN(quality_score) as worst_score,
    MAX(quality_score) as best_score
FROM quality_ratings
GROUP BY topic
ORDER BY avg_quality_score DESC;

-- ======================================================================
-- SECTION 5: CONSISTENCY ANALYSIS
-- ======================================================================
-- Which models are most consistent across batches and topics?

SELECT 
    '' as blank_line,
    '=== CONSISTENCY ANALYSIS ===' as section;

WITH quality_ratings AS (
    SELECT
        a.actor_id as model,
        v.variations_param_1 as topic,
        rr.batch_id,
        CASE 
            WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
            WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 3
            WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
            WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 1
            ELSE 0
        END as quality_score
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
    JOIN actors a ON s.actor_id = a.actor_id
    JOIN variations v ON rr.variation_id = v.variation_id
    JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
    JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
        AND rr.status = 'SUCCESS'
)
SELECT
    model,
    COUNT(*) as total_jokes,
    ROUND(AVG(quality_score), 2) as avg_quality,
    MIN(quality_score) as min_quality,
    MAX(quality_score) as max_quality,
    -- Calculate standard deviation as a measure of consistency
    ROUND(
        SQRT(AVG(quality_score * quality_score) - AVG(quality_score) * AVG(quality_score)),
        2
    ) as quality_std_dev,
    -- Lower std_dev = more consistent
    CASE 
        WHEN SQRT(AVG(quality_score * quality_score) - AVG(quality_score) * AVG(quality_score)) < 0.5 THEN '⭐⭐⭐ VERY CONSISTENT'
        WHEN SQRT(AVG(quality_score * quality_score) - AVG(quality_score) * AVG(quality_score)) < 1.0 THEN '⭐⭐ CONSISTENT'
        ELSE '⭐ VARIABLE'
    END as consistency_rating
FROM quality_ratings
GROUP BY model
HAVING COUNT(*) >= 5  -- Only models with at least 5 successful attempts
ORDER BY quality_std_dev ASC, avg_quality DESC;

-- ======================================================================
-- SECTION 6: FAILURE ANALYSIS
-- ======================================================================
-- Why did some attempts fail? Which models have reliability issues?

SELECT 
    '' as blank_line,
    '=== FAILURE ANALYSIS ===' as section;

SELECT
    a.actor_id as model,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN sr.status = 'FAILED' THEN 1 ELSE 0 END) as failed,
    SUM(CASE WHEN ir.status = 'TIMEOUT' THEN 1 ELSE 0 END) as timeouts,
    ROUND(100.0 * SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate_pct,
    GROUP_CONCAT(DISTINCT CASE WHEN sr.status = 'FAILED' THEN sr.error_details END, '; ') as error_types
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
JOIN actors a ON s.actor_id = a.actor_id
LEFT JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id AND sr.session_number = 1
LEFT JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE r.canonical_code = 'og_generate_and_grade_joke'
GROUP BY a.actor_id
HAVING failed > 0 OR timeouts > 0
ORDER BY success_rate_pct ASC, timeouts DESC;

-- ======================================================================
-- SECTION 7: SPEED VS QUALITY TRADEOFF
-- ======================================================================
-- Is there a correlation between generation speed and joke quality?

SELECT 
    '' as blank_line,
    '=== SPEED VS QUALITY TRADEOFF ===' as section;

WITH quality_ratings AS (
    SELECT
        a.actor_id as model,
        ir_gen.latency_ms as generation_time,
        CASE 
            WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
            WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 3
            WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
            WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 1
            ELSE 0
        END as quality_score
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
    JOIN actors a ON s.actor_id = a.actor_id
    JOIN session_runs sr_gen ON rr.recipe_run_id = sr_gen.recipe_run_id AND sr_gen.session_number = 1
    JOIN instruction_runs ir_gen ON sr_gen.session_run_id = ir_gen.session_run_id
    JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
    JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
        AND rr.status = 'SUCCESS'
)
SELECT
    model,
    COUNT(*) as total_jokes,
    ROUND(AVG(generation_time), 0) as avg_time_ms,
    ROUND(AVG(quality_score), 2) as avg_quality,
    -- Classify speed
    CASE 
        WHEN AVG(generation_time) < 3000 THEN '🚀 FAST (<3s)'
        WHEN AVG(generation_time) < 10000 THEN '⚡ MEDIUM (3-10s)'
        ELSE '🐌 SLOW (>10s)'
    END as speed_class,
    -- Calculate efficiency score (quality per second * 1000)
    ROUND(AVG(quality_score) * 1000.0 / AVG(generation_time), 2) as efficiency_score
FROM quality_ratings
GROUP BY model
ORDER BY efficiency_score DESC;

-- ======================================================================
-- SECTION 8: GRADER BIAS ANALYSIS
-- ======================================================================
-- Is gemma3:1b being too harsh? What's the distribution of ratings?

SELECT 
    '' as blank_line,
    '=== GRADER BIAS ANALYSIS ===' as section;

WITH quality_ratings AS (
    SELECT
        CASE 
            WHEN ir_grade.response_received LIKE '%IS_JOKE: YES%' THEN 'YES'
            WHEN ir_grade.response_received LIKE '%IS_JOKE: NO%' THEN 'NO'
            ELSE 'UNKNOWN'
        END as is_joke,
        CASE 
            WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
            ELSE 'UNKNOWN'
        END as quality
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
    JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
        AND rr.status = 'SUCCESS'
)
SELECT
    'IS_JOKE Distribution:' as metric,
    SUM(CASE WHEN is_joke = 'YES' THEN 1 ELSE 0 END) as yes_count,
    SUM(CASE WHEN is_joke = 'NO' THEN 1 ELSE 0 END) as no_count,
    ROUND(100.0 * SUM(CASE WHEN is_joke = 'YES' THEN 1 ELSE 0 END) / COUNT(*), 1) as yes_pct
FROM quality_ratings

UNION ALL

SELECT
    'QUALITY Distribution:' as metric,
    SUM(CASE WHEN quality = 'EXCELLENT' THEN 1 ELSE 0 END) as excellent_count,
    SUM(CASE WHEN quality = 'GOOD' THEN 1 ELSE 0 END) as good_count,
    ROUND(100.0 * SUM(CASE WHEN quality IN ('EXCELLENT', 'GOOD') THEN 1 ELSE 0 END) / COUNT(*), 1) as good_plus_pct
FROM quality_ratings

UNION ALL

SELECT
    'Average Score (1-4):' as metric,
    ROUND(AVG(
        CASE quality
            WHEN 'EXCELLENT' THEN 4
            WHEN 'GOOD' THEN 3
            WHEN 'MEDIOCRE' THEN 2
            WHEN 'BAD' THEN 1
            ELSE 0
        END
    ), 2) as avg_score,
    NULL as null_col,
    NULL as null_col2
FROM quality_ratings;

-- ======================================================================
-- SECTION 9: CHAMPION MODELS - THE WINNERS! 🏆
-- ======================================================================
-- Top performers across different categories

SELECT 
    '' as blank_line,
    '=== 🏆 CHAMPION MODELS 🏆 ===' as section;

WITH quality_ratings AS (
    SELECT
        a.actor_id as model,
        ir_gen.latency_ms as generation_time,
        CASE 
            WHEN ir_grade.response_received LIKE '%IS_JOKE: YES%' THEN 1
            ELSE 0
        END as is_joke,
        CASE 
            WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
            WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 3
            WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
            WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 1
            ELSE 0
        END as quality_score
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
    JOIN actors a ON s.actor_id = a.actor_id
    JOIN session_runs sr_gen ON rr.recipe_run_id = sr_gen.recipe_run_id AND sr_gen.session_number = 1
    JOIN instruction_runs ir_gen ON sr_gen.session_run_id = ir_gen.session_run_id
    JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
    JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
        AND rr.status = 'SUCCESS'
),
model_stats AS (
    SELECT
        model,
        COUNT(*) as total_jokes,
        ROUND(AVG(quality_score), 2) as avg_quality,
        ROUND(AVG(generation_time), 0) as avg_time_ms,
        ROUND(100.0 * SUM(is_joke) / COUNT(*), 1) as joke_recognition_pct,
        ROUND(AVG(quality_score) * 1000.0 / AVG(generation_time), 2) as efficiency_score
    FROM quality_ratings
    GROUP BY model
    HAVING COUNT(*) >= 5
)
SELECT * FROM (
    SELECT '🥇 HIGHEST QUALITY' as award, model, avg_quality as score, joke_recognition_pct || '%' as joke_pct, avg_time_ms || 'ms' as speed
    FROM model_stats
    ORDER BY avg_quality DESC
    LIMIT 1
) 
UNION ALL
SELECT * FROM (
    SELECT '🥈 BEST JOKE RECOGNITION', model, avg_quality, joke_recognition_pct || '%', avg_time_ms || 'ms'
    FROM model_stats
    ORDER BY joke_recognition_pct DESC, avg_quality DESC
    LIMIT 1
)
UNION ALL
SELECT * FROM (
    SELECT '🥉 FASTEST GENERATOR', model, avg_quality, joke_recognition_pct || '%', avg_time_ms || 'ms'
    FROM model_stats
    ORDER BY avg_time_ms ASC, avg_quality DESC
    LIMIT 1
)
UNION ALL
SELECT * FROM (
    SELECT '⚡ MOST EFFICIENT', model, avg_quality, joke_recognition_pct || '%', avg_time_ms || 'ms'
    FROM model_stats
    ORDER BY efficiency_score DESC
    LIMIT 1
)
UNION ALL
SELECT * FROM (
    SELECT '🎯 BEST OVERALL (Quality+Speed)', model, avg_quality, joke_recognition_pct || '%', avg_time_ms || 'ms'
    FROM model_stats
    WHERE avg_time_ms < 10000  -- Must be reasonably fast
    ORDER BY avg_quality DESC, avg_time_ms ASC
    LIMIT 1
);

-- ======================================================================
-- SECTION 10: SAMPLE JOKES - BEST AND WORST
-- ======================================================================
-- Let's see some actual jokes to understand what's working

SELECT 
    '' as blank_line,
    '=== SAMPLE JOKES - BEST RATED ===' as section;

WITH quality_ratings AS (
    SELECT
        a.actor_id as model,
        v.variations_param_1 as topic,
        ir_gen.response_received as joke,
        ir_grade.response_received as grade,
        CASE 
            WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
            WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 3
            WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
            WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 1
            ELSE 0
        END as quality_score
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
    JOIN actors a ON s.actor_id = a.actor_id
    JOIN variations v ON rr.variation_id = v.variation_id
    JOIN session_runs sr_gen ON rr.recipe_run_id = sr_gen.recipe_run_id AND sr_gen.session_number = 1
    JOIN instruction_runs ir_gen ON sr_gen.session_run_id = ir_gen.session_run_id
    JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
    JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
        AND rr.status = 'SUCCESS'
)
SELECT
    '🏆 ' || model as comedian,
    topic,
    SUBSTR(joke, 1, 200) || CASE WHEN LENGTH(joke) > 200 THEN '...' ELSE '' END as joke_preview,
    quality_score || '/4' as rating
FROM quality_ratings
WHERE quality_score >= 3  -- GOOD or EXCELLENT
ORDER BY quality_score DESC, LENGTH(joke) ASC
LIMIT 5;

-- ======================================================================
-- END OF ANALYSIS
-- ======================================================================

SELECT 
    '' as blank_line,
    '=== END OF REPORT ===' as section,
    datetime('now') as generated_at;
