-- Meta-Structure Implementation
-- Generated: 2025-11-09 11:22:04.298373
-- Creates parent folders and reassigns categories

BEGIN;

-- 1. Create meta-category: Business & Finance
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('business_&_finance', 'Business & Finance', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 2. Create meta-category: Technology & Engineering
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('technology_&_engineering', 'Technology & Engineering', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 3. Create meta-category: Data & Analytics
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('data_&_analytics', 'Data & Analytics', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 4. Create meta-category: Management & Leadership
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('management_&_leadership', 'Management & Leadership', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 5. Create meta-category: Communication & Soft Skills
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('communication_&_soft_skills', 'Communication & Soft Skills', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 6. Create meta-category: Sales & Marketing
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('sales_&_marketing', 'Sales & Marketing', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 7. Create meta-category: Security & Compliance
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('security_&_compliance', 'Security & Compliance', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 8. Create meta-category: Operations & Logistics
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('operations_&_logistics', 'Operations & Logistics', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 9. Create meta-category: Human Resources & Team Management
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('human_resources_&_team_management', 'Human Resources & Team Management', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- Add hierarchy relationships
-- (Add skill_hierarchy entries linking categories to meta-folders)

COMMIT;
