-- Migration: repair_geonames_contamination_20260227
-- Date: 2026-02-27
-- Author: arden (copilot-assisted)
--
-- A geonames_import run on 2026-02-13 wrote 13,218 German town names into
-- owl_names. 155 of those collided with berufenet_id values, overwriting
-- profession names with place names (e.g. Sales-Manager/in → Steingaden).
--
-- This contaminated the embedding space used by the berufenet classifier.
-- No postings were misclassified (all 22,701 affected postings were
-- classified before the import), but future runs would have produced
-- garbage results.
--
-- FIX:
--   1. UPDATE the 155 colliding rows: restore display_name from berufenet.name
--   2. DELETE the 13,063 non-colliding geonames rows (embedding pollution)
--   3. CREATE a trigger to prevent non-berufenet sources from writing
--      to rows that belong to berufenet IDs
--
-- This migration is IDEMPOTENT — safe to re-apply.

BEGIN;

-- Step 1: Restore 155 corrupted primary names
UPDATE owl_names o
SET display_name = b.name,
    confidence_source = 'import',
    created_by = 'repair_geonames_20260227',
    name_type = 'canonical'
FROM berufenet b
WHERE o.owl_id = b.berufenet_id
  AND o.confidence_source = 'geonames_import'
  AND o.is_primary = true;

-- Step 2: Delete all remaining geonames pollution
DELETE FROM owl_names WHERE confidence_source = 'geonames_import';

-- Step 3: Guard trigger — prevent non-berufenet sources from writing to berufenet IDs
CREATE OR REPLACE FUNCTION prevent_owl_names_berufenet_overwrite()
RETURNS TRIGGER AS $$
DECLARE
    berufenet_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM berufenet WHERE berufenet_id = NEW.owl_id)
    INTO berufenet_exists;

    IF berufenet_exists THEN
        IF NEW.confidence_source NOT IN (
            'import', 'llm_confirmed', 'llm_single', 'human',
            'posting_city_name', 'repair_geonames_20260227'
        ) THEN
            RAISE EXCEPTION
                'owl_names: source "%" cannot write to berufenet ID %. '
                'Only berufenet-aware sources may modify profession names.',
                NEW.confidence_source, NEW.owl_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_berufenet_overwrite ON owl_names;
CREATE TRIGGER trg_prevent_berufenet_overwrite
    BEFORE INSERT OR UPDATE ON owl_names
    FOR EACH ROW
    EXECUTE FUNCTION prevent_owl_names_berufenet_overwrite();

COMMIT;
