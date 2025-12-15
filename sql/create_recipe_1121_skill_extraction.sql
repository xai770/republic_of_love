-- ============================================================================
-- Recipe 1121: Job Skills Extraction from Summary
-- ============================================================================
-- Purpose: Extract taxonomy skills from job postings' extracted_summary
--          and populate postings.skill_keywords (JSONB)
--
-- Flow:
--   Session 1 (qwen2.5:7b): Extract skills from summary using taxonomy
--   Session 2 (llama3.2:latest): Format as JSON array
--
-- Input: postings.extracted_summary
-- Output: postings.skill_keywords (JSONB array)
--
-- Created: 2025-10-29
-- ============================================================================

-- ============================================================================
-- STEP 1: Create Instructions
-- ============================================================================

-- Session 1: Extract skills using taxonomy
INSERT INTO instructions (
    instruction_text,
    instruction_type,
    max_output_tokens,
    temperature,
    enabled
)
SELECT
    'You are a skill extraction expert. Extract skills from this job posting summary that match our taxonomy.

JOB SUMMARY:
{extracted_summary}

TAXONOMY (13 domains, 347 skills):

**SOFTWARE & TECHNOLOGY (26 skills):**
Java, Python, JavaScript, TypeScript, C#, React, Angular, Vue.js, Node.js, .NET, Spring, Django, REST APIs, GraphQL, Microservices, Git, Agile, Scrum, DevOps, CI/CD, Docker, Kubernetes, Cloud Development, Mobile Development, Full Stack Development, Software Architecture

**DATA & ANALYTICS (31 skills):**
SQL, Data Analysis, Business Intelligence, Power BI, Tableau, Excel, Data Visualization, ETL, Data Warehousing, Big Data, Hadoop, Spark, Data Mining, Statistical Analysis, Reporting, KPIs, Dashboards, Data Modeling, Database Design, NoSQL, MongoDB, PostgreSQL, MySQL, Oracle, Data Science, Machine Learning, Python (Data), R, Pandas, NumPy, Analytics

**INFRASTRUCTURE & CLOUD (29 skills):**
AWS, Azure, Google Cloud, Cloud Architecture, Cloud Migration, Linux, Unix, Windows Server, VMware, Virtualization, Network Administration, System Administration, Infrastructure as Code, Terraform, Ansible, Active Directory, DNS, Load Balancing, Firewalls, VPN, Storage Systems, Backup Solutions, Disaster Recovery, High Availability, Monitoring, Nagios, Zabbix, Server Management, IT Operations

**SECURITY & RISK (59 skills):**
Cybersecurity, Information Security, Network Security, Application Security, Cloud Security, Security Architecture, Penetration Testing, Vulnerability Assessment, Risk Assessment, Risk Management, Compliance, GDPR, ISO 27001, SOX, Audit, Security Audit, Risk Audit, Threat Detection, Incident Response, SIEM, Firewall Management, Encryption, Identity Management, Access Control, Security Policies, Data Privacy, Business Continuity, Disaster Recovery Planning, Fraud Detection, Anti-Money Laundering, Financial Risk, Operational Risk, Credit Risk, Market Risk, Regulatory Compliance, Internal Audit, External Audit, Control Testing, Risk Mitigation, Security Awareness, Security Testing, Code Review, Static Analysis, Dynamic Analysis, Security Operations, SOC, Threat Intelligence, Malware Analysis, Forensics, IAM, PAM, Certificate Management, PKI, HTTPS, SSL/TLS, OAuth, SAML, Zero Trust

**FINANCE & ACCOUNTING (60 skills):**
Financial Analysis, Financial Modeling, Financial Planning, Budgeting, Forecasting, Cost Analysis, Variance Analysis, Financial Reporting, IFRS, GAAP, Management Accounting, Cost Accounting, General Ledger, Accounts Payable, Accounts Receivable, Cash Management, Treasury, Tax Planning, Corporate Tax, VAT, Investment Analysis, Portfolio Management, Asset Management, Wealth Management, Corporate Finance, M&A, Due Diligence, Valuation, DCF, NPV, IRR, Financial Controls, Month-End Close, Year-End Close, Consolidation, Intercompany, SAP FI, SAP CO, Oracle Financials, Financial Systems, ERP Finance, Audit Support, Internal Controls, SOX Compliance, Financial Governance, Transfer Pricing, Financial Strategy, Capital Allocation, Working Capital, Cash Flow Analysis, P&L Management, Balance Sheet, Financial Statements, Revenue Recognition, Expense Management

