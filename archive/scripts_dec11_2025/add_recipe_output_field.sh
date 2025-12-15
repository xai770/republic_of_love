#!/bin/bash
# Add output_data field to recipe_runs table

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'
-- Add output_data column to recipe_runs
ALTER TABLE recipe_runs 
ADD COLUMN IF NOT EXISTS output_data TEXT;

COMMENT ON COLUMN recipe_runs.output_data IS 'Final output from recipe execution (e.g., concise job description from Recipe 1114)';

-- Verify
\d recipe_runs

SQL
