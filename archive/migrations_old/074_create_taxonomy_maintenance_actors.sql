-- Migration 074: Create actors for Workflow 3002 - Taxonomy Maintenance
-- Purpose: Create script actors for taxonomy export, organization, and indexing
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

-- Actor 1: Export skills from database to file system
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    url,
    enabled
) VALUES (
    'taxonomy_exporter',
    'script',
    'python_script',
    'tools/rebuild_skills_taxonomy.py',
    'local',
    true
) ON CONFLICT (actor_name) DO UPDATE SET
    execution_type = EXCLUDED.execution_type,
    execution_path = EXCLUDED.execution_path,
    url = EXCLUDED.url,
    enabled = EXCLUDED.enabled;

-- Actor 2: Organize taxonomy with infinite-depth AI
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    url,
    enabled
) VALUES (
    'taxonomy_organizer',
    'script',
    'python_script',
    'tools/multi_round_organize.py',
    'local',
    true
) ON CONFLICT (actor_name) DO UPDATE SET
    execution_type = EXCLUDED.execution_type,
    execution_path = EXCLUDED.execution_path,
    url = EXCLUDED.url,
    enabled = EXCLUDED.enabled;

-- Actor 3: Generate navigation index (we'll create this script)
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    url,
    enabled
) VALUES (
    'taxonomy_indexer',
    'script',
    'python_script',
    'tools/generate_taxonomy_index.py',
    'local',
    true
) ON CONFLICT (actor_name) DO UPDATE SET
    execution_type = EXCLUDED.execution_type,
    execution_path = EXCLUDED.execution_path,
    url = EXCLUDED.url,
    enabled = EXCLUDED.enabled;

COMMIT;

-- Verify
SELECT actor_id, actor_name, actor_type, execution_type, execution_path
FROM actors
WHERE actor_name IN ('taxonomy_exporter', 'taxonomy_organizer', 'taxonomy_indexer')
ORDER BY actor_name;
