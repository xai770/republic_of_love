-- Backfill extracted summaries from Recipe 1114 to postings table
-- Takes the latest successful run for each job and copies to postings.extracted_summary

BEGIN;

-- Update postings with summaries from instruction_runs
UPDATE postings p
SET 
  extracted_summary = ir.response_received,
  summary_extracted_at = ir.created_at,
  summary_extraction_status = 'completed'
FROM (
  -- Get the latest successful summary for each job_id
  SELECT DISTINCT ON (v.test_data->>'job_id')
    v.test_data->>'job_id' as job_id,
    ir.response_received,
    ir.created_at
  FROM instruction_runs ir
  JOIN session_runs sr USING (session_run_id)
  JOIN recipe_runs rr USING (recipe_run_id)
  JOIN variations v USING (variation_id)
  WHERE sr.session_id = 3341  -- Session 7: Format Standardization
    AND ir.status = 'SUCCESS'
    AND rr.recipe_id = 1114
    AND v.test_data->>'job_id' IS NOT NULL
  ORDER BY v.test_data->>'job_id', ir.instruction_run_id DESC
) ir
WHERE p.job_id = ir.job_id;

-- Show what we updated
SELECT 
  COUNT(*) as jobs_updated,
  MIN(LENGTH(extracted_summary)) as min_length,
  MAX(LENGTH(extracted_summary)) as max_length,
  AVG(LENGTH(extracted_summary))::int as avg_length
FROM postings
WHERE extracted_summary IS NOT NULL;

-- Show sample
SELECT 
  job_id,
  LENGTH(extracted_summary) as length,
  LEFT(extracted_summary, 150) as preview
FROM postings
WHERE extracted_summary IS NOT NULL
ORDER BY job_id
LIMIT 5;

COMMIT;
