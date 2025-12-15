-- ============================================================================
-- Create Variations for Recipe 1114 from Real Job Postings
-- ============================================================================
-- This populates the variations table with real job_description data
-- from the postings table, creating test cases for the dual grader recipe.

-- Insert variations from postings table
INSERT INTO variations (
    recipe_id,
    test_data,
    difficulty_level,
    expected_response,
    response_format,
    complexity_score,
    enabled
)
SELECT 
    1114 as recipe_id,
    jsonb_build_object(
        'param_1', job_description,
        'job_id', job_id,
        'job_title', job_title,
        'location', COALESCE(location_city, '') || 
                   CASE WHEN location_state != '' THEN ', ' || location_state ELSE '' END,
        'organization', organization_name
    ) as test_data,
    CASE 
        WHEN LENGTH(job_description) < 500 THEN 1
        WHEN LENGTH(job_description) < 1500 THEN 2
        WHEN LENGTH(job_description) < 3000 THEN 3
        ELSE 4
    END as difficulty_level,
    NULL as expected_response,
    'json' as response_format,
    CASE 
        WHEN LENGTH(job_description) < 500 THEN 0.3
        WHEN LENGTH(job_description) < 1500 THEN 0.5
        WHEN LENGTH(job_description) < 3000 THEN 0.7
        ELSE 0.9
    END as complexity_score,
    TRUE as enabled
FROM postings
WHERE enabled = TRUE
  AND job_description IS NOT NULL
  AND LENGTH(job_description) > 100
ORDER BY job_id
LIMIT 20;  -- Start with 20 variations

-- Verify creation
\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '📊 VARIATIONS CREATED FOR RECIPE 1114'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    COUNT(*) as total_variations,
    COUNT(*) FILTER (WHERE difficulty_level = 1) as difficulty_1,
    COUNT(*) FILTER (WHERE difficulty_level = 2) as difficulty_2,
    COUNT(*) FILTER (WHERE difficulty_level = 3) as difficulty_3,
    COUNT(*) FILTER (WHERE difficulty_level = 4) as difficulty_4,
    ROUND(AVG(complexity_score)::numeric, 2) as avg_complexity
FROM variations
WHERE recipe_id = 1114;

\echo ''
\echo '📋 Sample variations:'
SELECT 
    variation_id,
    difficulty_level,
    test_data->>'job_title' as job_title,
    test_data->>'organization' as organization,
    LENGTH(test_data->>'param_1') as description_length
FROM variations
WHERE recipe_id = 1114
ORDER BY variation_id
LIMIT 5;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '✅ Recipe 1114 variations ready for testing!'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
