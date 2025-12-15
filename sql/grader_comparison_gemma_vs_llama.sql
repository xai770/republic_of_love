-- =============================================================================
-- GRADER COMPARISON: gemma3:1b vs llama3.2:latest
-- =============================================================================
-- Comparing Session 2 (gemma3:1b) vs Session 3 (llama3.2:latest)
-- Same jokes, different graders - which one is more accurate?
-- =============================================================================

.mode markdown
.headers on

-- =============================================================================
-- SECTION 1: IS_JOKE RECOGNITION COMPARISON
-- =============================================================================

SELECT '=== IS_JOKE RECOGNITION COMPARISON ===' as '';

SELECT 
    'gemma3:1b (Session 2)' as grader,
    SUM(CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 0 END) as joke_yes,
    SUM(CASE WHEN response_received LIKE '%IS_JOKE: NO%' THEN 1 ELSE 0 END) as joke_no,
    ROUND(100.0 * SUM(CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 0 END) / COUNT(*), 1) as yes_percent,
    COUNT(*) as total
FROM instruction_runs ir
JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
WHERE sr.session_number = 2

UNION ALL

SELECT 
    'llama3.2:latest (Session 3)' as grader,
    SUM(CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 0 END) as joke_yes,
    SUM(CASE WHEN response_received LIKE '%IS_JOKE: NO%' THEN 1 ELSE 0 END) as joke_no,
    ROUND(100.0 * SUM(CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 0 END) / COUNT(*), 1) as yes_percent,
    COUNT(*) as total
FROM instruction_runs ir
JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
WHERE sr.session_number = 3;

-- =============================================================================
-- SECTION 2: QUALITY RATING DISTRIBUTION
-- =============================================================================

SELECT '' as '';
SELECT '=== QUALITY RATING DISTRIBUTION ===' as '';

WITH gemma_quality AS (
    SELECT 
        'gemma3:1b' as grader,
        CASE 
            WHEN response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
            ELSE 'UNKNOWN'
        END as quality
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 2
),
llama_quality AS (
    SELECT 
        'llama3.2:latest' as grader,
        CASE 
            WHEN response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
            ELSE 'UNKNOWN'
        END as quality
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 3
)
SELECT 
    grader,
    SUM(CASE WHEN quality = 'EXCELLENT' THEN 1 ELSE 0 END) as excellent,
    SUM(CASE WHEN quality = 'GOOD' THEN 1 ELSE 0 END) as good,
    SUM(CASE WHEN quality = 'MEDIOCRE' THEN 1 ELSE 0 END) as mediocre,
    SUM(CASE WHEN quality = 'BAD' THEN 1 ELSE 0 END) as bad,
    COUNT(*) as total
FROM (
    SELECT * FROM gemma_quality
    UNION ALL
    SELECT * FROM llama_quality
)
GROUP BY grader;

-- =============================================================================
-- SECTION 3: SIDE-BY-SIDE COMPARISON OF SAME JOKES
-- =============================================================================

SELECT '' as '';
SELECT '=== GRADER AGREEMENT ANALYSIS ===' as '';

WITH comparison AS (
    SELECT 
        rr.recipe_run_id,
        s1.actor_id as comedian,
        v.variations_param_1 as topic,
        
        -- Session 2 (gemma3:1b)
        CASE WHEN ir2.response_received LIKE '%IS_JOKE: YES%' THEN 'YES' ELSE 'NO' END as gemma_is_joke,
        CASE 
            WHEN ir2.response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN ir2.response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN ir2.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN ir2.response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
        END as gemma_quality,
        
        -- Session 3 (llama3.2:latest)
        CASE WHEN ir3.response_received LIKE '%IS_JOKE: YES%' THEN 'YES' ELSE 'NO' END as llama_is_joke,
        CASE 
            WHEN ir3.response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN ir3.response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN ir3.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN ir3.response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
        END as llama_quality
        
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN variations v ON rr.variation_id = v.variation_id
    JOIN sessions s1 ON s1.recipe_id = r.recipe_id AND s1.session_number = 1
    JOIN session_runs sr2 ON sr2.recipe_run_id = rr.recipe_run_id AND sr2.session_number = 2
    JOIN session_runs sr3 ON sr3.recipe_run_id = rr.recipe_run_id AND sr3.session_number = 3
    JOIN instruction_runs ir2 ON ir2.session_run_id = sr2.session_run_id
    JOIN instruction_runs ir3 ON ir3.session_run_id = sr3.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
)
SELECT 
    'Agreement on IS_JOKE' as metric,
    SUM(CASE WHEN gemma_is_joke = llama_is_joke THEN 1 ELSE 0 END) as agree,
    SUM(CASE WHEN gemma_is_joke != llama_is_joke THEN 1 ELSE 0 END) as disagree,
    ROUND(100.0 * SUM(CASE WHEN gemma_is_joke = llama_is_joke THEN 1 ELSE 0 END) / COUNT(*), 1) as agree_percent
FROM comparison

UNION ALL

SELECT 
    'Agreement on QUALITY' as metric,
    SUM(CASE WHEN gemma_quality = llama_quality THEN 1 ELSE 0 END) as agree,
    SUM(CASE WHEN gemma_quality != llama_quality THEN 1 ELSE 0 END) as disagree,
    ROUND(100.0 * SUM(CASE WHEN gemma_quality = llama_quality THEN 1 ELSE 0 END) / COUNT(*), 1) as agree_percent
FROM comparison;

-- =============================================================================
-- SECTION 4: MODEL PERFORMANCE WITH DIFFERENT GRADERS
-- =============================================================================

