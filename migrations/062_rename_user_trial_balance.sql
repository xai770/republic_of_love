-- ── 062 rename user_trial_balance → user_usage_summary ────────────────────────
-- The view covers far more than trial balance: subscription status, unbilled
-- cents, needs_payment flag, event count, last event. Rename for clarity.
-- ────────────────────────────────────────────────────────────────────────────

ALTER VIEW public.user_trial_balance RENAME TO user_usage_summary;

-- ── Sanity check ─────────────────────────────────────────────────────────────
-- SELECT user_id, subscription_status, trial_active, needs_payment
-- FROM user_usage_summary LIMIT 5;
