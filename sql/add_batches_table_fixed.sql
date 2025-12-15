-- Migration: Add batches table for dish repetition control (Fixed)
-- Date: 2025-10-05
-- Purpose: Add simple batches (1-5) to prevent overcooking dishes

-- Step 1: Create simple batches table with only values 1-5
CREATE TABLE batches (
    batch_id INTEGER PRIMARY KEY CHECK(batch_id BETWEEN 1 AND 5)
);

-- Step 2: Insert the only allowed batch values
INSERT INTO batches (batch_id) VALUES (1), (2), (3), (4), (5);

-- Step 3: Add batch_id column to dishes table (nullable initially)
ALTER TABLE dishes ADD COLUMN batch_id INTEGER;

-- Step 4: Assign batch_id to existing dishes
-- Use a simpler approach: cycle through 1-5 based on dish_id
UPDATE dishes 
SET batch_id = ((dish_id - 1) % 5) + 1
WHERE batch_id IS NULL;

-- Step 5: Verify all dishes have batch_id
UPDATE dishes SET batch_id = 1 WHERE batch_id IS NULL;

-- Step 6: Add foreign key constraint by recreating table
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

-- Step 7: Copy data ensuring all batch_id values are valid
INSERT INTO dishes_new (
    dish_id, ingredient_id, instruction_id, session_id, batch_id,
    exec_id, processing_payload_dish, prompt_rendered, 
    processing_received_response_dish, processing_latency_dish,
    execution_position, error_details, remarks, timestamp, enabled, model_name
)
SELECT 
    dish_id, ingredient_id, instruction_id, session_id,
    CASE 
        WHEN batch_id BETWEEN 1 AND 5 THEN batch_id 
        ELSE 1 
    END as batch_id,
    exec_id, processing_payload_dish, prompt_rendered,
    processing_received_response_dish, processing_latency_dish,
    execution_position, error_details, remarks, timestamp, enabled, model_name
FROM dishes;

-- Step 8: Replace tables
DROP TABLE dishes;
ALTER TABLE dishes_new RENAME TO dishes;

-- Step 9: Create indexes
CREATE UNIQUE INDEX idx_unique_dishes_batch 
ON dishes(ingredient_id, model_name, batch_id);

CREATE INDEX idx_dishes_ingredient ON dishes(ingredient_id);
CREATE INDEX idx_dishes_timestamp ON dishes(timestamp);
CREATE INDEX idx_dishes_session ON dishes(session_id);
CREATE INDEX idx_dishes_batch ON dishes(batch_id);

-- Verification
SELECT 'Batches created:' as status;
SELECT batch_id FROM batches ORDER BY batch_id;

SELECT 'Dishes per batch:' as status;
SELECT batch_id, COUNT(*) as dish_count 
FROM dishes 
GROUP BY batch_id 
ORDER BY batch_id;

SELECT 'Sample dishes with batches:' as status;
SELECT dish_id, ingredient_id, model_name, batch_id, session_id 
FROM dishes 
LIMIT 5;