**BUSINESS OPERATIONS (36 skills):**
Project Management, Program Management, Process Improvement, Change Management, Stakeholder Management, Business Analysis, Requirements Gathering, Business Process, Workflow Optimization, Operational Excellence, Lean, Six Sigma, Kaizen, Process Mapping, SLA Management, Vendor Management, Procurement, Sourcing, Contract Management, Supply Chain, Logistics, Inventory Management, Operations Management, Quality Management, Quality Assurance, Performance Management, Metrics & KPIs, Reporting & Analysis, Strategic Planning, Business Development, Sales Strategy, Marketing Strategy, Product Management, Product Launch, Go-to-Market, Business Intelligence

**LEADERSHIP & STRATEGY (44 skills):**
Leadership, Team Leadership, People Management, Team Management, Coaching, Mentoring, Talent Development, Performance Reviews, Succession Planning, Change Leadership, Organizational Development, Culture Building, Strategic Leadership, Vision Setting, Executive Leadership, C-Level, Board Relations, Corporate Strategy, Business Strategy, Strategic Planning, Strategic Execution, Portfolio Management, Innovation Management, Digital Transformation, Transformation Management, Business Transformation, Organizational Change, Cross-Functional Leadership, Global Leadership, Regional Leadership, Matrix Management, Remote Team Management, Team Building, Conflict Management, Decision Making, Strategic Thinking, Problem Solving, Critical Thinking, Business Acumen, Financial Acumen, Commercial Awareness, Industry Knowledge, Market Analysis

**COMMUNICATION (19 skills):**
Communication, Written Communication, Verbal Communication, Presentation Skills, Public Speaking, Technical Writing, Documentation, Reporting, Business Writing, Executive Communication, Stakeholder Communication, Cross-Cultural Communication, Language Skills (English), Language Skills (German), Language Skills (French), Language Skills (Spanish), Multilingual, Fluent Communication, Professional Communication

**TEAMWORK (12 skills):**
Teamwork, Collaboration, Cross-Functional Collaboration, Team Player, Coordination, Partnership Building, Relationship Building, Interpersonal Skills, Social Skills, Networking, Community Building, Cultural Awareness

**CLIENT RELATIONS (13 skills):**
Client Management, Customer Service, Customer Relations, Account Management, Client Relations, Stakeholder Relations, Client Care, Relationship Management, Customer Success, Customer Experience, Customer Satisfaction, Service Delivery, Client Communication

**NEGOTIATION (6 skills):**
Negotiation, Negotiation Skills, Conflict Resolution, Mediation, Bargaining, Persuasion

**DOMAIN EXPERTISE (6 skills):**
Healthcare, Financial Services, Telecommunications, Manufacturing, Retail, Public Sector

**PROFESSIONAL SKILLS (6 skills):**
Research, Analysis, Training, Coaching, Facilitation, Consulting

TASK:
1. Read the job summary carefully
2. Identify ALL skills that match our taxonomy
3. Return ONLY the skill names (exact matches from taxonomy)
4. Include soft skills and technical skills
5. Be comprehensive but accurate

Return a simple list of skills found, one per line:
skill_name_1
skill_name_2
skill_name_3',
    'task',
    1500,
    0.3,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM instructions 
    WHERE instruction_text LIKE '%Extract skills from this job posting summary that match our taxonomy%'
);

-- Session 2: Format as JSON array
INSERT INTO instructions (
    instruction_text,
    instruction_type,
    max_output_tokens,
    temperature,
    enabled
)
SELECT
    'Convert this skill list into a valid JSON array.

INPUT SKILLS:
{session_1_output}

