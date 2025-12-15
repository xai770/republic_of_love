-- Gradient Testing Results Analysis
-- Created: September 26, 2025
-- Purpose: Comprehensive analysis of model performance across canonicals and difficulty levels

-- Create the view (if it doesn't exist)
DROP VIEW IF EXISTS test_results_summary;
CREATE VIEW test_results_summary AS
SELECT
	models.model_name,
	canonicals.canonical_code,
	test_runs.test_run_pass,
	CASE WHEN test_runs.test_run_pass = 0 THEN 1 ELSE 0 END AS test_run_fail,
	test_parameters.difficulty_level,
	COUNT( * ) AS count
FROM
	facets
	INNER JOIN canonicals
	 ON facets.facet_id = canonicals.facet_id
	INNER JOIN tests
	 ON canonicals.canonical_code = tests.canonical_code
	INNER JOIN test_parameters
	 ON tests.test_id = test_parameters.test_id
	INNER JOIN models
	 ON tests.processing_model_name = models.model_name
	INNER JOIN test_runs
	 ON test_parameters.param_id = test_runs.param_id
GROUP BY
	models.model_name,
	canonicals.canonical_code,
	test_runs.test_run_pass,
	test_parameters.difficulty_level
ORDER BY
	models.model_name,
	canonicals.canonical_code,
	test_parameters.difficulty_level,
	test_runs.test_run_pass;

-- Usage examples:

-- Get all results
-- SELECT * FROM test_results_summary;

-- Success rate by model
-- SELECT 
--     model_name,
--     SUM(CASE WHEN test_run_pass = 1 THEN count ELSE 0 END) as successes,
--     SUM(count) as total_tests,
--     ROUND(100.0 * SUM(CASE WHEN test_run_pass = 1 THEN count ELSE 0 END) / SUM(count), 2) as success_rate_percent
-- FROM test_results_summary 
-- GROUP BY model_name 
-- ORDER BY success_rate_percent DESC;

-- Performance by canonical
-- SELECT 
--     canonical_code,
--     SUM(CASE WHEN test_run_pass = 1 THEN count ELSE 0 END) as successes,
--     SUM(count) as total_tests,
--     ROUND(100.0 * SUM(CASE WHEN test_run_pass = 1 THEN count ELSE 0 END) / SUM(count), 2) as success_rate_percent
-- FROM test_results_summary 
-- GROUP BY canonical_code 
-- ORDER BY success_rate_percent DESC;