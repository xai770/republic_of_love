-- Migration: Cleanup Legacy Terminology
-- Date: 2025-12-08
-- Author: Sandy (guided by Arden)
-- Purpose: Enforce "Entity Registry" as canonical term
--
-- Background: Found 12 unused actors with legacy terminology (dynatax, taxonomy, skillbridge)
-- that don't match our "Entity Registry" standard. Also 3 workflows need cleanup.
--
-- Note: Some actors have orphaned conversations (0 interactions). These are cascade deleted.

BEGIN;

-- 0. Delete orphaned instructions first (FK constraint from conversations)
DELETE FROM instructions 
WHERE conversation_id IN (
    SELECT c.conversation_id FROM conversations c
    JOIN actors a ON c.actor_id = a.actor_id
    WHERE a.actor_id IN (6, 10, 11, 34, 35, 41, 42, 47, 52, 54, 60, 61, 62)
);

-- 0a. Delete orphaned workflow_conversations (FK constraint)
DELETE FROM workflow_conversations 
WHERE conversation_id IN (
    SELECT c.conversation_id FROM conversations c
    JOIN actors a ON c.actor_id = a.actor_id
    WHERE a.actor_id IN (6, 10, 11, 34, 35, 41, 42, 47, 52, 54, 60, 61, 62)
);

-- 0b. Delete orphaned conversations (0 interactions, safe to delete)
DELETE FROM conversations 
WHERE actor_id IN (6, 10, 11, 34, 35, 41, 42, 47, 52, 54, 60, 61, 62);

-- 1. Delete unused actors with legacy terminology
-- These actors reference non-existent scripts and are not used by any enabled workflow
DELETE FROM actors WHERE actor_id IN (6, 10, 11, 34, 35, 41, 42, 47, 52, 54, 60, 61, 62);

-- 2. Rename actor 138 to use Entity Registry terminology
-- Currently named 'rebuild_skills_taxonomy', used by WF3004
UPDATE actors 
SET actor_name = 'entity_reorganizer'
WHERE actor_id = 138;

-- 3. Disable WF2002 (never ran, missing skill_merger.py)
UPDATE workflows SET enabled = FALSE WHERE workflow_id = 2002;

-- 4. Mark deprecated workflows in name
UPDATE workflows 
SET workflow_name = '[DEPRECATED] ' || workflow_name
WHERE workflow_id IN (3002, 3003)
  AND workflow_name NOT LIKE '%DEPRECATED%';

-- 5. Add deprecation notes
UPDATE workflows 
SET review_notes = 'DEPRECATED 2025-12-08: Replaced by WF3005 (Entity Registry - Skill Maintenance)'
WHERE workflow_id IN (3002, 3003);

COMMIT;
