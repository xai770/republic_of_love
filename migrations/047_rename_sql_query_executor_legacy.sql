-- Migration 047: Rename sql_query_executor_legacy to check_description
-- Date: December 2, 2025
-- Reason: Name was a) too long and b) wrong - it checks job descriptions, not arbitrary SQL

-- Rename the actor
UPDATE actors 
SET actor_name = 'check_description' 
WHERE actor_name = 'sql_query_executor_legacy';

-- Verify the change
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM actors WHERE actor_name = 'check_description') THEN
        RAISE EXCEPTION 'Migration failed: check_description actor not found after rename';
    END IF;
    RAISE NOTICE 'Migration 047 complete: sql_query_executor_legacy renamed to check_description';
END $$;
