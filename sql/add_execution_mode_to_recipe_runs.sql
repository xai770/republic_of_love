-- Add execution_mode and target_batch_count to recipe_runs
-- This allows base_yoga to serve both testing and production workflows

-- Add execution_mode: 'testing' (5 batches) vs 'production' (1 batch)
ALTER TABLE recipe_runs 
ADD COLUMN IF NOT EXISTS execution_mode TEXT DEFAULT 'testing' 
CHECK (execution_mode IN ('testing', 'production'));

-- Add target_batch_count: how many times this variation should be run
ALTER TABLE recipe_runs
ADD COLUMN IF NOT EXISTS target_batch_count INTEGER DEFAULT 5
CHECK (target_batch_count > 0);

-- Add batch_number: which batch iteration this is (1-5 for testing, 1 for production)
ALTER TABLE recipe_runs
ADD COLUMN IF NOT EXISTS batch_number INTEGER DEFAULT 1
CHECK (batch_number > 0);

-- Create index for efficient batch tracking queries
CREATE INDEX IF NOT EXISTS idx_recipe_runs_execution_mode 
ON recipe_runs(recipe_id, execution_mode, status);

CREATE INDEX IF NOT EXISTS idx_recipe_runs_batch_tracking
ON recipe_runs(variation_id, batch_number, status);

-- Add comments
COMMENT ON COLUMN recipe_runs.execution_mode IS 
'Execution mode: "testing" (5 batches for validation) or "production" (1 batch for real data)';

COMMENT ON COLUMN recipe_runs.target_batch_count IS 
'How many batch runs should be completed for this variation (5 for testing, 1 for production)';

COMMENT ON COLUMN recipe_runs.batch_number IS 
'Which batch iteration this is (1-N where N = target_batch_count)';

-- Update existing recipe_runs to production mode with batch_number 1
UPDATE recipe_runs 
SET execution_mode = 'production',
    target_batch_count = 1,
    batch_number = 1
WHERE execution_mode IS NULL;

SELECT 
    '✅ Schema updated: recipe_runs now supports testing vs production modes' as status;