SELECT '' as '';
SELECT '=== TOP 10 COMEDIANS BY LLAMA3.2 RATING ===' as '';
SELECT '(Models that benefit most from the lenient grader)' as '';

WITH comedian_scores AS (
    SELECT 
        s1.actor_id as comedian,
        
        -- gemma3:1b scores
        AVG(CASE 
            WHEN ir2.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
            WHEN ir2.response_received LIKE '%QUALITY: GOOD%' THEN 3
            WHEN ir2.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
            WHEN ir2.response_received LIKE '%QUALITY: BAD%' THEN 1
        END) as gemma_avg_score,
        
        -- llama3.2:latest scores
        AVG(CASE 
            WHEN ir3.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
            WHEN ir3.response_received LIKE '%QUALITY: GOOD%' THEN 3
            WHEN ir3.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
            WHEN ir3.response_received LIKE '%QUALITY: BAD%' THEN 1
        END) as llama_avg_score,
        
        -- llama3.2 joke recognition rate
        ROUND(100.0 * SUM(CASE WHEN ir3.response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 0 END) / COUNT(*), 0) as llama_recognition_pct,
        
        COUNT(*) as total_jokes
        
    FROM recipe_runs rr
    JOIN recipes r ON rr.recipe_id = r.recipe_id
    JOIN sessions s1 ON s1.recipe_id = r.recipe_id AND s1.session_number = 1
    JOIN session_runs sr2 ON sr2.recipe_run_id = rr.recipe_run_id AND sr2.session_number = 2
    JOIN session_runs sr3 ON sr3.recipe_run_id = rr.recipe_run_id AND sr3.session_number = 3
    JOIN instruction_runs ir2 ON ir2.session_run_id = sr2.session_run_id
    JOIN instruction_runs ir3 ON ir3.session_run_id = sr3.session_run_id
    WHERE r.canonical_code = 'og_generate_and_grade_joke'
    GROUP BY s1.actor_id
)
SELECT 
    comedian,
    ROUND(gemma_avg_score, 2) as gemma_score,
    ROUND(llama_avg_score, 2) as llama_score,
    ROUND(llama_avg_score - gemma_avg_score, 2) as score_improvement,
    llama_recognition_pct || '%' as recognition_rate,
    total_jokes
FROM comedian_scores
ORDER BY llama_avg_score DESC
LIMIT 10;

-- =============================================================================
-- SECTION 5: SAMPLE JOKES WITH BOTH RATINGS
-- =============================================================================

SELECT '' as '';
SELECT '=== SAMPLE JOKES: GEMMA vs LLAMA RATINGS ===' as '';
SELECT '(First 10 jokes showing grader differences)' as '';

SELECT 
    rr.recipe_run_id,
    s1.actor_id as comedian,
    v.variations_param_1 as topic,
    SUBSTR(ir1.response_received, 1, 60) || '...' as joke_preview,
    
    CASE WHEN ir2.response_received LIKE '%IS_JOKE: YES%' THEN 'YES' ELSE 'NO' END || ' / ' ||
    CASE 
        WHEN ir2.response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
        WHEN ir2.response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
        WHEN ir2.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
        WHEN ir2.response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
    END as gemma_rating,
    
    CASE WHEN ir3.response_received LIKE '%IS_JOKE: YES%' THEN 'YES' ELSE 'NO' END || ' / ' ||
    CASE 
        WHEN ir3.response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
        WHEN ir3.response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
        WHEN ir3.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
        WHEN ir3.response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
    END as llama_rating
    
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
JOIN variations v ON rr.variation_id = v.variation_id
JOIN sessions s1 ON s1.recipe_id = r.recipe_id AND s1.session_number = 1
JOIN session_runs sr1 ON sr1.recipe_run_id = rr.recipe_run_id AND sr1.session_number = 1
JOIN session_runs sr2 ON sr2.recipe_run_id = rr.recipe_run_id AND sr2.session_number = 2
JOIN session_runs sr3 ON sr3.recipe_run_id = rr.recipe_run_id AND sr3.session_number = 3
JOIN instruction_runs ir1 ON ir1.session_run_id = sr1.session_run_id
JOIN instruction_runs ir2 ON ir2.session_run_id = sr2.session_run_id
JOIN instruction_runs ir3 ON ir3.session_run_id = sr3.session_run_id
WHERE r.canonical_code = 'og_generate_and_grade_joke'
ORDER BY rr.recipe_run_id
LIMIT 10;

-- =============================================================================
-- SECTION 6: KEY INSIGHTS
-- =============================================================================

SELECT '' as '';
SELECT '=== KEY INSIGHTS ===' as '';

SELECT '1. JOKE RECOGNITION:' as insight
UNION ALL SELECT '   - gemma3:1b: 0% recognition (rejected ALL generated jokes)'
UNION ALL SELECT '   - llama3.2:latest: 82.6% recognition (much more realistic)'
UNION ALL SELECT ''
UNION ALL SELECT '2. GRADING PHILOSOPHY:'
UNION ALL SELECT '   - gemma3:1b: Extremely harsh, rated 100% as BAD quality'
UNION ALL SELECT '   - llama3.2:latest: Nuanced ratings across all categories'
UNION ALL SELECT ''
UNION ALL SELECT '3. RECOMMENDATION:'
UNION ALL SELECT '   - Use llama3.2:latest for fair, balanced joke evaluation'
UNION ALL SELECT '   - gemma3:1b appears to have a fundamental bias against AI-generated humor'
UNION ALL SELECT ''
UNION ALL SELECT '4. NEXT STEPS:'
UNION ALL SELECT '   - Update all recipes to use llama3.2:latest as default grader'
UNION ALL SELECT '   - Archive gemma3:1b ratings as "harsh baseline" for comparison';
