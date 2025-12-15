-- Meta-Structure Implementation
-- Generated: 2025-11-09 10:57:39.823619
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

-- 3. Create meta-category: Project & Program Management
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('project_&_program_management', 'Project & Program Management', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 4. Create meta-category: Sales & Marketing
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('sales_&_marketing', 'Sales & Marketing', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 5. Create meta-category: Soft Skills & Communication
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('soft_skills_&_communication', 'Soft Skills & Communication', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 6. Create meta-category: IT Infrastructure & Security
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('it_infrastructure_&_security', 'IT Infrastructure & Security', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 7. Create meta-category: Development & Programming
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('development_&_programming', 'Development & Programming', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 8. Create meta-category: Research & Analysis
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('research_&_analysis', 'Research & Analysis', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 9. Create meta-category: Human Resources & Organization
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('human_resources_&_organization', 'Human Resources & Organization', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 10. Create meta-category: Operations & Supply Chain
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('operations_&_supply_chain', 'Operations & Supply Chain', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- Add hierarchy relationships
-- (Add skill_hierarchy entries linking categories to meta-folders)

COMMIT;
