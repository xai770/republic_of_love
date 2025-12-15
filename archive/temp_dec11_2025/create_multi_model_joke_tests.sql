-- ============================================================================
-- Multi-Model Joke Classification Test Setup
-- ============================================================================
-- Create recipes for all enabled AI models and generate recipe_runs
-- for 5 joke variations × 5 batches each = 25 recipe_runs per model
-- ============================================================================

-- Step 1: Create a recipe for each enabled AI model (except humans/scripts)
-- Note: In V3.1, recipes don't have actor_id - that's on the session level
-- We'll create recipes first, then link actors via sessions

-- Get list of actors that don't have recipes yet
-- First, let's just create recipes (one per model we want to test)
-- We'll use a temp table to track which actors need recipes

-- Step 2: For each AI model that doesn't have a recipe yet, create:
-- 2a. A new recipe
-- 2b. A session with that actor_id
-- 2c. An instruction in that session

-- We can't do this in pure SQL easily, so let's do it step by step

-- Create recipes (one per new model)
-- We'll create 25 new recipes (26 models - 1 that already exists)
-- Since we can't easily reference actor_id in recipes table, we'll create them generically

-- Actually, let me do this differently - let's create a cleaner approach
-- We'll manually create recipes for specific models we want to test

-- Step 4: Create instruction for each new session
INSERT INTO instructions (session_id, step_number, step_description, prompt_template, timeout_seconds, enabled, is_terminal)
SELECT 
    s.session_id,
    1 as step_number,
    'Classify if text is a joke and rate quality' as step_description,
    'Read the following text and determine if it is a joke:

{variations_param_1}

Answer these two questions:
1. Is this actually a joke? Answer ONLY: YES or NO
2. If yes, rate its quality: BAD, MEDIOCRE, GOOD, or EXCELLENT

Format your answer exactly like this:
IS_JOKE: [YES or NO]
QUALITY: [BAD, MEDIOCRE, GOOD, or EXCELLENT]' as prompt_template,
    30 as timeout_seconds,
    1 as enabled,
    1 as is_terminal
FROM sessions s
JOIN recipes r ON s.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND s.session_id NOT IN (
    SELECT session_id FROM instructions
  );

-- Step 5: Create recipe_runs for each model × variation × batch combination
-- This will create 5 jokes × 5 batches = 25 recipe_runs per model
INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
SELECT 
    r.recipe_id,
    v.variation_id,
    b.batch_num as batch_id,
    'PENDING' as status
FROM recipes r
CROSS JOIN variations v
CROSS JOIN (
    SELECT 1 as batch_num UNION ALL
    SELECT 2 UNION ALL
    SELECT 3 UNION ALL
    SELECT 4 UNION ALL
    SELECT 5
) b
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND v.recipe_id = (SELECT MIN(recipe_id) FROM recipes WHERE canonical_code = 'ld_classify_joke_quality')
  AND NOT EXISTS (
    SELECT 1 FROM recipe_runs rr2
    WHERE rr2.recipe_id = r.recipe_id
      AND rr2.variation_id = v.variation_id
      AND rr2.batch_id = b.batch_num
  );

-- Verification queries
SELECT '=== SUMMARY ===' as info;
SELECT COUNT(DISTINCT recipe_id) || ' recipes created for canonical ld_classify_joke_quality' as info
FROM recipes 
WHERE canonical_code = 'ld_classify_joke_quality';

SELECT COUNT(*) || ' total recipe_runs created (should be ~650 for 26 models × 5 jokes × 5 batches)' as info
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality';

SELECT COUNT(*) || ' PENDING recipe_runs ready for execution' as info
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
  AND rr.status = 'PENDING';

-- Show breakdown by model
SELECT '=== RECIPE_RUNS BY MODEL ===' as info;
SELECT 
    r.actor_id,
    COUNT(*) as recipe_run_count,
    SUM(CASE WHEN rr.status = 'PENDING' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN rr.status = 'SUCCESS' THEN 1 ELSE 0 END) as success
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
WHERE r.canonical_code = 'ld_classify_joke_quality'
GROUP BY r.actor_id
ORDER BY r.actor_id;
