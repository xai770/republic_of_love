-- ============================================================================
-- Joke Classification Multi-Model Analysis
-- ============================================================================
-- Comprehensive analysis of joke classification tests across 25 AI models
-- Tests: 5 joke variations × 5 batches × 25 models = 625 recipe_runs
-- Date: 2025-10-20
-- ============================================================================

-- ============================================================================
-- 1. MODEL PERFORMANCE OVERVIEW
-- ============================================================================
-- Shows completion rate, average latency, and success rate per model

.print "============================================================================"
.print "1. MODEL PERFORMANCE OVERVIEW"
.print "============================================================================"
.mode column
.headers on

SELECT 
    s.actor_id as model,
    COUNT(rr.recipe_run_id) as total_runs,
    SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN rr.status = 'FAILED' THEN 1 ELSE 0 END) as failed,
    ROUND(100.0 * SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(rr.recipe_run_id), 1) as success_rate,
    ROUND(AVG(CASE WHEN ir.latency_ms > 0 THEN ir.latency_ms ELSE NULL END), 0) as avg_latency_ms
FROM recipes r
JOIN sessions s ON r.recipe_id = s.recipe_id
JOIN recipe_runs rr ON r.recipe_id = rr.recipe_id
LEFT JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
LEFT JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
GROUP BY s.actor_id
ORDER BY success_rate DESC, avg_latency_ms ASC;

-- ============================================================================
-- 2. JOKE CLASSIFICATION ACCURACY - Non-Joke Detection
-- ============================================================================
-- Tests which models correctly identified the "cat on the mat" as NOT a joke

.print ""
.print "============================================================================"
.print "2. NON-JOKE DETECTION (Cat on the mat - should be NO)"
.print "============================================================================"

SELECT 
    s.actor_id as model,
    COUNT(DISTINCT rr.recipe_run_id) as total_attempts,
    SUM(CASE WHEN ir.response_received LIKE '%IS_JOKE: NO%' OR ir.response_received LIKE '%IS JOKE: NO%' THEN 1 ELSE 0 END) as correct_no,
    SUM(CASE WHEN ir.response_received LIKE '%IS_JOKE: YES%' OR ir.response_received LIKE '%IS JOKE: YES%' THEN 1 ELSE 0 END) as incorrect_yes,
    ROUND(100.0 * SUM(CASE WHEN ir.response_received LIKE '%IS_JOKE: NO%' OR ir.response_received LIKE '%IS JOKE: NO%' THEN 1 ELSE 0 END) / COUNT(DISTINCT rr.recipe_run_id), 1) as accuracy_pct
FROM recipes r
JOIN sessions s ON r.recipe_id = s.recipe_id
JOIN recipe_runs rr ON r.recipe_id = rr.recipe_id
JOIN variations v ON rr.variation_id = v.variation_id
JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND v.difficulty_level = 3  -- The "cat on the mat" non-joke
  AND rr.status = 'SUCCESS'
GROUP BY s.actor_id
ORDER BY accuracy_pct DESC, model;

-- ============================================================================
-- 3. QUALITY RATING DISTRIBUTION BY JOKE
-- ============================================================================
-- Shows how models rated each joke's quality

.print ""
.print "============================================================================"
.print "3. QUALITY RATING DISTRIBUTION"
.print "============================================================================"

SELECT 
    v.difficulty_level,
    SUBSTR(v.variations_param_1, 1, 50) || '...' as joke,
    SUM(CASE WHEN ir.response_received LIKE '%EXCELLENT%' THEN 1 ELSE 0 END) as excellent,
    SUM(CASE WHEN ir.response_received LIKE '%GOOD%' THEN 1 ELSE 0 END) as good,
    SUM(CASE WHEN ir.response_received LIKE '%MEDIOCRE%' THEN 1 ELSE 0 END) as mediocre,
    SUM(CASE WHEN ir.response_received LIKE '%BAD%' THEN 1 ELSE 0 END) as bad,
    COUNT(*) as total_ratings
