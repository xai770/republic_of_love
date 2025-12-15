-- Migration 063: Move decision fields to user_posting_decisions table
-- Date: 2025-11-07
-- Reason: System is multi-user - decisions are per-user, not per-posting!

BEGIN;

-- ============================================================================
-- PART 1: Drop old views that reference decision columns
-- ============================================================================

DROP VIEW IF EXISTS v_client_action_list CASCADE;
DROP VIEW IF EXISTS v_client_job_report CASCADE;

-- ============================================================================
-- PART 2: Create user_posting_decisions table
-- ============================================================================

CREATE TABLE user_posting_decisions (
    decision_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user_preferences(user_id),
    posting_id INTEGER NOT NULL REFERENCES postings(posting_id),
    
    -- Decision fields (one of these should be filled)
    cover_letter_draft TEXT,
    no_go_reason TEXT,
    
    -- Metadata
    decision_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decision_workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id),
    
    -- Ensure one decision per user per posting
    UNIQUE(user_id, posting_id),
    
    -- Ensure either cover_letter OR no_go_reason, not both
    CONSTRAINT check_one_decision CHECK (
        (cover_letter_draft IS NOT NULL AND no_go_reason IS NULL) OR
        (cover_letter_draft IS NULL AND no_go_reason IS NOT NULL)
    )
);

CREATE INDEX idx_user_posting_decisions_user ON user_posting_decisions(user_id);
CREATE INDEX idx_user_posting_decisions_posting ON user_posting_decisions(posting_id);
CREATE INDEX idx_user_posting_decisions_generated ON user_posting_decisions(decision_generated_at);

COMMENT ON TABLE user_posting_decisions IS 
    'User-specific decisions about job postings.
    Each user gets their own cover_letter_draft (if applying) or no_go_reason (if skipping).
    This is multi-user aware - same job can be APPLY for one user, SKIP for another.';

COMMENT ON COLUMN user_posting_decisions.cover_letter_draft IS 
    'AI-generated personalized cover letter for this user applying to this job. Only set if recommendation is APPLY.';

COMMENT ON COLUMN user_posting_decisions.no_go_reason IS 
    'AI explanation why this user should NOT apply to this job. Examples: skill gaps, level mismatch, location conflict, high IHL risk. Only set if recommendation is SKIP.';

-- ============================================================================
-- PART 3: Remove decision fields from postings table
-- ============================================================================

ALTER TABLE postings DROP COLUMN cover_letter_draft;
ALTER TABLE postings DROP COLUMN no_go_reason;
ALTER TABLE postings DROP COLUMN decision_generated_at;
ALTER TABLE postings DROP COLUMN decision_workflow_run_id;

COMMENT ON TABLE postings IS 
    'Job postings from external sources. 
    
    Schema evolution:
    - 2025-11-06: Migration 060 - Changed UNIQUE to (source_id, posting_name), deleted duplicates (739→256)
    - 2025-11-06: Migration 061 - Dropped 10 dead columns (55→45)
    - 2025-11-07: Migration 062 - Dropped 23 legacy columns, added 4 client decision fields (45→28)
    - 2025-11-07: Migration 063 - Moved decision fields to user_posting_decisions (multi-user!) (28→24)
    
    Note: User-specific decisions (cover letters, no-go reasons) are now in user_posting_decisions table.
    All legacy data preserved in source_metadata JSONB column.';

-- ============================================================================
-- PART 4: Recreate views to use new table
-- ============================================================================

-- Drop old views
DROP VIEW IF EXISTS v_client_job_report CASCADE;
DROP VIEW IF EXISTS v_client_action_list CASCADE;

-- Recreate with user_posting_decisions join
CREATE OR REPLACE VIEW v_client_job_report AS
SELECT 
    -- User context
    up.user_id,
    up.user_name,
    
    -- Job Identity
    p.posting_id,
    p.external_job_id,
    p.job_title,
    p.external_url,
    
    -- Location & Level
    p.location_city,
    p.location_country,
    p.employment_career_level,
    
    -- Status & Freshness
    p.posting_status,
    p.first_seen_at::date as first_seen,
    p.last_seen_at::date as last_checked,
    CASE 
        WHEN p.first_seen_at > CURRENT_DATE - INTERVAL '7 days' THEN 'NEW'
        WHEN p.last_seen_at > CURRENT_DATE - INTERVAL '7 days' THEN 'RECENT'
        ELSE 'OLDER'
    END as freshness,
    
    -- Skills Analysis
    (SELECT COUNT(*) FROM job_skills js WHERE js.posting_id = p.posting_id) as skill_count,
    (SELECT STRING_AGG(sa.skill_name, ', ' ORDER BY js.importance DESC) 
     FROM job_skills js 
     JOIN skill_aliases sa ON js.skill_id = sa.skill_id 
     WHERE js.posting_id = p.posting_id 
     LIMIT 10) as top_10_skills,
    
    -- Quality Signals
    p.ihl_score,
    p.ihl_category,
    CASE 
        WHEN p.ihl_score IS NULL THEN 'Not Analyzed'
        WHEN p.ihl_score <= 40 THEN 'HIGH - Real Opportunity'
        WHEN p.ihl_score <= 70 THEN 'MEDIUM - Worth Applying'
        ELSE 'LOW - Likely Internal Hire'
    END as ihl_interpretation,
    
    -- User-specific Decision Guidance
    upd.cover_letter_draft,
    upd.no_go_reason,
    CASE 
        WHEN upd.cover_letter_draft IS NOT NULL THEN 'APPLY'
        WHEN upd.no_go_reason IS NOT NULL THEN 'SKIP'
        ELSE 'PENDING ANALYSIS'
    END as recommendation,
    upd.decision_generated_at::date as decision_date,
    
    -- Matching Score (from v_user_matched_postings logic)
    (
        CASE WHEN p.employment_career_level = ANY(up.preferred_career_levels) THEN 30 ELSE 0 END +
        CASE WHEN p.location_city = ANY(up.preferred_locations) THEN 30 ELSE 0 END +
        CASE WHEN p.ihl_score IS NOT NULL AND p.ihl_score <= 60 THEN 20 ELSE 0 END +
        CASE WHEN p.posting_status = 'active' THEN 20 ELSE 0 END
    ) AS match_score,
    
    -- Content preview
    LEFT(p.job_description, 500) || '...' as description_preview

