-- Migration: Add Actors Table and Foreign Key Constraints
-- Date: 2025-10-11
-- Purpose: 
--   1. Create unified actors table for humans, AI models, and scripts
--   2. Add FK constraint from instruction_runs.status to instruction_run_status.status
--   3. Add FK constraint from recipe_runs.batch_id to batches.batch_id

-- =============================================================================
-- 1. Create actors table for unified actor management
-- =============================================================================

CREATE TABLE IF NOT EXISTS actors (
    actor_id TEXT PRIMARY KEY,                    -- Unique identifier (e.g., 'llama3.2:latest', 'xai@email.com', 'validation_script')
    domain TEXT NOT NULL CHECK(domain IN ('human', 'AI', 'script')), -- Actor type
    url TEXT NOT NULL,                            -- Connection/execution method:
                                                  --   - Email for humans
                                                  --   - Ollama URL for local AI models  
                                                  --   - Web URL for cloud AI services
                                                  --   - Bash command/script path for scripts
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)), -- Enable/disable flag
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP -- Creation timestamp
);

-- Index for quick actor lookups by domain
CREATE INDEX IF NOT EXISTS idx_actors_domain ON actors(domain);
CREATE INDEX IF NOT EXISTS idx_actors_enabled ON actors(enabled);

-- =============================================================================
-- 2. Populate actors table with existing model data
-- =============================================================================

-- Insert existing AI models from models table
INSERT OR IGNORE INTO actors (actor_id, domain, url, enabled, timestamp)
SELECT 
    model_name,                                   -- Use model_name as actor_id
    'AI',                                        -- All models are AI domain
    'ollama://localhost:11434/' || model_name,   -- Construct ollama URL
    enabled,                                     -- Preserve enabled status
    CURRENT_TIMESTAMP                            -- Use current timestamp
FROM models
WHERE model_name IS NOT NULL;

-- =============================================================================
-- 3. Add sample human and script actors for reference
-- =============================================================================

-- Example human actors (update URLs with real email addresses)
INSERT OR IGNORE INTO actors VALUES 
    ('xai', 'human', 'xai@example.com', 1, CURRENT_TIMESTAMP),
    ('arden', 'human', 'arden@example.com', 1, CURRENT_TIMESTAMP);

-- Example script actors for automated processes
INSERT OR IGNORE INTO actors VALUES 
    ('validation_script', 'script', '/home/xai/Documents/ty_learn/scripts/validate_response.py', 1, CURRENT_TIMESTAMP),
    ('scoring_script', 'script', 'python /home/xai/Documents/ty_learn/scripts/score_instruction.py', 1, CURRENT_TIMESTAMP);

-- =============================================================================
-- 4. Add FK constraint: instruction_runs.status -> instruction_run_status.status
-- =============================================================================

-- First, let's populate instruction_run_status with current status values if not already present
INSERT OR IGNORE INTO instruction_run_status (status) 
SELECT DISTINCT status 
FROM instruction_runs 
WHERE status IS NOT NULL AND status != '';

-- Add some standard statuses if they don't exist
INSERT OR IGNORE INTO instruction_run_status (status) VALUES 
    ('SUCCESS'),
    ('FAILED'), 
    ('RUNNING'),
    ('PENDING'),
    ('TIMEOUT'),
    ('ERROR');

-- Since SQLite doesn't support adding FK constraints to existing tables,
-- we need to recreate the instruction_runs table
BEGIN TRANSACTION;

-- Create new table with FK constraint
CREATE TABLE instruction_runs_new (
    instruction_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_run_id INTEGER NOT NULL,
    instruction_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    prompt_rendered TEXT,
    response_received TEXT,
    latency_ms INTEGER,
    error_details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'SUCCESS',
    pass_fail INTEGER NOT NULL DEFAULT 0,
    academic_score TEXT,
    value_add NUMERIC,
    rank_in_group INTEGER,
    FOREIGN KEY(recipe_run_id) REFERENCES recipe_runs(recipe_run_id),
    FOREIGN KEY(instruction_id) REFERENCES instructions(instruction_id),
    FOREIGN KEY(status) REFERENCES instruction_run_status(status)
);

-- Copy data from old table
INSERT INTO instruction_runs_new SELECT * FROM instruction_runs;

-- Drop old table and rename new one
DROP TABLE instruction_runs;
ALTER TABLE instruction_runs_new RENAME TO instruction_runs;

-- Recreate indexes
CREATE INDEX idx_instruction_runs_recipe_run ON instruction_runs(recipe_run_id);
CREATE INDEX idx_instruction_runs_instruction ON instruction_runs(instruction_id);
CREATE INDEX idx_instruction_runs_step ON instruction_runs(step_number);
CREATE INDEX idx_instruction_runs_status ON instruction_runs(status);

COMMIT;

-- =============================================================================
-- 5. Add FK constraint: recipe_runs.batch_id -> batches.batch_id
-- =============================================================================

-- Recreate recipe_runs table with batch_id FK constraint
BEGIN TRANSACTION;

-- Create new table with FK constraint
CREATE TABLE recipe_runs_new (
    recipe_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    variation_id INTEGER NOT NULL,
    batch_id INTEGER NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    status TEXT DEFAULT 'RUNNING',
    total_steps INTEGER,
    completed_steps INTEGER DEFAULT 0,
    error_details TEXT,
    UNIQUE(recipe_id, variation_id, batch_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id),
    FOREIGN KEY (variation_id) REFERENCES variations(variation_id),
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
);

-- Copy data from old table (only valid batch_ids 1-5)
INSERT INTO recipe_runs_new 
SELECT * FROM recipe_runs 
WHERE batch_id BETWEEN 1 AND 5;

-- Drop old table and rename new one  
DROP TABLE recipe_runs;
ALTER TABLE recipe_runs_new RENAME TO recipe_runs;

-- Recreate indexes
CREATE INDEX idx_recipe_runs_recipe ON recipe_runs(recipe_id);
CREATE INDEX idx_recipe_runs_variation ON recipe_runs(variation_id);
CREATE INDEX idx_recipe_runs_status ON recipe_runs(status);
CREATE INDEX idx_recipe_runs_batch ON recipe_runs(batch_id);

COMMIT;

-- =============================================================================
-- 6. Verification queries
-- =============================================================================

-- Check actors table population
SELECT 'Actors by domain:', domain, COUNT(*) as count
FROM actors 
GROUP BY domain;

-- Verify FK constraints work
SELECT 'FK Test - instruction_runs.status references:', COUNT(*) as valid_statuses
FROM instruction_runs ir 
JOIN instruction_run_status irs ON ir.status = irs.status;

SELECT 'FK Test - recipe_runs.batch_id references:', COUNT(*) as valid_batches  
FROM recipe_runs rr
JOIN batches b ON rr.batch_id = b.batch_id;

-- Show sample actors
SELECT 'Sample actors:' as info;
SELECT actor_id, domain, url, enabled FROM actors LIMIT 10;