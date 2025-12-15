-- ============================================================================
-- Recipe 1122: Profile Career Analysis (Multi-Model Ensemble)
-- ============================================================================
-- Purpose: Deep organizational analysis of career history using multi-model ensemble
--          Generates comprehensive career reports with stakeholder mapping,
--          organizational dynamics, technical/soft skills, and progression insights
--
-- Flow:
--   Session 1: Career chunking (Python tool - chunked_deepseek_analyzer.py)
--   Session 2: Organizational analysis per chunk (deepseek-r1:8b)
--   Session 3: Technical skills extraction (qwen2.5:7b)
--   Session 4: Soft skills extraction (olmo2:7b)
--   Session 5: Synthesis and report generation (Claude via API)
--
-- Input: profiles.career_history OR docs/career_text
-- Output: career_analyses table + markdown report
--
-- Created: 2025-11-04
-- ============================================================================

-- ============================================================================
-- STEP 1: Create Instructions
-- ============================================================================

-- Session 2: DeepSeek Organizational Analysis (per chunk)
INSERT INTO instructions (
    instruction_text,
    instruction_type,
    max_output_tokens,
    temperature,
    enabled
)
SELECT
    'You are an expert at analyzing organizational dynamics at large financial institutions.

CAREER PERIOD: {period_start} - {period_end}
ORGANIZATION: {organization}

CAREER HISTORY EXCERPT:

{career_chunk_text}

Reason step-by-step and provide:

1. **STAKEHOLDER LEVELS**: What levels of stakeholders would this person interact with during this period?
   - C-level executives (CIO, CFO, CTO, etc.)
   - Directors/VPs (which functions?)
   - Managers (which departments?)
   - End users?

2. **FUNCTIONS INVOLVED**: What organizational functions would be engaged?
   - Legal? Procurement? IT? Finance? Compliance? Operations?
   - Be specific about WHY each function is involved

3. **ORGANIZATIONAL SKILLS REQUIRED**: What organizational navigation skills does this require?
   - Stakeholder management
   - Cross-functional collaboration
   - Influence without authority
   - Change management
   - Negotiation
   - Political savvy

4. **CAREER PROGRESSION INSIGHTS**: What does this period show about career development?
   - Leadership level (individual contributor, team lead, manager, director-level responsibilities?)
   - Scope of influence (team, department, division, global?)
   - Strategic vs tactical work?

Think through the organizational complexity carefully. Consider the size and nature of the organization.',
    'task',
    4000,
    0.7,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM instructions 
    WHERE instruction_text LIKE '%CAREER PERIOD:%ORGANIZATION:%CAREER HISTORY EXCERPT:%'
);

-- Session 3: Qwen Technical Skills Extraction
INSERT INTO instructions (
    instruction_text,
    instruction_type,
    max_output_tokens,
    temperature,
    enabled
)
SELECT
    'You are an expert at identifying technical skills, tools, and methodologies from career descriptions.

FULL CAREER HISTORY:

{full_career_text}

Analyze the MOST LIKELY technical skills, tools, and standards used. Be REALISTIC and PRACTICAL - avoid over-engineering or speculation.

Provide:

### 1. SOFTWARE & TOOLS

**Most Likely Used:**
- Office Tools (Excel, Word, etc.)
- Database Management (SQL databases, query tools)
- Data Analysis & Reporting (BI tools)
- Process Automation tools
- Backend/Development tools
- Project Management tools

### 2. TECHNICAL SKILLS

**Required Technical Competencies:**
- Programming Languages
- Database & Query Skills
- System Integration
- Data Analysis
- Process Automation

### 3. STANDARDS & METHODOLOGIES

**Industry Standards and Regulations:**
- Compliance Frameworks (GDPR, SOX, etc.)
- Software Licensing Standards
- Project Management Methodologies (Agile, Scrum, etc.)
- Data Quality & Integrity standards

Focus on tools and skills that are MOST LIKELY based on the job descriptions, not just POSSIBLE. If speculating, clearly mark as [LIKELY] vs [CONFIRMED].

Be specific and practical.',
    'task',
    2500,
    0.3,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM instructions 
    WHERE instruction_text LIKE '%MOST LIKELY technical skills, tools, and standards%'
);

-- Session 4: Olmo Soft Skills Extraction
INSERT INTO instructions (
    instruction_text,
    instruction_type,
    max_output_tokens,
    temperature,
    enabled
)
SELECT
    'You are an expert at identifying soft skills and interpersonal competencies from career descriptions.

FULL CAREER HISTORY:

{full_career_text}

Analyze and categorize the soft skills and interpersonal competencies demonstrated throughout this career.

