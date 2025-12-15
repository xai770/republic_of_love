-- ============================================================================
-- SkillBridge v2 Schema: Natural Keys + Targeted Relationships
-- Created: 2025-10-27
-- Strategy: Approach 2 (Natural Keys) + Approach 3 Lite (Focused Triples)
-- ============================================================================

-- Drop old schema if migrating (CAREFUL!)
-- DROP TABLE IF EXISTS skill_occurrences CASCADE;
-- DROP TABLE IF EXISTS skill_relationships CASCADE;
-- DROP TABLE IF EXISTS skill_hierarchy CASCADE;
-- DROP TABLE IF EXISTS skill_aliases CASCADE;

-- ============================================================================
-- TABLE 1: skill_aliases - Core lookup table (synonym → canonical)
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_aliases (
    skill_alias TEXT PRIMARY KEY,           -- "python", "python3", "python-programming"
    skill TEXT NOT NULL,                    -- Canonical: "python" (lowercase normalized)
    display_name TEXT,                      -- Pretty: "Python" (for UI display)
    language TEXT DEFAULT 'en',             -- 'en', 'de', 'fr', etc.
    confidence DECIMAL(3,2) DEFAULT 1.0,    -- 1.0 = human verified, <1.0 = LLM suggested
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT,                        -- 'human' or 'llm:qwen2.5:7b'
    notes TEXT
);

-- Unique constraint on canonical skill (required for FK references)
CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_aliases_skill_unique ON skill_aliases(skill);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_skill_aliases_language ON skill_aliases(language);

-- Self-referential: canonical skill points to itself
-- INSERT INTO skill_aliases (skill_alias, skill, display_name) VALUES ('python', 'python', 'Python');

COMMENT ON TABLE skill_aliases IS 'Maps all skill variations to canonical form. Includes self-references for canonical skills.';
COMMENT ON COLUMN skill_aliases.skill_alias IS 'Any variation: lowercase, uppercase, hyphenated, translated, etc.';
COMMENT ON COLUMN skill_aliases.skill IS 'Canonical skill name (lowercase normalized). Used as FK everywhere.';
COMMENT ON COLUMN skill_aliases.display_name IS 'Pretty format for UI display (e.g., "Python", "SQLite", "iShares")';

-- ============================================================================
-- TABLE 2: skill_hierarchy - Parent-child relationships (multi-level)
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_hierarchy (
    skill TEXT NOT NULL,                    -- Child: "python"
    parent_skill TEXT NOT NULL,             -- Parent: "programming_language"
    strength DECIMAL(3,2) DEFAULT 1.0,      -- How strong is this relationship?
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT,
    notes TEXT,
    PRIMARY KEY (skill, parent_skill),
    FOREIGN KEY (skill) REFERENCES skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (parent_skill) REFERENCES skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (skill != parent_skill)           -- Prevent self-loops
);

-- Index for traversing up the tree
CREATE INDEX IF NOT EXISTS idx_skill_hierarchy_skill ON skill_hierarchy(skill);
CREATE INDEX IF NOT EXISTS idx_skill_hierarchy_parent ON skill_hierarchy(parent_skill);

COMMENT ON TABLE skill_hierarchy IS 'Parent-child taxonomy. Supports unlimited depth via recursive queries.';
COMMENT ON COLUMN skill_hierarchy.strength IS 'Weight for matching: 1.0 = strong parent, 0.5 = weak/distant parent';

-- ============================================================================
-- TABLE 3: skill_relationships - Targeted semantic relationships (Approach 3 Lite)
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_relationships (
    subject_skill TEXT NOT NULL,            -- "django"
    relationship_type TEXT NOT NULL,        -- "requires", "alternative_to", "obsoletes"
    object_skill TEXT NOT NULL,             -- "python"
    strength DECIMAL(3,2) DEFAULT 1.0,      -- Weight for matching algorithms
    source TEXT,                            -- 'expert_curated', 'llm_suggested', 'data_mined'
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT,
    notes TEXT,
    PRIMARY KEY (subject_skill, relationship_type, object_skill),
    FOREIGN KEY (subject_skill) REFERENCES skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (object_skill) REFERENCES skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (relationship_type IN ('requires', 'alternative_to', 'obsoletes')),
    CHECK (subject_skill != object_skill)   -- Prevent self-references
);

-- Indexes for relationship traversal
CREATE INDEX IF NOT EXISTS idx_skill_rel_subject ON skill_relationships(subject_skill);
CREATE INDEX IF NOT EXISTS idx_skill_rel_object ON skill_relationships(object_skill);
CREATE INDEX IF NOT EXISTS idx_skill_rel_type ON skill_relationships(relationship_type);

COMMENT ON TABLE skill_relationships IS 'Targeted semantic relationships. Start with 3 types, expand only if proven valuable.';
COMMENT ON COLUMN skill_relationships.relationship_type IS 'CONSTRAINED to: requires, alternative_to, obsoletes. Add more via ALTER TABLE CHECK.';

