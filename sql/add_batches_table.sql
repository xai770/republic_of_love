-- Migration: Add batches table for dish repetition control
-- Date: 2025-10-05
-- Purpose: Add simple batches (1-5) to prevent overcooking dishes

-- Step 1: Create backup before migration
-- (Run manually: cp data/llmcore.db data/llmcore_backup_before_batches_$(date +%Y%m%d_%H%M%S).db)

-- Step 2: Create simple batches table with only values 1-5
CREATE TABLE batches (
    batch_id INTEGER PRIMARY KEY CHECK(batch_id BETWEEN 1 AND 5)
);

-- Step 3: Insert the only allowed batch values
INSERT INTO batches (batch_id) VALUES (1), (2), (3), (4), (5);

-- Step 4: Add batch_id column to dishes table
ALTER TABLE dishes ADD COLUMN batch_id INTEGER;

-- Step 5: Populate batch_id for existing dishes based on their current distribution
-- This assigns batch numbers 1-5 to existing dishes per ingredient+model combination
WITH dish_numbering AS (
    SELECT 
        dish_id,
        ROW_NUMBER() OVER (
            PARTITION BY ingredient_id, model_name 
            ORDER BY dish_id
        ) as dish_sequence
    FROM dishes
    WHERE enabled = 1
)
UPDATE dishes 
SET batch_id = (
    SELECT CASE 
        WHEN dish_sequence <= 5 THEN dish_sequence
        ELSE ((dish_sequence - 1) % 5) + 1  -- Wrap around for dishes > 5
    END
    FROM dish_numbering 
    WHERE dish_numbering.dish_id = dishes.dish_id
)
WHERE dish_id IN (SELECT dish_id FROM dish_numbering);

-- Step 6: Set default batch_id for any dishes that might not have been updated
UPDATE dishes SET batch_id = 1 WHERE batch_id IS NULL;

-- Step 7: Recreate dishes table with NOT NULL constraint and FK to batches
-- Create new dishes table with proper batch_id constraint
CREATE TABLE dishes_new (
    dish_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL,
    instruction_id INTEGER,
    session_id INTEGER,
    batch_id INTEGER NOT NULL,
    exec_id TEXT,
    processing_payload_dish TEXT,
    prompt_rendered TEXT,
    processing_received_response_dish TEXT,
    processing_latency_dish INTEGER,
    execution_position INTEGER,
    error_details TEXT,
    remarks TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enabled INTEGER DEFAULT 1,
    model_name TEXT,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id) ON DELETE CASCADE,
    FOREIGN KEY (instruction_id) REFERENCES instructions(instruction_id),
    FOREIGN KEY (session_id) REFERENCES cooking_sessions(session_id),
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
    FOREIGN KEY (model_name) REFERENCES models(model_name)
);

-- Step 8: Copy all data from old dishes table
INSERT INTO dishes_new SELECT * FROM dishes;

-- Step 9: Replace old dishes table
DROP TABLE dishes;
ALTER TABLE dishes_new RENAME TO dishes;

-- Step 10: Recreate indexes with batch_id
CREATE UNIQUE INDEX idx_unique_dishes_batch 
ON dishes(ingredient_id, model_name, batch_id) 
WHERE batch_id IS NOT NULL;

CREATE INDEX idx_dishes_ingredient ON dishes(ingredient_id);
CREATE INDEX idx_dishes_timestamp ON dishes(timestamp);
CREATE INDEX idx_dishes_session ON dishes(session_id);
CREATE INDEX idx_dishes_batch ON dishes(batch_id);

-- Migration complete!
-- Summary of changes:
-- 1. Created batches table with only values 1-5
-- 2. Added batch_id NOT NULL FK to dishes
-- 3. Assigned existing dishes to batches 1-5 based on sequence
-- 4. Added constraint to prevent cooking dishes more than 5 times
-- 5. Kept cooking_sessions for testing session management

-- Verification queries:
SELECT 'Batches table created with values:' as status;
SELECT * FROM batches;

SELECT 'Sample dishes with batch_id assigned:' as status;
SELECT dish_id, ingredient_id, model_name, batch_id, session_id 
FROM dishes 
WHERE batch_id IS NOT NULL 
LIMIT 5;