Provide:

### COMMUNICATION SKILLS:
- Written/verbal communication (WHY needed in this role?)
- Presentation skills (WHY needed?)
- Technical translation (WHY needed?)

### INTERPERSONAL SKILLS:
- Stakeholder management (WHY needed?)
- Negotiation (WHY needed?)
- Diplomacy (WHY needed?)
- Conflict resolution (WHY needed?)

### LEADERSHIP & INFLUENCE:
- Team leadership (WHY needed?)
- Influence without authority (WHY needed?)
- Change management (WHY needed?)

### ANALYTICAL & PROBLEM-SOLVING:
- Critical thinking (WHY needed?)
- Problem decomposition (WHY needed?)
- Root cause analysis (WHY needed?)

### PERSONAL ATTRIBUTES:
- Attention to detail (WHY needed?)
- Adaptability (WHY needed?)
- Persistence (WHY needed?)
- Political savvy (WHY needed?)

For each skill, explain WHY it is needed based on the specific responsibilities and organizational context described. Provide concrete examples from the career history.',
    'task',
    3000,
    0.5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM instructions 
    WHERE instruction_text LIKE '%soft skills and interpersonal competencies from career descriptions%'
);

-- Session 5: Synthesis Instruction (for Claude API)
INSERT INTO instructions (
    instruction_text,
    instruction_type,
    max_output_tokens,
    temperature,
    enabled
)
SELECT
    'You are synthesizing multi-model career analysis results into a comprehensive report.

INPUTS:

**DeepSeek Organizational Analysis (per period):**
{deepseek_chunks}

**Qwen Technical Skills:**
{qwen_technical}

**Olmo Soft Skills:**
{olmo_soft_skills}

**Profile Metadata:**
- Name: {profile_name}
- Career Span: {career_span}
- Organizations: {organizations}

Generate a comprehensive markdown report with:

1. **Executive Summary**
   - Career arc overview
   - Key organizations and roles
   - Unique value proposition

2. **Period-by-Period Analysis** (for each career chunk)
   - Stakeholder levels
   - Functions involved
   - Organizational skills
   - Career progression insights

3. **Cross-Period Analysis**
   - Stakeholder engagement patterns
   - Organizational skills evolution
   - Leadership progression timeline
   - Strategic impact metrics

4. **Technical Skills Summary** (from Qwen)
   - Tools and software
   - Technical competencies
   - Standards and methodologies

5. **Soft Skills Summary** (from Olmo)
   - Communication skills
   - Interpersonal skills
   - Leadership and influence
   - Analytical and problem-solving
   - Personal attributes

6. **Career Positioning Insights**
   - Unique skill combinations
   - Proven C-level engagement
   - Financial impact track record
   - Target role recommendations

7. **Recommendations**
   - Resume/LinkedIn optimization
   - Interview talking points
   - Job search strategy

Format: Clean markdown with clear sections, bullet points, and tables where appropriate. Be comprehensive but concise.',
    'task',
    8000,
    0.7,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM instructions 
    WHERE instruction_text LIKE '%synthesizing multi-model career analysis results%'
);

-- ============================================================================
-- STEP 2: Create Sessions
-- ============================================================================

-- Session 1: Career Chunking (handled by Python tool, no LLM session needed)

-- Session 2: DeepSeek Organizational Analysis (per chunk)
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1122_org_analysis',
    'deepseek_organizational_analysis',
    'deepseek-r1:8b',
    'Analyze organizational dynamics per career period (deepseek-r1:8b)',
    10,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1122_org_analysis'
);

-- Session 3: Qwen Technical Skills
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1122_technical_skills',
    'qwen_technical_skills',
    'qwen2.5:7b',
    'Extract technical skills, tools, and methodologies (qwen2.5:7b)',
    5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1122_technical_skills'
);

-- Session 4: Olmo Soft Skills
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1122_soft_skills',
    'olmo_soft_skills',
    'olmo2:7b',
    'Extract soft skills and interpersonal competencies (olmo2:7b)',
    5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1122_soft_skills'
);

-- Session 5: Claude Synthesis (API-based)
INSERT INTO sessions (
    session_name,
    canonical_code,
    actor_id,
    session_description,
    max_instruction_runs,
    enabled
)
SELECT 
    'r1122_synthesis',
    'claude_career_synthesis',
    'claude-3-5-sonnet-20241022',
    'Synthesize all analyses into comprehensive report (Claude API)',
    5,
    true
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE session_name = 'r1122_synthesis'
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
    1122,
    'Profile Career Analysis',
    'Multi-model ensemble for deep career analysis. DeepSeek-R1 analyzes organizational dynamics per period, Qwen2.5 extracts technical skills, Olmo2 identifies soft skills, Claude synthesizes comprehensive report. Output: career_analyses table + markdown.',
    1,
    150,
    true
)
ON CONFLICT (recipe_id) DO UPDATE SET
    recipe_name = EXCLUDED.recipe_name,
    recipe_description = EXCLUDED.recipe_description,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- STEP 4: Link Sessions to Recipe
