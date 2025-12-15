-- Add documentation field to recipes table
-- This field stores comprehensive documentation in Markdown format
-- Purpose: Link recipes to their full documentation (architecture, usage, troubleshooting)

-- Add the column
ALTER TABLE recipes 
ADD COLUMN documentation TEXT;

-- Add comment for clarity
COMMENT ON COLUMN recipes.documentation IS 'Comprehensive recipe documentation in Markdown format. Includes architecture, sessions, performance metrics, troubleshooting, and usage examples.';

-- Create index for full-text search (optional but useful)
CREATE INDEX idx_recipes_documentation_fts ON recipes USING gin(to_tsvector('english', COALESCE(documentation, '')));

-- Example: Update Recipe 1114 with its documentation
UPDATE recipes 
SET documentation = 'See docs/RECIPE_1114_COMPLETE.md for full documentation.

## Quick Summary
- **Purpose:** Extract job summaries and skills with dual grading quality control
- **Sessions:** 9 (summary extraction + dual grading + skill extraction + taxonomy mapping)
- **Performance:** ~2.5 min/job, 100% success rate
- **Bilingual:** German → English translation for skill taxonomy matching
- **Self-Healing:** Dual graders with automatic improvement loop

## Usage
```bash
# Process single job
python3 scripts/by_recipe_runner.py --recipe-id 1114 --job-id YOUR_JOB_ID

# Daily automation
python3 scripts/daily_recipe_1114.py
```

## Database Fields Updated
- `postings.extracted_summary` - Formatted job summary
- `postings.skill_keywords` - JSON array of taxonomy-matched skills

**Full Documentation:** docs/RECIPE_1114_COMPLETE.md'
WHERE recipe_id = 1114;

-- Verify
SELECT recipe_id, recipe_name, 
       LENGTH(documentation) as doc_length,
       LEFT(documentation, 100) as doc_preview
FROM recipes 
WHERE documentation IS NOT NULL;
