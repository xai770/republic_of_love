-- Phase 4 migration: engagement tracking + FAQ promotion
-- Date: 2026-03-30

-- 1. Add event_data JSONB to yogi_posting_events for engagement metadata
ALTER TABLE yogi_posting_events
    ADD COLUMN IF NOT EXISTS event_data JSONB DEFAULT '{}'::jsonb;

-- 2. Expand the event_type CHECK constraint to include engagement events
ALTER TABLE yogi_posting_events
    DROP CONSTRAINT IF EXISTS yogi_posting_events_event_type_check;

ALTER TABLE yogi_posting_events
    ADD CONSTRAINT yogi_posting_events_event_type_check CHECK (
        event_type = ANY (ARRAY[
            'viewed', 'saved', 'dismissed', 'apply_intent',
            'applied', 'not_applied', 'outcome_received',
            'time_in_modal', 'scroll_depth', 'maximized', 'external_click'
        ])
    );

-- 3. Create table for promoted FAQ entries (quick actions from pipeline)
CREATE TABLE IF NOT EXISTS mira_faq_promoted (
    id              SERIAL PRIMARY KEY,
    candidate_id    INTEGER REFERENCES mira_faq_candidates(id),
    faq_id          TEXT UNIQUE NOT NULL,
    page_key        TEXT NOT NULL,          -- e.g. '/account', '/search:power'
    label_en        TEXT NOT NULL,
    label_de        TEXT NOT NULL,
    message_text    TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faq_promoted_page ON mira_faq_promoted(page_key);
