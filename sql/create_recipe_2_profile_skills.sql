-- Recipe 2: Profile Skill Extraction
-- Purpose: Extract and map skills from candidate profiles (parallel to Recipe 1114 for jobs)
-- Reuses taxonomy and approach from Recipe 1114 Sessions 8-9

-- ============================================================================
-- Step 1: Create the Recipe
-- ============================================================================

INSERT INTO recipes (
    recipe_name,
    recipe_description,
    recipe_version,
    max_total_session_runs,
    enabled,
    created_at,
    updated_at
) VALUES (
    'profile_skill_extraction',
    'Extract professional summary and skills from candidate profiles. Maps skills to same taxonomy as job postings for matching.',
    1,
    100,
    TRUE,
    NOW(),
    NOW()
) RETURNING recipe_id;

-- Note: Save the recipe_id for next steps (should be 2 if this is second recipe)

-- ============================================================================
-- Step 2: Create Canonical for Profile Skills
-- ============================================================================

-- Check if dynatax_skills facet exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM facets WHERE facet_code = 'dynatax_skills') THEN
        INSERT INTO facets (facet_code, facet_name, facet_description)
        VALUES (
            'dynatax_skills',
            'Dynamic Taxonomy Skills',
            'Skills taxonomy and extraction processes'
        );
    END IF;
END $$;

-- Create canonical for profile skill extraction
INSERT INTO canonicals (
    canonical_code,
    canonical_name,
    canonical_description,
    facet_id,
    enabled
) SELECT
    'profile_skill_extraction',
    'Profile Skill Extraction',
    'Extract and map skills from candidate profiles to job taxonomy',
    facet_id,
    TRUE
FROM facets
WHERE facet_code = 'dynatax_skills';

-- ============================================================================
-- Step 3: Create Session 1 - Extract Profile Summary
-- ============================================================================

INSERT INTO sessions (
    session_name,
    session_description,
    canonical_id,
    actor_id,
    enabled
) SELECT
    'r2_extract_profile_summary',
    'Extract professional summary from candidate profile/CV',
    (SELECT canonical_id FROM canonicals WHERE canonical_code = 'profile_skill_extraction'),
    'gemma2:2b',
    TRUE;

-- Add instruction for Session 1
INSERT INTO instructions (
    instruction_text,
    instruction_version,
    session_id,
    enabled
) SELECT
    '# Task: Extract Professional Summary from Profile

You are analyzing a candidate profile/CV. Extract a clean, structured professional summary.

## Input
{profile_raw_text}

## Instructions
1. Extract core information:
   - Professional identity (current role, specialization)
   - Years of experience and career level
   - Key domains/industries worked in
   - Core competencies and strengths
   - Notable achievements or impact
   
2. Structure:
   - Start with current role and identity
   - List key domains/expertise areas
   - Highlight significant achievements
   - Note career trajectory (progression, industries)

3. Format as bullet points for clarity

## Output
Return ONLY the professional summary in this format:

**Professional Identity:** [Current role/specialization]

**Experience Level:** [Years] years, [Level: entry/junior/mid/senior/lead/executive]

**Core Domains:**
- [Domain 1]
- [Domain 2]
- [Domain 3]

**Key Competencies:**
- [Competency 1]
- [Competency 2]
- [Competency 3]

**Notable Achievements:**
- [Achievement 1]
- [Achievement 2]

**Career Trajectory:** [Brief summary of career progression]',
    1,
    (SELECT session_id FROM sessions WHERE session_name = 'r2_extract_profile_summary'),
    TRUE;

-- ============================================================================
-- Step 4: Create Session 2 - Extract Raw Skills
-- ============================================================================

INSERT INTO sessions (
    session_name,
    session_description,
    canonical_id,
    actor_id,
    enabled
) SELECT
    'r2_extract_skills',
    'Extract raw skills from profile summary and work history',
    (SELECT canonical_id FROM canonicals WHERE canonical_code = 'profile_skill_extraction'),
    'qwen2.5:7b',
    TRUE;

-- Add instruction for Session 2
INSERT INTO instructions (
    instruction_text,
    instruction_version,
    session_id,
    enabled
) SELECT
    '# Task: Extract Skills from Profile

You are analyzing a candidate profile. Extract ALL skills mentioned or implied.

## Input Summary
{session_1_output}

## Full Profile Text
{profile_raw_text}