Return ONLY a valid JSON array like:
["Skill_One", "Skill_Two", "Skill_Three"]

Rules:
- Use double quotes
- Proper JSON array format
- No extra text, just the array
- Each skill on separate item',
    'task',
    1000,
    0.1,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM instructions 
    WHERE instruction_text LIKE '%Convert this skill list into a valid JSON array%'
);

-- ============================================================================
-- STEP 2: Create Sessions
-- ============================================================================

-- Session 1: Extract skills (qwen2.5:7b - excellent at extraction)
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1121_extract_skills',
    'extract_skills_from_summary',
    'qwen2.5:7b',
    'Extract skills from job summary using taxonomy (qwen2.5:7b)',
    5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1121_extract_skills'
);

-- Session 2: Format JSON (llama3.2:latest - perfect at formatting)
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1121_format_json',
    'format_skills_json',
    'llama3.2:latest',
    'Format skill list as JSON array (llama3.2:latest)',
    5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1121_format_json'
);

-- ============================================================================
-- STEP 3: Create Recipe
-- ============================================================================

INSERT INTO recipes (
    recipe_id,
    recipe_name,
    recipe_description,
    recipe_version,
    max_total_session_runs,
    enabled
)
VALUES (
    1121,
    'Job Skills Extraction',
    'Extract taxonomy skills from job posting summaries and populate skill_keywords. Session 1: qwen2.5 extracts skills. Session 2: llama3.2 formats as JSON.',
    1,
    100,
    true
)
ON CONFLICT (recipe_id) DO UPDATE SET
    recipe_name = EXCLUDED.recipe_name,
    recipe_description = EXCLUDED.recipe_description,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- STEP 4: Link Sessions to Recipe
-- ============================================================================

-- Get instruction IDs
DO $$
DECLARE
    v_inst_extract_id INTEGER;
    v_inst_format_id INTEGER;
    v_sess_extract_id INTEGER;
    v_sess_format_id INTEGER;
    v_recipe_id INTEGER := 1121;
BEGIN
    -- Get instruction IDs
    SELECT instruction_id INTO v_inst_extract_id
    FROM instructions
    WHERE instruction_text LIKE '%Extract skills from this job posting summary that match our taxonomy%'
    LIMIT 1;
    
    SELECT instruction_id INTO v_inst_format_id
    FROM instructions
    WHERE instruction_text LIKE '%Convert this skill list into a valid JSON array%'
    LIMIT 1;
    
    -- Get session IDs
    SELECT session_id INTO v_sess_extract_id
    FROM sessions WHERE session_name = 'r1121_extract_skills';
    
    SELECT session_id INTO v_sess_format_id
    FROM sessions WHERE session_name = 'r1121_format_json';
    
    -- Link Session 1 (extract skills)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        instruction_id,
        session_order,
        enabled
    )
    VALUES (
        v_recipe_id,
        v_sess_extract_id,
        v_inst_extract_id,
        1,
        true
    )
    ON CONFLICT (recipe_id, session_order) DO UPDATE SET
        session_id = EXCLUDED.session_id,
        instruction_id = EXCLUDED.instruction_id,
        enabled = EXCLUDED.enabled;
    
    -- Link Session 2 (format JSON)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        instruction_id,
        session_order,
        enabled
    )
    VALUES (
        v_recipe_id,
        v_sess_format_id,
        v_inst_format_id,
        2,
        true
    )
    ON CONFLICT (recipe_id, session_order) DO UPDATE SET
        session_id = EXCLUDED.session_id,
        instruction_id = EXCLUDED.instruction_id,
        enabled = EXCLUDED.enabled;
    
    RAISE NOTICE 'Recipe 1121 configured successfully';
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 
    r.recipe_id,
    r.recipe_name,
    rs.session_order,
    s.session_name,
    s.actor_id,
    LEFT(i.instruction_text, 60) || '...' as instruction_preview
FROM recipes r
JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
JOIN sessions s ON rs.session_id = s.session_id
JOIN instructions i ON rs.instruction_id = i.instruction_id
WHERE r.recipe_id = 1121
ORDER BY rs.session_order;
