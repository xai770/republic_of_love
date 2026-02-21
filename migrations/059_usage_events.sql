-- Migration 059: Usage events + trial billing infrastructure
-- Tracks every billable AI action per user.
-- Cost unit: EUR cents (integer — no float rounding errors).
--
-- Event types and default prices (can be tuned in usage_event_prices):
--   mira_message      — one Mira chat exchange           2 cents
--   cv_extraction     — Adele CV parse + profile import  50 cents
--   cover_letter      — Clara cover letter generation    30 cents
--   match_report      — Clara match report               20 cents
--   profile_embed     — profile embedding refresh        5 cents
--
-- Trial model:
--   users.trial_ends_at  — when the free trial expires (default: 7 days after created_at)
--   users.trial_budget_cents — how much they can spend before being asked to subscribe (default: 0 = unlimited trial)
--   After trial_ends_at passes AND subscription_status != 'active': AI endpoints return 402.

-- ── 1. Price schedule (editable without code deploy) ─────────────────────────
CREATE TABLE IF NOT EXISTS usage_event_prices (
    event_type      VARCHAR(50) PRIMARY KEY,
    cost_cents      INTEGER     NOT NULL DEFAULT 0,
    description     TEXT,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO usage_event_prices (event_type, cost_cents, description) VALUES
    ('mira_message',   2,  'One Mira chat exchange (user message + LLM response)'),
    ('cv_extraction',  50, 'Adele CV parse + structured profile import'),
    ('cover_letter',   30, 'Clara cover letter generation for a specific posting'),
    ('match_report',   20, 'Clara match quality report for a posting'),
    ('profile_embed',  5,  'Profile embedding refresh after profile edit')
ON CONFLICT (event_type) DO NOTHING;

-- ── 2. Usage events log ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usage_events (
    event_id        BIGSERIAL PRIMARY KEY,
    user_id         INTEGER     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_type      VARCHAR(50) NOT NULL REFERENCES usage_event_prices(event_type),
    cost_cents      INTEGER     NOT NULL DEFAULT 0,   -- snapshot of price at event time
    context         JSONB       NOT NULL DEFAULT '{}', -- e.g. {"posting_id": 42, "tokens": 380}
    billed_at       TIMESTAMP WITH TIME ZONE,          -- NULL = not yet included in an invoice
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_events_user_created  ON usage_events (user_id, created_at DESC);
CREATE INDEX idx_usage_events_unbilled      ON usage_events (user_id) WHERE billed_at IS NULL;

-- ── 3. Trial columns on users ─────────────────────────────────────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS trial_ends_at      TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS trial_budget_cents INTEGER NOT NULL DEFAULT 500;
    -- 500 cents = €5.00 free trial budget. Set to 0 for unlimited.

-- Backfill: existing users get trial_ends_at = created_at + 7 days
-- (already past for all existing test accounts — they won't be gated)
UPDATE users
SET trial_ends_at = created_at + INTERVAL '7 days'
WHERE trial_ends_at IS NULL AND created_at IS NOT NULL;

-- New users automatically get trial_ends_at set to now() + 7 days via app logic
-- (done in auth router at registration, not here)

-- ── 4. Convenience view: per-user unbilled balance ────────────────────────────
CREATE OR REPLACE VIEW user_trial_balance AS
SELECT
    u.user_id,
    u.yogi_name,
    u.email,
    u.subscription_status,
    u.trial_ends_at,
    u.trial_budget_cents,
    COALESCE(SUM(e.cost_cents), 0)                          AS total_spent_cents,
    COALESCE(SUM(e.cost_cents) FILTER (WHERE e.billed_at IS NULL), 0) AS unbilled_cents,
    COUNT(e.event_id)                                        AS event_count,
    MAX(e.created_at)                                        AS last_event_at,
    -- Is trial active?
    (u.trial_ends_at IS NULL OR u.trial_ends_at > NOW())     AS trial_active,
    -- Is account in arrears? (trial expired AND not paid AND has unbilled usage)
    (
        u.trial_ends_at IS NOT NULL
        AND u.trial_ends_at < NOW()
        AND u.subscription_status != 'active'
        AND COALESCE(SUM(e.cost_cents) FILTER (WHERE e.billed_at IS NULL), 0) > 0
    ) AS needs_payment
FROM users u
LEFT JOIN usage_events e ON e.user_id = u.user_id
GROUP BY u.user_id, u.yogi_name, u.email, u.subscription_status, u.trial_ends_at, u.trial_budget_cents;

-- ── 5. Quick sanity check ─────────────────────────────────────────────────────
-- Run after applying: SELECT * FROM user_trial_balance;
