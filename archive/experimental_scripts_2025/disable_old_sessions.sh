#!/bin/bash
# Disable old sessions (id <= 3312)

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'
-- Disable old sessions
UPDATE sessions 
SET enabled = false 
WHERE session_id <= 3312;

-- Show what was disabled
SELECT COUNT(*) as disabled_count 
FROM sessions 
WHERE session_id <= 3312;

-- Show active sessions
\echo ''
\echo 'ACTIVE SESSIONS:'
SELECT session_id, session_name, enabled 
FROM sessions 
WHERE enabled = true 
ORDER BY session_id;

SQL
