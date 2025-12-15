-- ============================================================================
-- INSTRUCTION BRANCHES: Conditional Flow Control for Turing-Complete Recipes
-- ============================================================================
-- Created: 2025-10-26
-- Purpose: Enable state machine behavior with branching, loops, and conditionals
--
-- This transforms recipes from linear flows into programmable workflows:
-- - Conditional branching based on output patterns
-- - Loop protection with max_iterations
-- - Cross-session jumps
-- - Priority-based evaluation (specific → generic → catch-all)

CREATE TABLE instruction_branches (
    branch_id SERIAL PRIMARY KEY,
    instruction_id INTEGER NOT NULL,
    branch_condition TEXT NOT NULL,
    next_instruction_id INTEGER,
    next_session_id INTEGER,
    max_iterations INTEGER DEFAULT NULL,
    branch_priority INTEGER DEFAULT 5,
    branch_description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_instruction 
        FOREIGN KEY (instruction_id) 
        REFERENCES instructions(instruction_id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_next_instruction 
        FOREIGN KEY (next_instruction_id) 
        REFERENCES instructions(instruction_id) 
        ON DELETE SET NULL,
    
    CONSTRAINT fk_next_session 
        FOREIGN KEY (next_session_id) 
        REFERENCES sessions(session_id) 
        ON DELETE SET NULL,
    
    CONSTRAINT chk_branch_target 
        CHECK (
            (next_instruction_id IS NOT NULL AND next_session_id IS NULL) OR
            (next_instruction_id IS NULL AND next_session_id IS NOT NULL) OR
            (next_instruction_id IS NULL AND next_session_id IS NULL)
        ),
    
    CONSTRAINT chk_positive_iterations 
        CHECK (max_iterations IS NULL OR max_iterations > 0)
);

-- Indexes for performance
CREATE INDEX idx_branches_instruction ON instruction_branches(instruction_id) WHERE enabled = TRUE;
CREATE INDEX idx_branches_priority ON instruction_branches(instruction_id, branch_priority DESC) WHERE enabled = TRUE;

-- Comments
COMMENT ON TABLE instruction_branches IS 
'Conditional branching logic for instructions. Enables Turing-complete workflows with loops, conditionals, and state transitions. Evaluation order: priority DESC → first matching condition wins.';

COMMENT ON COLUMN instruction_branches.instruction_id IS 
'Source instruction. After this instruction executes, evaluate its branches.';

COMMENT ON COLUMN instruction_branches.branch_condition IS 
'Regex pattern to match against instruction output. Use "^\\[PASS\\]" for exact prefix match, ".*error.*" for substring, or "*" for catch-all. Evaluated in priority order.';

COMMENT ON COLUMN instruction_branches.next_instruction_id IS 
'Target instruction to execute if condition matches (same session). NULL with NULL next_session_id = end session.';

COMMENT ON COLUMN instruction_branches.next_session_id IS 
'Target session to jump to if condition matches (cross-session jump). Mutually exclusive with next_instruction_id.';

COMMENT ON COLUMN instruction_branches.max_iterations IS 
'Maximum times this branch can be taken within a single session_run (loop guard). NULL = unlimited. Prevents infinite loops in retry logic.';

COMMENT ON COLUMN instruction_branches.branch_priority IS 
'Evaluation order (DESC). Higher priority = evaluated first. Use: 10=exact match, 5=common patterns (PASS/FAIL), 1=loose patterns, 0=catch-all (*). Default: 5.';

COMMENT ON COLUMN instruction_branches.branch_description IS 
'Human-readable explanation of what this branch does. Example: "If grading passes, skip to format session" or "If failed 3 times, create error ticket".';

-- ============================================================================
-- EXECUTION TRACKING: Record which branches were taken
-- ============================================================================

CREATE TABLE instruction_branch_executions (
    execution_id SERIAL PRIMARY KEY,
    instruction_run_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    condition_matched TEXT NOT NULL,
    iteration_count INTEGER DEFAULT 1,
    executed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_instruction_run 
        FOREIGN KEY (instruction_run_id) 
        REFERENCES instruction_runs(instruction_run_id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_branch 
        FOREIGN KEY (branch_id) 
        REFERENCES instruction_branches(branch_id) 
        ON DELETE CASCADE
);

CREATE INDEX idx_branch_exec_run ON instruction_branch_executions(instruction_run_id);
CREATE INDEX idx_branch_exec_branch ON instruction_branch_executions(branch_id);

COMMENT ON TABLE instruction_branch_executions IS 
'Audit log of branch decisions. Records which branch was taken, what output pattern matched, and iteration count for loop tracking.';

COMMENT ON COLUMN instruction_branch_executions.condition_matched IS 
'The actual output text that matched the branch_condition regex. Useful for debugging pattern matching.';

COMMENT ON COLUMN instruction_branch_executions.iteration_count IS 
'How many times this specific branch has been taken in the current session_run. Used to enforce max_iterations limit.';

-- ============================================================================
-- HELPER VIEW: Branch Flow Visualization
-- ============================================================================

CREATE VIEW v_instruction_flow AS
SELECT 
    i.instruction_id,
    s.session_name,
    i.step_number,
    i.step_description AS instruction_desc,
    ib.branch_id,
    ib.branch_condition,
    ib.branch_priority,
    ib.branch_description,
    ib.max_iterations,
    CASE 
        WHEN ib.next_instruction_id IS NOT NULL THEN 
            'INSTRUCTION: ' || ni.step_description
        WHEN ib.next_session_id IS NOT NULL THEN 
            'SESSION: ' || ns.session_name
        ELSE 
            'END_SESSION'
    END AS branch_target,
    ib.enabled AS branch_enabled
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
LEFT JOIN instruction_branches ib ON i.instruction_id = ib.instruction_id
LEFT JOIN instructions ni ON ib.next_instruction_id = ni.instruction_id
LEFT JOIN sessions ns ON ib.next_session_id = ns.session_id
ORDER BY s.session_name, i.step_number, ib.branch_priority DESC;

COMMENT ON VIEW v_instruction_flow IS 
'Human-readable view of instruction flow with branching logic. Shows what happens after each instruction based on output conditions.';

-- ============================================================================
-- EXAMPLE: Recipe 1114 Self-Healing Dual Grader
-- ============================================================================

-- Session 2 (gemma2 grader) → Always continue to Session 3
-- (No branches needed - linear flow to next grader)

-- Session 3 (qwen2.5 grader) → Branch on combined result
INSERT INTO instruction_branches (
    instruction_id,
    branch_condition,
    next_session_id,
    branch_priority,
    branch_description,
    max_iterations
)
SELECT 
    i.instruction_id,
    '^\\[PASS\\]',  -- If qwen2.5 says PASS (and gemma2 passed earlier)
    (SELECT session_id FROM sessions WHERE session_name = 'Format Standardization'),
    10,  -- High priority (specific pattern)
    'Both graders passed - skip improvement, go directly to format',
    NULL
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name = 'session_c_qwen25_grade'
  AND i.step_number = 1;

INSERT INTO instruction_branches (
    instruction_id,
    branch_condition,
    next_session_id,
    branch_priority,
    branch_description,
    max_iterations
)
SELECT 
    i.instruction_id,
    '^\\[FAIL\\]',  -- If qwen2.5 says FAIL
    (SELECT session_id FROM sessions WHERE session_name = 'session_d_qwen25_improve'),
    10,  -- High priority (specific pattern)
    'Grading failed - go to improvement session',
    NULL
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name = 'session_c_qwen25_grade'
  AND i.step_number = 1;

-- Session 5 (re-grade after improvement) → Branch on success/retry
INSERT INTO instruction_branches (
    instruction_id,
    branch_condition,
    next_session_id,
    branch_priority,
    branch_description,
    max_iterations
)
SELECT 
    i.instruction_id,
    '^\\[PASS\\]',
    (SELECT session_id FROM sessions WHERE session_name = 'Format Standardization'),
    10,
    'Improvement successful - format the improved version',
    NULL
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name = 'session_e_qwen25_regrade'
  AND i.step_number = 1;

INSERT INTO instruction_branches (
    instruction_id,
    branch_condition,
    next_session_id,
    branch_priority,
    branch_description,
    max_iterations
)
SELECT 
    i.instruction_id,
    '^\\[FAIL\\]',
    (SELECT session_id FROM sessions WHERE session_name = 'session_f_create_ticket'),
    10,
    'Still failing after improvement - create error ticket',
    3  -- Max 3 retry attempts
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name = 'session_e_qwen25_regrade'
  AND i.step_number = 1;

-- Catch-all for unexpected outputs
INSERT INTO instruction_branches (
    instruction_id,
    branch_condition,
    next_session_id,
    branch_priority,
    branch_description,
    max_iterations
)
SELECT 
    i.instruction_id,
    '*',  -- Catch-all
    (SELECT session_id FROM sessions WHERE session_name = 'session_f_create_ticket'),
    0,  -- Lowest priority
    'Unexpected output format - create error ticket',
    1
FROM instructions i
JOIN sessions s ON i.session_id = s.session_id
WHERE s.session_name IN ('session_c_qwen25_grade', 'session_e_qwen25_regrade')
  AND i.step_number = 1;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '📊 INSTRUCTION BRANCHES CREATED'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    s.session_name AS source_session,
    ib.branch_condition,
    ib.branch_priority,
    ib.branch_description,
    CASE 
        WHEN ib.next_session_id IS NOT NULL THEN ns.session_name
        ELSE 'END_SESSION'
    END AS target
FROM instruction_branches ib
JOIN instructions i ON ib.instruction_id = i.instruction_id
JOIN sessions s ON i.session_id = s.session_id
LEFT JOIN sessions ns ON ib.next_session_id = ns.session_id
WHERE ib.enabled = TRUE
ORDER BY s.session_name, ib.branch_priority DESC;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '🔥 FUSE LIT! Recipe 1114 now has Turing-complete branching logic.'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