## Instructions
1. Review both the summary and full profile text
2. Extract technical skills (programming languages, tools, platforms)
3. Extract domain skills (SAM, compliance, project management, etc.)
4. Extract soft skills (leadership, communication, etc.)
5. Include skills from:
   - Explicitly mentioned tools/technologies
   - Work responsibilities (e.g., "managed team" → Leadership)
   - Achievements (e.g., "negotiated contracts" → Negotiation)
   - Industry context (e.g., "banking" → Financial Services)

## Guidelines
- Extract 10-30 skills
- Use specific names (e.g., "Python" not "programming")
- Include both technical and soft skills
- Extract in original language (German or English)
- Avoid duplicates
- Infer reasonable skills from context

## Output
Return ONLY a JSON array of extracted skills:

["skill1", "skill2", "skill3", ...]

Example:
["SAP", "Contract Management", "Leadership", "Python", "Software Compliance", "Project Management", "Stakeholder Management"]',
    1,
    (SELECT session_id FROM sessions WHERE session_name = 'r2_extract_skills'),
    TRUE;

-- ============================================================================
-- Step 5: Create Session 3 - Map to Taxonomy
-- ============================================================================

INSERT INTO sessions (
    session_name,
    session_description,
    canonical_id,
    actor_id,
    enabled
) SELECT
    'r2_map_to_taxonomy',
    'Translate skills to English and map to canonical job taxonomy',
    (SELECT canonical_id FROM canonicals WHERE canonical_code = 'profile_skill_extraction'),
    'qwen2.5:7b',
    TRUE;

-- Add instruction for Session 3 (reuses taxonomy from Recipe 1114)
INSERT INTO instructions (
    instruction_text,
    instruction_version,
    session_id,
    enabled
) SELECT
    '# Task: Map Skills to Taxonomy

You are mapping extracted skills to our canonical job taxonomy.

## Extracted Skills
{session_2_output}

## Job Taxonomy (347 Skills in 13 Domains)

### SOFTWARE_AND_TECHNOLOGY (26 skills)
Java, Python, C_Sharp, JavaScript, TypeScript, React, Angular, Node_js, SQL, NoSQL, HTML_CSS, Docker, Kubernetes, Git, CI_CD, REST_APIs, Microservices, Object_Oriented_Programming, Agile_Methodologies, DevOps, System_Architecture, API_Development, Frontend_Development, Backend_Development, Full_Stack_Development, Mobile_Development

### DATA_AND_ANALYTICS (31 skills)
SQL, Data_Analysis, Power_BI, Tableau, Excel, Data_Visualization, Statistical_Analysis, Machine_Learning, Python, R, Data_Modeling, ETL, Data_Warehousing, Business_Intelligence, Predictive_Analytics, Big_Data, Apache_Spark, Hadoop, Data_Mining, Reporting, Dashboard_Development, SAS, SPSS, Data_Quality, Data_Governance, Data_Strategy, A_B_Testing, Experimental_Design, Quantitative_Analysis, Descriptive_Statistics, Inferential_Statistics

### INFRASTRUCTURE_AND_CLOUD (29 skills)
AWS, Azure, Google_Cloud, Linux, Windows_Server, VMware, Networking, System_Administration, Cloud_Architecture, Infrastructure_as_Code, Terraform, Ansible, Load_Balancing, DNS, Firewall_Configuration, VPN, Active_Directory, Virtualization, Storage_Management, Backup_Recovery, Disaster_Recovery, High_Availability, Scalability, Monitoring, Logging, Performance_Tuning, Capacity_Planning, Patch_Management, Server_Configuration

### SECURITY_AND_RISK (59 skills)
Cybersecurity, Information_Security, Risk_Management, Compliance, GDPR, ISO_27001, SOX, HIPAA, PCI_DSS, Security_Auditing, Penetration_Testing, Vulnerability_Assessment, Incident_Response, Threat_Analysis, Identity_Access_Management, IAM, Single_Sign_On, Multi_Factor_Authentication, Encryption, PKI, Network_Security, Endpoint_Security, SIEM, Security_Operations, SOC, Threat_Intelligence, Malware_Analysis, Forensics, Security_Architecture, Zero_Trust, Data_Loss_Prevention, Security_Awareness, Security_Policies, Business_Continuity, Disaster_Recovery_Planning, Operational_Risk, Credit_Risk, Market_Risk, Internal_Controls, Audit, Regulatory_Compliance, Anti_Money_Laundering, KYC, Fraud_Detection, Third_Party_Risk, Vendor_Risk, Privacy, Data_Protection, Security_Governance, Risk_Assessment, Risk_Mitigation, Control_Testing, Risk_Reporting, Basel_III, MiFID, Dodd_Frank, AML_CTF, GRC