FROM variations v
JOIN recipe_runs rr ON v.variation_id = rr.variation_id
JOIN recipes r ON rr.recipe_id = r.recipe_id
JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND rr.status = 'SUCCESS'
  AND (ir.response_received LIKE '%IS_JOKE: YES%' OR ir.response_received LIKE '%IS JOKE: YES%')
GROUP BY v.difficulty_level, v.variations_param_1
ORDER BY v.difficulty_level;

-- ============================================================================
-- 4. FASTEST MODELS (Top 10)
-- ============================================================================
-- Ranks models by average response time

.print ""
.print "============================================================================"
.print "4. FASTEST MODELS (Top 10)"
.print "============================================================================"

SELECT 
    s.actor_id as model,
    COUNT(ir.instruction_run_id) as completed_tests,
    ROUND(AVG(ir.latency_ms), 0) as avg_latency_ms,
    ROUND(MIN(ir.latency_ms), 0) as min_latency_ms,
    ROUND(MAX(ir.latency_ms), 0) as max_latency_ms
FROM recipes r
JOIN sessions s ON r.recipe_id = s.recipe_id
JOIN recipe_runs rr ON r.recipe_id = rr.recipe_id
JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND ir.status = 'SUCCESS'
  AND ir.latency_ms > 0
GROUP BY s.actor_id
ORDER BY avg_latency_ms ASC
LIMIT 10;

-- ============================================================================
-- 5. CONSISTENCY ANALYSIS - Same Response Across Batches
-- ============================================================================
-- Tests if models give consistent answers for the same joke across 5 batches

.print ""
.print "============================================================================"
.print "5. CONSISTENCY ANALYSIS (Same joke, different batches)"
.print "============================================================================"

WITH joke_responses AS (
    SELECT 
        s.actor_id,
        v.difficulty_level,
        rr.batch_id,
        CASE 
            WHEN ir.response_received LIKE '%IS_JOKE: YES%' OR ir.response_received LIKE '%IS JOKE: YES%' THEN 'YES'
            WHEN ir.response_received LIKE '%IS_JOKE: NO%' OR ir.response_received LIKE '%IS JOKE: NO%' THEN 'NO'
            ELSE 'UNKNOWN'
        END as is_joke_response,
        CASE 
            WHEN ir.response_received LIKE '%EXCELLENT%' THEN 'EXCELLENT'
            WHEN ir.response_received LIKE '%GOOD%' THEN 'GOOD'
            WHEN ir.response_received LIKE '%MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN ir.response_received LIKE '%BAD%' THEN 'BAD'
            ELSE 'NONE'
        END as quality_rating
    FROM recipes r
    JOIN sessions s ON r.recipe_id = s.recipe_id
    JOIN recipe_runs rr ON r.recipe_id = rr.recipe_id
    JOIN variations v ON rr.variation_id = v.variation_id
    JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
    JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
    WHERE r.canonical_code = 'ld_classify_joke_quality'
      AND rr.status = 'SUCCESS'
)
SELECT 
    actor_id as model,
    difficulty_level as joke,
    COUNT(DISTINCT is_joke_response) as unique_joke_responses,
    COUNT(DISTINCT quality_rating) as unique_quality_ratings,
    CASE 
        WHEN COUNT(DISTINCT is_joke_response) = 1 AND COUNT(DISTINCT quality_rating) <= 2 THEN 'Highly Consistent'
        WHEN COUNT(DISTINCT is_joke_response) = 1 THEN 'Consistent'
        ELSE 'Inconsistent'
    END as consistency_rating
FROM joke_responses
GROUP BY actor_id, difficulty_level
ORDER BY actor_id, difficulty_level;

-- ============================================================================
-- 6. MODEL COMPARISON - Side by Side on Same Joke
-- ============================================================================
-- Shows how different models classified the knock-knock joke (difficulty 1)

