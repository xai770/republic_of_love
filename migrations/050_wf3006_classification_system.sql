-- Migration 050: WF3006 Entity Classification System
-- Date: 2025-12-15
-- Author: Arden
-- 
-- Creates tables and views for the entity classification workflow:
-- 1. classification_reasoning - stores reasoning chain for learning
-- 2. domain_split_proposals - human review queue for taxonomy changes
-- 3. v_orphan_skills - view of unclassified skills
-- 4. v_classification_quality - metrics view

BEGIN;

-- ============================================================================
-- 1. CLASSIFICATION_REASONING TABLE
-- Stores the reasoning chain from each classification attempt
-- ============================================================================

CREATE TABLE IF NOT EXISTS classification_reasoning (
    reasoning_id SERIAL PRIMARY KEY,
    
    -- What was classified
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id),
    decision_id INTEGER REFERENCES registry_decisions(decision_id),
    
    -- Who made this reasoning
    model TEXT NOT NULL,                    -- 'gemma3:4b', 'qwen2.5:7b', 'human:sandy'
    role TEXT NOT NULL,                     -- 'classifier', 'challenger', 'defender', 'judge', 'reset'
    
    -- The reasoning itself
    reasoning TEXT NOT NULL,                -- Full explanation
    confidence NUMERIC(3,2),                -- 0.00 to 1.00
    suggested_domain TEXT,                  -- Domain this step suggested
    
    -- Learning feedback
    was_overturned BOOLEAN DEFAULT FALSE,   -- Was this later proven wrong?
    overturn_reason TEXT,                   -- Why was it wrong?
    
    -- Metadata
    workflow_run_id INTEGER,                -- Which WF3006 run
    interaction_id INTEGER,                 -- Which interaction
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for quick lookups
CREATE INDEX IF NOT EXISTS idx_reasoning_entity ON classification_reasoning(entity_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_decision ON classification_reasoning(decision_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_role ON classification_reasoning(role);
CREATE INDEX IF NOT EXISTS idx_reasoning_overturned ON classification_reasoning(was_overturned) WHERE was_overturned = TRUE;

COMMENT ON TABLE classification_reasoning IS 'Stores reasoning chain from WF3006 classification attempts for institutional learning';
COMMENT ON COLUMN classification_reasoning.role IS 'Role in debate: classifier, challenger, defender, judge, or reset';
COMMENT ON COLUMN classification_reasoning.was_overturned IS 'Set to TRUE when a human or later run rejects this reasoning';

-- ============================================================================
-- 2. DOMAIN_SPLIT_PROPOSALS TABLE
-- Queue for human review of taxonomy changes
-- ============================================================================

CREATE TABLE IF NOT EXISTS domain_split_proposals (
    proposal_id SERIAL PRIMARY KEY,
    
    -- What's being proposed
    proposal_type TEXT NOT NULL CHECK (proposal_type IN ('new_domain', 'split', 'merge')),
    
    -- For new domain
    suggested_name TEXT,
    suggested_description TEXT,
    example_skills TEXT[],
    
    -- For split/merge
    parent_domain TEXT,
    suggested_children TEXT[],
    affected_skill_count INTEGER,
    
    -- Reasoning
    reasoning TEXT NOT NULL,
    confidence NUMERIC(3,2),
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'implemented')),
    
    -- Review
    reviewed_by TEXT,
    review_notes TEXT,
    reviewed_at TIMESTAMP,
    
    -- Metadata
    proposed_by TEXT DEFAULT 'wf3006',      -- 'wf3006' or 'human:name'
    triggering_skill_id INTEGER,            -- What skill triggered this proposal
    workflow_run_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proposals_status ON domain_split_proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_type ON domain_split_proposals(proposal_type);

COMMENT ON TABLE domain_split_proposals IS 'Human review queue for taxonomy changes proposed by WF3006';

-- ============================================================================
-- 3. V_ORPHAN_SKILLS VIEW
-- Skills that need classification
-- ============================================================================

CREATE OR REPLACE VIEW v_orphan_skills AS
SELECT 
    e.entity_id,
    e.canonical_name,
    e.description,
    e.created_at,
    -- Check if this is a reclassification (has history)
    EXISTS (
        SELECT 1 FROM classification_reasoning cr 
        WHERE cr.entity_id = e.entity_id
    ) AS has_history,
    -- Count previous attempts
    (
        SELECT COUNT(*) FROM classification_reasoning cr 
        WHERE cr.entity_id = e.entity_id AND cr.role = 'classifier'
    ) AS attempt_count
FROM entities e
WHERE e.entity_type = 'skill'
  AND e.status = 'active'
  -- No is_a relationship to a skill_domain
  AND NOT EXISTS (
      SELECT 1 FROM entity_relationships er
      JOIN entities domain ON er.related_entity_id = domain.entity_id
      WHERE er.entity_id = e.entity_id
        AND er.relationship = 'is_a'
        AND domain.entity_type = 'skill_domain'
  )
  -- No pending or approved decision
  AND NOT EXISTS (
      SELECT 1 FROM registry_decisions rd
      WHERE rd.subject_entity_id = e.entity_id
        AND rd.decision_type = 'skill_domain_mapping'
        AND rd.review_status IN ('pending', 'approved', 'auto_approved')
  );

COMMENT ON VIEW v_orphan_skills IS 'Skills needing classification - no domain assignment and no pending decision';

-- ============================================================================
-- 4. V_CLASSIFICATION_QUALITY VIEW
-- Metrics for monitoring classification quality
-- ============================================================================

CREATE OR REPLACE VIEW v_classification_quality AS
WITH domain_stats AS (
    SELECT 
        d.entity_id AS domain_id,
        d.canonical_name AS domain_name,
        COUNT(er.entity_id) AS skill_count,
        AVG(rd.confidence) AS avg_confidence,
        COUNT(CASE WHEN rd.review_status = 'pending' THEN 1 END) AS pending_review,
        COUNT(CASE WHEN cr.was_overturned THEN 1 END) AS overturned_count
    FROM entities d
    LEFT JOIN entity_relationships er ON d.entity_id = er.related_entity_id 
        AND er.relationship = 'is_a'
    LEFT JOIN registry_decisions rd ON er.entity_id = rd.subject_entity_id
        AND rd.decision_type = 'skill_domain_mapping'
    LEFT JOIN classification_reasoning cr ON er.entity_id = cr.entity_id
        AND cr.role = 'classifier'
    WHERE d.entity_type = 'skill_domain'
      AND d.status = 'active'
    GROUP BY d.entity_id, d.canonical_name
)
SELECT 
    domain_name,
    skill_count,
    ROUND(avg_confidence * 100, 1) AS avg_confidence_pct,
    pending_review,
    overturned_count,
    CASE 
        WHEN skill_count > 50 THEN 'NEEDS_SPLIT'
        WHEN skill_count = 0 THEN 'EMPTY'
        ELSE 'OK'
    END AS status
FROM domain_stats
ORDER BY skill_count DESC;

COMMENT ON VIEW v_classification_quality IS 'Quality metrics per domain for monitoring WF3006';

-- ============================================================================
-- 5. V_DOMAINS_WITH_EXAMPLES VIEW
-- For building dynamic prompts
-- ============================================================================

CREATE OR REPLACE VIEW v_domains_with_examples AS
SELECT 
    d.entity_id AS domain_id,
    d.canonical_name AS domain_name,
    d.description AS domain_description,
    COUNT(er.entity_id) AS skill_count,
    -- Get top 3 example skills
    (
        SELECT ARRAY_AGG(e2.canonical_name ORDER BY rd.confidence DESC NULLS LAST)
        FROM (
            SELECT er2.entity_id
            FROM entity_relationships er2
            WHERE er2.related_entity_id = d.entity_id
              AND er2.relationship = 'is_a'
            LIMIT 5
        ) top5
        JOIN entities e2 ON top5.entity_id = e2.entity_id
        LEFT JOIN registry_decisions rd ON e2.entity_id = rd.subject_entity_id
    ) AS example_skills
FROM entities d
LEFT JOIN entity_relationships er ON d.entity_id = er.related_entity_id 
    AND er.relationship = 'is_a'
WHERE d.entity_type = 'skill_domain'
  AND d.status = 'active'
GROUP BY d.entity_id, d.canonical_name, d.description
ORDER BY d.canonical_name;

COMMENT ON VIEW v_domains_with_examples IS 'Domains with skill counts and examples for LLM prompts';

-- ============================================================================
-- 6. HELPER FUNCTION: Get reasoning history for a skill
-- ============================================================================

CREATE OR REPLACE FUNCTION get_skill_reasoning_history(p_entity_id INTEGER)
RETURNS TABLE (
    model TEXT,
    role TEXT,
    reasoning TEXT,
    confidence NUMERIC,
    suggested_domain TEXT,
    was_overturned BOOLEAN,
    overturn_reason TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cr.model,
        cr.role,
        cr.reasoning,
        cr.confidence,
        cr.suggested_domain,
        cr.was_overturned,
        cr.overturn_reason,
        cr.created_at
    FROM classification_reasoning cr
    WHERE cr.entity_id = p_entity_id
    ORDER BY cr.created_at;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_skill_reasoning_history IS 'Get full reasoning history for a skill for learning context';

-- ============================================================================
-- 7. DOMAIN CREATION RATE LIMITING
-- Track domain creation for rate limiting
-- ============================================================================

CREATE OR REPLACE FUNCTION count_domains_created_this_week()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM entities
    WHERE entity_type = 'skill_domain'
      AND created_at > NOW() - INTERVAL '7 days'
      AND created_by = 'wf3006';
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. Add created_by column to entities if not exists
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'entities' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE entities ADD COLUMN created_by TEXT;
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    v_orphan_count INTEGER;
    v_domain_count INTEGER;
BEGIN
    -- Count orphans
    SELECT COUNT(*) INTO v_orphan_count FROM v_orphan_skills;
    
    -- Count domains
    SELECT COUNT(*) INTO v_domain_count FROM v_domains_with_examples;
    
    RAISE NOTICE 'Migration 050 complete:';
    RAISE NOTICE '  - classification_reasoning table created';
    RAISE NOTICE '  - domain_split_proposals table created';
    RAISE NOTICE '  - v_orphan_skills view: % skills need classification', v_orphan_count;
    RAISE NOTICE '  - v_domains_with_examples: % domains available', v_domain_count;
END $$;

COMMIT;