### FINANCE_AND_ACCOUNTING (60 skills)
Financial_Analysis, Financial_Modeling, Budgeting, Forecasting, Financial_Reporting, GAAP, IFRS, Accounting, Bookkeeping, General_Ledger, Accounts_Payable, Accounts_Receivable, Financial_Planning, FP_A, Management_Accounting, Cost_Accounting, Tax_Accounting, Audit, Internal_Audit, External_Audit, Financial_Controls, SOX_Compliance, Revenue_Recognition, Cash_Flow_Management, Working_Capital, Treasury, Investment_Analysis, Portfolio_Management, Asset_Management, Valuation, M_A, Due_Diligence, Corporate_Finance, Capital_Markets, Equity_Research, Credit_Analysis, Risk_Management, Derivatives, Fixed_Income, Trading, Quantitative_Finance, Financial_Engineering, Econometrics, Bloomberg_Terminal, SAP_FICO, Oracle_Financials, QuickBooks, Xero, NetSuite, Hyperion, Essbase, TM1, Anaplan, Adaptive_Insights, BlackLine, Workiva, Alteryx_Finance, Tableau_Finance, Power_BI_Finance

### BUSINESS_OPERATIONS (36 skills)
Project_Management, Program_Management, Portfolio_Management, Agile, Scrum, Kanban, Waterfall, PMP, Change_Management, Process_Improvement, Lean, Six_Sigma, Business_Process_Reengineering, Workflow_Optimization, Standard_Operating_Procedures, Quality_Management, Quality_Assurance, Continuous_Improvement, Operational_Excellence, Supply_Chain_Management, Logistics, Procurement, Vendor_Management, Contract_Management, Supplier_Relationship_Management, Inventory_Management, Demand_Planning, Operations_Management, Production_Planning, Capacity_Management, Resource_Allocation, Performance_Management, KPI_Development, Metrics_Reporting

### LEADERSHIP_AND_STRATEGY (44 skills)
Leadership, Team_Leadership, People_Management, Talent_Development, Performance_Management, Coaching, Mentoring, Succession_Planning, Organizational_Development, Change_Leadership, Transformation, Turnaround_Management, Strategic_Planning, Business_Strategy, Corporate_Strategy, Strategic_Thinking, Vision_Setting, Goal_Setting, Objective_Setting, OKRs, Balanced_Scorecard, Strategic_Execution, Business_Development, Market_Analysis, Competitive_Analysis, SWOT_Analysis, Business_Case_Development, Feasibility_Studies, Innovation_Management, Product_Strategy, Go_to_Market_Strategy, Growth_Strategy, Digital_Transformation, Operating_Model_Design, Organizational_Design, Governance, Board_Relations, Executive_Communication, Crisis_Management, Reputation_Management, Stakeholder_Engagement, Influence, Decision_Making, Problem_Solving

### COMMUNICATION (19 skills)
Communication, Written_Communication, Verbal_Communication, Presentation_Skills, Public_Speaking, Executive_Presentations, Storytelling, Report_Writing, Technical_Writing, Documentation, Copywriting, Content_Creation, Editing, Proofreading, Visual_Communication, Interpersonal_Skills, Active_Listening, Feedback_Delivery, Meeting_Facilitation

### TEAMWORK (12 skills)
Collaboration, Teamwork, Cross_Functional_Teams, Matrix_Management, Remote_Collaboration, Virtual_Teams, Team_Building, Conflict_Resolution, Consensus_Building, Delegation, Empowerment, Inclusion

### CLIENT_RELATIONS (13 skills)
Customer_Service, Client_Relationship_Management, Account_Management, Customer_Success, Client_Engagement, Relationship_Building, Trust_Building, Customer_Retention, Customer_Satisfaction, CRM_Systems, Salesforce, Client_Communication, Client_Advisory

### NEGOTIATION (6 skills)
Negotiation, Contract_Negotiation, Vendor_Negotiation, Conflict_Resolution, Mediation, Persuasion

