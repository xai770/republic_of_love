-- ============================================================================
-- 2-Step Recipe: Generate Joke + Grade It
-- ============================================================================
-- Canonical: og_generate_and_grade_joke
-- Session 1: Generate a joke (actor varies by recipe - the joke tellers)
-- Session 2: Grade the joke (actor: gemma3:1b - our best classifier)
-- ============================================================================

-- Step 1: Create canonical
INSERT INTO canonicals (canonical_code, facet_id, capability_description, timestamp)
VALUES (
    'og_generate_and_grade_joke',
    'og',
    'Generate an original joke and have it graded for quality by our best classifier',
    CURRENT_TIMESTAMP
);

-- Step 2: Create variations (different joke topics to test creativity)
INSERT INTO variations (recipe_id, variations_param_1, variations_param_2, variations_param_3, difficulty_level, timestamp)
SELECT 
    (SELECT MIN(recipe_id) FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke'),
    topic,
    NULL,
    NULL,
    difficulty,
    CURRENT_TIMESTAMP
FROM (
    SELECT 'programming' as topic, 1 as difficulty UNION ALL
    SELECT 'cats and dogs', 2 UNION ALL
    SELECT 'food and cooking', 3 UNION ALL
    SELECT 'science and technology', 4 UNION ALL
    SELECT 'anything you want - be creative!', 5
);

SELECT '✅ Created canonical and variations';

-- Note: We'll create recipes/sessions/instructions via Python script
-- since we need to iterate over all enabled models for joke generation
SELECT 'Next: Run Python script to create recipes for all enabled models';
