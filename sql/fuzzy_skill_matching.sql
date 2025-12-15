-- =====================================================================
-- FUZZY SKILL MATCHING FUNCTIONS
-- =====================================================================
-- Purpose: Calculate skill similarity scores using hierarchy relationships
-- Use case: "Client wants Oracle, candidate has PostgreSQL" → not 0, partial match
--
-- Created: 2025-11-07
-- Author: GitHub Copilot + xai
-- =====================================================================

-- =====================================================================
-- 1. Find shortest path between two skills in hierarchy
-- =====================================================================
-- Returns: path length and relationship type (parent/child/sibling/exact)
-- Example: find_skill_path(postgresql_id, oracle_id) → distance=2, type='sibling'
--
CREATE OR REPLACE FUNCTION find_skill_path(
    skill_a INTEGER,
    skill_b INTEGER,
    max_depth INTEGER DEFAULT 5
)
RETURNS TABLE (
    path_length INTEGER,
    relationship_type TEXT,
    common_ancestor INTEGER,  -- The shared parent (if sibling match)
    path_strength NUMERIC      -- Product of strength values along path
) AS $$
DECLARE
    v_path_length INTEGER;
    v_relationship TEXT;
    v_ancestor INTEGER;
    v_strength NUMERIC;
BEGIN
    -- Case 1: Exact match
    IF skill_a = skill_b THEN
        RETURN QUERY SELECT 0, 'exact'::TEXT, NULL::INTEGER, 1.0::NUMERIC;
        RETURN;
    END IF;
    
    -- Case 2: Direct parent (A is parent of B)
    SELECT 1, 'parent', skill_a, strength
    INTO v_path_length, v_relationship, v_ancestor, v_strength
    FROM skill_hierarchy
    WHERE skill_id = skill_b AND parent_skill_id = skill_a;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_path_length, v_relationship, v_ancestor, v_strength;
        RETURN;
    END IF;
    
    -- Case 3: Direct child (A is child of B)
    SELECT 1, 'child', skill_b, strength
    INTO v_path_length, v_relationship, v_ancestor, v_strength
    FROM skill_hierarchy
    WHERE skill_id = skill_a AND parent_skill_id = skill_b;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_path_length, v_relationship, v_ancestor, v_strength;
        RETURN;
    END IF;
    
    -- Case 4: Siblings (share common parent)
    -- Find common parent with shortest combined distance
    WITH common_parents AS (
        SELECT 
            h1.parent_skill_id as common_parent,
            h1.strength * h2.strength as combined_strength,
            2 as distance  -- 1 hop up + 1 hop down = 2
        FROM skill_hierarchy h1
        JOIN skill_hierarchy h2 ON h1.parent_skill_id = h2.parent_skill_id
        WHERE h1.skill_id = skill_a 
          AND h2.skill_id = skill_b
    )
    SELECT distance, 'sibling', common_parent, combined_strength
    INTO v_path_length, v_relationship, v_ancestor, v_strength
    FROM common_parents
    ORDER BY combined_strength DESC, common_parent
    LIMIT 1;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_path_length, v_relationship, v_ancestor, v_strength;
        RETURN;
    END IF;
    
    -- Case 5: Deeper relationship (BFS through hierarchy up to max_depth)
    -- This gets complex - for now, return "unrelated"
    -- TODO: Implement full graph traversal if needed
    
    RETURN QUERY SELECT NULL::INTEGER, 'unrelated'::TEXT, NULL::INTEGER, 0.0::NUMERIC;
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- 2. Calculate skill match score
-- =====================================================================
-- Given: job requires skill_a with weight X, candidate has skill_b
-- Returns: match score based on relationship
--
-- Scoring algorithm (from xai):
--   - Exact match: full weight
--   - Parent/child: weight * (1 / distance) OR weight * 0.7 per level
--   - Sibling: weight * (strength / distance)
--   - Unrelated: 0
--
CREATE OR REPLACE FUNCTION calculate_skill_match_score(
    job_skill_id INTEGER,      -- Required skill ID
    candidate_skill_id INTEGER, -- Candidate's skill ID
    job_weight INTEGER,         -- Importance weight (10-100)
    decay_mode TEXT DEFAULT 'reciprocal'  -- 'reciprocal' or 'exponential'
)
RETURNS TABLE (
    match_score NUMERIC,
    match_type TEXT,
    distance INTEGER,
    explanation TEXT
) AS $$
DECLARE
    v_path RECORD;
    v_score NUMERIC;
    v_explanation TEXT;
