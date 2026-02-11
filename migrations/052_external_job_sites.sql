-- Migration: 052_external_job_sites.sql
-- Add external job site configuration to owl table
-- Date: 2026-02-07
--
-- This migration seeds owl with configuration for external job sites that AA
-- redirects to. Each entry maps an AA prefix to a scraper and site config.
--
-- Structure:
-- - owl_type = 'external_job_site'
-- - canonical_name = scraper key (e.g., 'jobvector')
-- - metadata = { aa_prefix, selector, scrapeable, ... }

-- ============================================================================
-- JOBVECTOR.DE (prefix: 12288)
-- ============================================================================
-- ~3,000 NULL descriptions
-- Site is scrapeable but requires URL mapping (AA doesn't provide external URL)
INSERT INTO owl (owl_type, canonical_name, status, metadata, description, created_by)
VALUES (
    'external_job_site',
    'jobvector',
    'active',
    '{
        "aa_prefix": "12288",
        "domain": "jobvector.de",
        "selector": "main article > div > div:nth-child(2)",
        "cookie_consent_selector": "button:has-text(\"Akzeptieren\")",
        "needs_playwright": true,
        "rate_limit_ms": 1000,
        "scrapeable": true,
        "notes": "URL mapping required - AA does not provide external URLs"
    }'::jsonb,
    'External job site: jobvector.de (IT/tech jobs). Prefix 12288.',
    'migration_052'
)
ON CONFLICT (owl_type, canonical_name) WHERE owl_type = 'external_job_site' AND canonical_name = 'jobvector'
DO UPDATE SET 
    metadata = EXCLUDED.metadata,
    description = EXCLUDED.description;

-- ============================================================================
-- STEPSTONE.DE (prefix: 18024)
-- ============================================================================
-- ~1,800 NULL descriptions
-- Site actively blocks scrapers
INSERT INTO owl (owl_type, canonical_name, status, metadata, description, created_by)
VALUES (
    'external_job_site',
    'stepstone',
    'active',
    '{
        "aa_prefix": "18024",
        "domain": "stepstone.de",
        "scrapeable": false,
        "skip_reason": "Site blocks automated access (Cloudflare, bot detection)",
        "notes": "Major job board - would need partnership or manual data entry"
    }'::jsonb,
    'External job site: stepstone.de (general jobs). Prefix 18024. NOT SCRAPEABLE.',
    'migration_052'
)
ON CONFLICT (owl_type, canonical_name) WHERE owl_type = 'external_job_site' AND canonical_name = 'stepstone'
DO UPDATE SET 
    metadata = EXCLUDED.metadata,
    description = EXCLUDED.description;

-- ============================================================================
-- HAYS.DE (prefix: 13319)
-- ============================================================================
-- ~400 NULL descriptions
-- Staffing agency - may redirect to various client sites
INSERT INTO owl (owl_type, canonical_name, status, metadata, description, created_by)
VALUES (
    'external_job_site',
    'hays',
    'active',
    '{
        "aa_prefix": "13319",
        "domain": "hays.de",
        "scrapeable": false,
        "skip_reason": "Staffing agency - redirects vary by job, complex extraction",
        "notes": "Would need per-job URL mapping"
    }'::jsonb,
    'External job site: hays.de (staffing agency). Prefix 13319.',
    'migration_052'
)
ON CONFLICT (owl_type, canonical_name) WHERE owl_type = 'external_job_site' AND canonical_name = 'hays'
DO UPDATE SET 
    metadata = EXCLUDED.metadata,
    description = EXCLUDED.description;

-- ============================================================================
-- UNKNOWN PREFIXES (mark as needs investigation)
-- ============================================================================
-- 12518, 14751, 14225, 11119, 12117, etc.
-- Add placeholder entries so the actor knows these exist but aren't configured

INSERT INTO owl (owl_type, canonical_name, status, metadata, description, created_by)
SELECT 
    'external_job_site',
    'unknown_' || prefix,
    'inactive',
    jsonb_build_object(
        'aa_prefix', prefix,
        'scrapeable', false,
        'skip_reason', 'Site not yet identified - needs investigation',
        'discovered_at', NOW()::text
    ),
    'Unknown external site for AA prefix ' || prefix || '. Needs investigation.',
    'migration_052'
FROM (
    SELECT DISTINCT split_part(external_id, '-', 2) AS prefix
    FROM postings
    WHERE source = 'arbeitsagentur'
      AND job_description IS NULL
      AND invalidated_at IS NULL
      AND external_id NOT LIKE 'aa-10001-%%'
      AND split_part(external_id, '-', 2) NOT IN ('12288', '18024', '13319')
    ORDER BY 1
    LIMIT 20
) unknown_prefixes
ON CONFLICT DO NOTHING;

-- ============================================================================
-- INDEX for efficient lookup
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_owl_external_job_site_prefix 
ON owl ((metadata->>'aa_prefix'))
WHERE owl_type = 'external_job_site';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM owl WHERE owl_type = 'external_job_site';
    RAISE NOTICE 'External job site entries: %', cnt;
END $$;
