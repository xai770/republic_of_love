-- Update Recipe 1114 with Session-Level Branching Logic
-- Self-Healing Dual Grader with conditional execution paths

-- Session 1: Extract (always runs first)
UPDATE recipe_sessions 
SET 
    execute_condition = 'always',
    on_success_action = 'continue',
    on_failure_action = 'stop'
WHERE recipe_session_id = 249;

-- Session 2: Grade with gemma2 (always runs after extract)
UPDATE recipe_sessions 
SET 
    execute_condition = 'always',
    on_success_action = 'continue',
    on_failure_action = 'stop'
WHERE recipe_session_id = 250;

-- Session 3: Grade with qwen2.5 (always runs after gemma2)
-- After this session, we check if BOTH grades passed
UPDATE recipe_sessions 
SET 
    execute_condition = 'always',
    on_success_action = 'skip_to',  -- If BOTH pass, skip to formatting
    on_success_goto_order = 7,       -- Go to Session 7: Format
    on_failure_action = 'continue'   -- If either failed, continue to improve
WHERE recipe_session_id = 251;

-- Session 4: Improve summary based on feedback
-- Only runs if Session 3 detected a failure (either grader)
UPDATE recipe_sessions 
SET 
    execute_condition = 'if_previous_failed',  -- Only if grades failed
    on_success_action = 'continue',            -- Continue to re-grade
    on_failure_action = 'skip_to',             -- If improve fails, create ticket
    on_failure_goto_order = 6
WHERE recipe_session_id = 252;

-- Session 5: Re-grade the improved version
UPDATE recipe_sessions 
SET 
    execute_condition = 'always',
    on_success_action = 'skip_to',      -- If re-grade passes, skip to format
    on_success_goto_order = 7,
    on_failure_action = 'skip_to',      -- If re-grade fails, create ticket
    on_failure_goto_order = 6
WHERE recipe_session_id = 253;

-- Session 6: Create ticket for human review
-- Only runs if re-grade failed
UPDATE recipe_sessions 
SET 
    execute_condition = 'if_previous_failed',
    on_success_action = 'stop',  -- End recipe after creating ticket
    on_failure_action = 'stop'
WHERE recipe_session_id = 254;

-- Session 7: Format standardization (final cleanup)
-- Runs if either initial grades passed OR re-grade passed
UPDATE recipe_sessions 
SET 
    execute_condition = 'always',
    on_success_action = 'stop',  -- End recipe successfully
    on_failure_action = 'stop'
WHERE recipe_session_id = 255;

-- Show updated configuration
SELECT 
    rs.execution_order,
    s.session_name,
    rs.execute_condition,
    rs.on_success_action,
    rs.on_success_goto_order,
    rs.on_failure_action,
    rs.on_failure_goto_order
FROM recipe_sessions rs
JOIN sessions s ON rs.session_id = s.session_id
WHERE rs.recipe_id = 1114
ORDER BY rs.execution_order;
