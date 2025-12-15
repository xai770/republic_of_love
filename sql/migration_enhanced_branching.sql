-- Enhanced Instruction Branching Schema
-- Date: 2025-10-12
-- Purpose: Add advanced branching capabilities and actor integration

-- =============================================================================
-- 1. Add actor_id field to instructions table
-- =============================================================================

ALTER TABLE instructions ADD COLUMN actor_id TEXT;
ALTER TABLE instructions ADD COLUMN timeout_seconds INTEGER DEFAULT 300;
ALTER TABLE instructions ADD COLUMN expected_runtime_seconds INTEGER;
ALTER TABLE instructions ADD COLUMN resource_requirements TEXT; -- JSON: {"memory_mb": 512, "cpu_cores": 1}

-- Create FK constraint to actors table (will require table recreation)
-- For now, let's add the index and we'll handle FK in next migration
CREATE INDEX IF NOT EXISTS idx_instructions_actor ON instructions(actor_id);

-- Populate actor_id from existing model_name for backward compatibility
UPDATE instructions 
SET actor_id = model_name 
WHERE model_name IS NOT NULL AND actor_id IS NULL;

-- =============================================================================
-- 2. Enhanced instruction_branches table 
-- =============================================================================

ALTER TABLE instruction_branches ADD COLUMN condition_type TEXT DEFAULT 'pattern_match';
ALTER TABLE instruction_branches ADD COLUMN condition_operator TEXT DEFAULT 'contains';
ALTER TABLE instruction_branches ADD COLUMN condition_value TEXT;
ALTER TABLE instruction_branches ADD COLUMN branch_priority INTEGER DEFAULT 1;
ALTER TABLE instruction_branches ADD COLUMN enabled INTEGER DEFAULT 1;

-- Index for efficient branch evaluation
CREATE INDEX IF NOT EXISTS idx_instruction_branches_instruction ON instruction_branches(instruction_id);
CREATE INDEX IF NOT EXISTS idx_instruction_branches_priority ON instruction_branches(instruction_id, branch_priority);

-- =============================================================================
-- 3. Branch execution tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS instruction_branch_executions (
    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_run_id INTEGER NOT NULL,
    instruction_run_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    condition_result TEXT, -- JSON: evaluation details
    taken BOOLEAN NOT NULL, -- Whether this branch was taken
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_run_id) REFERENCES recipe_runs(recipe_run_id),
    FOREIGN KEY (instruction_run_id) REFERENCES instruction_runs(instruction_run_id),
    FOREIGN KEY (branch_id) REFERENCES instruction_branches(branch_id)
);

CREATE INDEX idx_branch_executions_recipe_run ON instruction_branch_executions(recipe_run_id);
CREATE INDEX idx_branch_executions_branch ON instruction_branch_executions(branch_id);

-- =============================================================================
-- 4. Sample branching scenarios
-- =============================================================================

-- Example 1: Error handling branch
INSERT OR IGNORE INTO instruction_branches (
    instruction_id, 
    branch_condition, 
    next_step_id, 
    branch_action, 
    branch_metadata,
    condition_type,
    condition_operator,
    condition_value,
    branch_priority
) VALUES (
    912,  -- Source instruction (strategy generation)
    'response_contains_error_indicators',
    1527, -- Go to grading/validation step 
    'ERROR_HANDLER',
    '{"pattern": "(error|failed|unable|don''t know)", "case_sensitive": false}',
    'pattern_match',
    'regex_match', 
    '(error|failed|unable|don''t know)',
    1 -- High priority
);

-- Example 2: Length validation branch  
INSERT OR IGNORE INTO instruction_branches (
    instruction_id,
    branch_condition,
    next_step_id,
    branch_action,
    branch_metadata,
    condition_type,
    condition_operator,
    condition_value,
    branch_priority
) VALUES (
    912,  -- Source instruction
    'response_too_short',
    NULL, -- NULL means repeat current instruction with modified prompt
    'REQUEST_MORE_DETAIL',
    '{"min_length": 100, "retry_prompt_suffix": "Please provide more detailed explanation."}',
    'length_check',
    'less_than',
    '100',
    2 -- Medium priority
);

-- Example 3: AI evaluation branch
INSERT OR IGNORE INTO instruction_branches (
    instruction_id,
    branch_condition, 
    next_step_id,
    branch_action,
    branch_metadata,
    condition_type,
    condition_operator,
    condition_value,
    branch_priority
) VALUES (
    912,  -- Source instruction
    'ai_quality_evaluation',
    1527, -- Go to grading step if quality is good
    'QUALITY_APPROVED',
    '{"evaluator_actor": "qwen3:latest", "eval_prompt": "Rate response quality 1-10. Respond with just the number.", "threshold": 7}',
    'ai_evaluation',
    'greater_equal',
    '7',
    3 -- Lower priority
);

-- Example 4: Default continuation branch
INSERT OR IGNORE INTO instruction_branches (
    instruction_id,
    branch_condition,
    next_step_id, 
    branch_action,
    branch_metadata,
    condition_type,
    condition_operator,
    condition_value,
    branch_priority
) VALUES (
    912,  -- Source instruction
    'default_continue',
    1527, -- Default next step (grading)
    'DEFAULT_CONTINUE', 
    '{}',
    'default',
    'always',
    'true',
    999 -- Lowest priority (fallback)
);

-- =============================================================================
-- 5. Verification queries
-- =============================================================================

SELECT 'Instructions with actor_id populated:' as info;
SELECT COUNT(*) as count FROM instructions WHERE actor_id IS NOT NULL;

SELECT 'Sample instruction branches:' as info;
SELECT 
    ib.branch_id,
    ib.instruction_id,
    ib.condition_type,
    ib.condition_operator, 
    ib.condition_value,
    ib.next_step_id,
    ib.branch_priority
FROM instruction_branches ib 
ORDER BY ib.instruction_id, ib.branch_priority
LIMIT 10;