-- ============================================================================
-- TABLE 4: skill_occurrences - Where skills appear (CV, job posting, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_occurrences (
    occurrence_id SERIAL PRIMARY KEY,       -- Surrogate key for this table only
    skill_source TEXT NOT NULL,             -- 'posting', 'cv', 'profile', 'job_description'
    source_id TEXT NOT NULL,                -- 'posting_352123', 'gershon_cv', 'recipe_run_12345'
    skill TEXT NOT NULL,                    -- Canonical skill (normalized)
    skill_alias TEXT,                       -- What was actually written (original text)
    confidence DECIMAL(3,2) DEFAULT 1.0,    -- LLM extraction confidence
    context TEXT,                           -- Surrounding sentence for debugging
    extraction_method TEXT,                 -- 'recipe_1120', 'manual_entry', 'imported'
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (skill) REFERENCES skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_skill_occ_source ON skill_occurrences(skill_source, source_id);
CREATE INDEX IF NOT EXISTS idx_skill_occ_skill ON skill_occurrences(skill);
CREATE INDEX IF NOT EXISTS idx_skill_occ_created ON skill_occurrences(created_at);

COMMENT ON TABLE skill_occurrences IS 'Tracks every mention of a skill in any source (CV, job, profile).';
COMMENT ON COLUMN skill_occurrences.skill_alias IS 'Original text before normalization (e.g., "Python 3.11", "python-programming")';
COMMENT ON COLUMN skill_occurrences.context IS 'Sentence or paragraph where skill was found (for debugging/validation)';

-- ============================================================================
-- VIEW 1: v_skill_tree - Recursive hierarchy view
-- ============================================================================
CREATE OR REPLACE VIEW v_skill_tree AS
WITH RECURSIVE tree AS (
    -- Base case: all skills with their immediate parents
    SELECT 
        skill,
        parent_skill,
        1 as level,
        skill::TEXT as path,
        ARRAY[skill] as ancestors
    FROM skill_hierarchy
    
    UNION ALL
    
    -- Recursive case: climb up the tree
    SELECT 
        t.skill,
        h.parent_skill,
        t.level + 1,
        t.path || ' → ' || h.parent_skill,
        t.ancestors || h.parent_skill
    FROM tree t
    JOIN skill_hierarchy h ON t.parent_skill = h.skill
    WHERE NOT (h.parent_skill = ANY(t.ancestors))  -- Prevent cycles
)
SELECT * FROM tree
ORDER BY skill, level;

COMMENT ON VIEW v_skill_tree IS 'Recursive view showing full ancestry path for each skill.';

-- ============================================================================
-- VIEW 2: v_skill_summary - Quick stats per skill
-- ============================================================================
CREATE OR REPLACE VIEW v_skill_summary AS
SELECT 
    sa.skill,
    sa.display_name,
    COUNT(DISTINCT sa2.skill_alias) as alias_count,
    COUNT(DISTINCT h.parent_skill) as parent_count,
    COUNT(DISTINCT r.object_skill) as relationship_count,
    COUNT(DISTINCT so.occurrence_id) as mention_count
FROM skill_aliases sa
LEFT JOIN skill_aliases sa2 ON sa.skill = sa2.skill
LEFT JOIN skill_hierarchy h ON sa.skill = h.skill
LEFT JOIN skill_relationships r ON sa.skill = r.subject_skill
LEFT JOIN skill_occurrences so ON sa.skill = so.skill
GROUP BY sa.skill, sa.display_name
ORDER BY mention_count DESC;

COMMENT ON VIEW v_skill_summary IS 'Aggregate stats: aliases, parents, relationships, mentions per skill.';

-- ============================================================================
-- VIEW 3: v_pending_synonyms - LLM-suggested skills needing human review
-- ============================================================================
CREATE OR REPLACE VIEW v_pending_synonyms AS
SELECT 
    skill_alias,
    skill,
    language,
    confidence,
    created_at,
    created_by,
    notes
FROM skill_aliases
WHERE confidence < 1.0  -- LLM-suggested, not yet verified
  AND created_by LIKE 'llm:%'
ORDER BY confidence DESC, created_at DESC;

COMMENT ON VIEW v_pending_synonyms IS 'Skills suggested by LLM awaiting human approval. Target: review monthly, approve 90%+.';

-- ============================================================================
-- SEED DATA: Bootstrap with discovered skills from Recipe 1120
-- ============================================================================

-- Top 20 most frequent skills from your 71 German job extractions
-- (You'll populate these next with a Python script)

/*
INSERT INTO skill_aliases (skill_alias, skill, display_name, confidence, created_by) VALUES
    -- Top skills from extraction
    ('b2b_sales', 'b2b_sales', 'B2B Sales', 1.0, 'human'),
    ('customer_service', 'customer_service', 'Customer Service', 1.0, 'human'),
    ('python', 'python', 'Python', 1.0, 'human'),
    ('presentation_skills', 'presentation_skills', 'Presentation Skills', 1.0, 'human'),
    ('aws', 'aws', 'AWS', 1.0, 'human'),
    -- ... more to come
    
INSERT INTO skill_hierarchy (skill, parent_skill) VALUES
    ('python', 'programming_language'),
    ('programming_language', 'technical_skill'),
    ('b2b_sales', 'sales'),
    ('sales', 'business_skill'),
    -- ... more to come
*/

-- ============================================================================
-- SUCCESS!
-- ============================================================================
SELECT 'SkillBridge v2 schema created successfully!' as status;
SELECT 'Next steps:' as todo, '1. Populate skill_aliases from Recipe 1120 extractions' as step;
