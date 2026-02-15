-- Migration: idle_in_transaction_session_timeout
-- Date: 2026-02-15
-- Purpose: Prevent sessions from holding locks indefinitely when idle in a transaction
-- Context: An orphaned berufenet phase2 process sat idle_in_transaction for 7+ minutes,
--          blocking the entire AA upsert pipeline. This timeout auto-kills such sessions.

ALTER DATABASE turing 
SET idle_in_transaction_session_timeout = '5min';
