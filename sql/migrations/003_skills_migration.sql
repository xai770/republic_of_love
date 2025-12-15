-- Migration 003: Skills Migration to UEO Schema
-- Migrates skill_aliases and skill_hierarchy to entities/entity_names/entity_relationships
-- Preserves all existing data and creates backward-compatible views
--
-- Date: 2025-12-07
-- Author: Sandy (with Arden guidance)

BEGIN;

-- ============================================================================
-- STEP 1: Determine entity_id offset
-- We already have geography entities (IDs ~49-72), skills should start fresh
-- ============================================================================

-- Find the max entity_id to avoid collisions
DO $$
DECLARE
    max_id INT;
BEGIN
    SELECT COALESCE(MAX(entity_id), 0) INTO max_id FROM entities;
    RAISE NOTICE 'Current max entity_id: %. Skills will start from %', max_id, max_id + 1;
END $$;

-- ============================================================================
-- STEP 2: Create mapping table to track old skill_id → new entity_id
-- ============================================================================

CREATE TABLE IF NOT EXISTS skill_entity_map (
    skill_id        INT PRIMARY KEY,
    entity_id       INT NOT NULL,
    skill_name      TEXT NOT NULL,
    migrated_at     TIMESTAMP DEFAULT now()
);

-- ============================================================================
-- STEP 3: Insert skills as entities
-- ============================================================================

-- Determine hierarchy level for each skill:
--   - No parent in skill_hierarchy = domain or orphan
--   - Parent has no parent = category
--   - Otherwise = skill (leaf)

-- First, let's make all skills type 'skill' and tag them with metadata
-- We'll determine domain/category/leaf later based on relationships
INSERT INTO entities (canonical_name, entity_type, status, created_at, created_by, metadata)
SELECT 
    sa.skill_name,
    'skill',  -- All skills start as type 'skill'
    'active',
    sa.created_at,
    COALESCE(sa.created_by, 'migration_003'),
    jsonb_build_object(
        'original_skill_id', sa.skill_id,
        'is_orphan', sh.skill_id IS NULL AND NOT EXISTS (SELECT 1 FROM skill_hierarchy ch WHERE ch.parent_skill_id = sa.skill_id),
        'is_domain', sh.skill_id IS NULL AND EXISTS (SELECT 1 FROM skill_hierarchy ch WHERE ch.parent_skill_id = sa.skill_id),
        'migrated_from', 'skill_aliases'
    )
FROM skill_aliases sa
LEFT JOIN skill_hierarchy sh ON sa.skill_id = sh.skill_id
WHERE NOT EXISTS (
    SELECT 1 FROM entities e 
    WHERE e.canonical_name = sa.skill_name 
    AND e.entity_type = 'skill'
);

-- ============================================================================
-- STEP 4: Build the mapping table
-- ============================================================================

INSERT INTO skill_entity_map (skill_id, entity_id, skill_name)
SELECT sa.skill_id, e.entity_id, sa.skill_name
FROM skill_aliases sa
JOIN entities e ON e.canonical_name = sa.skill_name AND e.entity_type = 'skill'
WHERE sa.skill_id NOT IN (SELECT skill_id FROM skill_entity_map)
ON CONFLICT (skill_id) DO NOTHING;

-- ============================================================================
-- STEP 5: Insert display names (from skill_aliases.display_name)
-- ============================================================================

INSERT INTO entity_names (entity_id, language, display_name, is_primary, confidence, created_at, created_by)
SELECT 
    sem.entity_id,
    COALESCE(sa.language, 'en'),
    COALESCE(sa.display_name, sa.skill_name),
    true,  -- is_primary
    COALESCE(sa.confidence, 1.0),
    sa.created_at,
    COALESCE(sa.created_by, 'migration_003')
FROM skill_aliases sa
JOIN skill_entity_map sem ON sa.skill_id = sem.skill_id
ON CONFLICT (entity_id, language, display_name) DO NOTHING;

-- ============================================================================
-- STEP 6: Insert aliases (skill_alias field, if different from skill_name)
-- ============================================================================

INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence, created_at, created_by)
SELECT 
    sem.entity_id,
    sa.skill_alias,
    'alternative',
    COALESCE(sa.confidence, 1.0),
    sa.created_at,
    COALESCE(sa.created_by, 'migration_003')
FROM skill_aliases sa
JOIN skill_entity_map sem ON sa.skill_id = sem.skill_id
WHERE sa.skill_alias IS NOT NULL 
  AND sa.skill_alias <> sa.skill_name
  AND sa.skill_alias <> ''
ON CONFLICT (entity_id, alias) DO NOTHING;

-- ============================================================================
-- STEP 7: Insert hierarchy relationships
-- ============================================================================

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, strength, created_at, created_by, is_primary)
SELECT 
    child_map.entity_id,      -- child skill
    parent_map.entity_id,     -- parent skill
    'child_of',               -- relationship type (child → parent)
    COALESCE(sh.strength, 1.0),
    sh.created_at,
    COALESCE(sh.created_by, 'migration_003'),
    true                      -- is_primary (single parent in original schema)
