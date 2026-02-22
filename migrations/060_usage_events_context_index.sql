-- Migration 060: GIN index on usage_events.context for transaction drill-down
-- Enables efficient queries like: context->>'user_message_id' = '123'
-- Date: 2026-02-22

CREATE INDEX IF NOT EXISTS idx_usage_events_context
    ON usage_events USING GIN (context jsonb_path_ops);
