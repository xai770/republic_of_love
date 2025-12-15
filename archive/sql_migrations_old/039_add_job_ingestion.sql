-- Migration 039: Job Ingestion Integration
-- Created: 2025-11-03
-- Purpose: Integrate ty_extract into Turing - complete end-to-end job processing pipeline
-- Philosophy: Everything is a workflow. Fetching is computation. Data flows through Turing.

-- ============================================================================
-- JOB SOURCES: Track external job APIs and data sources
-- ============================================================================

CREATE TABLE job_sources (
    source_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,  -- 'api', 'scraper', 'manual_upload', 'rss_feed'
    source_url TEXT,
    
    -- API Configuration (stored as JSONB for flexibility)
    api_config JSONB,
    -- Example: {
    --   "base_url": "https://api-deutschebank.beesite.de/search/",
    --   "headers": {"User-Agent": "...", "Content-Type": "application/json"},
    --   "auth_type": "none|api_key|oauth",
    --   "pagination": {"method": "offset", "page_size": 20}
    -- }
    
    -- Workflow Integration
    fetch_workflow_id INTEGER REFERENCES workflows(workflow_id),
    -- The workflow that knows how to fetch from this source
    
    -- Scheduling
    fetch_schedule TEXT,  -- 'manual', 'daily', 'weekly', 'hourly', or cron expression
    last_fetch_at TIMESTAMP,
    last_fetch_count INTEGER,
    next_fetch_at TIMESTAMP,
    
    -- Statistics
    total_jobs_fetched INTEGER DEFAULT 0,
    total_jobs_active INTEGER DEFAULT 0,
    
    -- Control
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,  -- 1-10, for scheduling priority
    
    -- Metadata
    description TEXT,
    notes TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_source_type CHECK (source_type IN ('api', 'scraper', 'manual_upload', 'rss_feed', 'webhook')),
    CONSTRAINT valid_priority CHECK (priority BETWEEN 1 AND 10)
);

CREATE INDEX idx_job_sources_active ON job_sources(is_active, priority);
CREATE INDEX idx_job_sources_next_fetch ON job_sources(next_fetch_at) WHERE is_active = true;

COMMENT ON TABLE job_sources IS 'External job data sources (APIs, scrapers, feeds) that feed into Turing';
COMMENT ON COLUMN job_sources.api_config IS 'JSONB config for API authentication, endpoints, pagination, etc.';
COMMENT ON COLUMN job_sources.fetch_workflow_id IS 'Workflow that executes the fetch operation for this source';

-- ============================================================================
-- JOB FETCH RUNS: Track each fetch operation
-- ============================================================================

CREATE TABLE job_fetch_runs (
    fetch_run_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES job_sources(source_id) ON DELETE CASCADE,
    workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id) ON DELETE SET NULL,
    -- Links to the workflow execution that performed the fetch
    
    -- Timing
    fetch_started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fetch_completed_at TIMESTAMP WITHOUT TIME ZONE,
    duration_ms INTEGER,
    
    -- Results
    jobs_fetched INTEGER DEFAULT 0,
    jobs_new INTEGER DEFAULT 0,
    jobs_updated INTEGER DEFAULT 0,
    jobs_duplicate INTEGER DEFAULT 0,
    jobs_error INTEGER DEFAULT 0,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'RUNNING',
    -- RUNNING, SUCCESS, PARTIAL_SUCCESS, ERROR
    error_message TEXT,
    
    -- Metadata
    fetch_metadata JSONB,
    -- Example: {
    --   "api_response_time_ms": 234,
    --   "pagination": {"pages_fetched": 5, "total_pages": 10},
    --   "rate_limit": {"remaining": 950, "reset_at": "2025-11-03T12:00:00Z"}
    -- }
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_fetch_status CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'ERROR'))
);

CREATE INDEX idx_fetch_runs_source ON job_fetch_runs(source_id, fetch_started_at DESC);
CREATE INDEX idx_fetch_runs_status ON job_fetch_runs(status, fetch_started_at DESC);
CREATE INDEX idx_fetch_runs_workflow ON job_fetch_runs(workflow_run_id);

COMMENT ON TABLE job_fetch_runs IS 'Execution log for each job fetch operation';
COMMENT ON COLUMN job_fetch_runs.fetch_metadata IS 'API response metadata, rate limits, pagination info, etc.';

