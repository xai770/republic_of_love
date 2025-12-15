-- Deutsche Bank Job Market Analysis - Quick Query Reference
-- Database: turing, Table: postings (source_id=1)
-- Generated: November 9, 2025

-- ============================================================================
-- DATA OVERVIEW
-- ============================================================================

-- Basic dataset statistics
SELECT 
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE posting_status = 'active') as active_jobs,
    COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as with_skills,
    COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as with_ihl,
    ROUND(AVG(LENGTH(job_description))) as avg_desc_length,
    ROUND(AVG(jsonb_array_length(skill_keywords))) as avg_skills_per_job
FROM postings WHERE source_id = 1;

-- Skills extraction quality
SELECT 
    COUNT(*) as jobs_with_skills,
    MIN(jsonb_array_length(skill_keywords)) as min_skills,
    MAX(jsonb_array_length(skill_keywords)) as max_skills,
    ROUND(AVG(jsonb_array_length(skill_keywords)), 1) as avg_skills,
    ROUND(STDDEV(jsonb_array_length(skill_keywords)), 1) as stddev
FROM postings WHERE source_id = 1 AND skill_keywords IS NOT NULL;

-- ============================================================================
-- SKILLS ANALYSIS
-- ============================================================================

-- Top 30 skills (case-insensitive)
SELECT 
    LOWER(skill->>'skill') as skill_name,
    COUNT(DISTINCT posting_id) as job_count,
    ROUND(100.0 * COUNT(DISTINCT posting_id) / 
          (SELECT COUNT(*) FROM postings WHERE source_id=1 AND skill_keywords IS NOT NULL), 
          1) as pct_of_jobs
FROM postings, jsonb_array_elements(skill_keywords) as skill
WHERE source_id = 1 AND skill_keywords IS NOT NULL
GROUP BY LOWER(skill->>'skill')
ORDER BY job_count DESC
LIMIT 30;

-- Skills by importance level
SELECT 
    skill->>'importance' as importance_level,
    COUNT(*) as skill_mentions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct_of_total,
    ROUND(AVG((skill->>'weight')::int), 1) as avg_weight
FROM postings, jsonb_array_elements(skill_keywords) as skill
WHERE source_id = 1 AND skill_keywords IS NOT NULL
GROUP BY skill->>'importance'
ORDER BY 
    CASE skill->>'importance'
        WHEN 'essential' THEN 1
        WHEN 'critical' THEN 2
        WHEN 'important' THEN 3
        WHEN 'preferred' THEN 4
        ELSE 5
    END;

-- Find jobs requiring specific skill (e.g., Java)
SELECT posting_id, job_title
FROM postings
WHERE source_id = 1 
  AND posting_status = 'active'
  AND skill_keywords @> '[{"skill": "Java"}]'::jsonb;

-- ============================================================================
-- GEOGRAPHIC ANALYSIS
-- ============================================================================

-- Cities mentioned in job descriptions
SELECT 
    SUBSTRING(job_description FROM '(?i)(frankfurt|london|new york|singapore|hong kong|tokyo|mumbai|berlin|paris|dubai|sydney|toronto|zürich|amsterdam)') as city,
    COUNT(*) as mention_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct_of_mentions
FROM postings
WHERE source_id = 1 
  AND posting_status = 'active'
  AND job_description ~* '(frankfurt|london|new york|singapore|hong kong|tokyo|mumbai|berlin|paris|dubai|sydney|toronto|zürich|amsterdam)'
GROUP BY city
ORDER BY mention_count DESC;

-- ============================================================================
-- CAREER LEVEL ANALYSIS
-- ============================================================================

-- Infer seniority from job titles
SELECT 
    CASE 
        WHEN job_title ILIKE '%vp%' OR job_title ILIKE '%vice president%' THEN 'VP'
        WHEN job_title ILIKE '%director%' THEN 'Director'
        WHEN job_title ILIKE '%senior%' THEN 'Senior'
        WHEN job_title ILIKE '%manager%' THEN 'Manager'
        WHEN job_title ILIKE '%analyst%' THEN 'Analyst'
        WHEN job_title ILIKE '%associate%' THEN 'Associate'
        WHEN job_title ILIKE '%specialist%' THEN 'Specialist'
        WHEN job_title ILIKE '%junior%' THEN 'Junior'
        ELSE 'Other'
    END as seniority,
    COUNT(*) as job_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct_of_total
FROM postings
WHERE source_id = 1 AND posting_status = 'active'
GROUP BY seniority
ORDER BY job_count DESC;

-- ============================================================================
-- IHL ANALYSIS (FAKE JOB DETECTION)
-- ============================================================================

