-- ============================================================================
-- HUMAN REVIEW: Input vs Output Comparison
-- ============================================================================
-- Purpose: Compare raw job postings with AI-extracted summaries for quality review
-- Recipe: 1114 (self_healing_dual_grader)
-- Generated: 2025-10-23
-- ============================================================================

.mode column
.headers on
.width 10 50 50 15 10

-- ============================================================================
-- Query 1: Side-by-Side Comparison (Latest Batch)
-- ============================================================================

SELECT 
    rr.recipe_run_id as run_id,
    
    -- Raw input (truncated for readability)
    SUBSTR(v.variations_param_1, 1, 300) || '...' as raw_input_snippet,
    
    -- Final validated output (either improved or initial)
    SUBSTR(
        COALESCE(
            (SELECT session_output FROM session_runs 
             WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4),
            (SELECT session_output FROM session_runs 
             WHERE recipe_run_id = rr.recipe_run_id AND session_number = 1)
        ),
        1, 300
    ) || '...' as ai_summary_snippet,
    
    -- Quality path
    CASE 
        WHEN EXISTS (SELECT 1 FROM session_runs 
                     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4)
        THEN 'AUTO-CORRECTED'
        ELSE 'FIRST-ATTEMPT'
    END as quality_path,
    
    -- Processing time
    ROUND((julianday(rr.end_time) - julianday(rr.start_time)) * 1440, 1) as minutes

FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
WHERE rr.recipe_id = 1114
AND rr.status = 'SUCCESS'
ORDER BY rr.recipe_run_id DESC
LIMIT 20;

-- ============================================================================
-- Query 2: Full Detail Export (For External Review)
-- ============================================================================

.mode json
.output human_review_full_$(date +%Y%m%d).json

SELECT 
    rr.recipe_run_id,
    rr.batch_id,
    
    -- Complete raw input
    v.variations_param_1 as raw_job_posting,
    
    -- Initial extraction (Session A)
    (SELECT session_output FROM session_runs 
     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 1) 
     as initial_extraction,
    
    -- First strict grade (Session C)
    (SELECT session_output FROM session_runs 
     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 3) 
     as first_grade_feedback,
    
    -- Improved extraction (Session D) if correction was needed
    (SELECT session_output FROM session_runs 
     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4) 
     as improved_extraction,
    
    -- Final validated output (use improved if exists, else initial)
    COALESCE(
        (SELECT session_output FROM session_runs 
         WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4),
        (SELECT session_output FROM session_runs 
         WHERE recipe_run_id = rr.recipe_run_id AND session_number = 1)
    ) as final_validated_output,
    
    -- Metadata
    CASE 
        WHEN EXISTS (SELECT 1 FROM session_runs 
                     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4)
        THEN 'auto_corrected'
        ELSE 'first_attempt_pass'
    END as quality_path,
    
    rr.start_time,
    rr.end_time,
    ROUND((julianday(rr.end_time) - julianday(rr.start_time)) * 1440, 1) 
        as processing_minutes

FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
WHERE rr.recipe_id = 1114
AND rr.status = 'SUCCESS'
ORDER BY rr.recipe_run_id;

.output stdout
.mode column

-- ============================================================================
-- Query 3: Quality Metrics Summary
-- ============================================================================

SELECT 
    '=== QUALITY METRICS SUMMARY ===' as metric;

SELECT 
    'Total Jobs Processed' as metric,
    COUNT(*) as value
FROM recipe_runs
WHERE recipe_id = 1114 AND status = 'SUCCESS'

UNION ALL

SELECT 
    'First-Attempt Pass Rate' as metric,
    ROUND(100.0 * COUNT(CASE 
        WHEN (SELECT session_output FROM session_runs 
              WHERE recipe_run_id = rr.recipe_run_id AND session_number = 3)
             LIKE '[PASS]%' 
        THEN 1 END) / COUNT(*), 1) || '%' as value
FROM recipe_runs rr
WHERE recipe_id = 1114 AND status = 'SUCCESS'

UNION ALL

SELECT 
    'Auto-Correction Rate' as metric,
    ROUND(100.0 * COUNT(CASE 
        WHEN EXISTS (SELECT 1 FROM session_runs 
                     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4)
        THEN 1 END) / COUNT(*), 1) || '%' as value
FROM recipe_runs rr
WHERE recipe_id = 1114 AND status = 'SUCCESS'

UNION ALL

SELECT 
    'Human Escalation Rate' as metric,
    ROUND(100.0 * COUNT(CASE 
        WHEN EXISTS (SELECT 1 FROM session_runs 
                     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 6)
        THEN 1 END) / COUNT(*), 1) || '%' as value
FROM recipe_runs rr
WHERE recipe_id = 1114 AND status = 'SUCCESS'

UNION ALL

SELECT 
    'Avg Processing Time (minutes)' as metric,
    ROUND(AVG((julianday(end_time) - julianday(start_time)) * 1440), 1) as value
FROM recipe_runs
WHERE recipe_id = 1114 AND status = 'SUCCESS';

-- ============================================================================
-- Query 4: Detailed Comparison (One Job at a Time)
-- ============================================================================

.mode list
.separator '\n'

SELECT '
============================================================================
DETAILED COMPARISON: Recipe Run ' || rr.recipe_run_id || '
============================================================================

BATCH: ' || rr.batch_id || '
QUALITY PATH: ' || 
    CASE 
        WHEN EXISTS (SELECT 1 FROM session_runs 
                     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4)
        THEN 'AUTO-CORRECTED ✅'
        ELSE 'FIRST-ATTEMPT PASS ✅'
    END || '
PROCESSING TIME: ' || ROUND((julianday(rr.end_time) - julianday(rr.start_time)) * 1440, 1) || ' minutes

----------------------------------------------------------------------------
RAW INPUT (Job Posting):
----------------------------------------------------------------------------
' || v.variations_param_1 || '

----------------------------------------------------------------------------
AI EXTRACTED SUMMARY:
----------------------------------------------------------------------------
' || COALESCE(
    (SELECT session_output FROM session_runs 
     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4),
    (SELECT session_output FROM session_runs 
     WHERE recipe_run_id = rr.recipe_run_id AND session_number = 1)
) || '

' || CASE 
    WHEN EXISTS (SELECT 1 FROM session_runs 
                 WHERE recipe_run_id = rr.recipe_run_id AND session_number = 4)
    THEN '----------------------------------------------------------------------------
GRADER FEEDBACK (Why Auto-Correction Was Needed):
----------------------------------------------------------------------------
' || (SELECT session_output FROM session_runs 
      WHERE recipe_run_id = rr.recipe_run_id AND session_number = 3) || '

----------------------------------------------------------------------------
ORIGINAL EXTRACTION (Before Correction):
----------------------------------------------------------------------------
' || (SELECT session_output FROM session_runs 
      WHERE recipe_run_id = rr.recipe_run_id AND session_number = 1) || '

'
    ELSE ''
END || '
============================================================================

'

FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
WHERE rr.recipe_id = 1114
AND rr.status = 'SUCCESS'
ORDER BY rr.recipe_run_id DESC
LIMIT 5;

.mode column

-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================
-- 
-- To run this script:
--   sqlite3 data/llmcore.db < tools/human_review.sql > review_output.txt
--
-- To export just JSON:
--   sqlite3 data/llmcore.db < tools/human_review.sql
--
-- To review specific batch:
--   Add: AND rr.batch_id = '20251022'
--
-- To review specific run:
--   Add: AND rr.recipe_run_id = 1234
--
-- ============================================================================
