-- ── 063 Add is_protected flag to users ───────────────────────────────────────
-- Marks user accounts that must never be wiped by reset scripts.
-- Used to protect the developer's personal account from accidental nukes.
-- Test/demo accounts have is_protected = FALSE.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_protected BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN users.is_protected IS
    'If true, reset/seed scripts refuse to touch this user. Set manually on real personal accounts.';

-- ── Sanity check ──────────────────────────────────────────────────────────────
-- SELECT user_id, yogi_name, is_protected FROM users ORDER BY user_id;
