-- QA Findings Table
-- Stores data quality issues discovered during QA checks
-- Replaces file-based hallucination reports with queryable database storage

CREATE TABLE IF NOT EXISTS qa_findings (
    finding_id SERIAL PRIMARY KEY,
    
    -- What was checked
    posting_id INTEGER NOT NULL REFERENCES postings(posting_id),
    check_type VARCHAR(50) NOT NULL,  -- 'hallucination', 'length', 'processing_time', 'manual_review', etc.
    check_category VARCHAR(100),       -- Specific category (e.g., 'PLACEHOLDER', 'META_COMMENTARY', 'TOO_SHORT')
    
    -- The finding
    severity VARCHAR(20) NOT NULL,     -- 'high', 'medium', 'low', 'info'
    pattern_matched VARCHAR(100),      -- Which pattern triggered (e.g., 'template_session', 'too_long')
    description TEXT,                  -- Human-readable description
    evidence TEXT,                     -- Excerpt or sample showing the issue
    
    -- Context
    field_checked VARCHAR(50),         -- Which field was analyzed ('extracted_summary', 'job_description', etc.)
    field_length INTEGER,              -- Length of the field checked
    metric_value NUMERIC,              -- Quantitative metric (e.g., processing time in ms, repetition count)
    
    -- Metadata
    detected_at TIMESTAMP DEFAULT NOW(),
    detected_by VARCHAR(50),           -- 'qa_check_hallucinations.py', 'manual_review', etc.
    qa_run_id INTEGER,                 -- Group findings from same QA run
    
    -- Resolution
    status VARCHAR(20) DEFAULT 'open', -- 'open', 'reviewed', 'false_positive', 'fixed', 'wont_fix'
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMP,
    resolution_notes TEXT,
    
    -- Indexes for common queries
    CONSTRAINT qa_findings_check_type_check CHECK (check_type IN (
        'hallucination', 'length_outlier', 'processing_time_outlier', 
        'manual_review', 'data_quality', 'other'
    )),
    CONSTRAINT qa_findings_severity_check CHECK (severity IN ('high', 'medium', 'low', 'info'))
);

-- Indexes for efficient querying
CREATE INDEX idx_qa_findings_posting ON qa_findings(posting_id);
CREATE INDEX idx_qa_findings_check_type ON qa_findings(check_type);
CREATE INDEX idx_qa_findings_severity ON qa_findings(severity);
CREATE INDEX idx_qa_findings_status ON qa_findings(status);
CREATE INDEX idx_qa_findings_detected_at ON qa_findings(detected_at);
CREATE INDEX idx_qa_findings_qa_run ON qa_findings(qa_run_id);

-- View for open high-severity findings
CREATE OR REPLACE VIEW qa_critical_findings AS
SELECT 
    f.finding_id,
    f.posting_id,
    p.job_title,
    f.check_type,
    f.check_category,
    f.pattern_matched,
    f.description,
    f.detected_at,
    f.detected_by
FROM qa_findings f
JOIN postings p ON f.posting_id = p.posting_id
WHERE f.status = 'open' 
  AND f.severity = 'high'
ORDER BY f.detected_at DESC;

-- View for QA run summaries
CREATE OR REPLACE VIEW qa_run_summary AS
SELECT 
    qa_run_id,
    COUNT(*) as total_findings,
    COUNT(*) FILTER (WHERE severity = 'high') as high_severity,
    COUNT(*) FILTER (WHERE severity = 'medium') as medium_severity,
    COUNT(*) FILTER (WHERE severity = 'low') as low_severity,
    COUNT(DISTINCT posting_id) as postings_affected,
    COUNT(DISTINCT check_type) as check_types_run,
    MIN(detected_at) as run_started_at,
    MAX(detected_at) as run_completed_at,
    detected_by
FROM qa_findings
WHERE qa_run_id IS NOT NULL
GROUP BY qa_run_id, detected_by
ORDER BY qa_run_id DESC;

COMMENT ON TABLE qa_findings IS 'Stores data quality findings from automated and manual QA checks';
COMMENT ON COLUMN qa_findings.check_type IS 'Type of QA check performed';
COMMENT ON COLUMN qa_findings.check_category IS 'Specific category within the check type';
COMMENT ON COLUMN qa_findings.pattern_matched IS 'Name of the specific pattern that triggered this finding';
COMMENT ON COLUMN qa_findings.evidence IS 'Sample text or excerpt demonstrating the issue';
COMMENT ON COLUMN qa_findings.metric_value IS 'Quantitative metric associated with this finding';
COMMENT ON COLUMN qa_findings.qa_run_id IS 'Groups findings from the same QA execution';