### DOMAIN_EXPERTISE (6 skills)
Healthcare, Financial_Services, Telecommunications, Manufacturing, Retail, Public_Sector

### PROFESSIONAL_SKILLS (6 skills)
Research, Critical_Thinking, Analytical_Skills, Problem_Solving, Attention_to_Detail, Time_Management

## Instructions
1. For each extracted skill:
   a. If German, translate to English first
   b. Find best match in taxonomy (fuzzy matching OK)
   c. Use exact canonical name from taxonomy
   d. If no match, skip (will be tracked separately)

2. Mapping rules:
   - Exact match: Use immediately
   - Close match (e.g., "Programme Management" → "Program_Management"): Use canonical
   - Synonym (e.g., "ML" → "Machine_Learning"): Use canonical
   - No match: Skip

3. Include 5-25 matched skills
4. Use underscore format from taxonomy (e.g., "Machine_Learning" not "Machine Learning")

## Output
Return ONLY a JSON array of matched taxonomy skills:

["Taxonomy_Skill_1", "Taxonomy_Skill_2", "Taxonomy_Skill_3", ...]

Example:
["Project_Management", "Leadership", "SAP_FICO", "Contract_Management", "Stakeholder_Engagement", "Risk_Management"]',
    1,
    (SELECT session_id FROM sessions WHERE session_name = 'r2_map_to_taxonomy'),
    TRUE;

-- ============================================================================
-- Step 6: Link Sessions to Recipe
-- ============================================================================

-- Session 1: Extract Summary (execution_order = 1)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order, enabled)
SELECT 
    r.recipe_id,
    s.session_id,
    1,
    TRUE
FROM recipes r
CROSS JOIN sessions s
WHERE r.recipe_name = 'profile_skill_extraction'
  AND s.session_name = 'r2_extract_profile_summary';

-- Session 2: Extract Skills (execution_order = 2)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order, enabled)
SELECT 
    r.recipe_id,
    s.session_id,
    2,
    TRUE
FROM recipes r
CROSS JOIN sessions s
WHERE r.recipe_name = 'profile_skill_extraction'
  AND s.session_name = 'r2_extract_skills';

-- Session 3: Map to Taxonomy (execution_order = 3)
INSERT INTO recipe_sessions (recipe_id, session_id, execution_order, enabled)
SELECT 
    r.recipe_id,
    s.session_id,
    3,
    TRUE
FROM recipes r
CROSS JOIN sessions s
WHERE r.recipe_name = 'profile_skill_extraction'
  AND s.session_name = 'r2_map_to_taxonomy';

-- ============================================================================
-- Step 7: Add Documentation
-- ============================================================================

UPDATE recipes
SET documentation = 'See docs/RECIPE_2_PROFILE_SKILLS.md for full documentation.

## Quick Summary
- **Purpose:** Extract skills from candidate profiles and map to job taxonomy
- **Sessions:** 3 (summary extraction + raw skill extraction + taxonomy mapping)
- **Parallel to Recipe 1114:** Uses same taxonomy for job-to-candidate matching
- **Bilingual:** German → English translation before taxonomy matching

## Usage
```bash
# Process single profile
python3 scripts/by_recipe_runner.py --recipe-id 2 --profile-id 1

# Daily automation
python3 scripts/daily_recipe_2.py
```

## Database Fields Updated
- `profiles.profile_summary` - Professional summary
- `profiles.skill_keywords` - JSON array of taxonomy-matched skills

**Full Documentation:** docs/RECIPE_2_PROFILE_SKILLS.md'
WHERE recipe_name = 'profile_skill_extraction';

-- ============================================================================
-- Verification
-- ============================================================================

SELECT 'Recipe 2 created successfully!' as status;

-- Show recipe details
SELECT 
    r.recipe_id,
    r.recipe_name,
    r.recipe_description,
    COUNT(rs.session_id) as session_count
FROM recipes r
LEFT JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
WHERE r.recipe_name = 'profile_skill_extraction'
GROUP BY r.recipe_id, r.recipe_name, r.recipe_description;

-- Show sessions
SELECT 
    rs.execution_order,
    s.session_name,
    s.actor_id,
    s.session_description
FROM recipe_sessions rs
JOIN sessions s ON rs.session_id = s.session_id
JOIN recipes r ON rs.recipe_id = r.recipe_id
WHERE r.recipe_name = 'profile_skill_extraction'
ORDER BY rs.execution_order;
