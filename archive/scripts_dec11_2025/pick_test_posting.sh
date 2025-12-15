#!/bin/bash
# Pick a sample posting for Recipe 1114 test

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 SAMPLE POSTING FOR RECIPE 1114 TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

psql -h localhost -U base_admin -d base_yoga << 'SQL'
\pset border 2
\pset format wrapped

-- Pick one posting with good data
SELECT 
    job_id,
    job_title,
    organization_name,
    LEFT(job_description, 300) as description_preview,
    LENGTH(job_description) as description_length
FROM postings
WHERE job_description IS NOT NULL
  AND LENGTH(job_description) > 100
  AND enabled = true
ORDER BY LENGTH(job_description) DESC
LIMIT 5;

SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
