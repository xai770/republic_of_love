-- Migration 048: Rename actor names for clarity and brevity
-- Date: December 2, 2025
-- Reason: 
--   summary_saver_legacy → summary_saver (drop the _legacy suffix, it's the active one)
--   posting_skills_saver → postingskill_save (shorter, consistent with other savers)

-- Rename actors
UPDATE actors SET actor_name = 'summary_saver' WHERE actor_name = 'summary_saver_legacy';
UPDATE actors SET actor_name = 'postingskill_save' WHERE actor_name = 'posting_skills_saver';

-- Verify
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'summary_saver') THEN
        RAISE EXCEPTION 'Migration failed: summary_saver not found';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'postingskill_save') THEN
        RAISE EXCEPTION 'Migration failed: postingskill_save not found';
    END IF;
    RAISE NOTICE 'Migration 048 complete: summary_saver_legacy → summary_saver, posting_skills_saver → postingskill_save';
END $$;
