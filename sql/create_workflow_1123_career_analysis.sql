-- ============================================================================
-- Workflow 1125: Profile Career Deep Analysis (Multi-Model Ensemble)
-- ============================================================================
-- Purpose: Deep organizational analysis of career history using multi-model ensemble
--          Generates comprehensive career reports with stakeholder mapping,
--          organizational dynamics, technical/soft skills, and progression insights
--
-- Extends Workflow 1122 (profile_skill_extraction) with deeper career analysis
--
-- Flow:
--   Conversation 1: Organizational analysis per period (deepseek-r1:8b)
--   Conversation 2: Technical skills extraction (qwen2.5:7b)
--   Conversation 3: Soft skills extraction (olmo2:7b)
--   Conversation 4: Career synthesis (qwen2.5:7b or Claude)
--
-- Input: profiles.{career_fields} OR docs/career_text
-- Output: career_analyses table + markdown report
--
-- Note: Links to skill_aliases via profile_skills for job matching
--
-- Created: 2025-11-04
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Create Conversations (was "sessions")
-- ============================================================================

-- Conversation 1: DeepSeek Organizational Analysis (per career period)
INSERT INTO conversations (
    conversation_name,
    conversation_description,
    actor_id,
    context_strategy,
    max_instruction_runs,
    enabled,
    canonical_name,
    conversation_type
)
SELECT
    'c1125_org_analysis',
    'Analyze organizational dynamics for a career period using DeepSeek-R1',
    actor_id,
    'isolated',  -- Each period analyzed independently
    20,  -- Up to 20 career periods
    true,
    'career_organizational_analysis',
    'single_actor'
FROM actors WHERE actor_name = 'deepseek-r1:8b'
RETURNING conversation_id;

-- Store conversation_id for later reference
DO $$
DECLARE
    conv1_id INTEGER;
    conv2_id INTEGER;
    conv3_id INTEGER;
    conv4_id INTEGER;
    wflow_id INTEGER;
BEGIN

-- Get conversation 1 ID
SELECT conversation_id INTO conv1_id 
FROM conversations 
WHERE conversation_name = 'c1125_org_analysis';

-- Conversation 2: Qwen Technical Skills
INSERT INTO conversations (
    conversation_name,
    conversation_description,
    actor_id,
    context_strategy,
    max_instruction_runs,
    enabled,
    canonical_name,
    conversation_type
)
SELECT
    'c1125_technical_skills',
    'Extract technical skills, tools, and standards from full career history',
    actor_id,
    'isolated',
    5,
    true,
    'career_technical_skills',
    'single_actor'
FROM actors WHERE actor_name = 'qwen2.5:7b'
RETURNING conversation_id INTO conv2_id;

-- Conversation 3: Olmo Soft Skills
INSERT INTO conversations (
    conversation_name,
    conversation_description,
    actor_id,
    context_strategy,
    max_instruction_runs,
    enabled,
    canonical_name,
    conversation_type
)
SELECT
    'c1125_soft_skills',
    'Extract soft skills and interpersonal competencies from career history',
    actor_id,
    'isolated',
    5,
    true,
    'career_soft_skills',
    'single_actor'
FROM actors WHERE actor_name = 'olmo2:7b'
RETURNING conversation_id INTO conv3_id;

-- Conversation 4: Synthesis
INSERT INTO conversations (
    conversation_name,
    conversation_description,
    actor_id,
    context_strategy,
    max_instruction_runs,
    enabled,
    canonical_name,
    conversation_type
)
SELECT
    'c1125_synthesis',
    'Synthesize all analysis into comprehensive career report',
    actor_id,
    'shared_conversation',  -- Has access to previous conversations
    5,
    true,
    'career_synthesis_report',
    'single_actor'
FROM actors WHERE actor_name = 'qwen2.5:7b'
RETURNING conversation_id INTO conv4_id;

-- ============================================================================
-- STEP 2: Create Instructions (prompts)
-- ============================================================================

