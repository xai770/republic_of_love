-- 2026-02-15: Add lazy posting validation
--
-- Postings are validated (HEAD request to external_url) before being shown
-- to candidates, but only once per 24 hours. This column tracks the last
-- successful validation time.
--
-- A posting with last_validated_at NULL or > 24h old will be checked on
-- next display. If the external_url returns 404, the posting is invalidated.
-- If 200, last_validated_at is updated.
--
-- This is a "lazy" approach — we only validate postings that are actually
-- being shown to users, not all 240K+ postings in the database.

ALTER TABLE postings 
ADD COLUMN IF NOT EXISTS last_validated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
