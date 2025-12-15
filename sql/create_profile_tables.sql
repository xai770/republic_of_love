-- Profile Tables for Talent Yoga
-- Purpose: Store candidate profiles with skills mapped to same taxonomy as job postings
-- Design: Similar structure to postings table for easy matching

-- ============================================================================
-- Main Profile Table
-- ============================================================================
CREATE TABLE profiles (
    profile_id SERIAL PRIMARY KEY,
    
    -- Basic Information
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    location TEXT,
    linkedin_url TEXT,
    
    -- Profile Content (raw)
    profile_source TEXT, -- 'linkedin', 'cv', 'manual', 'indeed', etc.
    profile_raw_text TEXT, -- Original CV/profile text
    profile_summary TEXT, -- Extracted professional summary (like extracted_summary for jobs)
    
    -- Skills (parallel to job postings)
    skill_keywords JSONB, -- Array of taxonomy-matched skills, same format as postings.skill_keywords
    skills_extraction_status TEXT DEFAULT 'pending', -- 'pending', 'success', 'failed'
    
    -- Experience Level Classification
    experience_level TEXT, -- 'entry', 'junior', 'mid', 'senior', 'lead', 'executive'
    years_of_experience INTEGER,
    
    -- Availability & Preferences
    current_title TEXT,
    desired_roles TEXT[], -- Array of desired job titles
    desired_locations TEXT[], -- Array of preferred locations
    availability_status TEXT, -- 'active', 'passive', 'not_available'
    expected_salary_min INTEGER,
    expected_salary_max INTEGER,
    currency TEXT DEFAULT 'CHF',
    
    -- Metadata
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_date TIMESTAMP,
    
    -- Search & Matching
    search_vector tsvector -- Full-text search across all profile content
);

-- Indexes for performance
CREATE INDEX idx_profiles_enabled ON profiles(enabled);
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_experience_level ON profiles(experience_level);
CREATE INDEX idx_profiles_availability ON profiles(availability_status);
CREATE INDEX idx_profiles_skill_keywords ON profiles USING gin(skill_keywords);
CREATE INDEX idx_profiles_search_vector ON profiles USING gin(search_vector);
CREATE INDEX idx_profiles_updated ON profiles(updated_at);

-- Unique constraint on email (one profile per person)
CREATE UNIQUE INDEX idx_profiles_email_unique ON profiles(email) WHERE email IS NOT NULL;

