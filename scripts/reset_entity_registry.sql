-- Entity Registry Reset Script
-- Purpose: Clear all skill entities to test workflow determinism
-- Created: 2025-12-08 by Arden
--
-- PRESERVES:
--   - postings (1,740 job postings)
--   - posting_skills (10,430 raw skills) - entity_id set to NULL
--   - geo entities (24 cities/countries/states/continents)
--   - interactions (workflow history)
--
-- CLEARS:
--   - skill entities (2,720+)
--   - skill relationships
--   - skill aliases
--   - skill names  
--   - registry_decisions (skill-related)
--   - entities_pending
--
-- RUN WITH: psql -d turing -f scripts/reset_entity_registry.sql

\echo '=== Entity Registry Reset ==='
\echo 'Starting transaction...'

BEGIN;

-- 0. Unlink posting_skills from entities (preserve raw_skill_name!)
\echo 'Step 0: Unlinking posting_skills from entities...'
UPDATE posting_skills 
SET entity_id = NULL 
WHERE entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill');

-- 0b. Unlink profile_skills from entities
\echo 'Step 0b: Unlinking profile_skills from entities...'
UPDATE profile_skills 
SET entity_id = NULL 
WHERE entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill');

-- 1. Clear registry decisions for skill entities
\echo 'Step 1: Clearing registry_decisions...'
DELETE FROM registry_decisions
WHERE subject_entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill')
   OR target_entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill');

-- 2. Clear skill relationships (keep geo relationships)
\echo 'Step 2: Clearing entity_relationships for skills...'
DELETE FROM entity_relationships 
WHERE entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill')
   OR related_entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill');

-- 3. Clear skill aliases
\echo 'Step 3: Clearing entity_aliases for skills...'
DELETE FROM entity_aliases
WHERE entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill');

-- 4. Clear skill names
\echo 'Step 4: Clearing entity_names for skills...'
DELETE FROM entity_names
WHERE entity_id IN (SELECT entity_id FROM entities WHERE entity_type = 'skill');

-- 5. Delete merged skill entities first (constraint: merged status requires merged_into_entity_id)
\echo 'Step 5: Deleting merged skill entities...'
DELETE FROM entities 
WHERE entity_type = 'skill' AND status = 'merged';

-- 6. Clear skill entities (remaining active/deprecated)
\echo 'Step 6: Deleting skill entities...'
DELETE FROM entities WHERE entity_type = 'skill';

-- 7. Clear pending queue
\echo 'Step 7: Truncating entities_pending...'
TRUNCATE entities_pending;

COMMIT;

\echo ''
\echo '=== Verification ==='

-- 8. Verify geo entities preserved
\echo 'Remaining entities by type:'
SELECT entity_type, COUNT(*) as count FROM entities GROUP BY entity_type ORDER BY entity_type;

-- 9. Verify posting_skills raw data intact  
\echo ''
\echo 'Posting skills status:'
SELECT 
    COUNT(*) as total_skills,
    COUNT(entity_id) as linked_to_entity,
    COUNT(*) - COUNT(entity_id) as unlinked
FROM posting_skills;

\echo ''
\echo '=== Reset Complete ==='