FROM user_preferences up
CROSS JOIN postings p
LEFT JOIN user_posting_decisions upd ON upd.user_id = up.user_id AND upd.posting_id = p.posting_id
WHERE up.is_active = true
  AND p.source_id = 1  -- Deutsche Bank
  AND p.enabled = true
  AND p.posting_status IN ('active', 'filled')
  AND (up.preferred_career_levels IS NULL OR p.employment_career_level = ANY(up.preferred_career_levels))
  AND (up.preferred_locations IS NULL OR p.location_city = ANY(up.preferred_locations))
ORDER BY 
    up.user_id,
    CASE 
        WHEN upd.cover_letter_draft IS NOT NULL THEN 1  -- APPLY recommendations first
        WHEN upd.no_go_reason IS NULL THEN 2            -- Pending analysis second
        WHEN upd.no_go_reason IS NOT NULL THEN 3        -- SKIP recommendations last
    END,
    p.first_seen_at DESC;

COMMENT ON VIEW v_client_job_report IS 
    'Multi-user export-ready client job report with AI decision guidance.
    
    IMPORTANT: Now multi-user aware! Each user sees their own cover_letter_draft/no_go_reason.
    
    Key Fields:
    - user_id, user_name: Which user this report is for
    - recommendation: APPLY (has cover_letter_draft) | SKIP (has no_go_reason) | PENDING ANALYSIS
    - cover_letter_draft: Personalized cover letter for THIS user
    - no_go_reason: Why THIS user should not apply
    - match_score: How well this job matches this user''s preferences
    
    Export Examples:
    
    1. Report for specific user:
       \COPY (SELECT * FROM v_client_job_report WHERE user_id = 1) TO ''user1_jobs.csv'' CSV HEADER
    
    2. User''s jobs to apply for:
       \COPY (SELECT * FROM v_client_job_report WHERE user_id = 1 AND recommendation = ''APPLY'') TO ''user1_apply.csv'' CSV HEADER
    
    3. All users'' pending analyses:
       \COPY (SELECT * FROM v_client_job_report WHERE recommendation = ''PENDING ANALYSIS'') TO ''pending.csv'' CSV HEADER
    ';

CREATE OR REPLACE VIEW v_client_action_list AS
SELECT 
    user_id,
    user_name,
    external_job_id,
    job_title,
    location_city,
    employment_career_level,
    recommendation,
    ihl_interpretation,
    match_score,
    external_url,
    CASE 
        WHEN recommendation = 'APPLY' THEN cover_letter_draft
        WHEN recommendation = 'SKIP' THEN no_go_reason
        ELSE 'Analysis pending - run decision workflow'
    END as action_guidance
FROM v_client_job_report
WHERE posting_status = 'active'
ORDER BY 
    user_id,
    CASE recommendation
        WHEN 'APPLY' THEN 1
        WHEN 'PENDING ANALYSIS' THEN 2
        WHEN 'SKIP' THEN 3
    END,
    match_score DESC,
    ihl_score NULLS LAST;

COMMENT ON VIEW v_client_action_list IS 
    'Simplified multi-user action list: what each user should do about each active job.
    Shows either cover_letter_draft (if APPLY) or no_go_reason (if SKIP).
    Perfect for daily review workflow.';

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check column count (should be 22 now)
SELECT 'Total columns after migration 063' as metric, COUNT(*) as count
FROM information_schema.columns 
WHERE table_name = 'postings';

-- Verify new table exists
SELECT 'user_posting_decisions table' as metric, 
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_posting_decisions') 
       THEN 'Created' ELSE 'Missing!' END as status;

-- Show final postings schema
SELECT column_name, data_type
FROM information_schema.columns 
WHERE table_name = 'postings' 
ORDER BY ordinal_position;
