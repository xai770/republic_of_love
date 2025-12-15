-- Migration 040: User Preferences & Posting Lifecycle
-- Created: 2025-11-03
-- Purpose: User-centric job search with preferences, deduplication, and status tracking

-- ============================================================================
-- USER PREFERENCES: Store user job search criteria
-- ============================================================================

CREATE TABLE user_preferences (
    user_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_name TEXT NOT NULL,
    email TEXT,
    
    -- Career preferences
    preferred_career_levels TEXT[],
    preferred_locations TEXT[],
    preferred_divisions TEXT[],
    preferred_companies TEXT[],
    
    -- Salary expectations
    min_salary INTEGER,
    max_salary INTEGER,
    currency TEXT DEFAULT 'EUR',
    
    -- Work preferences
    remote_only BOOLEAN DEFAULT false,
    willing_to_relocate BOOLEAN DEFAULT true,
    
    -- Skills
    required_skills TEXT[],
    preferred_skills TEXT[],
    
    -- Employment preferences
    employment_types TEXT[],  -- 'Full-time', 'Contract', 'Part-time'
    max_travel_percentage INTEGER,
    
    -- Alert settings
    alert_on_new_jobs BOOLEAN DEFAULT true,
    alert_on_matches BOOLEAN DEFAULT true,
    alert_frequency TEXT DEFAULT 'daily',
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_alert_frequency CHECK (alert_frequency IN ('immediate', 'daily', 'weekly', 'never'))
);

CREATE INDEX idx_user_prefs_active ON user_preferences(is_active);

COMMENT ON TABLE user_preferences IS 'User job search preferences and filters';

-- Seed with xai's preferences
INSERT INTO user_preferences (
    user_name,
    preferred_career_levels,
    preferred_locations,
    alert_frequency
) VALUES (
    'xai',
    ARRAY['Assistant Vice President', 'Vice President'],
    ARRAY['Frankfurt', 'Frankfurt am Main'],
    'daily'
);

-- ============================================================================
-- POSTING LIFECYCLE: Track posting status over time
-- ============================================================================

ALTER TABLE postings 
    ADD COLUMN IF NOT EXISTS posting_status TEXT DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS status_reason TEXT,
    ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS times_checked INTEGER DEFAULT 1;

CREATE INDEX idx_postings_status ON postings(posting_status, last_seen_at);
CREATE INDEX idx_postings_active ON postings(posting_status) WHERE posting_status = 'active';

COMMENT ON COLUMN postings.posting_status IS 'Lifecycle status: active, filled, expired, withdrawn, archived';
COMMENT ON COLUMN postings.first_seen_at IS 'When this posting was first fetched';
COMMENT ON COLUMN postings.last_seen_at IS 'Last time this posting was confirmed on source site';
COMMENT ON COLUMN postings.times_checked IS 'How many times we''ve checked if this posting still exists';

-- Add constraint for valid statuses
ALTER TABLE postings 
    ADD CONSTRAINT valid_posting_status CHECK (
        posting_status IN ('active', 'filled', 'expired', 'withdrawn', 'archived')
    );

-- ============================================================================
-- DEDUPLICATION FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION posting_exists(
    p_source_id INTEGER,
    p_external_job_id TEXT
) RETURNS INTEGER AS $$
DECLARE
    existing_id INTEGER;
BEGIN
    SELECT posting_id INTO existing_id
    FROM postings
    WHERE source_id = p_source_id
    AND external_job_id = p_external_job_id;
    
    RETURN existing_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION posting_exists IS 'Check if a posting already exists by source and external ID';

CREATE OR REPLACE FUNCTION update_posting_seen(
    p_posting_id INTEGER,
    p_still_active BOOLEAN
) RETURNS VOID AS $$
BEGIN
    IF p_still_active THEN
        -- Still live on source site
        UPDATE postings
        SET 
            last_seen_at = CURRENT_TIMESTAMP,
            times_checked = times_checked + 1,
            posting_status = 'active'
        WHERE posting_id = p_posting_id;
    ELSE
        -- No longer on source site
        UPDATE postings
        SET 
            posting_status = 'filled',
            status_changed_at = CURRENT_TIMESTAMP,
            status_reason = 'No longer found on source site during re-check',
            times_checked = times_checked + 1
        WHERE posting_id = p_posting_id
        AND posting_status = 'active';
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_posting_seen IS 'Update posting status when re-checked (still active or disappeared)';

-- ============================================================================
-- USER-MATCHED POSTINGS VIEW
-- ============================================================================

