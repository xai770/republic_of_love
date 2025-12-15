-- Migration 028: Per-conversation timeout thresholds
-- Date: 2025-12-14
-- Author: Copilot
-- Purpose: Enable per-conversation reaper timeouts instead of global 2-minute threshold

-- 1. Add timeout_seconds column if not exists (may already exist)
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER DEFAULT 300;
COMMENT ON COLUMN conversations.timeout_seconds IS 
    'Reaper threshold in seconds. Default 300s (5 min). Set based on p99 latency analysis.';

-- 2. Set per-conversation timeouts based on Sandy's latency analysis

-- Fast scripts (should complete in <1s, 30s is generous)
UPDATE conversations SET timeout_seconds = 30 
WHERE canonical_name IN (
    'format_standardization', 
    'save_summary_check_ihl', 
    'postingskill_save',
    'save_skill_record'
);

-- Normal LLM tasks (~30-60s typical, 120s threshold)
UPDATE conversations SET timeout_seconds = 120 
WHERE canonical_name LIKE 'w%_c%_analyst'
   OR canonical_name LIKE 'w%_c%_expert'
   OR canonical_name LIKE 'w%_c%_skeptic'
   OR canonical_name LIKE '%triage%';

-- Slow extraction tasks (can legitimately take 5-10 min)
UPDATE conversations SET timeout_seconds = 600 
WHERE canonical_name LIKE '%extract%'
   OR canonical_name LIKE '%fetch%'
   OR canonical_name = 'gopher_skill_extraction';

-- 3. Index for reaper query performance
CREATE INDEX IF NOT EXISTS idx_conversations_timeout ON conversations(timeout_seconds);

-- Verification
SELECT canonical_name, timeout_seconds 
FROM conversations 
WHERE canonical_name IS NOT NULL 
ORDER BY timeout_seconds, canonical_name;
