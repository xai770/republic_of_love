-- Seed Test Skills Script
-- Purpose: Create 20 test skills as orphan entities for WF3005 determinism testing
-- Created: 2025-12-08 by Arden
--
-- These skills are hand-picked for diversity:
-- - Simple (5): Single concept, clear hierarchy
-- - Compound (5): Multiple concepts in one string
-- - Ambiguous (5): Could go multiple places
-- - Case Variants (2): Test normalization
-- - Edge Cases (3): Templates, acronyms, certifications
--
-- RUN WITH: psql -d turing -f scripts/seed_test_skills.sql
-- RUN AFTER: scripts/reset_entity_registry.sql

\echo '=== Seeding 20 Test Skills ==='

BEGIN;

-- Insert skills (no parent relationships = orphans)
\echo 'Inserting skill entities...'
INSERT INTO entities (entity_type, canonical_name, status)
VALUES 
    -- Simple (5)
    ('skill', 'Project Management', 'active'),
    ('skill', 'Machine Learning', 'active'),
    ('skill', 'Communication', 'active'),
    ('skill', 'Data Analysis', 'active'),
    ('skill', 'Budget Management', 'active'),
    -- Compound (5)
    ('skill', 'Programming Skills (Python/R)', 'active'),
    ('skill', 'Programming languages (e.g., Python, Java)', 'active'),
    ('skill', 'Database design and optimization', 'active'),
    ('skill', 'Version control systems (e.g., Git)', 'active'),
    ('skill', 'Coding/Programming', 'active'),
    -- Ambiguous (5)
    ('skill', 'Agile Methodologies', 'active'),
    ('skill', 'Team Leadership', 'active'),
    ('skill', 'Customer Service', 'active'),
    ('skill', 'Quality Assurance', 'active'),
    ('skill', 'Risk Assessment', 'active'),
    -- Case Variants (2)
    ('skill', 'software development', 'active'),
    ('skill', 'team leadership', 'active'),
    -- Edge Cases (3)
    ('skill', 'Technical Expertise in [Specific Technology]', 'active'),
    ('skill', 'User Experience (UX) Design', 'active'),
    ('skill', 'Scrum Master Certification', 'active');

-- Add names (required for entity display)
\echo 'Adding entity names...'
INSERT INTO entity_names (entity_id, display_name, language, is_primary)
SELECT entity_id, canonical_name, 'en', true
FROM entities
WHERE entity_type = 'skill' 
  AND status = 'active'
  AND NOT EXISTS (
      SELECT 1 FROM entity_names en WHERE en.entity_id = entities.entity_id
  );

COMMIT;

\echo ''
\echo '=== Verification ==='

-- Count skills
\echo 'Skill count:'
SELECT COUNT(*) as skill_count FROM entities WHERE entity_type = 'skill' AND status = 'active';

-- Count orphans (should match skill count - no parents yet)
\echo ''
\echo 'Orphan count (skills without parents):'
SELECT COUNT(*) as orphan_count
FROM entities e
WHERE e.entity_type = 'skill'
  AND e.status = 'active'
  AND NOT EXISTS (
      SELECT 1 FROM entity_relationships er 
      WHERE er.entity_id = e.entity_id 
      AND er.relationship = 'child_of'
  );

-- List all seeded skills
\echo ''
\echo 'All seeded skills:'
SELECT canonical_name FROM entities 
WHERE entity_type = 'skill' AND status = 'active'
ORDER BY canonical_name;

\echo ''
\echo '=== Seeding Complete ==='
\echo 'Ready to run: python3 scripts/prod/run_workflow_3005.py'
