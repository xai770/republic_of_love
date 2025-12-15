-- ============================================================================
-- Add Skill Extraction to Recipe 1114
-- ============================================================================
-- Purpose: Extend Recipe 1114 to extract skills from job summaries
--
-- New Sessions:
--   Session 8: Extract raw skills (qwen2.5:7b)
--   Session 9: Translate & map to taxonomy (qwen2.5:7b)
--
-- Input: {session_7_output} (formatted job summary)
-- Output: skill_keywords JSONB array saved to postings table
--
-- Created: 2025-10-29
-- ============================================================================

-- ============================================================================
-- STEP 1: Create Canonical
-- ============================================================================

INSERT INTO canonicals (
    canonical_code,
    facet_id,
    capability_description,
    prompt,
    response,
    enabled
)
VALUES (
    'taxonomy_skill_extraction',
    'dynatax_skills',
    'Extract skills from job summaries and map to taxonomy (bilingual support)',
    'Extract skills from job posting summary and map to our standardized taxonomy. Supports German to English translation for skill matching.',
    'JSON array of taxonomy-matched skills',
    true
)
ON CONFLICT (canonical_code) DO UPDATE SET
    capability_description = EXCLUDED.capability_description,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- STEP 2: Create Sessions
-- ============================================================================

-- Session 8: Extract raw skills from summary
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1114_extract_skills',
    'taxonomy_skill_extraction',
    'qwen2.5:7b',
    'Extract raw skills from job summary (qwen2.5:7b)',
    5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1114_extract_skills'
);

-- Session 9: Translate to English and format as JSON
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1114_map_to_taxonomy',
    'taxonomy_skill_extraction',
    'qwen2.5:7b',
    'Translate skills to English and map to taxonomy (qwen2.5:7b)',
    5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1114_map_to_taxonomy'
);

-- ============================================================================
-- STEP 3: Create Instructions
-- ============================================================================

-- Get session IDs for instructions
DO $$
DECLARE
    v_session_extract_id INTEGER;
    v_session_map_id INTEGER;
