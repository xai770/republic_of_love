-- ============================================================================
-- DYNATAX JOB MATCHING ANALYSIS - SQL Queries
-- ============================================================================
-- Run these queries to explore how DynaTax derived your skills and matched jobs
-- ============================================================================

-- 1. VIEW ALL DERIVED SKILLS FROM YOUR CAREER
-- ============================================================================
-- Session 1 extracted skills from your 25+ year profile
SELECT 
    '=== YOUR DERIVED SKILLS ===' as section,
    session_output as skills_json
FROM session_runs
WHERE recipe_run_id = 1444  -- First match
AND session_number = 1;

-- 2. VIEW THE TWO SUCCESSFUL MATCHES
-- ============================================================================
SELECT 
    '=== MATCH #' || (rr.recipe_run_id - 1443) || ' ===' as match_number,
    SUBSTR(v.variations_param_2, 1, 100) as job_title,
    sr.session_number,
    CASE sr.session_number
        WHEN 1 THEN 'Skills Derived'
        WHEN 2 THEN 'Job Match Analysis'
    END as session_type,
    SUBSTR(sr.session_output, 1, 800) as output_preview
FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
WHERE rr.batch_id = 'gershon_matching_1761219568'
AND rr.recipe_run_id IN (1444, 1445)  -- The two that worked
ORDER BY rr.recipe_run_id, sr.session_number;

-- 3. EXTRACT JUST THE MATCH SCORES
-- ============================================================================
SELECT 
    rr.recipe_run_id,
    SUBSTR(v.variations_param_2, 1, 80) as job_title,
    -- Extract score with regex-like substring search
    CASE 
        WHEN sr.session_output LIKE '%"match_score"%' 
        THEN CAST(
            SUBSTR(
                sr.session_output,
                INSTR(sr.session_output, '"match_score":') + 15,
                3
            ) AS INTEGER
        )
        ELSE 0
    END as match_score
FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
LEFT JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id AND sr.session_number = 2
WHERE rr.batch_id = 'gershon_matching_1761219568'
ORDER BY match_score DESC;

-- 4. COUNT SKILLS DERIVED PER MATCH
-- ============================================================================
SELECT 
    rr.recipe_run_id,
    LENGTH(sr.session_output) - LENGTH(REPLACE(sr.session_output, '"skill":', '')) 
        / LENGTH('"skill":') as skills_extracted
FROM recipe_runs rr
JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id
WHERE rr.batch_id = 'gershon_matching_1761219568'
AND sr.session_number = 1;

-- 5. HALLUCINATION DETECTION - Find where Session 2 went wrong
-- ============================================================================
SELECT 
    rr.recipe_run_id,
    CASE 
        WHEN sr.session_output LIKE '%{%match_score%}%' THEN 'Valid JSON'
        WHEN sr.session_output LIKE '%Deutsche Post%' THEN 'Hallucination Detected'
        WHEN sr.session_output IS NULL THEN 'No Output'
        ELSE 'Unknown Format'
    END as output_status,
    LENGTH(sr.session_output) as output_length,
    SUBSTR(sr.session_output, 1, 150) as preview
FROM recipe_runs rr
LEFT JOIN session_runs sr ON rr.recipe_run_id = sr.recipe_run_id AND sr.session_number = 2
WHERE rr.batch_id = 'gershon_matching_1761219568'
ORDER BY rr.recipe_run_id;

-- 6. DEEP DIVE: First Successful Match (Full Output)
-- ============================================================================
SELECT 
    '=== MATCH #1 COMPLETE OUTPUT ===' as section,
    sr.session_number,
    sr.session_output
FROM session_runs sr
WHERE sr.recipe_run_id = 1444
ORDER BY sr.session_number;

