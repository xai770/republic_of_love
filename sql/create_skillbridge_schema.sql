-- ============================================================================
-- SkillBridge Schema: Hierarchical Skill Taxonomy with Synonym Mapping
-- Created: 2025-10-26
-- Purpose: Core tables for SkillBridge skill matching system
-- ============================================================================

-- Based on: 
--   - Gershon's vendor invoice mapping pattern (synonym handling)
--   - Facets table structure (hierarchical parent_id)
--   - Recipe 1114/1120 integration (job extraction → skill matching)

-- ============================================================================
-- TABLE 1: skills (The Canonical Catalog)
-- ============================================================================

CREATE TABLE IF NOT EXISTS skills (
    skill_id SERIAL PRIMARY KEY,
    skill_name TEXT UNIQUE NOT NULL,          -- Canonical name (e.g., "Kubernetes")
    parent_skill_id INT REFERENCES skills(skill_id),  -- Hierarchical: NULL = root level
    level INT NOT NULL,                       -- 1=Category, 2=Subcategory, 3=Specific, etc.
    description TEXT,                         -- What this skill means
    enabled BOOLEAN DEFAULT TRUE,             -- Active in taxonomy?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_skills_parent ON skills(parent_skill_id);
CREATE INDEX IF NOT EXISTS idx_skills_level ON skills(level);
CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_skills_name_lower ON skills(LOWER(skill_name));

-- Comments
COMMENT ON TABLE skills IS 
'Hierarchical skill taxonomy. The heart of SkillBridge - without accurate skill taxonomy, no meaningful job-candidate matching is possible.';

COMMENT ON COLUMN skills.parent_skill_id IS 
'Self-referencing hierarchy. NULL = root level (e.g., "Technical Skills"). Allows unlimited depth.';

COMMENT ON COLUMN skills.level IS 
'Hierarchy depth: 1=Category (Technical/Soft), 2=Subcategory (Cloud/Programming), 3=Specific (Kubernetes/Python), etc.';

-- ============================================================================
-- TABLE 2: skill_synonyms (Fuzzy Matching Layer - Invoice Pattern)
-- ============================================================================

CREATE TABLE IF NOT EXISTS skill_synonyms (
    synonym_id SERIAL PRIMARY KEY,
    synonym_text TEXT NOT NULL,               -- "K8s", "k8", "kube", "kubernetes"
    canonical_skill_id INT REFERENCES skills(skill_id) NOT NULL,
    confidence FLOAT DEFAULT 1.0,             -- 1.0 = human verified, <1.0 = LLM suggested
    source TEXT,                              -- 'human', 'olmo2:7b', 'gemma3:1b', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by TEXT,                         -- Username if human-approved
    review_notes TEXT,                        -- Why this mapping was made
    
    UNIQUE(synonym_text, canonical_skill_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_synonyms_text_lower ON skill_synonyms(LOWER(synonym_text));
CREATE INDEX IF NOT EXISTS idx_synonyms_canonical ON skill_synonyms(canonical_skill_id);
CREATE INDEX IF NOT EXISTS idx_synonyms_confidence ON skill_synonyms(confidence) WHERE confidence < 0.7;

-- Comments
COMMENT ON TABLE skill_synonyms IS 
'Synonym mapping for fuzzy skill matching. Inspired by Gershon''s vendor invoice mapping: name_on_invoice → canonical_name. After 3-4 months of curation, achieves 90%+ automatic matching.';

COMMENT ON COLUMN skill_synonyms.confidence IS 
'1.0 = human verified (gold standard), 0.7-0.9 = LLM high confidence (auto-add), <0.7 = requires human review';

-- ============================================================================
-- TABLE 3: profile_skills (CV Parsing Output)
-- ============================================================================

CREATE TABLE IF NOT EXISTS profile_skills (
    profile_skill_id SERIAL PRIMARY KEY,
    profile_id INT NOT NULL,                  -- References profiles/users table (to be created)
    skill_id INT REFERENCES skills(skill_id) NOT NULL,
    years_experience FLOAT,                   -- 3.5 years
    proficiency_level TEXT,                   -- 'beginner', 'intermediate', 'expert', 'master'
    is_implicit BOOLEAN DEFAULT FALSE,        -- Derived via inference (not explicitly stated)
    derivation_reason TEXT,                   -- "Inferred from: Senior Python Developer = Python expert"
    last_used_date DATE,                      -- When last used this skill
    evidence_text TEXT,                       -- Quote from CV where skill appears
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(profile_id, skill_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_profile_skills_profile ON profile_skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_skills_skill ON profile_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_profile_skills_implicit ON profile_skills(is_implicit);
CREATE INDEX IF NOT EXISTS idx_profile_skills_proficiency ON profile_skills(proficiency_level);

-- Comments
COMMENT ON TABLE profile_skills IS 
'Candidate/CV skills parsed and normalized to canonical taxonomy. Includes explicit skills (stated) and implicit skills (derived).';

COMMENT ON COLUMN profile_skills.is_implicit IS 
'TRUE = derived via inference rules. Examples: (1) Hierarchical: has "Kubernetes" → implies "Container Orchestration". (2) Common sense: "Traveling Salesman" → implies "Driver''s License".';

COMMENT ON COLUMN profile_skills.derivation_reason IS 
'Audit trail for implicit skills. LLM explanation or rule name that generated this inference.';

-- ============================================================================
-- TABLE 4: job_skills (Posting Requirements)
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_skills (
    job_skill_id SERIAL PRIMARY KEY,
    job_id TEXT REFERENCES postings(job_id) NOT NULL,
    skill_id INT REFERENCES skills(skill_id) NOT NULL,
    required BOOLEAN DEFAULT TRUE,            -- vs. "nice to have"
    min_years_experience INT,                 -- Minimum required
    mentioned_count INT DEFAULT 1,            -- How many times in posting?
    context_snippet TEXT,                     -- Where it appeared in posting
    extracted_by TEXT,                        -- 'recipe_1120', 'manual', etc.
    recipe_run_id INT REFERENCES recipe_runs(recipe_run_id),  -- Audit trail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(job_id, skill_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_job_skills_job ON job_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_required ON job_skills(required) WHERE required = TRUE;
CREATE INDEX IF NOT EXISTS idx_job_skills_recipe ON job_skills(recipe_run_id);

-- Comments
COMMENT ON TABLE job_skills IS 
'Skills required by job postings, extracted via Recipe 1120 and normalized to canonical taxonomy. Links postings → skills for matching.';

COMMENT ON COLUMN job_skills.mentioned_count IS 
'Frequency tracking. "Python" mentioned 5 times = higher importance than skill mentioned once.';

-- ============================================================================
-- TABLE 5: skill_inference_rules (Implicit Skill Derivation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS skill_inference_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name TEXT UNIQUE NOT NULL,           -- "hierarchical_parent_inference"
    rule_type TEXT NOT NULL,                  -- 'hierarchical', 'common_sense', 'llm_powered'
    source_skill_id INT REFERENCES skills(skill_id),  -- If has this skill...
    inferred_skill_id INT REFERENCES skills(skill_id),  -- ...then also has this
    confidence FLOAT DEFAULT 0.8,             -- How confident in this inference?
    rule_description TEXT,                    -- Human-readable explanation
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(source_skill_id, inferred_skill_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_inference_rules_source ON skill_inference_rules(source_skill_id);
CREATE INDEX IF NOT EXISTS idx_inference_rules_inferred ON skill_inference_rules(inferred_skill_id);
CREATE INDEX IF NOT EXISTS idx_inference_rules_enabled ON skill_inference_rules(enabled) WHERE enabled = TRUE;

-- Comments
COMMENT ON TABLE skill_inference_rules IS 
'Rules for deriving implicit skills. Types: (1) Hierarchical = parent propagation, (2) Common sense = domain knowledge, (3) LLM-powered = contextual inference.';

COMMENT ON COLUMN skill_inference_rules.rule_type IS 
'hierarchical: Has "Kubernetes" → implies all parents. common_sense: "Traveling Salesman" → "Driver''s License". llm_powered: Ask LLM for context-specific inference.';

-- ============================================================================
-- VIEW: v_skill_hierarchy (Flatten tree for queries)
-- ============================================================================

CREATE OR REPLACE VIEW v_skill_hierarchy AS
WITH RECURSIVE skill_tree AS (
    -- Base: root skills (no parent)
    SELECT 
        skill_id,
        skill_name,
        parent_skill_id,
        level,
        skill_name::TEXT as skill_path,
        ARRAY[skill_id] as skill_path_ids
    FROM skills
    WHERE parent_skill_id IS NULL
    
    UNION ALL
    
    -- Recursive: children
    SELECT 
        s.skill_id,
        s.skill_name,
        s.parent_skill_id,
        s.level,
        st.skill_path || ' → ' || s.skill_name,
        st.skill_path_ids || s.skill_id
    FROM skills s
    JOIN skill_tree st ON s.parent_skill_id = st.skill_id
)
SELECT * FROM skill_tree
ORDER BY skill_path;

COMMENT ON VIEW v_skill_hierarchy IS 
'Flattened skill hierarchy with full paths. Example: "Technical Skills → Cloud Infrastructure → Container Orchestration → Kubernetes"';

-- ============================================================================
-- VIEW: v_pending_synonyms (Monthly Review Dashboard)
-- ============================================================================

CREATE OR REPLACE VIEW v_pending_synonyms AS
SELECT 
    ss.synonym_id,
    ss.synonym_text,
    s.skill_name as suggested_canonical,
    ss.confidence,
    ss.source,
    ss.created_at,
    COUNT(*) OVER (PARTITION BY ss.synonym_text) as appearances
FROM skill_synonyms ss
JOIN skills s ON ss.canonical_skill_id = s.skill_id
WHERE ss.confidence < 0.7  -- Requires review
  AND ss.reviewed_by IS NULL
ORDER BY appearances DESC, ss.created_at ASC;

COMMENT ON VIEW v_pending_synonyms IS 
'Monthly review dashboard: synonyms requiring human approval. Sorted by frequency (high appearances = prioritize first).';

-- ============================================================================
-- SAMPLE DATA: Bootstrap taxonomy
-- ============================================================================

-- Level 1: Root categories
INSERT INTO skills (skill_name, parent_skill_id, level, description) VALUES
('Technical Skills', NULL, 1, 'All technical/hard skills'),
('Soft Skills', NULL, 1, 'Interpersonal and communication skills'),
('Domain Knowledge', NULL, 1, 'Industry-specific expertise')
ON CONFLICT (skill_name) DO NOTHING;

-- Level 2: Technical subcategories
INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Programming Languages', skill_id, 2, 'Software development languages'
FROM skills WHERE skill_name = 'Technical Skills'
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Cloud & Infrastructure', skill_id, 2, 'Cloud platforms and infrastructure'
FROM skills WHERE skill_name = 'Technical Skills'
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Databases', skill_id, 2, 'Database systems and technologies'
FROM skills WHERE skill_name = 'Technical Skills'
ON CONFLICT (skill_name) DO NOTHING;

-- Level 3: Specific technical skills
INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Python', skill_id, 3, 'Python programming language'
FROM skills WHERE skill_name = 'Programming Languages'
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'JavaScript', skill_id, 3, 'JavaScript programming language'
FROM skills WHERE skill_name = 'Programming Languages'
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Container Orchestration', skill_id, 3, 'Container management platforms'
FROM skills WHERE skill_name = 'Cloud & Infrastructure'
ON CONFLICT (skill_name) DO NOTHING;

-- Level 4: Ultra-specific skills
INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Kubernetes', skill_id, 4, 'Container orchestration platform'
FROM skills WHERE skill_name = 'Container Orchestration'
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Docker', skill_id, 4, 'Container runtime platform'
FROM skills WHERE skill_name = 'Container Orchestration'
ON CONFLICT (skill_name) DO NOTHING;

-- Level 2: Soft skills subcategories
INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Communication', skill_id, 2, 'Verbal and written communication'
FROM skills WHERE skill_name = 'Soft Skills'
ON CONFLICT (skill_name) DO NOTHING;

INSERT INTO skills (skill_name, parent_skill_id, level, description)
SELECT 'Leadership', skill_id, 2, 'Team leadership and management'
FROM skills WHERE skill_name = 'Soft Skills'
ON CONFLICT (skill_name) DO NOTHING;

-- Sample synonyms (human-verified, confidence=1.0)
INSERT INTO skill_synonyms (synonym_text, canonical_skill_id, confidence, source, reviewed_by)
SELECT 'K8s', skill_id, 1.0, 'human', 'gershon'
FROM skills WHERE skill_name = 'Kubernetes'
ON CONFLICT (synonym_text, canonical_skill_id) DO NOTHING;

INSERT INTO skill_synonyms (synonym_text, canonical_skill_id, confidence, source, reviewed_by)
SELECT 'k8', skill_id, 1.0, 'human', 'gershon'
FROM skills WHERE skill_name = 'Kubernetes'
ON CONFLICT (synonym_text, canonical_skill_id) DO NOTHING;

INSERT INTO skill_synonyms (synonym_text, canonical_skill_id, confidence, source, reviewed_by)
SELECT 'kube', skill_id, 0.95, 'olmo2:7b', NULL
FROM skills WHERE skill_name = 'Kubernetes'
ON CONFLICT (synonym_text, canonical_skill_id) DO NOTHING;

INSERT INTO skill_synonyms (synonym_text, canonical_skill_id, confidence, source, reviewed_by)
SELECT 'py', skill_id, 0.85, 'phi3:latest', NULL
FROM skills WHERE skill_name = 'Python'
ON CONFLICT (synonym_text, canonical_skill_id) DO NOTHING;

-- Sample inference rules (hierarchical parent propagation)
INSERT INTO skill_inference_rules (rule_name, rule_type, source_skill_id, inferred_skill_id, confidence, rule_description)
SELECT 
    'kubernetes_implies_container_orchestration',
    'hierarchical',
    k.skill_id,
    co.skill_id,
    1.0,
    'Having Kubernetes skill implies Container Orchestration knowledge'
FROM skills k
CROSS JOIN skills co
WHERE k.skill_name = 'Kubernetes' 
  AND co.skill_name = 'Container Orchestration'
ON CONFLICT (source_skill_id, inferred_skill_id) DO NOTHING;

INSERT INTO skill_inference_rules (rule_name, rule_type, source_skill_id, inferred_skill_id, confidence, rule_description)
SELECT 
    'container_orchestration_implies_cloud',
    'hierarchical',
    co.skill_id,
    ci.skill_id,
    1.0,
    'Container Orchestration implies Cloud & Infrastructure knowledge'
FROM skills co
CROSS JOIN skills ci
WHERE co.skill_name = 'Container Orchestration' 
  AND ci.skill_name = 'Cloud & Infrastructure'
ON CONFLICT (source_skill_id, inferred_skill_id) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- 1. Show full hierarchy
SELECT * FROM v_skill_hierarchy ORDER BY skill_path;

-- 2. Show all synonyms
SELECT 
    s.skill_name,
    ss.synonym_text,
    ss.confidence,
    ss.source,
    ss.reviewed_by
FROM skill_synonyms ss
JOIN skills s ON ss.canonical_skill_id = s.skill_id
ORDER BY s.skill_name, ss.confidence DESC;

-- 3. Show inference rules
SELECT 
    sir.rule_name,
    sir.rule_type,
    src.skill_name as source_skill,
    inf.skill_name as inferred_skill,
    sir.confidence
FROM skill_inference_rules sir
JOIN skills src ON sir.source_skill_id = src.skill_id
JOIN skills inf ON sir.inferred_skill_id = inf.skill_id
ORDER BY sir.rule_type, src.skill_name;

-- 4. Table counts
SELECT 
    'skills' as table_name, COUNT(*) as row_count FROM skills
UNION ALL
SELECT 'skill_synonyms', COUNT(*) FROM skill_synonyms
UNION ALL
SELECT 'profile_skills', COUNT(*) FROM profile_skills
UNION ALL
SELECT 'job_skills', COUNT(*) FROM job_skills
UNION ALL
SELECT 'skill_inference_rules', COUNT(*) FROM skill_inference_rules;
