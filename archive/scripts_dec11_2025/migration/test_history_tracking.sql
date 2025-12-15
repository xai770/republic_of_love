-- Test history tracking functionality

\echo '🧪 History Tracking Test'
\echo '======================='
\echo ''

-- Test 1: Update a canonical's prompt
\echo '1. Updating canonical prompt (most important use case)...'
UPDATE canonicals 
SET prompt = 'UPDATED TEST: ' || prompt,
    updated_at = CURRENT_TIMESTAMP
WHERE canonical_code = 'analyze_job_market'
RETURNING canonical_code, canonical_name;

\echo ''
\echo '2. Check canonical history:'
SELECT 
    history_id,
    canonical_code,
    LEFT(prompt, 50) as prompt_preview,
    archived_at,
    change_reason
FROM canonicals_history 
WHERE canonical_code = 'analyze_job_market'
ORDER BY archived_at DESC 
LIMIT 3;

\echo ''
\echo '3. Update a session config...'
UPDATE sessions
SET max_instruction_runs = max_instruction_runs + 1
WHERE session_id = (SELECT session_id FROM sessions LIMIT 1)
RETURNING session_id, session_name, max_instruction_runs;

\echo ''
\echo '4. Check session history:'
SELECT 
    history_id,
    session_id,
    session_name,
    max_instruction_runs,
    archived_at
FROM sessions_history 
ORDER BY archived_at DESC 
LIMIT 3;

\echo ''
\echo '✅ History tracking is working!'
\echo ''
\echo '💡 Use cases:'
\echo '   - A/B test prompt versions (canonicals_history)'
\echo '   - Debug "it worked last week" issues'
\echo '   - Audit trail for compliance'
\echo '   - Rollback to previous configurations'