BEGIN
    -- Find path between skills
    SELECT * INTO v_path
    FROM find_skill_path(job_skill_id, candidate_skill_id, 5);
    
    -- Calculate score based on relationship type
    CASE v_path.relationship_type
        WHEN 'exact' THEN
            v_score := job_weight;
            v_explanation := 'Exact match';
            
        WHEN 'parent' THEN
            -- Candidate has more general skill (e.g., has "databases" when job wants "PostgreSQL")
            IF decay_mode = 'exponential' THEN
                v_score := job_weight * POWER(0.7, v_path.path_length);
                v_explanation := format('Parent skill (70%% per level, %s levels up)', v_path.path_length);
            ELSE
                v_score := job_weight * (1.0 / v_path.path_length) * v_path.path_strength;
                v_explanation := format('Parent skill (reciprocal distance=%s, strength=%s)', 
                                       v_path.path_length, v_path.path_strength);
            END IF;
            
        WHEN 'child' THEN
            -- Candidate has more specific skill (e.g., has "PostgreSQL" when job wants "databases")
            -- This is actually BETTER than exact match in many cases!
            v_score := job_weight * 1.1 * v_path.path_strength;  -- 10% bonus for specificity
            v_explanation := format('Child skill (more specific, +10%% bonus, strength=%s)', 
                                   v_path.path_strength);
            
        WHEN 'sibling' THEN
            -- Related skills through common parent (e.g., PostgreSQL ↔ MySQL via "databases")
            IF decay_mode = 'exponential' THEN
                v_score := job_weight * POWER(0.7, v_path.path_length);
                v_explanation := format('Sibling skill (70%% per level, %s levels total)', 
                                       v_path.path_length);
            ELSE
                v_score := job_weight * (v_path.path_strength / v_path.path_length);
                v_explanation := format('Sibling skill (strength=%s / distance=%s)', 
                                       v_path.path_strength, v_path.path_length);
            END IF;
            
        ELSE  -- 'unrelated'
            v_score := 0;
            v_explanation := 'No relationship found in hierarchy';
    END CASE;
    
    RETURN QUERY SELECT 
        v_score,
        v_path.relationship_type,
        v_path.path_length,
        v_explanation;
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- 3. Match candidate profile to job posting (FULL MATCHING)
-- =====================================================================
-- Compares ALL job requirements against ALL candidate skills
-- Returns: total score, matched skills, missing skills
--
CREATE OR REPLACE FUNCTION match_profile_to_job(
    p_profile_id INTEGER,
    p_posting_id INTEGER,
    p_decay_mode TEXT DEFAULT 'reciprocal'
)
RETURNS TABLE (
    total_score NUMERIC,
    max_possible_score NUMERIC,
    match_percentage NUMERIC,
    matched_skills_count INTEGER,
    required_skills_count INTEGER,
    skill_matches JSONB  -- Detailed breakdown
) AS $$
DECLARE
    v_total_score NUMERIC := 0;
    v_max_score NUMERIC := 0;
    v_matched_count INTEGER := 0;
    v_required_count INTEGER;
    v_matches JSONB := '[]'::JSONB;
    v_job_skill RECORD;
    v_candidate_skill RECORD;
    v_best_match RECORD;