-- ============================================================================
-- Work History Table
-- ============================================================================
CREATE TABLE profile_work_history (
    work_history_id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    
    -- Company & Role
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    department TEXT,
    
    -- Dates
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    duration_months INTEGER, -- Calculated field
    
    -- Details
    job_description TEXT,
    achievements TEXT[], -- Array of bullet points
    technologies_used TEXT[], -- Skills/tools used in this role
    
    -- Location
    location TEXT,
    remote BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_work_history_profile ON profile_work_history(profile_id);
CREATE INDEX idx_work_history_current ON profile_work_history(is_current);
CREATE INDEX idx_work_history_dates ON profile_work_history(start_date, end_date);

-- ============================================================================
-- Education Table
-- ============================================================================
CREATE TABLE profile_education (
    education_id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    
    -- Institution
    institution_name TEXT NOT NULL,
    institution_location TEXT,
    
    -- Degree
    degree_type TEXT, -- 'bachelor', 'master', 'phd', 'mba', 'certificate', etc.
    degree_name TEXT, -- 'Computer Science', 'Business Administration', etc.
    field_of_study TEXT,
    
    -- Dates
    start_date DATE,
    end_date DATE,
    graduation_year INTEGER,
    is_current BOOLEAN DEFAULT FALSE,
    
    -- Details
    gpa DECIMAL(3,2),
    honors TEXT, -- 'summa cum laude', 'magna cum laude', etc.
    thesis_title TEXT,
    relevant_coursework TEXT[],
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_education_profile ON profile_education(profile_id);
CREATE INDEX idx_education_degree ON profile_education(degree_type);
CREATE INDEX idx_education_graduation ON profile_education(graduation_year);

-- ============================================================================
-- Certifications & Licenses Table
-- ============================================================================
CREATE TABLE profile_certifications (
    certification_id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    
    -- Certification Details
    certification_name TEXT NOT NULL,
    issuing_organization TEXT,
    credential_id TEXT,
    credential_url TEXT,
    
    -- Dates
    issue_date DATE,
    expiration_date DATE,
    does_not_expire BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_certifications_profile ON profile_certifications(profile_id);
CREATE INDEX idx_certifications_expiration ON profile_certifications(expiration_date);

-- ============================================================================
-- Languages Table
-- ============================================================================
CREATE TABLE profile_languages (
    language_id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    
    -- Language Details
    language_name TEXT NOT NULL, -- 'English', 'German', 'French', etc.
    proficiency_level TEXT, -- 'native', 'fluent', 'advanced', 'intermediate', 'basic'
    
    -- Speaking/Writing breakdown (optional)
    speaking_level TEXT,
    writing_level TEXT,
    reading_level TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_languages_profile ON profile_languages(profile_id);
CREATE INDEX idx_languages_proficiency ON profile_languages(proficiency_level);

-- ============================================================================
-- Profile-Job Matches Table (for matching results)
-- ============================================================================
CREATE TABLE profile_job_matches (
    match_id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES postings(job_id) ON DELETE CASCADE,
    
    -- Match Scores
    overall_match_score DECIMAL(5,2), -- 0.00 to 100.00
    skill_match_score DECIMAL(5,2),
    experience_match_score DECIMAL(5,2),
    location_match_score DECIMAL(5,2),
    
    -- Skill Details
    matched_skills JSONB, -- Array of skills that match
    missing_skills JSONB, -- Skills job requires but candidate lacks
    extra_skills JSONB, -- Skills candidate has that job doesn't require
    
    -- Match Metadata
    match_status TEXT DEFAULT 'pending', -- 'pending', 'reviewed', 'contacted', 'rejected', 'hired'
    match_quality TEXT, -- 'excellent', 'good', 'fair', 'poor'
    match_explanation TEXT, -- LLM-generated explanation of the match
    
    -- Timestamps
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    contacted_at TIMESTAMP,
    
    -- Notes
    recruiter_notes TEXT,
    
    -- Constraints
    UNIQUE(profile_id, job_id) -- One match record per profile-job pair
);

CREATE INDEX idx_matches_profile ON profile_job_matches(profile_id);
CREATE INDEX idx_matches_job ON profile_job_matches(job_id);
CREATE INDEX idx_matches_score ON profile_job_matches(overall_match_score DESC);
CREATE INDEX idx_matches_status ON profile_job_matches(match_status);
CREATE INDEX idx_matches_quality ON profile_job_matches(match_quality);
CREATE INDEX idx_matches_matched_at ON profile_job_matches(matched_at DESC);

-- ============================================================================
-- Triggers for updated_at
-- ============================================================================

-- Update updated_at on profiles
CREATE OR REPLACE FUNCTION update_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at_trigger
BEFORE UPDATE ON profiles
FOR EACH ROW
EXECUTE FUNCTION update_profiles_updated_at();

-- Similar triggers for related tables
CREATE TRIGGER work_history_updated_at_trigger
BEFORE UPDATE ON profile_work_history
FOR EACH ROW
EXECUTE FUNCTION update_profiles_updated_at();

CREATE TRIGGER education_updated_at_trigger
BEFORE UPDATE ON profile_education
FOR EACH ROW
EXECUTE FUNCTION update_profiles_updated_at();

CREATE TRIGGER certifications_updated_at_trigger
BEFORE UPDATE ON profile_certifications
FOR EACH ROW
EXECUTE FUNCTION update_profiles_updated_at();

-- ============================================================================
-- Helper Function: Calculate work duration in months
-- ============================================================================
CREATE OR REPLACE FUNCTION calculate_work_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.start_date IS NOT NULL THEN
        NEW.duration_months = EXTRACT(YEAR FROM AGE(
            COALESCE(NEW.end_date, CURRENT_DATE), 
            NEW.start_date
        )) * 12 + 
        EXTRACT(MONTH FROM AGE(
            COALESCE(NEW.end_date, CURRENT_DATE), 
            NEW.start_date
        ));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER work_history_duration_trigger
BEFORE INSERT OR UPDATE ON profile_work_history
FOR EACH ROW
EXECUTE FUNCTION calculate_work_duration();

-- ============================================================================
-- Helper Function: Update search vector for full-text search
-- ============================================================================
CREATE OR REPLACE FUNCTION update_profile_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = 
        setweight(to_tsvector('english', COALESCE(NEW.full_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.current_title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.profile_summary, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.profile_raw_text, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profile_search_vector_trigger
BEFORE INSERT OR UPDATE ON profiles
FOR EACH ROW
EXECUTE FUNCTION update_profile_search_vector();

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE profiles IS 'Candidate profiles with skills mapped to job taxonomy';
COMMENT ON COLUMN profiles.skill_keywords IS 'Array of taxonomy-matched skills (same format as postings.skill_keywords)';
COMMENT ON COLUMN profiles.profile_summary IS 'LLM-extracted professional summary (parallel to postings.extracted_summary)';
COMMENT ON COLUMN profiles.experience_level IS 'Classification: entry/junior/mid/senior/lead/executive';
COMMENT ON TABLE profile_job_matches IS 'Match scores between profiles and job postings';
COMMENT ON COLUMN profile_job_matches.overall_match_score IS 'Composite score from 0-100';
COMMENT ON COLUMN profile_job_matches.matched_skills IS 'Skills that overlap between profile and job';

-- ============================================================================
-- Verify schema
-- ============================================================================
SELECT 'Profile tables created successfully!' as status;

-- Show table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN (
    'profiles', 
    'profile_work_history', 
    'profile_education', 
    'profile_certifications',
    'profile_languages',
    'profile_job_matches'
)
ORDER BY tablename;
