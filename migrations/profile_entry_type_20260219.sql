-- 2026-02-19: Add entry_type to profile_work_history
-- Allows work, education, and project entries in the same table.
-- Already applied live.

ALTER TABLE profile_work_history
    ADD COLUMN entry_type text NOT NULL DEFAULT 'work';

COMMENT ON COLUMN profile_work_history.entry_type
    IS 'work, education, or project';

CREATE INDEX idx_work_history_entry_type
    ON profile_work_history (entry_type);