BEGIN
    -- Count required skills
    SELECT COUNT(*) INTO v_required_count
    FROM posting_skills
    WHERE posting_id = p_posting_id;
    
    -- For each required skill in job
    FOR v_job_skill IN 
        SELECT ps.skill_id, ps.weight, ps.importance, sa.skill_name
        FROM posting_skills ps
        JOIN skill_aliases sa ON ps.skill_id = sa.skill_id
        WHERE ps.posting_id = p_posting_id
    LOOP
        v_max_score := v_max_score + v_job_skill.weight;
        
        -- Find best matching candidate skill
        SELECT 
            ms.match_score,
            ms.match_type,
            ms.distance,
            ms.explanation,
            sa.skill_name as candidate_skill_name,
            ps.proficiency_level,
            ps.years_experience
        INTO v_best_match
        FROM profile_skills ps
        JOIN skill_aliases sa ON ps.skill_id = sa.skill_id
        CROSS JOIN LATERAL calculate_skill_match_score(
            v_job_skill.skill_id,
            ps.skill_id,
            v_job_skill.weight,
            p_decay_mode
        ) ms
        WHERE ps.profile_id = p_profile_id
        ORDER BY ms.match_score DESC
        LIMIT 1;
        
        IF FOUND AND v_best_match.match_score > 0 THEN
            v_total_score := v_total_score + v_best_match.match_score;
            v_matched_count := v_matched_count + 1;
            
            -- Add to matches array
            v_matches := v_matches || jsonb_build_object(
                'required_skill', v_job_skill.skill_name,
                'candidate_skill', v_best_match.candidate_skill_name,
                'match_score', v_best_match.match_score,
                'max_score', v_job_skill.weight,
                'match_type', v_best_match.match_type,
                'distance', v_best_match.distance,
                'explanation', v_best_match.explanation,
                'importance', v_job_skill.importance,
                'proficiency', v_best_match.proficiency_level,
                'years_experience', v_best_match.years_experience
            );
        ELSE
            -- No match found
            v_matches := v_matches || jsonb_build_object(
                'required_skill', v_job_skill.skill_name,
                'candidate_skill', NULL,
                'match_score', 0,
                'max_score', v_job_skill.weight,
                'match_type', 'missing',
                'importance', v_job_skill.importance
            );
        END IF;
    END LOOP;
    
    RETURN QUERY SELECT 
        v_total_score,
        v_max_score,
        CASE WHEN v_max_score > 0 THEN (v_total_score / v_max_score) * 100 ELSE 0 END,
        v_matched_count,
        v_required_count,
        v_matches;
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- USAGE EXAMPLES
-- =====================================================================

-- Example 1: Find path between two skills
-- SELECT * FROM find_skill_path(
--     (SELECT skill_id FROM skill_aliases WHERE skill_name = 'postgresql'),
--     (SELECT skill_id FROM skill_aliases WHERE skill_name = 'mysql')
-- );

-- Example 2: Calculate match score for specific skills
-- SELECT * FROM calculate_skill_match_score(
--     (SELECT skill_id FROM skill_aliases WHERE skill_name = 'oracle'),
--     (SELECT skill_id FROM skill_aliases WHERE skill_name = 'postgresql'),
--     80,  -- job weight
--     'exponential'
-- );

-- Example 3: Full profile-to-job matching
-- SELECT * FROM match_profile_to_job(
--     1,  -- profile_id
--     2,  -- posting_id
--     'reciprocal'
-- );

-- Example 4: Find top matching candidates for a job
-- SELECT 
--     p.profile_id,
--     p.full_name,
--     m.match_percentage,
--     m.matched_skills_count,
--     m.required_skills_count,
--     m.total_score,
--     m.skill_matches
-- FROM profiles p
-- CROSS JOIN LATERAL match_profile_to_job(p.profile_id, 2, 'reciprocal') m
-- WHERE m.match_percentage > 50
-- ORDER BY m.match_percentage DESC
-- LIMIT 10;
