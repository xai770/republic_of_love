-- GDPR CV consent timestamp
-- 2026-02-23
--
-- Records the moment a user explicitly consented to LLM processing of their CV.
-- Set by the parse_cv endpoint when gdpr_consent=true is received.
-- Combined with the yogi_audit_log event_type='gdpr_consent' for the full trail.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS gdpr_cv_consent_at TIMESTAMPTZ;

COMMENT ON COLUMN users.gdpr_cv_consent_at IS
    'Timestamp of the most recent explicit GDPR consent for CV processing by AI services.';