-- IHL category distribution
SELECT 
    COALESCE(ihl_category, 'Not analyzed') as category,
    COUNT(*) as job_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct,
    ROUND(AVG(ihl_score), 1) as avg_score,
    MIN(ihl_score) as min_score,
    MAX(ihl_score) as max_score
FROM postings
WHERE source_id = 1
GROUP BY ihl_category
ORDER BY AVG(ihl_score) NULLS LAST;

-- Jobs flagged as potentially fake (IHL > 70%)
SELECT 
    posting_id,
    job_title,
    ihl_score,
    ihl_category,
    ihl_analyzed_at
FROM postings
WHERE source_id = 1 
  AND ihl_score > 70
ORDER BY ihl_score DESC;

-- ============================================================================
-- CROSS-TABULATIONS
-- ============================================================================

-- Skills by inferred seniority
SELECT 
    CASE 
        WHEN job_title ILIKE '%vp%' THEN 'VP'
        WHEN job_title ILIKE '%director%' THEN 'Director'
        WHEN job_title ILIKE '%senior%' THEN 'Senior'
        WHEN job_title ILIKE '%analyst%' THEN 'Analyst'
        ELSE 'Other'
    END as seniority,
    LOWER(skill->>'skill') as skill_name,
    COUNT(*) as occurrences
FROM postings, jsonb_array_elements(skill_keywords) as skill
WHERE source_id = 1 AND skill_keywords IS NOT NULL
GROUP BY seniority, LOWER(skill->>'skill')
HAVING COUNT(*) >= 5
ORDER BY seniority, occurrences DESC;

-- IHL by inferred seniority
SELECT 
    CASE 
        WHEN job_title ILIKE '%vp%' THEN 'VP'
        WHEN job_title ILIKE '%senior%' THEN 'Senior'
        WHEN job_title ILIKE '%analyst%' THEN 'Analyst'
        ELSE 'Other'
    END as seniority,
    COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as ihl_analyzed,
    ROUND(AVG(ihl_score), 1) as avg_ihl_score,
    COUNT(*) FILTER (WHERE ihl_category = 'COMPETITIVE') as competitive_jobs
FROM postings
WHERE source_id = 1
GROUP BY seniority
ORDER BY ihl_analyzed DESC;

-- ============================================================================
-- DATA QUALITY CHECKS
-- ============================================================================

-- Jobs missing skills (potential extraction failures)
SELECT 
    posting_id,
    job_title,
    LENGTH(job_description) as desc_length,
    posting_status
FROM postings
WHERE source_id = 1
  AND (skill_keywords IS NULL OR jsonb_array_length(skill_keywords) = 0)
ORDER BY desc_length DESC;

-- Skills without importance level (data quality issue)
SELECT 
    skill->>'skill' as skill_name,
    COUNT(*) as mentions
FROM postings, jsonb_array_elements(skill_keywords) as skill
WHERE source_id = 1 
  AND skill_keywords IS NOT NULL
  AND skill->>'importance' IS NULL
GROUP BY skill->>'skill'
ORDER BY mentions DESC;

-- ============================================================================
-- EXPORT QUERIES
-- ============================================================================

-- Export top skills to CSV
COPY (
    SELECT 
        LOWER(skill->>'skill') as skill_name,
        COUNT(DISTINCT posting_id) as job_count,
        ROUND(100.0 * COUNT(DISTINCT posting_id) / 
              (SELECT COUNT(*) FROM postings WHERE source_id=1 AND skill_keywords IS NOT NULL), 
              2) as pct_of_jobs,
        string_agg(DISTINCT skill->>'importance', ', ') as importance_levels,
        ROUND(AVG((skill->>'weight')::int), 1) as avg_weight
    FROM postings, jsonb_array_elements(skill_keywords) as skill
    WHERE source_id = 1 AND skill_keywords IS NOT NULL
    GROUP BY LOWER(skill->>'skill')
    HAVING COUNT(DISTINCT posting_id) >= 10
    ORDER BY job_count DESC
) TO '/tmp/deutsche_bank_top_skills.csv' WITH CSV HEADER;

-- Export jobs with location/seniority/IHL for analysis
COPY (
    SELECT 
        posting_id,
        job_title,
        CASE 
            WHEN job_title ILIKE '%vp%' THEN 'VP'
            WHEN job_title ILIKE '%senior%' THEN 'Senior'
            WHEN job_title ILIKE '%analyst%' THEN 'Analyst'
            ELSE 'Other'
        END as inferred_seniority,
        SUBSTRING(job_description FROM '(?i)(frankfurt|london|new york|mumbai|berlin)') as inferred_city,
        jsonb_array_length(skill_keywords) as num_skills,
        ihl_score,
        ihl_category,
        posting_status,
        fetched_at
    FROM postings
    WHERE source_id = 1
) TO '/tmp/deutsche_bank_jobs_full.csv' WITH CSV HEADER;
