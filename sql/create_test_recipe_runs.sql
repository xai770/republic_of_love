-- Create Test Recipe Runs for Multi-Step Execution
-- Date: 2025-10-12
-- Purpose: Create sample recipe_runs for testing the RecipeRunTestRunner

-- =============================================================================
-- Create recipe_runs for testing (recipe_id=241, using first 2 variations, all 5 batches)
-- =============================================================================

-- Get the first 2 variation_ids for recipe 241
INSERT OR IGNORE INTO recipe_runs (recipe_id, variation_id, batch_id, status, total_steps)
SELECT 
    241 as recipe_id,
    v.variation_id,
    b.batch_id,
    'PENDING' as status,
    (SELECT COUNT(*) FROM instructions WHERE recipe_id = 241 AND enabled = 1) as total_steps
FROM variations v
CROSS JOIN batches b  
WHERE v.recipe_id = 241 
  AND v.enabled = 1
  AND v.variation_id IN (
      SELECT variation_id FROM variations 
      WHERE recipe_id = 241 AND enabled = 1 
      ORDER BY variation_id LIMIT 2
  )
ORDER BY v.variation_id, b.batch_id;

-- =============================================================================
-- Verification queries
-- =============================================================================

SELECT 'Created recipe_runs:' as info;
SELECT 
    rr.recipe_run_id,
    rr.recipe_id, 
    rr.variation_id,
    rr.batch_id,
    rr.status,
    rr.total_steps,
    v.variations_param_1 as test_input
FROM recipe_runs rr
JOIN variations v ON rr.variation_id = v.variation_id
ORDER BY rr.recipe_run_id;

SELECT 'Instructions for recipe 241:' as info;
SELECT 
    instruction_id,
    step_number,
    step_description,
    actor_id,
    timeout_seconds
FROM instructions 
WHERE recipe_id = 241 AND enabled = 1
ORDER BY step_number;