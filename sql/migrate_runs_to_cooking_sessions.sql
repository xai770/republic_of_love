-- Migration: Rename runs to cooking_sessions and add proper schema
-- Date: 2025-10-05
-- Purpose: Update restaurant schema to use cooking_sessions instead of runs

-- Step 1: Create new cooking_sessions table with proper structure
CREATE TABLE cooking_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    run_count INTEGER DEFAULT 1,
    session_name TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    enabled INTEGER DEFAULT 1,
    session_notes TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE
);

-- Step 2: Migrate data from runs to cooking_sessions
-- Since runs only has run_number, we'll create a default session for each run
-- Using the first available recipe_id for the mapping
INSERT INTO cooking_sessions (session_id, recipe_id, run_count, session_name, session_notes)
SELECT 
    run_number as session_id,
    (SELECT MIN(recipe_id) FROM recipes WHERE enabled = 1) as recipe_id, -- Use first available recipe
    1 as run_count,
    'Legacy Run ' || run_number as session_name,
    'Migrated from old runs table on ' || datetime('now') as session_notes
FROM runs;

-- Step 3: Add session_id column to dishes table
ALTER TABLE dishes ADD COLUMN session_id INTEGER;

-- Step 4: Update dishes to reference cooking_sessions instead of run_number
-- Map run_number to session_id (they should be the same for now)
UPDATE dishes SET session_id = run_number WHERE run_number IS NOT NULL;

-- Step 5: Add foreign key constraint for session_id (SQLite doesn't support adding FK constraints after table creation)
-- We'll need to recreate the dishes table with the proper foreign key

-- Create temporary dishes table with proper foreign keys
CREATE TABLE dishes_new (
    dish_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL,
    instruction_id INTEGER,
    session_id INTEGER,
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
    FOREIGN KEY (model_name) REFERENCES models(model_name)
);

-- Copy data from old dishes table to new one (mapping column names to restaurant schema)
INSERT INTO dishes_new (
    dish_id,
    ingredient_id,
    instruction_id,
    session_id,
    exec_id,
    processing_payload_dish,
    prompt_rendered,
    processing_received_response_dish,
    processing_latency_dish,
    execution_position,
    error_details,
    remarks,
    timestamp,
    enabled,
    model_name
)
SELECT 
    dish_id,
    ingredient_id,
    instruction_id,
    session_id,
    exec_id,
    processing_payload_test_run,  -- rename to processing_payload_dish
    prompt_rendered,
    processing_received_response_test_run,  -- rename to processing_received_response_dish
    processing_latency_test_run,  -- rename to processing_latency_dish
    execution_position,
    error_details,
    remarks,
    timestamp,
    enabled,
    model_name
FROM dishes;

-- Step 6: Replace old dishes table with new one
DROP TABLE dishes;
ALTER TABLE dishes_new RENAME TO dishes;

-- Step 7: Recreate indexes for dishes table with new structure
CREATE UNIQUE INDEX idx_unique_dishes_model 
ON dishes(ingredient_id, model_name, session_id) 
WHERE session_id IS NOT NULL;

CREATE INDEX idx_dishes_ingredient ON dishes(ingredient_id);
CREATE INDEX idx_dishes_timestamp ON dishes(timestamp);
CREATE INDEX idx_dishes_session ON dishes(session_id);

-- Step 8: Drop the old runs table
DROP TABLE runs;

-- Step 9: Create indexes for cooking_sessions
CREATE INDEX idx_cooking_sessions_recipe ON cooking_sessions(recipe_id);
CREATE INDEX idx_cooking_sessions_started ON cooking_sessions(started_at);

-- Migration complete!
-- Summary of changes:
-- 1. runs → cooking_sessions (with proper columns)
-- 2. dishes.run_number → dishes.session_id (with FK constraint)
-- 3. Updated column names to restaurant schema
-- 4. Added proper indexes and foreign key constraints