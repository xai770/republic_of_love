-- ============================================================================
-- Migration: Add enabled column to workflow_conversations
-- ============================================================================
-- Purpose: Every table needs an enabled column for soft enable/disable
-- Date: 2025-11-04
-- ============================================================================

BEGIN;

-- Add enabled column (default true for existing records)
ALTER TABLE workflow_conversations 
ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT true;

-- Create index for performance (common filter)
CREATE INDEX IF NOT EXISTS idx_workflow_conversations_enabled 
ON workflow_conversations(enabled);

-- Add comment
COMMENT ON COLUMN workflow_conversations.enabled IS 
'Soft enable/disable flag - allows deactivating workflow steps without deletion';

COMMIT;

-- Verify
SELECT 
    'workflow_conversations.enabled' as added_column,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE enabled = true) as enabled_rows,
    COUNT(*) FILTER (WHERE enabled = false) as disabled_rows
FROM workflow_conversations;

-- Success message
DO $$ BEGIN
    RAISE NOTICE '✅ enabled column added to workflow_conversations';
    RAISE NOTICE '   All existing rows set to enabled=true';
END $$;
