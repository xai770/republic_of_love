-- Migration: Drop Legacy Skill Tables
-- Date: 2025-12-08
-- Author: Sandy (approved by Arden)
-- Purpose: Remove deprecated skill_* tables after Entity Registry migration
--
-- VERIFICATION BEFORE RUNNING:
-- 1. All active workflows use Entity Registry tables (entities, entity_relationships)
-- 2. Legacy actors are only in disabled/deprecated workflows
-- 3. Backups created before dropping

BEGIN;

-- ============================================================
-- PHASE 1: Create archive schema and backup tables
-- ============================================================

CREATE SCHEMA IF NOT EXISTS archive;

-- Backup all legacy tables to archive schema
CREATE TABLE IF NOT EXISTS archive.skill_aliases_final AS SELECT * FROM skill_aliases;
CREATE TABLE IF NOT EXISTS archive.skill_hierarchy_final AS SELECT * FROM skill_hierarchy;
CREATE TABLE IF NOT EXISTS archive.skill_occurrences_final AS SELECT * FROM skill_occurrences;
CREATE TABLE IF NOT EXISTS archive.skill_entity_map_final AS SELECT * FROM skill_entity_map;
CREATE TABLE IF NOT EXISTS archive.skills_pending_taxonomy_final AS SELECT * FROM skills_pending_taxonomy;

-- ============================================================
-- PHASE 2: Disable legacy actors
-- ============================================================

UPDATE actors 
SET enabled = FALSE,
    actor_name = CASE 
        WHEN actor_name NOT LIKE '[DEPRECATED]%' 
        THEN '[DEPRECATED] ' || actor_name 
        ELSE actor_name 
    END
WHERE actor_name IN (
    'hierarchy_resetter',
    'orphan_skills_fetcher',
    'skill_taxonomy_saver',
    'hierarchy_applier',
    'unmatched_skills_fetcher'
);

-- ============================================================
-- PHASE 3: Drop legacy tables
-- ============================================================

-- Drop staging table (empty, no dependencies)
DROP TABLE IF EXISTS skill_aliases_staging CASCADE;

-- Drop backup table
DROP TABLE IF EXISTS skill_hierarchy_backup_20251205_094228 CASCADE;

-- Drop entity map (replaced by entities.entity_id direct reference)
DROP TABLE IF EXISTS skill_entity_map CASCADE;

-- Drop occurrences (can be computed from posting_skills)
DROP TABLE IF EXISTS skill_occurrences CASCADE;

-- Drop pending taxonomy (replaced by entities_pending)
DROP TABLE IF EXISTS skills_pending_taxonomy CASCADE;

-- Drop hierarchy (replaced by entity_relationships)
DROP TABLE IF EXISTS skill_hierarchy CASCADE;

-- Drop aliases LAST (other tables may reference it)
DROP TABLE IF EXISTS skill_aliases CASCADE;

COMMIT;

-- ============================================================
-- VERIFICATION
-- ============================================================

-- Check tables are gone
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename LIKE 'skill%';

-- Check archive tables exist
SELECT tablename, pg_size_pretty(pg_total_relation_size('archive.' || tablename)) as size
FROM pg_tables 
WHERE schemaname = 'archive' 
  AND tablename LIKE 'skill%';

-- Check Entity Registry is healthy
SELECT 
    (SELECT COUNT(*) FROM entities WHERE entity_type = 'skill') as skills,
    (SELECT COUNT(*) FROM entities WHERE entity_type = 'skill_domain') as domains,
    (SELECT COUNT(*) FROM entity_relationships WHERE relationship = 'is_a') as classifications,
    (SELECT COUNT(*) FROM entities_pending WHERE status = 'pending') as pending;