-- ============================================================================

DO $$
DECLARE
    v_inst_org_id INTEGER;
    v_inst_tech_id INTEGER;
    v_inst_soft_id INTEGER;
    v_inst_synth_id INTEGER;
    v_sess_org_id INTEGER;
    v_sess_tech_id INTEGER;
    v_sess_soft_id INTEGER;
    v_sess_synth_id INTEGER;
    v_recipe_id INTEGER := 1122;
BEGIN
    -- Get instruction IDs
    SELECT instruction_id INTO v_inst_org_id
    FROM instructions
    WHERE instruction_text LIKE '%CAREER PERIOD:%ORGANIZATION:%CAREER HISTORY EXCERPT:%'
    LIMIT 1;
    
    SELECT instruction_id INTO v_inst_tech_id
    FROM instructions
    WHERE instruction_text LIKE '%MOST LIKELY technical skills, tools, and standards%'
    LIMIT 1;
    
    SELECT instruction_id INTO v_inst_soft_id
    FROM instructions
    WHERE instruction_text LIKE '%soft skills and interpersonal competencies from career descriptions%'
    LIMIT 1;
    
    SELECT instruction_id INTO v_inst_synth_id
    FROM instructions
    WHERE instruction_text LIKE '%synthesizing multi-model career analysis results%'
    LIMIT 1;
    
    -- Get session IDs
    SELECT session_id INTO v_sess_org_id
    FROM sessions WHERE session_name = 'r1122_org_analysis';
    
    SELECT session_id INTO v_sess_tech_id
    FROM sessions WHERE session_name = 'r1122_technical_skills';
    
    SELECT session_id INTO v_sess_soft_id
    FROM sessions WHERE session_name = 'r1122_soft_skills';
    
    SELECT session_id INTO v_sess_synth_id
    FROM sessions WHERE session_name = 'r1122_synthesis';
    
    -- Link Session 1: Organizational Analysis (DeepSeek, per chunk - parallel)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        instruction_id,
        session_order,
        enabled
    )
    VALUES (
        v_recipe_id,
        v_sess_org_id,
        v_inst_org_id,
        1,
        true
    )
    ON CONFLICT (recipe_id, session_order) DO UPDATE SET
        session_id = EXCLUDED.session_id,
        instruction_id = EXCLUDED.instruction_id,
        enabled = EXCLUDED.enabled;
    
    -- Link Session 2: Technical Skills (Qwen)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        instruction_id,
        session_order,
        enabled
    )
    VALUES (
        v_recipe_id,
        v_sess_tech_id,
        v_inst_tech_id,
        2,
        true
    )
    ON CONFLICT (recipe_id, session_order) DO UPDATE SET
        session_id = EXCLUDED.session_id,
        instruction_id = EXCLUDED.instruction_id,
        enabled = EXCLUDED.enabled;
    
    -- Link Session 3: Soft Skills (Olmo)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        instruction_id,
        session_order,
        enabled
    )
    VALUES (
        v_recipe_id,
        v_sess_soft_id,
        v_inst_soft_id,
        3,
        true
    )
    ON CONFLICT (recipe_id, session_order) DO UPDATE SET
        session_id = EXCLUDED.session_id,
        instruction_id = EXCLUDED.instruction_id,
        enabled = EXCLUDED.enabled;
    
    -- Link Session 4: Synthesis (Claude)
    INSERT INTO recipe_sessions (
        recipe_id,
        session_id,
        instruction_id,
        session_order,
        enabled
    )
    VALUES (
        v_recipe_id,
        v_sess_synth_id,
        v_inst_synth_id,
        4,
        true
    )
    ON CONFLICT (recipe_id, session_order) DO UPDATE SET
        session_id = EXCLUDED.session_id,
        instruction_id = EXCLUDED.instruction_id,
        enabled = EXCLUDED.enabled;
    
    RAISE NOTICE 'Recipe 1122 configured successfully';
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
    LEFT(i.instruction_text, 80) || '...' as instruction_preview
FROM recipes r
JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
JOIN sessions s ON rs.session_id = s.session_id
JOIN instructions i ON rs.instruction_id = i.instruction_id
WHERE r.recipe_id = 1122
ORDER BY rs.session_order;