-- ============================================================================
-- EXTEND POSTINGS: Link to source and fetch tracking
-- ============================================================================

ALTER TABLE postings 
    ADD COLUMN source_id INTEGER REFERENCES job_sources(source_id),
    ADD COLUMN fetch_run_id INTEGER REFERENCES job_fetch_runs(fetch_run_id),
    ADD COLUMN external_job_id TEXT,  -- Original ID from source API (e.g., "R0380583")
    ADD COLUMN external_url TEXT,     -- Direct link to job on external site
    ADD COLUMN fetched_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN last_checked_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN fetch_hash TEXT;  -- SHA256 of job content to detect changes

CREATE INDEX idx_postings_source ON postings(source_id);
CREATE INDEX idx_postings_external_id ON postings(source_id, external_job_id);
CREATE UNIQUE INDEX idx_postings_external_unique ON postings(source_id, external_job_id) WHERE external_job_id IS NOT NULL;
CREATE INDEX idx_postings_fetched_at ON postings(fetched_at DESC);
CREATE INDEX idx_postings_fetch_hash ON postings(fetch_hash);

COMMENT ON COLUMN postings.source_id IS 'Which job source this posting came from';
COMMENT ON COLUMN postings.external_job_id IS 'Original job ID from external system (for deduplication and updates)';
COMMENT ON COLUMN postings.fetch_hash IS 'Content hash to detect if job description has changed';

-- ============================================================================
-- PROCESSING PIPELINE TRACKING
-- ============================================================================

CREATE TABLE posting_processing_status (
    posting_id INTEGER PRIMARY KEY REFERENCES postings(posting_id) ON DELETE CASCADE,
    
    -- Processing stages
    summary_extracted BOOLEAN DEFAULT false,
    summary_extracted_at TIMESTAMP,
    summary_workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id),
    
    skills_extracted BOOLEAN DEFAULT false,
    skills_extracted_at TIMESTAMP,
    skills_workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id),
    
    ihl_analyzed BOOLEAN DEFAULT false,
    ihl_analyzed_at TIMESTAMP,
    ihl_workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id),
    
    candidates_matched BOOLEAN DEFAULT false,
    candidates_matched_at TIMESTAMP,
    matching_workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id),
    
    -- Overall status
    processing_complete BOOLEAN GENERATED ALWAYS AS (
        summary_extracted AND skills_extracted AND ihl_analyzed
    ) STORED,
    
    last_processed_at TIMESTAMP WITHOUT TIME ZONE,
    processing_notes TEXT
);

CREATE INDEX idx_posting_processing_incomplete ON posting_processing_status(posting_id) 
    WHERE NOT processing_complete;
CREATE INDEX idx_posting_processing_stages ON posting_processing_status(
    summary_extracted, skills_extracted, ihl_analyzed, candidates_matched
);

COMMENT ON TABLE posting_processing_status IS 'Track which processing stages have been completed for each posting';
COMMENT ON COLUMN posting_processing_status.processing_complete IS 'Auto-computed: true when summary, skills, and IHL are all extracted';

-- ============================================================================
-- SEED DATA: Deutsche Bank API Source
-- ============================================================================

