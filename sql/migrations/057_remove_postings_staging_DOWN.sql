-- Migration: 057_remove_postings_staging_DOWN.sql
-- Description: Restore postings_staging table (NOT RECOMMENDED)
-- Date: 2024-12-02

-- WARNING: This restores the old pattern. Only use if absolutely necessary.

-- Restore from backup
CREATE TABLE IF NOT EXISTS postings_staging AS 
SELECT * FROM postings_staging_backup;

-- Recreate primary key
ALTER TABLE postings_staging ADD PRIMARY KEY (staging_id);

-- Recreate sequence
CREATE SEQUENCE IF NOT EXISTS postings_staging_staging_id_seq;
ALTER TABLE postings_staging ALTER COLUMN staging_id SET DEFAULT nextval('postings_staging_staging_id_seq');
SELECT setval('postings_staging_staging_id_seq', COALESCE((SELECT MAX(staging_id) FROM postings_staging), 1));

RAISE NOTICE '⚠️ postings_staging restored from backup. Remember to update db_job_fetcher.py!';
