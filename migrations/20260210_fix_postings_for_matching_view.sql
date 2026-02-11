-- Fix postings_for_matching view to:
-- 1. Exclude posting_status = 'invalid' (HTML-bloated postings)
-- 2. Require job_description > 150 chars (bge-m3 returns NaN for shorter texts)
-- 
-- Run date: 2026-02-10

CREATE OR REPLACE VIEW postings_for_matching AS
SELECT postings.posting_id,
    postings.posting_name,
    postings.enabled,
    postings.job_description,
    postings.job_title,
    postings.location_city,
    postings.location_country,
    postings.ihl_score,
    postings.external_job_id,
    postings.external_url,
    postings.posting_status,
    postings.first_seen_at,
    postings.last_seen_at,
    postings.source_metadata,
    postings.updated_at,
    postings.extracted_summary,
    postings.source,
    postings.external_id,
    postings.invalidated,
    postings.processing_failures,
    postings.source_language,
    postings.domain_gate,
    COALESCE(postings.extracted_summary, postings.job_description) AS match_text
FROM postings
WHERE postings.job_description IS NOT NULL 
  AND length(postings.job_description) > 150
  AND postings.invalidated = false
  AND postings.posting_status != 'invalid';
