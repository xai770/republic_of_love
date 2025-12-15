-- Migration 059: Cleanup postings table - part 2
-- Date: 2025-12-02
-- Purpose: Drop more unused columns and fix data

BEGIN;

-- Drop unused columns
ALTER TABLE postings DROP COLUMN IF EXISTS summary_extracted_at;
ALTER TABLE postings DROP COLUMN IF EXISTS summary_extraction_status;

-- Fill external_id from external_job_id (they should be the same)
UPDATE postings 
SET external_id = external_job_id 
WHERE external_id IS NULL AND external_job_id IS NOT NULL;

-- Extract location_country from job_description
-- Pattern: "Location: <City>, <Country>" in the job description
UPDATE postings
SET location_country = CASE
    WHEN job_description ILIKE '%Location:%India%' THEN 'India'
    WHEN job_description ILIKE '%Location:%Singapore%' THEN 'Singapore'
    WHEN job_description ILIKE '%Location:%Germany%' THEN 'Germany'
    WHEN job_description ILIKE '%Location:%United Kingdom%' THEN 'United Kingdom'
    WHEN job_description ILIKE '%Location:%UK%' THEN 'United Kingdom'
    WHEN job_description ILIKE '%Location:%USA%' THEN 'United States'
    WHEN job_description ILIKE '%Location:%United States%' THEN 'United States'
    WHEN location_city ILIKE '%India%' THEN 'India'
    WHEN location_city ILIKE '%Singapore%' THEN 'Singapore'
    WHEN location_city ILIKE '%Pune%' THEN 'India'
    WHEN location_city ILIKE '%Mumbai%' THEN 'India'
    WHEN location_city ILIKE '%Bangalore%' THEN 'India'
    WHEN location_city ILIKE '%Chennai%' THEN 'India'
    WHEN location_city ILIKE '%Delhi%' THEN 'India'
    WHEN location_city ILIKE '%London%' THEN 'United Kingdom'
    WHEN location_city ILIKE '%Frankfurt%' THEN 'Germany'
    WHEN location_city ILIKE '%Berlin%' THEN 'Germany'
    WHEN location_city ILIKE '%New York%' THEN 'United States'
    ELSE location_country
END
WHERE location_country IS NULL;

COMMIT;
