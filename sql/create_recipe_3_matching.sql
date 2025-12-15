-- Recipe 3: Profile-Job Matching Engine
-- Weighted skill matching with essential gates and compensatory logic
-- Date: October 29, 2025

-- Insert the recipe
INSERT INTO recipes (recipe_id, recipe_name, description, documentation)
VALUES (
    3,
    'profile_job_matching',
    'Match profiles to jobs using weighted skill scoring, essential gates, and compensatory skill logic',
    'Implements context-aware matching that solves the "MS Office Problem" by weighting skills based on importance. Essential skills act as gates (missing = disqualified), while critical and important skills contribute to weighted score. Outputs match percentage, qualification status, and detailed explanation.'
)
ON CONFLICT (recipe_id) DO UPDATE
SET 
    recipe_name = EXCLUDED.recipe_name,
    description = EXCLUDED.description,
    documentation = EXCLUDED.documentation;

-- Get the canonical code for matching
DO $$ 
DECLARE 
    matching_code_id INTEGER;
BEGIN
    -- Insert or get canonical code for matching
    INSERT INTO canonical_codes (canonical_code, description, category)
    VALUES (
        'profile_job_matching',
        'Weighted matching between profile skills and job requirements',
        'matching'
    )
    ON CONFLICT (canonical_code) DO NOTHING;
    
    SELECT canonical_code_id INTO matching_code_id
    FROM canonical_codes 
    WHERE canonical_code = 'profile_job_matching';
    
    -- Session 1: Calculate weighted match score
    INSERT INTO sessions (
        session_name,
        canonical_code_id,
        actor_id,
        prompt_template_id,
        session_instruction,
        step_number,
        execution_order,
        requires_llm,
        metadata
    )
    SELECT
        'r3_calculate_match_score',
        matching_code_id,
        a.actor_id,
        NULL,  -- No prompt template needed (pure computation)
        'Calculate weighted match score between profile skills and job requirements.

INPUT:
- Profile skills: {profile_skills} (JSONB array from profiles.skill_keywords)
- Job requirements: {job_requirements} (JSONB array from postings.skill_keywords)

ALGORITHM:
1. For each job requirement:
   - Check if skill exists in profile skills
   - If match: add requirement weight to matched_weight
   - If no match: check compensatory skills (TODO: Phase 2)
   
2. Calculate base match score:
   match_percentage = (matched_weight / total_weight) * 100
   
3. Apply essential gate:
   - Identify all requirements where importance = "essential"
   - Check if profile has ALL essential skills
   - If missing ANY essential: cap match_percentage at 25%
   
4. Categorize match quality:
   - HIGH (80-100%): Strong candidate, recommend interview
   - MEDIUM (50-79%): Partial fit, some transferable skills
   - LOW (25-49%): Weak fit, few overlapping skills
   - DISQUALIFIED (<25%): Missing essential requirements

OUTPUT FORMAT (JSON):
{
  "match_percentage": 87.5,
  "match_category": "HIGH",
  "qualified": true,
  "total_requirements": 10,
  "matched_requirements": 8,
  "total_weight": 800,
  "matched_weight": 700,
  "essential_skills_met": 5,
  "essential_skills_total": 5,
  "critical_skills_met": 3,
  "critical_skills_total": 4,
  "important_skills_met": 0,
  "important_skills_total": 1,
  "matched_skills": ["Oracle", "RAC", "Performance_Tuning", ...],
  "missing_essential": [],
  "missing_critical": ["Oracle_Cloud"],
  "missing_important": ["MS_Office"]
}

This session uses pure computation (Python/SQL), not LLM inference.',
        1,
        1,
        FALSE,
        '{"computation_type": "weighted_scoring", "output_type": "json"}'::jsonb
    FROM actors a
    WHERE a.model_name = 'computation'  -- Marker for non-LLM processing
    ON CONFLICT (session_name) DO UPDATE
    SET 
        session_instruction = EXCLUDED.session_instruction,
        execution_order = EXCLUDED.execution_order;
    
    -- Session 2: Generate match explanation (LLM)
    INSERT INTO sessions (
        session_name,
        canonical_code_id,
        actor_id,
        prompt_template_id,
        session_instruction,
        step_number,
        execution_order,
        requires_llm,
        metadata
    )
    SELECT
        'r3_generate_match_explanation',
        matching_code_id,
        a.actor_id,
        NULL,
        'Generate human-readable explanation of the match between profile and job.

INPUT:
- Match score data: {session_1_output} (JSON from Session 1)
- Profile summary: {profile_summary} (from profiles.profile_summary)
- Job description excerpt: {job_title} and {job_requirements}

YOUR TASK:
Analyze the match score and generate a clear, actionable explanation for recruiters.

EXPLANATION STRUCTURE:

1. **MATCH VERDICT** (1-2 sentences):
   - State overall match quality and recommendation
   - Example: "Strong match (87%). Candidate has all essential Oracle DBA skills and extensive hands-on experience. Recommend for interview."

2. **STRENGTHS** (2-4 bullet points):
   - Highlight matched essential and critical skills
   - Note relevant experience or certifications
   - Example: "✅ 5+ years Oracle RAC experience with proven high availability track record"

3. **GAPS** (1-3 bullet points, if any):
   - List missing critical or important skills
   - Assess if gaps are learnable or deal-breakers
   - Example: "⚠️ No Oracle Cloud experience, but strong traditional Oracle background suggests quick ramp-up"

4. **RECOMMENDATIONS** (1-2 sentences):
   - Next steps for recruiter
   - Example: "Schedule technical interview focusing on RAC architecture and performance tuning. Consider asking about cloud migration readiness."

TONE: Professional, concise, actionable. Focus on insights that help hiring decisions.

OUTPUT: Plain text explanation (200-300 words max).',
        1,
        2,
        TRUE,
        '{"model_preference": "qwen2.5:7b", "output_type": "text"}'::jsonb
    FROM actors a
    WHERE a.model_name = 'qwen2.5:7b'
    ON CONFLICT (session_name) DO UPDATE
    SET 
        session_instruction = EXCLUDED.session_instruction,
        execution_order = EXCLUDED.execution_order;
    
    -- Link sessions to recipe with execution order
    INSERT INTO recipe_sessions (recipe_id, session_id, execution_order)
    SELECT 
        3,
        s.session_id,
        s.execution_order
    FROM sessions s
    WHERE s.session_name IN ('r3_calculate_match_score', 'r3_generate_match_explanation')
    ON CONFLICT (recipe_id, session_id) DO UPDATE
    SET execution_order = EXCLUDED.execution_order;
    
    RAISE NOTICE 'Recipe 3 created successfully with 2 sessions';
END $$;

-- Verify creation
SELECT 
    r.recipe_id,
    r.recipe_name,
    COUNT(rs.session_id) as session_count,
    array_agg(s.session_name ORDER BY rs.execution_order) as sessions
FROM recipes r
JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
JOIN sessions s ON rs.session_id = s.session_id
WHERE r.recipe_id = 3
GROUP BY r.recipe_id, r.recipe_name;
