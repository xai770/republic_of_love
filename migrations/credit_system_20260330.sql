-- Credit system: balance column + transactions table
-- Phase 3 Task 23 — 2026-03-30

BEGIN;

-- 1. Add credit_balance to users (integer, cents)
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS credit_balance INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN users.credit_balance IS 'Prepaid credit balance in euro-cents. Deducted on paid deliverable use.';

-- 2. Credit transactions ledger
CREATE TABLE IF NOT EXISTS credit_transactions (
    txn_id          BIGSERIAL   PRIMARY KEY,
    user_id         INTEGER     NOT NULL REFERENCES users(user_id),
    amount_cents    INTEGER     NOT NULL,          -- positive = top-up/refund, negative = spend
    balance_after   INTEGER     NOT NULL,          -- snapshot after this txn
    txn_type        VARCHAR(20) NOT NULL,          -- 'topup', 'spend', 'refund', 'trial_grant', 'sustainer_grant'
    description     TEXT,                          -- human-readable: "Clara match report", "€10 top-up"
    deliverable_ref TEXT,                          -- optional FK-ish: 'clara:<match_id>', 'doug:<interaction_id>'
    stripe_payment_intent_id VARCHAR(100),         -- for top-ups: Stripe PI id
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_txn_user
    ON credit_transactions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_credit_txn_type
    ON credit_transactions(txn_type);

COMMENT ON TABLE credit_transactions IS 'Immutable ledger of all credit movements — top-ups, spends, refunds.';

-- 3. Grant trial credits to existing users who have none
-- (New users get trial credits via onboarding; this backfills existing ones)
UPDATE users
SET credit_balance = 500
WHERE credit_balance = 0
  AND subscription_tier = 'free'
  AND trial_ends_at IS NOT NULL
  AND trial_ends_at > NOW();

-- Record trial grants as transactions
INSERT INTO credit_transactions (user_id, amount_cents, balance_after, txn_type, description)
SELECT user_id, 500, 500, 'trial_grant', 'Welcome trial — €5.00 credit'
FROM users
WHERE credit_balance = 500
  AND NOT EXISTS (
    SELECT 1 FROM credit_transactions ct
    WHERE ct.user_id = users.user_id AND ct.txn_type = 'trial_grant'
  );

COMMIT;
