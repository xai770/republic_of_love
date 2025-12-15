-- Check Recipe 1114 processing progress
-- Shows which postings have been processed and which are pending
-- Now supports testing (5 batches) vs production (1 batch) modes

-- Summary statistics
WITH stats AS (
    SELECT 
        COUNT(*) FILTER (WHERE p.enabled = TRUE AND p.job_description IS NOT NULL) as total_postings,
        COUNT(*) FILTER (
            WHERE p.enabled = TRUE 
              AND p.job_description IS NOT NULL
              AND EXISTS (
                  SELECT 1 
                  FROM recipe_runs rr
                  JOIN variations v ON rr.variation_id = v.variation_id
                  WHERE rr.recipe_id = 1114
                    AND rr.status = 'SUCCESS'
                    AND v.test_data->>'job_id' = p.job_id
                    AND rr.execution_mode = 'production'  -- Only count production runs
              )
        ) as completed_postings,
        COUNT(*) FILTER (
            WHERE p.enabled = TRUE 
              AND p.job_description IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 
                  FROM recipe_runs rr
                  JOIN variations v ON rr.variation_id = v.variation_id
                  WHERE rr.recipe_id = 1114
                    AND rr.status = 'SUCCESS'
                    AND v.test_data->>'job_id' = p.job_id
                    AND rr.execution_mode = 'production'  -- Only count production runs
              )
        ) as pending_postings
    FROM postings p
)
SELECT 
    '📊 RECIPE 1114 PROGRESS' as metric,
    '' as value
UNION ALL
SELECT '─────────────────────', '──────────'
UNION ALL
SELECT 
    '✅ Completed',
    completed_postings || '/' || total_postings || ' (' || 
    ROUND((completed_postings::numeric / total_postings * 100), 1) || '%)'
FROM stats
UNION ALL
SELECT 
    '⏳ Pending',
    pending_postings::text
FROM stats
UNION ALL
SELECT '', ''
UNION ALL
SELECT '🎯 Estimated time remaining', 
    ROUND(pending_postings * 2.5, 1) || ' minutes (avg 2.5 min/posting)'
FROM stats;

-- Show pending postings (first 10)
WITH pending AS (
    SELECT 
        p.job_id, p.job_title, LENGTH(p.job_description) as desc_len
    FROM postings p
    WHERE p.enabled = TRUE
      AND p.job_description IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 
          FROM recipe_runs rr
          JOIN variations v ON rr.variation_id = v.variation_id
          WHERE rr.recipe_id = 1114
            AND rr.status = 'SUCCESS'
            AND v.test_data->>'job_id' = p.job_id
            AND rr.execution_mode = 'production'
      )
    ORDER BY LENGTH(p.job_description) ASC
    LIMIT 10
)
SELECT 
    '📋 PENDING POSTINGS (first 10)' as info
UNION ALL
SELECT '─────────────────────────────────────────────────────────────────────'
UNION ALL
SELECT 
    job_id || ': ' || LEFT(job_title, 50) || '... (' || desc_len || ' chars)'
FROM pending;

-- Show recent completions
WITH recent AS (
    SELECT 
        v.test_data->>'job_id' as job_id,
        rr.status,
        rr.recipe_run_id,
        EXTRACT(EPOCH FROM (rr.completed_at - rr.started_at))::int as duration_s,
        rr.execution_mode,
        rr.completed_at
    FROM recipe_runs rr
    JOIN variations v ON rr.variation_id = v.variation_id
    WHERE rr.recipe_id = 1114
      AND rr.status = 'SUCCESS'
    ORDER BY rr.completed_at DESC
    LIMIT 5
)
SELECT '' as separator
UNION ALL
SELECT '✅ RECENTLY COMPLETED (last 5)'
UNION ALL
SELECT '─────────────────────────────────────────────────────────────────────'
UNION ALL
SELECT 
    job_id || ': ' || status || 
    ' (Run #' || recipe_run_id || ', ' || 
    duration_s || 's, ' || execution_mode || ' mode)'
FROM recent;