BEGIN
    -- Get session IDs
    SELECT session_id INTO v_session_extract_id
    FROM sessions WHERE session_name = 'r1114_extract_skills';
    
    SELECT session_id INTO v_session_map_id
    FROM sessions WHERE session_name = 'r1114_map_to_taxonomy';
    
    -- Instruction for Session 8: Extract skills
    INSERT INTO instructions (
        session_id,
        step_number,
        step_description,
        prompt_template,
        timeout_seconds,
        enabled
    )
    VALUES (
        v_session_extract_id,
        1,
        'Extract all skills from job summary',
        'Extract ALL skills, technologies, and competencies mentioned in this job posting.

JOB SUMMARY:
{session_7_output}

TASK:
- List EVERY skill, tool, technology, or competency mentioned
- Include technical skills (Python, SQL, AWS, etc.)
- Include soft skills (leadership, communication, etc.)
- Include domain knowledge (finance, healthcare, etc.)
- Keep skills SHORT and ATOMIC (e.g., "SQL" not "Fundierte SQL Kenntnisse")
- Extract the core skill name, not full descriptions
- If text is in German, extract German skill names
- Return 5-20 skills typically

Return a simple JSON array of skills found:
["skill_1", "skill_2", "skill_3"]

Return ONLY the JSON array, no other text.',
        300,
        true
    )
    ON CONFLICT (session_id, step_number) DO UPDATE SET
        prompt_template = EXCLUDED.prompt_template,
        updated_at = CURRENT_TIMESTAMP;
    
    -- Instruction for Session 9: Translate and map
    INSERT INTO instructions (
        session_id,
        step_number,
        step_description,
        prompt_template,
        timeout_seconds,
        enabled
    )
    VALUES (
        v_session_map_id,
        1,
        'Translate skills to English for taxonomy mapping',
        'Translate these skills to English and match them to our taxonomy.

RAW SKILLS EXTRACTED:
{session_8_output}

TAXONOMY (13 domains, 347 skills - English canonical names):

**SOFTWARE_AND_TECHNOLOGY:** Java, Python, JavaScript, TypeScript, C#, React, Angular, Vue.js, Node.js, .NET, Spring, Django, REST APIs, GraphQL, Microservices, Git, Agile, Scrum, DevOps, CI/CD, Docker, Kubernetes, Programming, Full_Stack, Mobile_Development

**DATA_AND_ANALYTICS:** SQL, Data_Analysis, Business_Intelligence, Power_BI, Tableau, Excel, Data_Visualization, ETL, Data_Warehousing, Big_Data, Hadoop, Spark, Data_Mining, Statistical_Analysis, Reporting, KPIs, Dashboards, Data_Modeling, Database_Design, NoSQL, MongoDB, PostgreSQL, MySQL, Oracle, Data_Science, Machine_Learning, Analytics

**INFRASTRUCTURE_AND_CLOUD:** AWS, Azure, Google_Cloud, Cloud_Architecture, Linux, Unix, Windows_Server, VMware, Virtualization, Network_Administration, System_Administration, Infrastructure_as_Code, Terraform, Ansible, Active_Directory, Monitoring, Server_Management

**SECURITY_AND_RISK:** Cybersecurity, Information_Security, Network_Security, Application_Security, Cloud_Security, Penetration_Testing, Risk_Assessment, Risk_Management, Compliance, GDPR, ISO_27001, Audit, Threat_Detection, Incident_Response, Encryption, Identity_Management, Security_Policies

**FINANCE_AND_ACCOUNTING:** Financial_Analysis, Financial_Modeling, Financial_Planning, Budgeting, Forecasting, Cost_Analysis, Financial_Reporting, IFRS, GAAP, Management_Accounting, General_Ledger, Tax_Planning, Investment_Analysis, Corporate_Finance, M&A, Valuation

**BUSINESS_OPERATIONS:** Project_Management, Program_Management, Process_Improvement, Change_Management, Stakeholder_Management, Business_Analysis, Requirements_Gathering, Process_Mapping, Vendor_Management, Procurement, Supply_Chain, Quality_Management, Strategic_Planning

**LEADERSHIP_AND_STRATEGY:** Leadership, Team_Leadership, People_Management, Coaching, Mentoring, Talent_Development, Strategic_Leadership, Executive_Leadership, Corporate_Strategy, Business_Strategy, Digital_Transformation, Decision_Making, Problem_Solving, Business_Acumen

**COMMUNICATION:** Communication, Written_Communication, Verbal_Communication, Presentation_Skills, Public_Speaking, Technical_Writing, Documentation, Business_Writing, English, German, French, Spanish, Multilingual

**TEAMWORK:** Teamwork, Collaboration, Cross_Functional_Collaboration, Team_Player, Coordination, Partnership_Building, Interpersonal_Skills, Networking

**CLIENT_RELATIONS:** Client_Management, Customer_Service, Account_Management, Client_Relations, Stakeholder_Relations, Relationship_Management, Customer_Success

**NEGOTIATION:** Negotiation, Conflict_Resolution, Mediation, Persuasion

**DOMAIN_EXPERTISE:** Healthcare, Financial_Services, Telecommunications, Manufacturing, Retail, Public_Sector

**PROFESSIONAL_SKILLS:** Research, Analysis, Training, Consulting, Facilitation

TASK:
1. For each raw skill, find the closest matching taxonomy skill
2. If the skill is in German, translate to English first
3. Return ONLY skills that match the taxonomy (don''t add new ones)
4. Use exact taxonomy names (underscores, capitalization)

Return a JSON array of matched taxonomy skills:
["SQL", "Python", "Leadership", "Communication"]

Return ONLY the JSON array, no other text.',
        300,
        true
    )
    ON CONFLICT (session_id, step_number) DO UPDATE SET
        prompt_template = EXCLUDED.prompt_template,
        updated_at = CURRENT_TIMESTAMP;
    
    RAISE NOTICE 'Instructions created for skill extraction sessions';
END $$;

-- ============================================================================
-- STEP 3: Add Sessions to Recipe 1114
-- ============================================================================

-- Get session IDs
DO $$
DECLARE
    v_session_extract_id INTEGER;
    v_session_map_id INTEGER;
    v_recipe_id INTEGER := 1114;
BEGIN
    SELECT session_id INTO v_session_extract_id
    FROM sessions WHERE session_name = 'r1114_extract_skills';
    
    SELECT session_id INTO v_session_map_id
    FROM sessions WHERE session_name = 'r1114_map_to_taxonomy';
    
    -- Add Session 8 (execution_order 8)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    )
    VALUES (
        v_recipe_id,
        v_session_extract_id,
        8,
        'always',
        'continue',
        'stop',
        1
    )
    ON CONFLICT (recipe_id, execution_order) DO UPDATE SET
        session_id = EXCLUDED.session_id;
    
    -- Add Session 9 (execution_order 9)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    )
    VALUES (
        v_recipe_id,
        v_session_map_id,
        9,
        'always',
        'continue',
        'stop',
        1
    )
    ON CONFLICT (recipe_id, execution_order) DO UPDATE SET
        session_id = EXCLUDED.session_id;
    
    RAISE NOTICE 'Sessions added to Recipe 1114';
END $$;

-- ============================================================================
-- STEP 5: Update by_recipe_runner.py to save skill_keywords
-- ============================================================================
-- NOTE: This needs manual code update in by_recipe_runner.py
-- After Session 9 completes, save session_9_output to postings.skill_keywords
-- ============================================================================

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 
    r.recipe_id,
    r.recipe_name,
    rs.execution_order,
    s.session_name,
    s.actor_id,
    LEFT(i.prompt_template, 60) || '...' as instruction_preview
FROM recipes r
JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
JOIN sessions s ON rs.session_id = s.session_id
LEFT JOIN instructions i ON i.session_id = s.session_id AND i.step_number = 1
WHERE r.recipe_id = 1114
ORDER BY rs.execution_order;