INSERT INTO job_sources (
    source_name,
    source_type,
    source_url,
    api_config,
    fetch_schedule,
    priority,
    description,
    is_active
) VALUES (
    'Deutsche Bank Careers API',
    'api',
    'https://api-deutschebank.beesite.de/search/',
    jsonb_build_object(
        'base_url', 'https://api-deutschebank.beesite.de/search/',
        'career_site_base', 'https://careers.db.com',
        'headers', jsonb_build_object(
            'Content-Type', 'application/json',
            'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        ),
        'pagination', jsonb_build_object(
            'method', 'offset',
            'page_size', 20,
            'max_pages', 10
        ),
        'rate_limit', jsonb_build_object(
            'requests_per_minute', 60,
            'retry_on_limit', true
        )
    ),
    'daily',
    8,
    'Deutsche Bank job postings API - primary source for banking roles',
    true
);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: Recent fetch activity
CREATE VIEW v_recent_fetch_activity AS
SELECT 
    js.source_name,
    jfr.fetch_run_id,
    jfr.fetch_started_at,
    jfr.duration_ms,
    jfr.jobs_fetched,
    jfr.jobs_new,
    jfr.jobs_updated,
    jfr.status,
    wr.workflow_name
FROM job_fetch_runs jfr
JOIN job_sources js ON js.source_id = jfr.source_id
LEFT JOIN workflow_runs wr ON wr.workflow_run_id = jfr.workflow_run_id
LEFT JOIN workflows w ON w.workflow_id = wr.workflow_id
ORDER BY jfr.fetch_started_at DESC
LIMIT 100;

COMMENT ON VIEW v_recent_fetch_activity IS 'Recent job fetch operations with status and results';

-- View: Processing pipeline status summary
CREATE VIEW v_processing_pipeline_status AS
SELECT 
    COUNT(*) as total_postings,
    COUNT(*) FILTER (WHERE summary_extracted) as with_summary,
    COUNT(*) FILTER (WHERE skills_extracted) as with_skills,
    COUNT(*) FILTER (WHERE ihl_analyzed) as with_ihl,
    COUNT(*) FILTER (WHERE candidates_matched) as with_matches,
    COUNT(*) FILTER (WHERE processing_complete) as complete,
    COUNT(*) FILTER (WHERE NOT processing_complete) as incomplete,
    ROUND(COUNT(*) FILTER (WHERE processing_complete)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as completion_percentage
FROM posting_processing_status;

COMMENT ON VIEW v_processing_pipeline_status IS 'Overall pipeline processing statistics';

-- View: Source health dashboard
CREATE VIEW v_source_health AS
SELECT 
    js.source_name,
    js.is_active,
    js.last_fetch_at,
    js.total_jobs_fetched,
    COUNT(jfr.fetch_run_id) as total_fetch_runs,
    COUNT(jfr.fetch_run_id) FILTER (WHERE jfr.status = 'SUCCESS') as successful_runs,
    COUNT(jfr.fetch_run_id) FILTER (WHERE jfr.status = 'ERROR') as failed_runs,
    AVG(jfr.duration_ms) FILTER (WHERE jfr.status = 'SUCCESS') as avg_fetch_duration_ms,
    SUM(jfr.jobs_new) as total_new_jobs,
    MAX(jfr.fetch_started_at) as last_run_at
FROM job_sources js
LEFT JOIN job_fetch_runs jfr ON jfr.source_id = js.source_id
GROUP BY js.source_id, js.source_name, js.is_active, js.last_fetch_at, js.total_jobs_fetched;

COMMENT ON VIEW v_source_health IS 'Health metrics for each job source';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_source_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Update job_sources statistics when a fetch completes
    IF NEW.status IN ('SUCCESS', 'PARTIAL_SUCCESS') AND OLD.status = 'RUNNING' THEN
        UPDATE job_sources
        SET 
            last_fetch_at = NEW.fetch_completed_at,
            last_fetch_count = NEW.jobs_fetched,
            total_jobs_fetched = total_jobs_fetched + NEW.jobs_new,
            updated_at = CURRENT_TIMESTAMP
        WHERE source_id = NEW.source_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_source_stats
    AFTER UPDATE ON job_fetch_runs
    FOR EACH ROW
    WHEN (OLD.status = 'RUNNING' AND NEW.status IN ('SUCCESS', 'PARTIAL_SUCCESS', 'ERROR'))
    EXECUTE FUNCTION update_source_stats();

COMMENT ON FUNCTION update_source_stats IS 'Auto-update job_sources statistics when fetch completes';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
DECLARE
    source_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO source_count FROM job_sources;
    
    RAISE NOTICE '✅ Migration 039 complete: Job Ingestion Integration';
    RAISE NOTICE '   - Created job_sources table (% sources)', source_count;
    RAISE NOTICE '   - Created job_fetch_runs table';
    RAISE NOTICE '   - Extended postings table with source tracking';
    RAISE NOTICE '   - Created posting_processing_status table';
    RAISE NOTICE '   - Created 3 helper views for monitoring';
    RAISE NOTICE '   - Created auto-update trigger for source stats';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Next Steps:';
    RAISE NOTICE '   1. Create Workflow 2001 (Job Ingestion Pipeline)';
    RAISE NOTICE '   2. Migrate job_api_fetcher_v6.py into Turing actors';
    RAISE NOTICE '   3. Run: SELECT * FROM v_source_health;';
END $$;