.print ""
.print "============================================================================"
.print "6. MODEL COMPARISON - Knock Knock Joke (Difficulty 1)"
.print "============================================================================"

SELECT 
    s.actor_id as model,
    CASE 
        WHEN ir.response_received LIKE '%IS_JOKE: YES%' OR ir.response_received LIKE '%IS JOKE: YES%' THEN 'YES'
        WHEN ir.response_received LIKE '%IS_JOKE: NO%' OR ir.response_received LIKE '%IS JOKE: NO%' THEN 'NO'
        ELSE 'UNCLEAR'
    END as is_joke,
    CASE 
        WHEN ir.response_received LIKE '%EXCELLENT%' THEN 'EXCELLENT'
        WHEN ir.response_received LIKE '%GOOD%' THEN 'GOOD'
        WHEN ir.response_received LIKE '%MEDIOCRE%' THEN 'MEDIOCRE'
        WHEN ir.response_received LIKE '%BAD%' THEN 'BAD'
        ELSE 'N/A'
    END as quality,
    ROUND(AVG(ir.latency_ms), 0) as avg_latency
FROM recipes r
JOIN sessions s ON r.recipe_id = s.recipe_id
JOIN recipe_runs rr ON r.recipe_id = rr.recipe_id
JOIN variations v ON rr.variation_id = v.variation_id
JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
JOIN instruction_runs ir ON sr.session_run_id = ir.session_run_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND v.difficulty_level = 1  -- Knock knock joke
  AND rr.status = 'SUCCESS'
GROUP BY s.actor_id
ORDER BY s.actor_id;

-- ============================================================================
-- 7. FAILURE ANALYSIS
-- ============================================================================
-- Shows which models and jokes had the most failures

.print ""
.print "============================================================================"
.print "7. FAILURE ANALYSIS"
.print "============================================================================"

SELECT 
    s.actor_id as model,
    v.difficulty_level as joke_difficulty,
    SUBSTR(v.variations_param_1, 1, 40) as joke_snippet,
    COUNT(*) as failure_count,
    GROUP_CONCAT(DISTINCT rr.status) as failure_types
FROM recipes r
JOIN sessions s ON r.recipe_id = s.recipe_id
JOIN recipe_runs rr ON r.recipe_id = rr.recipe_id
JOIN variations v ON rr.variation_id = v.variation_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND rr.status != 'SUCCESS'
GROUP BY s.actor_id, v.difficulty_level
ORDER BY failure_count DESC;

-- ============================================================================
-- 8. OVERALL STATISTICS
-- ============================================================================

.print ""
.print "============================================================================"
.print "8. OVERALL TEST STATISTICS"
.print "============================================================================"

SELECT 
    'Total Recipe Runs' as metric,
    COUNT(*) as value
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'

UNION ALL

SELECT 
    'Successful Tests',
    COUNT(*)
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND rr.status = 'SUCCESS'

UNION ALL

SELECT 
    'Failed Tests',
    COUNT(*)
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND rr.status = 'FAILED'

UNION ALL

SELECT 
    'Models Tested',
    COUNT(DISTINCT s.actor_id)
FROM recipes r
JOIN sessions s ON r.recipe_id = s.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'

UNION ALL

SELECT 
    'Joke Variations',
    COUNT(DISTINCT v.variation_id)
FROM variations v
JOIN recipe_runs rr ON v.variation_id = rr.variation_id
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'

UNION ALL

SELECT 
    'Total Execution Time (seconds)',
    ROUND(SUM(ir.latency_ms) / 1000.0, 0)
FROM instruction_runs ir
JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
JOIN recipe_runs rr ON sr.recipe_run_id = rr.recipe_run_id
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND ir.status = 'SUCCESS';

.print ""
.print "============================================================================"
.print "Analysis Complete!"
.print "============================================================================"
