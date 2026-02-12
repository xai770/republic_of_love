-- Migration 054: Create yogi_events table
-- Tracks behavioral events for Mira's contextual awareness.
-- NOT chat messages — those stay in yogi_messages.
-- 
-- Events: login, page_view, search_filter, posting_view, match_action
-- Retention: lightweight rows, ~200 bytes each. Auto-prune after 90 days.

BEGIN;

CREATE TABLE IF NOT EXISTS yogi_events (
    event_id    SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,
    event_data  JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_yogi_events_user_time ON yogi_events(user_id, created_at DESC);
CREATE INDEX idx_yogi_events_type ON yogi_events(event_type, created_at DESC);

COMMENT ON TABLE yogi_events IS 'Behavioral events for Mira context — not chat messages';
COMMENT ON COLUMN yogi_events.event_type IS 'login | page_view | search_filter | posting_view | match_action';
COMMENT ON COLUMN yogi_events.event_data IS 'JSON payload: {page, posting_id, title, domains, ql, city, radius, action, dwell_s}';

COMMIT;
