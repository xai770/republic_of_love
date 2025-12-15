-- Add subject-centric columns to queue table
-- Allows queue to handle postings, skills, or other entity types

ALTER TABLE queue ADD COLUMN IF NOT EXISTS workflow_id INTEGER REFERENCES workflows(workflow_id);
ALTER TABLE queue ADD COLUMN IF NOT EXISTS subject_type VARCHAR(50) DEFAULT 'posting';
ALTER TABLE queue ADD COLUMN IF NOT EXISTS subject_id INTEGER;
ALTER TABLE queue ALTER COLUMN posting_id DROP NOT NULL;
