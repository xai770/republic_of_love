-- ============================================================
-- Yogi posting events: read-tracking + activity log
-- 2026-02-23
--
-- Design decisions:
-- 1. "Viewed" is logged like email read: first_viewed_at set once,
--    view_count incremented each visit (JS fires after 3s on page).
--    Stored on profile_posting_matches — no extra join needed for
--    the common case of "has this yogi seen this posting?"
--
-- 2. yogi_posting_events is the append-only event log that powers:
--    a) The activity log on /home (first-person narrative)
--    b) The Yog-meter funnel chart
--    Events: viewed | saved | dismissed | apply_intent | applied
--            not_applied | outcome_received
--    The 'viewed' event here is the initial open only (not re-views);
--    re-views increment view_count on profile_posting_matches only.
--
-- 3. No PII in the event log itself — posting title/URL are looked
--    up at render time via posting_id join. reason/note are yogi-
--    authored free text; they see only their own rows.
-- ============================================================

-- ── Step 1: Add read-tracking columns to profile_posting_matches ──

ALTER TABLE profile_posting_matches
    ADD COLUMN IF NOT EXISTS first_viewed_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_viewed_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS view_count       INTEGER NOT NULL DEFAULT 0;

-- Index for "show me all postings this yogi has viewed"
CREATE INDEX IF NOT EXISTS idx_ppm_first_viewed
    ON profile_posting_matches (profile_id, first_viewed_at)
    WHERE first_viewed_at IS NOT NULL;


-- ── Step 2: Event log table ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS yogi_posting_events (
    event_id    BIGSERIAL PRIMARY KEY,
    profile_id  INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    posting_id  INTEGER NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    match_id    INTEGER          REFERENCES profile_posting_matches(match_id) ON DELETE SET NULL,

    -- Event type enum — extend as needed, never delete values
    event_type  TEXT NOT NULL CHECK (event_type IN (
                    'viewed',           -- first open (3s dwell), like email read
                    'saved',            -- bookmarked / starred
                    'dismissed',        -- "not for me" swipe / click
                    'apply_intent',     -- "Ja, ich möchte mich bewerben"
                    'applied',          -- confirmed as sent
                    'not_applied',      -- decided against after intent
                    'outcome_received'  -- got a reply (Zusage / Absage / no response)
                )),

    -- Optional structured reason (for dismiss / not_applied / outcome)
    reason      TEXT,

    -- Optional free-text note (yogi's own words, shown in activity log)
    note        TEXT,

    -- Metadata
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for the two main read patterns:
-- 1) Activity log: all events for a yogi, newest first
CREATE INDEX IF NOT EXISTS idx_ype_profile_created
    ON yogi_posting_events (profile_id, created_at DESC);

-- 2) Yog-meter funnel: count by event_type for a yogi
CREATE INDEX IF NOT EXISTS idx_ype_profile_type
    ON yogi_posting_events (profile_id, event_type);
