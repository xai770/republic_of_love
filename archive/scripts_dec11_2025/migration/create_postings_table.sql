-- ================================================================
-- LLMCore Postings Table Creation and Data Import
-- Captures comprehensive job posting data for real-world validation
-- ================================================================

-- Create the postings table with comprehensive schema
CREATE TABLE IF NOT EXISTS postings (
    -- Primary Key from filename (job15929.json -> 15929)
    job_id TEXT NOT NULL PRIMARY KEY,
    
    -- Job Metadata Section
    metadata_version TEXT,
    metadata_created_at TIMESTAMP,
    metadata_last_modified TIMESTAMP,
    metadata_source TEXT,
    metadata_processor TEXT,
    metadata_status TEXT,
    
    -- Job Content Section
    job_title TEXT,
    job_description TEXT,
    job_requirements TEXT,  -- JSON array as TEXT
    
    -- Location Details
    location_city TEXT,
    location_state TEXT,
    location_country TEXT,
    location_remote_options INTEGER DEFAULT 0,
    
    -- Employment Details
    employment_type TEXT,
    employment_schedule TEXT,
    employment_career_level TEXT,
    employment_salary_range TEXT,
    employment_benefits TEXT,  -- JSON array as TEXT
    
    -- Organization Details
    organization_name TEXT,
    organization_division TEXT,
    organization_division_id INTEGER,
    
    -- Posting Details
    posting_publication_date DATE,
    posting_position_uri TEXT,
    posting_hiring_year TEXT,
    
    -- System Fields
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enabled INTEGER DEFAULT 1 CHECK(enabled IN (0, 1)),
    
    -- Analysis Fields (for future use)
    skill_keywords TEXT,     -- Extracted skills for matching
    complexity_score REAL,   -- Difficulty assessment
    processing_notes TEXT    -- Analysis notes
);

-- Create postings history table
CREATE TABLE IF NOT EXISTS postings_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    metadata_version TEXT,
    metadata_created_at TIMESTAMP,
    metadata_last_modified TIMESTAMP,
    metadata_source TEXT,
    metadata_processor TEXT,
    metadata_status TEXT,
    job_title TEXT,
    job_description TEXT,
    job_requirements TEXT,
    location_city TEXT,
    location_state TEXT,
    location_country TEXT,
    location_remote_options INTEGER,
    employment_type TEXT,
    employment_schedule TEXT,
    employment_career_level TEXT,
    employment_salary_range TEXT,
    employment_benefits TEXT,
    organization_name TEXT,
    organization_division TEXT,
    organization_division_id INTEGER,
    posting_publication_date DATE,
    posting_position_uri TEXT,
    posting_hiring_year TEXT,
    imported_at TIMESTAMP,
    updated_at TIMESTAMP,
    enabled INTEGER,
    skill_keywords TEXT,
    complexity_score REAL,
    processing_notes TEXT,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Create trigger for automatic history tracking
CREATE TRIGGER IF NOT EXISTS postings_history_trigger
    BEFORE UPDATE ON postings
    FOR EACH ROW
BEGIN
    INSERT INTO postings_history (
        job_id, metadata_version, metadata_created_at, metadata_last_modified,
        metadata_source, metadata_processor, metadata_status, job_title,
        job_description, job_requirements, location_city, location_state,
        location_country, location_remote_options, employment_type,
        employment_schedule, employment_career_level, employment_salary_range,
        employment_benefits, organization_name, organization_division,
        organization_division_id, posting_publication_date, posting_position_uri,
        posting_hiring_year, imported_at, updated_at, enabled, skill_keywords,
        complexity_score, processing_notes
    ) VALUES (
        OLD.job_id, OLD.metadata_version, OLD.metadata_created_at, OLD.metadata_last_modified,
        OLD.metadata_source, OLD.metadata_processor, OLD.metadata_status, OLD.job_title,
        OLD.job_description, OLD.job_requirements, OLD.location_city, OLD.location_state,
        OLD.location_country, OLD.location_remote_options, OLD.employment_type,
        OLD.employment_schedule, OLD.employment_career_level, OLD.employment_salary_range,
        OLD.employment_benefits, OLD.organization_name, OLD.organization_division,
        OLD.organization_division_id, OLD.posting_publication_date, OLD.posting_position_uri,
        OLD.posting_hiring_year, OLD.imported_at, OLD.updated_at, OLD.enabled, OLD.skill_keywords,
        OLD.complexity_score, OLD.processing_notes
    );
    
    -- Update timestamp in main table
    UPDATE postings SET updated_at = CURRENT_TIMESTAMP WHERE job_id = NEW.job_id;
END;
