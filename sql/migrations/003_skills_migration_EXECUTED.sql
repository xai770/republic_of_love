-- Migration 003: Skills Migration to UEO Schema
-- Migrates skill_aliases and skill_hierarchy to entities/entity_names/entity_relationships
-- Preserves all existing data and creates backward-compatible views
--
-- Date: 2025-12-07
-- Author: Sandy (with Arden guidance)
-- Status: EXECUTED SUCCESSFULLY
--
-- Results:
--   - 2,786 skills migrated to entities
--   - 2,344 hierarchy relationships migrated
--   - 730 aliases migrated
--   - 2,786 display names migrated

-- ============================================================================
-- STEP 1: Create mapping table to track old skill_id → new entity_id
-- ============================================================================

CREATE TABLE IF NOT EXISTS skill_entity_map (
    skill_id        INT PRIMARY KEY,
    entity_id       INT NOT NULL,
    skill_name      TEXT NOT NULL,
    migrated_at     TIMESTAMP DEFAULT now()
);

-- ============================================================================
-- STEP 2: Insert skills as entities (all type 'skill')
-- ============================================================================

INSERT INTO entities (canonical_name, entity_type, status, created_at, created_by, metadata)
SELECT 
    sa.skill_name,
    'skill',
    'active',
    sa.created_at,
    COALESCE(sa.created_by, 'migration_003'),
    jsonb_build_object(
        'original_skill_id', sa.skill_id,
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
-- STEP 3: Build the mapping table
-- ============================================================================

INSERT INTO skill_entity_map (skill_id, entity_id, skill_name)
SELECT sa.skill_id, e.entity_id, sa.skill_name
FROM skill_aliases sa
JOIN entities e ON e.canonical_name = sa.skill_name AND e.entity_type = 'skill'
WHERE sa.skill_id NOT IN (SELECT skill_id FROM skill_entity_map);

-- ============================================================================
-- STEP 4: Insert display names (from skill_aliases.display_name)
-- ============================================================================

INSERT INTO entity_names (entity_id, language, display_name, is_primary, confidence, created_at, created_by)
SELECT 
    sem.entity_id,
    COALESCE(sa.language, 'en'),
    COALESCE(sa.display_name, sa.skill_name),
    true,
    COALESCE(sa.confidence, 1.0),
    sa.created_at,
    COALESCE(sa.created_by, 'migration_003')
FROM skill_aliases sa
JOIN skill_entity_map sem ON sa.skill_id = sem.skill_id
ON CONFLICT (entity_id, language, display_name) DO NOTHING;

-- ============================================================================
-- STEP 5: Insert aliases (skill_alias field, if different from skill_name)
-- Note: Unique constraint is on (alias, language), not (entity_id, alias)
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
ON CONFLICT (alias, language) DO NOTHING;

-- ============================================================================
-- STEP 6: Insert hierarchy relationships
-- ============================================================================

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, strength, created_at, created_by, is_primary)
SELECT 
    child_map.entity_id,
    parent_map.entity_id,
    'child_of',
    COALESCE(sh.strength, 1.0),
    sh.created_at,
    COALESCE(sh.created_by, 'migration_003'),
    true
FROM skill_hierarchy sh
JOIN skill_entity_map child_map ON sh.skill_id = child_map.skill_id
JOIN skill_entity_map parent_map ON sh.parent_skill_id = parent_map.skill_id
ON CONFLICT (entity_id, related_entity_id, relationship) DO NOTHING;

-- ============================================================================
-- STEP 7: Create backward-compatible views
-- ============================================================================

-- View that looks like skill_aliases but reads from entities
CREATE OR REPLACE VIEW v_skill_aliases AS
SELECT 
    sem.skill_id,
    e.canonical_name AS skill_name,
    en.display_name,
    ea.alias AS skill_alias,
    en.confidence,
    COALESCE(en.language, 'en') as language,
    e.created_at,
    e.created_by,
    NULL::TEXT AS notes
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
-- VALIDATION QUERIES (run after migration)
-- ============================================================================

-- Count comparison:
-- SELECT 'skill_aliases' as source, COUNT(*) FROM skill_aliases
-- UNION ALL SELECT 'entities (skill)', COUNT(*) FROM entities WHERE entity_type = 'skill'
-- UNION ALL SELECT 'skill_hierarchy', COUNT(*) FROM skill_hierarchy
-- UNION ALL SELECT 'entity_relationships (child_of)', COUNT(*) FROM entity_relationships WHERE relationship = 'child_of';

-- Hierarchy traversal (Python example):
-- WITH RECURSIVE hierarchy AS (
--     SELECT e.entity_id, e.canonical_name, 0 as depth
--     FROM entities e WHERE e.entity_id = 5652  -- python
--     UNION ALL
--     SELECT e.entity_id, e.canonical_name, h.depth + 1
--     FROM hierarchy h
--     JOIN entity_relationships er ON h.entity_id = er.entity_id AND er.relationship = 'child_of'
--     JOIN entities e ON er.related_entity_id = e.entity_id
-- )
-- SELECT * FROM hierarchy ORDER BY depth;
-- Result: python → development → technology

-- ============================================================================
-- POST-MIGRATION NOTES
-- ============================================================================
-- 
-- The original tables (skill_aliases, skill_hierarchy) are preserved.
-- Use the v_skill_aliases and v_skill_hierarchy views for backward compatibility.
-- 
-- To query skills in the new schema:
--   SELECT * FROM entities WHERE entity_type = 'skill';
--   SELECT * FROM entity_relationships WHERE relationship = 'child_of';
--
-- To find a skill by name:
--   SELECT e.*, en.display_name 
--   FROM entities e 
--   JOIN entity_names en ON e.entity_id = en.entity_id 
--   WHERE e.canonical_name ILIKE '%python%';
