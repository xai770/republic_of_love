-- ============================================================================
-- 🎯 DYNATAX EXPLORATION QUERIES
-- ============================================================================
-- Your personal job matching system - skills derived from experience!
-- ============================================================================

-- QUERY 1: Show all derived skills from your career
-- ============================================================================
.mode line
.headers off

SELECT '🎯 SKILLS DYNATAX DERIVED FROM YOUR 25+ YEAR CAREER:' as title;
SELECT '';
SELECT session_output 
FROM session_runs 
WHERE recipe_run_id = 1444 AND session_number = 1;

-- QUERY 2: The two successful matches
-- ============================================================================
.mode column
.headers on
.width 5 70 10

SELECT '' as '';
SELECT '📊 MATCH SCORES (2 successful, 8 hallucinated):' as title;
SELECT '' as '';

SELECT 
    CAST(rr.recipe_run_id - 1443 AS TEXT) as '#',
    SUBSTR(v.variations_param_2, 1, 70) as Job,
    CASE 
        WHEN sr.session_output LIKE '%match_score%' 
        THEN CAST(SUBSTR(SUBSTR(sr.session_output, INSTR(sr.session_output, '"match_score":')), 16, 2) AS TEXT) || '/100'
        ELSE 'N/A'
    END as Score
FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
LEFT JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id AND sr.session_number = 2
WHERE rr.batch_id = 'gershon_matching_1761219568'
ORDER BY rr.recipe_run_id;

-- QUERY 3: What went wrong? (phi3:latest continuous session bug)
-- ============================================================================
SELECT '' as '';
SELECT '🔍 WHAT HAPPENED WITH EACH MATCH:' as title;
SELECT '' as '';

SELECT 
    CAST(rr.recipe_run_id - 1443 AS TEXT) as '#',
    CASE 
        WHEN sr.session_output LIKE '%match_score%' THEN '✅ Success'
        WHEN sr.session_output LIKE '%Deutsche Post%' THEN '❌ Hallucination'
        WHEN sr.session_output IS NULL THEN '⚠️  No Output'
        ELSE '🤷 Corrupted'
    END as Result,
    SUBSTR(sr.session_output, 1, 60) as Preview
FROM recipe_runs rr
LEFT JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id AND sr.session_number = 2
WHERE rr.batch_id = 'gershon_matching_1761219568'
ORDER BY rr.recipe_run_id;

-- QUERY 4: Deep dive into Match #1 (the successful one)
-- ============================================================================
.mode line

SELECT '' as '';
SELECT '=' || HEX('===========================================') as '';
SELECT '🏆 MATCH #1 - COMPLETE ANALYSIS' as title;
SELECT '=' || HEX('===========================================') as '';
SELECT '' as '';

SELECT '📋 JOB TITLE:' as section;
SELECT SUBSTR(variations_param_2, 1, 200) as job
FROM variations 
WHERE variation_id = (SELECT variation_id FROM recipe_runs WHERE recipe_run_id = 1444);

SELECT '' as '';
SELECT '💡 DERIVED SKILLS (Session 1):' as section;
SELECT session_output as skills
FROM session_runs 
WHERE recipe_run_id = 1444 AND session_number = 1;

SELECT '' as '';
SELECT '🎯 MATCH ANALYSIS (Session 2):' as section;
SELECT session_output as analysis
FROM session_runs 
WHERE recipe_run_id = 1444 AND session_number = 2;

