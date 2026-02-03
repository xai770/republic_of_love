-- Migration: Drop deprecated facet tables
-- Date: 2026-02-03
-- Reason: Embeddings handle skill matching, CPS facet extraction abandoned
-- 
-- Backup counts before drop:
--   profile_facets: 336 rows (4 profiles, experimental Clara/Diego pipeline)
--   posting_facets: 14,896 rows (legacy CPS competency extraction)
--
-- These tables were:
-- 1. profile_facets - Clara extracted CPS facets from profile work history
-- 2. posting_facets - Ava expanded competency_keywords to skill rows
--
-- Now: bge-m3 embeddings compare skill_keywords directly with posting text
-- No intermediate tables needed.

-- Drop profile_facets (336 rows)
DROP TABLE IF EXISTS profile_facets CASCADE;

-- Drop posting_facets (14,896 rows)  
DROP TABLE IF EXISTS posting_facets CASCADE;

-- Verify
-- \dt *facets* should return empty