-- Instruction 1: Organizational Analysis
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    enabled
) VALUES (
    'Analyze organizational dynamics for career period',
    conv1_id,
    1,
    'Deep reasoning about stakeholder levels, functions, and organizational skills',
    E'You are an expert at analyzing organizational dynamics at large financial institutions and global corporations.

CAREER PERIOD: {period_start} - {period_end}
ORGANIZATION: {organization}
ROLE: {role_title}

CAREER HISTORY EXCERPT:
{career_chunk_text}

Analyze this career period step-by-step:

1. **STAKEHOLDER LEVELS**: What levels of stakeholders would this person interact with?
   - C-level executives (CIO, CFO, CTO, CEO, CPO, etc.) - List specific titles if mentioned
   - Directors/VPs (which functions: Legal, Finance, IT, Operations, etc.)
   - Managers (which departments/teams)
   - End users/team members

2. **FUNCTIONS INVOLVED**: What organizational functions were engaged?
   - Legal/Compliance
   - Finance/Procurement
   - IT/Technology
   - Operations
   - HR
   - Sales/Marketing
   - Other (specify)

3. **ORGANIZATIONAL SKILLS DEMONSTRATED**: What high-level organizational capabilities are evident?
   - Stakeholder management
   - Cross-functional collaboration
   - Negotiation
   - Strategic planning
   - Change management
   - Risk management
   - Governance
   - Budget/financial oversight
   - Vendor/partner management
   - Matrix organization navigation
   - Global/regional coordination

4. **LEADERSHIP SCOPE**: What was the scope of influence?
   - Budget/financial responsibility (amounts if mentioned)
   - Team size (direct/indirect reports)
   - Geographic reach (countries, regions)
   - Strategic vs. tactical focus
   - Project scale (complexity, stakeholders, duration)

5. **CAREER INSIGHTS**: What does this tell us about career progression?
   - Level of autonomy
   - Decision-making authority
   - Exposure to C-suite
   - Strategic vs. operational balance
   - Growth trajectory

Provide structured JSON output with these exact fields:
{
  "period": "YYYY - YYYY",
  "organization": "Company Name",
  "stakeholder_levels": {
    "c_level": ["specific titles"],
    "directors_vps": ["functions"],
    "managers": ["departments"],
    "end_users": true/false
  },
  "functions_involved": ["Legal", "IT", ...],
  "organizational_skills": ["Stakeholder management", ...],
  "leadership_scope": {
    "budget_responsibility": "€X million" or null,
    "team_size": "X people" or null,
    "geographic_reach": "description",
    "strategic_focus": "high/medium/low",
    "decision_authority": "description"
  },
  "career_insights": {
    "seniority_level": "IC/Manager/Director/VP/C-level",
    "c_suite_exposure": "high/medium/low",
    "strategic_operational_balance": "80/20" (example),
    "unique_aspects": ["description"],
    "progression_indicators": ["description"]
  }
}',
    900,  -- 15 minutes timeout
    true
);

-- Instruction 2: Technical Skills
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    enabled
) VALUES (
    'Extract technical skills from full career',
    conv2_id,
    1,
    'Extract tools, technologies, methodologies, and standards',
    E'Extract technical skills from this career history.

FULL CAREER HISTORY:
{career_text}

Focus on ACTUALLY DEMONSTRATED skills (not aspirational). Extract:

1. **SOFTWARE/TOOLS**: Specific applications used
   - Enterprise software (SAP, ServiceNow, etc.)
   - Office tools (Excel, PowerPoint, Word, etc.)
   - Database tools (SQL clients, reporting tools)
   - Collaboration tools (SharePoint, Teams, etc.)

2. **TECHNICAL COMPETENCIES**: 
   - Data analysis
   - Process automation
   - System integration
   - Reporting/visualization
   - Technical documentation

3. **METHODOLOGIES/FRAMEWORKS**:
   - Agile/Scrum
   - ITIL
   - Six Sigma
   - Project management methodologies

4. **STANDARDS/REGULATIONS**:
   - GDPR
   - SOX (Sarbanes-Oxley)
   - ISO standards
   - Industry-specific compliance

5. **DOMAIN KNOWLEDGE**:
   - Software licensing
   - Telecom
   - Cloud services
   - Contract management
   - Vendor management

Provide structured output:
{
  "tools": [
    {"name": "Tool Name", "category": "Enterprise Software", "proficiency": "expert/advanced/intermediate"}
  ],
  "competencies": [
    {"name": "Competency", "description": "brief context from career"}
  ],
  "methodologies": ["Agile", "ITIL", ...],
  "standards": ["GDPR", "SOX", ...],
  "domains": ["Software Licensing", ...]
}',
    600,  -- 10 minutes
    true
);

