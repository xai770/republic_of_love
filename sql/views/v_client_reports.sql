-- Client Report View: Export-ready job data with decision guidance
-- Created: 2025-11-07
-- Purpose: Provide clients with actionable job reports including AI-generated decisions

CREATE OR REPLACE VIEW v_client_job_report AS
SELECT 
    -- Job Identity
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
    p.skill_keywords,
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
    
    -- Client Decision Guidance (NEW!)
    p.cover_letter_draft,
    p.no_go_reason,
    CASE 
        WHEN p.cover_letter_draft IS NOT NULL THEN 'APPLY'
        WHEN p.no_go_reason IS NOT NULL THEN 'SKIP'
        ELSE 'PENDING ANALYSIS'
    END as recommendation,
    p.decision_generated_at::date as decision_date,
    
    -- Content (for reference)
    LEFT(p.job_description, 500) || '...' as description_preview,
    LENGTH(p.job_description) as description_length

FROM postings p
WHERE p.source_id = 1  -- Deutsche Bank
  AND p.enabled = true
ORDER BY 
    CASE 
        WHEN p.cover_letter_draft IS NOT NULL THEN 1  -- APPLY recommendations first
        WHEN p.no_go_reason IS NULL THEN 2            -- Pending analysis second
        WHEN p.no_go_reason IS NOT NULL THEN 3        -- SKIP recommendations last
    END,
    p.first_seen_at DESC;

COMMENT ON VIEW v_client_job_report IS 
    'Export-ready client job report with AI decision guidance.
    
    Key Fields:
    - recommendation: APPLY (has cover_letter_draft) | SKIP (has no_go_reason) | PENDING ANALYSIS
    - cover_letter_draft: Personalized cover letter if applying
    - no_go_reason: Why NOT to apply (persona learning)
    - ihl_interpretation: Human-readable internal hire likelihood
    - freshness: NEW (<7 days) | RECENT (checked <7 days ago) | OLDER
    - top_10_skills: Comma-separated top skills
    
    Export Examples:
    
    1. Excel export (all jobs):
       \COPY (SELECT * FROM v_client_job_report) TO ''jobs_report.csv'' CSV HEADER
    
    2. Jobs to apply for:
       \COPY (SELECT * FROM v_client_job_report WHERE recommendation = ''APPLY'') TO ''apply_these.csv'' CSV HEADER
    
    3. New jobs this week:
       \COPY (SELECT * FROM v_client_job_report WHERE freshness = ''NEW'') TO ''new_this_week.csv'' CSV HEADER
    
    4. High-quality opportunities (low IHL, active, with cover letter):
       \COPY (SELECT * FROM v_client_job_report 
              WHERE recommendation = ''APPLY'' 
                AND ihl_score <= 40 
                AND posting_status = ''active'') 
       TO ''best_opportunities.csv'' CSV HEADER
    ';

-- Create simplified "action list" view
CREATE OR REPLACE VIEW v_client_action_list AS
SELECT 
    external_job_id,
    job_title,
    location_city,
    employment_career_level,
    recommendation,
    ihl_interpretation,
    external_url,
    CASE 
        WHEN recommendation = 'APPLY' THEN cover_letter_draft
        WHEN recommendation = 'SKIP' THEN no_go_reason
        ELSE 'Analysis pending - run decision workflow'
    END as action_guidance
FROM v_client_job_report
WHERE posting_status = 'active'
ORDER BY 
    CASE recommendation
        WHEN 'APPLY' THEN 1
        WHEN 'PENDING ANALYSIS' THEN 2
        WHEN 'SKIP' THEN 3
    END,
    ihl_score NULLS LAST,
    first_seen DESC;

COMMENT ON VIEW v_client_action_list IS 
    'Simplified action list: what to do about each active job.
    Shows either cover_letter_draft (if APPLY) or no_go_reason (if SKIP).
    Perfect for daily review workflow.';

-- Grant access (adjust as needed)
-- GRANT SELECT ON v_client_job_report TO client_user;
-- GRANT SELECT ON v_client_action_list TO client_user;