FROM skill_hierarchy sh
JOIN skill_entity_map child_map ON sh.skill_id = child_map.skill_id
JOIN skill_entity_map parent_map ON sh.parent_skill_id = parent_map.skill_id
ON CONFLICT (entity_id, related_entity_id, relationship) DO NOTHING;

-- ============================================================================
-- STEP 8: Create backward-compatible views
-- ============================================================================

-- View that looks like skill_aliases but reads from entities
CREATE OR REPLACE VIEW v_skill_aliases AS
SELECT 
    sem.skill_id,
    e.canonical_name AS skill_name,
    en.display_name,
    ea.alias AS skill_alias,
    en.confidence,
    en.language,
    e.created_at,
    e.created_by,
    NULL::TEXT AS notes  -- Notes not migrated to UEO
FROM skill_entity_map sem
JOIN entities e ON sem.entity_id = e.entity_id
LEFT JOIN entity_names en ON e.entity_id = en.entity_id AND en.is_primary = true
LEFT JOIN entity_aliases ea ON e.entity_id = ea.entity_id;

-- View that looks like skill_hierarchy but reads from entity_relationships
CREATE OR REPLACE VIEW v_skill_hierarchy AS
SELECT 
    child_map.skill_id,
    parent_map.skill_id AS parent_skill_id,
    er.strength,
    er.created_at,
    er.created_by,
    er.notes
FROM entity_relationships er
JOIN skill_entity_map child_map ON er.entity_id = child_map.entity_id
JOIN skill_entity_map parent_map ON er.related_entity_id = parent_map.entity_id
WHERE er.relationship = 'child_of';

-- ============================================================================
-- STEP 9: Validation queries
-- ============================================================================

-- Count comparison
DO $$
DECLARE
    old_skill_count INT;
    new_entity_count INT;
    old_hierarchy_count INT;
    new_relationship_count INT;
BEGIN
    SELECT COUNT(*) INTO old_skill_count FROM skill_aliases;
    SELECT COUNT(*) INTO new_entity_count FROM skill_entity_map;
    SELECT COUNT(*) INTO old_hierarchy_count FROM skill_hierarchy;
    SELECT COUNT(*) INTO new_relationship_count FROM entity_relationships WHERE relationship = 'child_of';
    
    RAISE NOTICE '=== Migration Validation ===';
    RAISE NOTICE 'Skills: % in skill_aliases, % migrated to entities', old_skill_count, new_entity_count;
    RAISE NOTICE 'Hierarchy: % in skill_hierarchy, % migrated to entity_relationships', old_hierarchy_count, new_relationship_count;
    
    IF old_skill_count <> new_entity_count THEN
        RAISE WARNING 'Skill count mismatch! % vs %', old_skill_count, new_entity_count;
    END IF;
    
    IF old_hierarchy_count <> new_relationship_count THEN
        RAISE WARNING 'Hierarchy count mismatch! % vs %', old_hierarchy_count, new_relationship_count;
    END IF;
END $$;

-- Show entity type distribution
DO $$
DECLARE
    rec RECORD;
BEGIN
    RAISE NOTICE '=== Entity Type Distribution ===';
    FOR rec IN 
        SELECT entity_type, COUNT(*) as cnt 
        FROM entities 
        WHERE entity_type LIKE 'skill%'
        GROUP BY entity_type 
        ORDER BY cnt DESC
    LOOP
        RAISE NOTICE '%: %', rec.entity_type, rec.cnt;
    END LOOP;
END $$;

COMMIT;

-- ============================================================================
-- POST-MIGRATION NOTES
-- ============================================================================
-- 
-- The original tables (skill_aliases, skill_hierarchy) are preserved.
-- Use the v_skill_aliases and v_skill_hierarchy views for backward compatibility.
-- 
-- To query skills in the new schema:
--   SELECT * FROM entities WHERE entity_type LIKE 'skill%';
--   SELECT * FROM entity_relationships WHERE relationship = 'child_of';
--
-- To find a skill by name:
--   SELECT e.*, en.display_name 
--   FROM entities e 
--   JOIN entity_names en ON e.entity_id = en.entity_id 
--   WHERE e.canonical_name ILIKE '%python%';
--
-- To traverse hierarchy (child → parent → grandparent):
--   WITH RECURSIVE tree AS (
--       SELECT entity_id, canonical_name, 0 as depth
--       FROM entities WHERE canonical_name = 'python_programming'
--       UNION ALL
--       SELECT e.entity_id, e.canonical_name, t.depth + 1
--       FROM tree t
--       JOIN entity_relationships er ON t.entity_id = er.entity_id AND er.relationship = 'child_of'
--       JOIN entities e ON er.related_entity_id = e.entity_id
--   )
--   SELECT * FROM tree ORDER BY depth;