-- Instruction 3: Soft Skills
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    enabled
) VALUES (
    'Extract soft skills and interpersonal competencies',
    conv3_id,
    1,
    'Identify communication, leadership, analytical, and personal skills',
    E'Extract soft skills from this career history.

FULL CAREER HISTORY:
{career_text}

Identify DEMONSTRATED soft skills (not aspirational claims). Provide WHY for each.

Categories:
1. **COMMUNICATION**: Written, verbal, presentation, cross-cultural, stakeholder communication
2. **INTERPERSONAL**: Relationship building, collaboration, conflict resolution, empathy
3. **LEADERSHIP**: Team leadership, mentoring, delegation, vision setting, change leadership
4. **ANALYTICAL**: Problem-solving, critical thinking, data-driven decision making, strategic analysis
5. **PERSONAL**: Adaptability, resilience, self-motivation, attention to detail, time management

For each skill provide:
- Skill name
- Category
- Evidence (specific example from career history)
- Level (demonstrated consistently / occasionally evident)

Output format:
{
  "communication_skills": [
    {"skill": "Stakeholder Communication", "evidence": "brief quote or reference", "level": "consistent"}
  ],
  "interpersonal_skills": [...],
  "leadership_skills": [...],
  "analytical_skills": [...],
  "personal_skills": [...]
}',
    600,  -- 10 minutes
    true
);

-- Instruction 4: Synthesis
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    enabled
) VALUES (
    'Synthesize career analysis into comprehensive report',
    conv4_id,
    1,
    'Create markdown report combining all analysis',
    E'Create a comprehensive career analysis report in markdown format.

ORGANIZATIONAL ANALYSIS (per period):
{session_1_output}

TECHNICAL SKILLS:
{session_2_output}

SOFT SKILLS:
{session_3_output}

PROFILE SUMMARY (from workflow 1122 if available):
{profile_summary}

Create a structured markdown report with:

# Career Analysis Report: {profile_name}

## Executive Summary
- Career span and organizations
- Key themes and unique value proposition
- Target role positioning

## Organizational Analysis by Period
For each career period:
- Period and organization
- Stakeholder engagement summary
- Key organizational skills
- Leadership scope highlights

## Cross-Period Insights
- Stakeholder patterns (progression to higher levels?)
- Skill evolution (what deepened over time?)
- Leadership trajectory
- Strategic vs operational balance over time

## Technical Skills Summary
- Core tools and technologies
- Methodologies and frameworks
- Domain expertise areas
- Standards/compliance knowledge

## Soft Skills Profile
- Communication strengths
- Leadership style
- Analytical capabilities
- Interpersonal competencies

## Career Positioning
- Unique skill combinations
- C-level credibility
- Financial impact (if measurable)
- Global/enterprise scale experience

## Target Role Recommendations
Based on this analysis, suggest 3-5 ideal role types with reasoning.

Format: Clean markdown, professional tone, data-driven insights.',
    600,  -- 10 minutes
    true
);

-- ============================================================================
-- STEP 3: Create Workflow
-- ============================================================================

