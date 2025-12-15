-- Backfill extracted summaries from Recipe 1114 instruction_runs to postings table
-- Recipe 1114 ran 25 times successfully but never saved to postings.extracted_summary
-- Session 7 (ID 3341) has the formatted summaries

BEGIN;

-- First, let's see what we have
SELECT 
  COUNT(*) as total_summaries,
  COUNT(DISTINCT sr.recipe_run_id) as unique_runs
FROM instruction_runs ir
JOIN session_runs sr USING (session_run_id)
WHERE sr.session_id = 3341  -- Session 7: Format Standardization
  AND ir.status = 'SUCCESS';

-- Now let's see which jobs these correspond to
-- (Need to trace back through recipe_runs -> variations -> test_data)
SELECT 
  v.test_data->>'job_id' as job_id,
  COUNT(*) as run_count,
  MAX(ir.instruction_run_id) as latest_run_id
FROM instruction_runs ir
JOIN session_runs sr USING (session_run_id)
JOIN recipe_runs rr USING (recipe_run_id)
JOIN variations v USING (variation_id)
WHERE sr.session_id = 3341
  AND ir.status = 'SUCCESS'
  AND rr.recipe_id = 1114
GROUP BY v.test_data->>'job_id'
ORDER BY v.test_data->>'job_id';

COMMIT;
