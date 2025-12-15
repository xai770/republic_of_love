-- Meta-Structure Implementation
-- Generated: 2025-11-09 10:50:03.562853
-- Creates parent folders and reassigns categories

BEGIN;

-- 1. Create meta-category: Accounting And Finance
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('accounting_and_finance', 'Accounting And Finance', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 2. Create meta-category: Technology & Engineering
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('technology_&_engineering', 'Technology & Engineering', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 3. Create meta-category: Project Management & Strategy
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('project_management_&_strategy', 'Project Management & Strategy', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 4. Create meta-category: Communication & Collaboration
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('communication_&_collaboration', 'Communication & Collaboration', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 5. Create meta-category: IT & Cybersecurity
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('it_&_cybersecurity', 'IT & Cybersecurity', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 6. Create meta-category: Operations & Maintenance
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('operations_&_maintenance', 'Operations & Maintenance', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 7. Create meta-category: Development & Programming
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('development_&_programming', 'Development & Programming', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 8. Create meta-category: Management & Leadership
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('management_&_leadership', 'Management & Leadership', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- Add hierarchy relationships
-- (Add skill_hierarchy entries linking categories to meta-folders)

COMMIT;
