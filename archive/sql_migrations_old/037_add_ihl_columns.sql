-- Migration 037: Add IHL (Internal Hire Likelihood) tracking columns
-- Created: 2025-11-03
-- Purpose: Store fake job detector results directly in postings table

ALTER TABLE postings 
  ADD COLUMN ihl_score INTEGER,
  ADD COLUMN ihl_category TEXT,
  ADD COLUMN ihl_analyzed_at TIMESTAMP,
  ADD COLUMN ihl_workflow_run_id INTEGER REFERENCES workflow_runs(workflow_run_id);

-- Add check constraint for valid IHL scores (0-100)
ALTER TABLE postings 
  ADD CONSTRAINT ihl_score_valid CHECK (ihl_score IS NULL OR (ihl_score >= 0 AND ihl_score <= 100));

-- Add check constraint for valid categories
ALTER TABLE postings 
  ADD CONSTRAINT ihl_category_valid CHECK (
    ihl_category IS NULL OR 
    ihl_category IN ('OPEN SEARCH', 'COMPETITIVE', 'INTERNAL LIKELY', 'PRE-DETERMINED')
  );

-- Create index for IHL queries
CREATE INDEX idx_postings_ihl_score ON postings(ihl_score) WHERE ihl_score IS NOT NULL;
CREATE INDEX idx_postings_ihl_category ON postings(ihl_category) WHERE ihl_category IS NOT NULL;

COMMENT ON COLUMN postings.ihl_score IS 'Internal Hire Likelihood score (0-100): probability that position is pre-wired for internal candidate';
COMMENT ON COLUMN postings.ihl_category IS 'IHL category: OPEN SEARCH (10-30%), COMPETITIVE (40-60%), INTERNAL LIKELY (70-85%), PRE-DETERMINED (90-100%)';
COMMENT ON COLUMN postings.ihl_analyzed_at IS 'Timestamp when IHL analysis was performed';
COMMENT ON COLUMN postings.ihl_workflow_run_id IS 'Reference to workflow_run that generated this IHL score';