INSERT INTO workflows (
    workflow_id,
    workflow_name,
    workflow_description,
    max_total_session_runs,
    enabled,
    documentation
) VALUES (
    1125,
    'Profile Career Deep Analysis',
    'Multi-model ensemble for deep career analysis. Extracts organizational dynamics, stakeholder patterns, technical/soft skills, and generates comprehensive career reports. Complements workflow 1122 (profile_skill_extraction) for job matching.',
    150,  -- Total conversation runs across all conversations
    true,
    E'# Workflow 1125: Profile Career Deep Analysis

## Purpose
Provides deep organizational analysis of career histories using a multi-model ensemble approach. Goes beyond basic skill extraction (workflow 1122) to understand stakeholder engagement, organizational dynamics, leadership scope, and career progression patterns.

## Use Cases
- Job matching: Links to skill_aliases via profile_skills table
- Career coaching: Understand progression and positioning
- Talent assessment: Map organizational capabilities
- Resume optimization: Highlight C-level engagement and strategic impact

## Input
- Profile ID (loads from profiles table)
- OR career text file

## Output
- career_analyses table (JSONB fields for querying)
- Markdown report (comprehensive career analysis)
- Links to profile_skills for job matching via skill_aliases

## Workflow Steps
1. **Organizational Analysis** (per period, parallel): DeepSeek-R1 analyzes stakeholder levels, functions, org skills
2. **Technical Skills**: Qwen2.5 extracts tools, methodologies, standards
3. **Soft Skills**: Olmo2 identifies communication, leadership, analytical skills
4. **Synthesis**: Qwen2.5 creates comprehensive markdown report

## Integration with Skill Matching
- Workflow 1122 extracts skills → profile_skills → skill_aliases
- Workflow 1121 extracts job skills → job_skills → skill_aliases
- Matching happens via skill_aliases.skill_id + skill_hierarchy
- Workflow 1125 provides deeper context for match quality assessment

## Model Selection Rationale
- **DeepSeek-R1**: Exceptional reasoning for organizational dynamics
- **Qwen2.5**: Practical skill extraction, avoids over-engineering
- **Olmo2**: Structured soft skill categorization with evidence
- **Qwen2.5 (synthesis)**: Fast local model for report generation

## Performance
- Execution time: 40-70 minutes for 30-year career
- Chunking strategy: Automatic career period detection
- Timeout: 15 min per model/chunk'
);

-- ============================================================================
-- STEP 4: Link Conversations to Workflow
-- ============================================================================

-- Link conversation 1: Organizational analysis
INSERT INTO workflow_conversations (
    1125,
    conversation_id,
    execution_order,
    execute_condition,
    on_success_action,
    on_failure_action,
    max_retry_attempts,
    parallel_group,
    wait_for_group
) VALUES (
    1125,
    conv1_id,
    1,
    'always',
    'continue',
    'stop',
    1,
    1,  -- All chunks can run in parallel
    false  -- Don't wait for this group before starting next
);

-- Link conversation 2: Technical skills (can start while org analysis runs)
INSERT INTO workflow_conversations (
    1125,
    conversation_id,
    execution_order,
    execute_condition,
    on_success_action,
    on_failure_action,
    max_retry_attempts,
    parallel_group,
    wait_for_group
) VALUES (
    1125,
    conv2_id,
    2,
    'always',
    'continue',
    'stop',
    1,
    NULL,  -- Not in parallel group
    false
);

-- Link conversation 3: Soft skills
INSERT INTO workflow_conversations (
    1125,
    conversation_id,
    execution_order,
    execute_condition,
    on_success_action,
    on_failure_action,
    max_retry_attempts,
    parallel_group,
    wait_for_group
) VALUES (
    1125,
    conv3_id,
    3,
    'always',
    'continue',
    'stop',
    1,
    NULL,
    false
);

-- Link conversation 4: Synthesis (must wait for all previous)
INSERT INTO workflow_conversations (
    1125,
    conversation_id,
    execution_order,
    execute_condition,
    on_success_action,
    on_failure_action,
    max_retry_attempts,
    parallel_group,
    wait_for_group
) VALUES (
    1125,
    conv4_id,
    4,
    'always',  -- Only runs if previous succeeded
    'stop',
    'stop',
    1,
    NULL,
    true  -- Wait for all previous parallel groups
);

END $$;

-- ============================================================================
-- STEP 5: Verification
-- ============================================================================

-- Verify workflow created
SELECT 
    w.workflow_id,
    w.workflow_name,
    COUNT(wc.step_id) as conversation_count
FROM workflows w
LEFT JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
WHERE w.workflow_id = 1125
GROUP BY w.workflow_id, w.workflow_name;

-- Verify conversations and instructions
SELECT 
    w.workflow_name,
    wc.execution_order,
    c.conversation_name,
    a.actor_name,
    i.instruction_name,
    i.timeout_seconds
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN instructions i ON c.conversation_id = i.conversation_id
WHERE w.workflow_id = 1125
ORDER BY wc.execution_order, i.step_number;

COMMIT;

-- ============================================================================
-- Usage Example
-- ============================================================================
-- Run via recipe_1122_runner.py (will be renamed to workflow_1123_runner.py):
--   python3 scripts/workflow_1123_runner.py --profile-id 1
--
-- Results stored in:
--   - career_analyses table (queryable via JSONB fields)
--   - Links to profile_skills for job matching
--   - Markdown report in analysis_markdown field
-- ============================================================================
