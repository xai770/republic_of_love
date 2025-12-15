-- Check Recipe 1120 Progress: SkillBridge Skills Extraction
-- Shows completion status and extracted skills

-- Summary stats
SELECT 
    '📊 Recipe 1120 Progress' as status,
    COUNT(DISTINCT CASE WHEN rr.status = 'SUCCESS' THEN v.test_data->>'job_id' END) as completed,
    COUNT(DISTINCT p.job_id) as total,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN rr.status = 'SUCCESS' THEN v.test_data->>'job_id' END) / COUNT(DISTINCT p.job_id), 1) as pct_complete
FROM postings p
LEFT JOIN variations v ON v.test_data->>'job_id' = p.job_id
LEFT JOIN recipe_runs rr ON rr.variation_id = v.variation_id AND rr.recipe_id = 1120;

-- Recent completions
SELECT 
    '✅ Last 5 Completed' as status,
    v.test_data->>'job_id' as job_id,
    p.job_title,
    rr.completed_at,
    EXTRACT(EPOCH FROM (rr.completed_at - rr.started_at))::int as duration_seconds
FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
JOIN postings p ON p.job_id = v.test_data->>'job_id'
WHERE rr.recipe_id = 1120 
  AND rr.status = 'SUCCESS'
ORDER BY rr.completed_at DESC
LIMIT 5;

-- Pending jobs (not yet processed)
SELECT 
    '⏳ Next 10 Pending' as status,
    p.job_id,
    p.job_title,
    LENGTH(p.job_description) as desc_length
FROM postings p
WHERE NOT EXISTS (
    SELECT 1 FROM recipe_runs rr
    JOIN variations v ON rr.variation_id = v.variation_id
    WHERE rr.recipe_id = 1120
      AND v.test_data->>'job_id' = p.job_id
      AND rr.status = 'SUCCESS'
)
ORDER BY LENGTH(p.job_description)
LIMIT 10;

-- Skills extracted (sample from recent runs)
SELECT 
    '🎯 Sample Extracted Skills' as status,
    v.test_data->>'job_id' as job_id,
    LEFT(ir.response_received, 500) as extracted_skills
FROM instruction_runs ir
JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
JOIN recipe_runs rr ON sr.recipe_run_id = rr.recipe_run_id
JOIN sessions s ON sr.session_id = s.session_id
JOIN variations v ON rr.variation_id = v.variation_id
WHERE rr.recipe_id = 1120
  AND s.session_name = 'sb_technical_skills_phi3'  -- Session 2 (qwen2.5:7b)
  AND rr.status = 'SUCCESS'
  AND ir.response_received LIKE '+++OUTPUT START+++%'
ORDER BY rr.completed_at DESC
LIMIT 3;