CREATE VIEW v_user_matched_postings AS
SELECT 
    p.posting_id,
    p.posting_name,
    p.organization_name,
    p.location_city,
    p.employment_career_level,
    p.posting_status,
    p.ihl_score,
    p.ihl_category,
    p.fetched_at,
    p.last_seen_at,
    up.user_id,
    up.user_name,
    -- Match score (0-100)
    (
        CASE WHEN p.employment_career_level = ANY(up.preferred_career_levels) THEN 30 ELSE 0 END +
        CASE WHEN p.location_city = ANY(up.preferred_locations) THEN 30 ELSE 0 END +
        CASE WHEN p.ihl_score IS NOT NULL AND p.ihl_score <= 60 THEN 20 ELSE 0 END +
        CASE WHEN p.posting_status = 'active' THEN 20 ELSE 0 END
    ) AS match_score,
    -- Match reasons
    ARRAY_REMOVE(ARRAY[
        CASE WHEN p.employment_career_level = ANY(up.preferred_career_levels) THEN 'Career Level Match' END,
        CASE WHEN p.location_city = ANY(up.preferred_locations) THEN 'Location Match' END,
        CASE WHEN p.ihl_score IS NOT NULL AND p.ihl_score <= 60 THEN 'Low IHL (Open Position)' END,
        CASE WHEN p.posting_status = 'active' THEN 'Currently Active' END
    ], NULL) AS match_reasons
FROM postings p
CROSS JOIN user_preferences up
WHERE up.is_active = true
AND p.posting_status IN ('active', 'filled')
AND (
    up.preferred_career_levels IS NULL 
    OR p.employment_career_level = ANY(up.preferred_career_levels)
)
AND (
    up.preferred_locations IS NULL 
    OR p.location_city = ANY(up.preferred_locations)
)
ORDER BY match_score DESC, p.fetched_at DESC;

COMMENT ON VIEW v_user_matched_postings IS 'Jobs matching user preferences with scoring and reasons';

-- ============================================================================
-- POSTING STATUS SUMMARY VIEW
-- ============================================================================

CREATE VIEW v_posting_status_summary AS
SELECT 
    posting_status,
    COUNT(*) as count,
    MIN(first_seen_at) as oldest,
    MAX(last_seen_at) as newest,
    AVG(times_checked)::integer as avg_checks
FROM postings
GROUP BY posting_status
ORDER BY 
    CASE posting_status
        WHEN 'active' THEN 1
        WHEN 'filled' THEN 2
        WHEN 'expired' THEN 3
        WHEN 'withdrawn' THEN 4
        WHEN 'archived' THEN 5
    END;

COMMENT ON VIEW v_posting_status_summary IS 'Summary of postings by status';

-- ============================================================================
-- USER DASHBOARD VIEW
-- ============================================================================

CREATE VIEW v_user_dashboard AS
SELECT 
    up.user_id,
    up.user_name,
    COUNT(DISTINCT p.posting_id) as total_matches,
    COUNT(DISTINCT p.posting_id) FILTER (WHERE p.posting_status = 'active') as active_matches,
    COUNT(DISTINCT p.posting_id) FILTER (WHERE p.ihl_score <= 60) as open_positions,
    COUNT(DISTINCT p.posting_id) FILTER (WHERE p.fetched_at > CURRENT_DATE - INTERVAL '7 days') as new_this_week,
    AVG(p.ihl_score) FILTER (WHERE p.posting_status = 'active')::integer as avg_ihl_active
FROM user_preferences up
LEFT JOIN v_user_matched_postings vump ON vump.user_id = up.user_id
LEFT JOIN postings p ON p.posting_id = vump.posting_id
WHERE up.is_active = true
GROUP BY up.user_id, up.user_name;

COMMENT ON VIEW v_user_dashboard IS 'User-level statistics for matched jobs';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
DECLARE
    user_count INTEGER;
    prefs_career TEXT[];
    prefs_location TEXT[];
BEGIN
    SELECT COUNT(*) INTO user_count FROM user_preferences;
    SELECT preferred_career_levels, preferred_locations 
    INTO prefs_career, prefs_location
    FROM user_preferences WHERE user_name = 'xai';
    
    RAISE NOTICE '✅ Migration 040 complete: User Preferences & Posting Lifecycle';
    RAISE NOTICE '   - Created user_preferences table (% users)', user_count;
    RAISE NOTICE '   - Extended postings with lifecycle tracking';
    RAISE NOTICE '   - Created deduplication functions';
    RAISE NOTICE '   - Created 3 user-centric views';
    RAISE NOTICE '';
    RAISE NOTICE '👤 User "xai" preferences:';
    RAISE NOTICE '   - Career Levels: %', prefs_career;
    RAISE NOTICE '   - Locations: %', prefs_location;
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Next: Query your matches!';
    RAISE NOTICE '   SELECT * FROM v_user_matched_postings WHERE user_name = ''xai'' LIMIT 10;';
END $$;
