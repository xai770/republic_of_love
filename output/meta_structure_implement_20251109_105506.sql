-- Meta-Structure Implementation
-- Generated: 2025-11-09 10:55:06.435012
-- Creates parent folders and reassigns categories

BEGIN;

-- 1. Create meta-category: Business & Finance
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('business_&_finance', 'Business & Finance', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 2. Create meta-category: Leadership & Management
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('leadership_&_management', 'Leadership & Management', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 3. Create meta-category: Operations & Supply Chain
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('operations_&_supply_chain', 'Operations & Supply Chain', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 4. Create meta-category: Marketing & Sales
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('marketing_&_sales', 'Marketing & Sales', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 5. Create meta-category: Technical Excellence & Innovation
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('technical_excellence_&_innovation', 'Technical Excellence & Innovation', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 6. Create meta-category: Information Technology & Cybersecurity
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('information_technology_&_cybersecurity', 'Information Technology & Cybersecurity', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 7. Create meta-category: Soft Skills & Professional Development
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('soft_skills_&_professional_development', 'Soft Skills & Professional Development', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- 8. Create meta-category: Human Resources & HR Processes
INSERT INTO skill_aliases (skill_name, display_name, confidence, language)
VALUES ('human_resources_&_hr_processes', 'Human Resources & HR Processes', 1.0, 'en')
ON CONFLICT (skill_name) DO NOTHING;

-- Add hierarchy relationships
-- (Add skill_hierarchy entries linking categories to meta-folders)

COMMIT;
