-- Migration 053: Mira FAQ Candidate Staging Table
-- Purpose: Store interesting Mira exchanges for human review and potential FAQ promotion
-- Author: Arden
-- Date: 2026-02-09

-- ============================================================================
-- STAGING TABLE FOR FAQ CANDIDATES
-- ============================================================================

CREATE TABLE IF NOT EXISTS mira_faq_candidates (
    id SERIAL PRIMARY KEY,
    
    -- Context
    user_id INTEGER,                  -- References users(id) but no FK for flexibility
    session_id VARCHAR(64),           -- Group exchanges from same session
    
    -- The exchange
    user_message TEXT NOT NULL,
    mira_response TEXT NOT NULL,
    
    -- Detection metadata
    faq_score FLOAT,                  -- Embedding match score (0-1)
    faq_matched_id VARCHAR(64),       -- Which FAQ entry was closest (if any)
    flagged_reason VARCHAR(32) NOT NULL,  -- 'low_match', 'positive_feedback', 'novel_topic'
    
    -- User signal (if any)
    user_feedback VARCHAR(16),        -- 'positive', 'negative', null
    
    -- Review workflow
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER,              -- References users(id) 
    review_decision VARCHAR(16),      -- 'promote', 'reject', 'defer'
    review_notes TEXT,
    
    -- Promotion tracking
    promoted_at TIMESTAMP,
    promoted_faq_id VARCHAR(64),      -- ID assigned in mira_faq.md after promotion
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_flagged_reason CHECK (
        flagged_reason IN ('low_match', 'positive_feedback', 'novel_topic', 'explicit_flag')
    ),
    CONSTRAINT valid_review_decision CHECK (
        review_decision IS NULL OR review_decision IN ('promote', 'reject', 'defer')
    )
);

-- Index for pending review queue
CREATE INDEX IF NOT EXISTS idx_faq_candidates_pending 
ON mira_faq_candidates(created_at) 
WHERE reviewed_at IS NULL;

-- Index for finding duplicates
CREATE INDEX IF NOT EXISTS idx_faq_candidates_user_message 
ON mira_faq_candidates USING gin(to_tsvector('german', user_message));

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE mira_faq_candidates IS 'Staging table for Mira exchanges that might become FAQ entries';
COMMENT ON COLUMN mira_faq_candidates.flagged_reason IS 'Why this exchange was flagged: low_match (FAQ score < 0.60), positive_feedback (user said thanks/helpful), novel_topic (new category detected), explicit_flag (admin flagged)';
COMMENT ON COLUMN mira_faq_candidates.faq_score IS 'Best cosine similarity score from BGE-M3 embedding match';
