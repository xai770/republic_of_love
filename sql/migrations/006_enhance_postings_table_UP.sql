-- Migration: 006_enhance_postings_table_UP.sql
-- Description: Add Wave Runner V2 audit columns to postings table
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)
-- Reference: docs/WAVE_RUNNER_V2_DESIGN_DECISIONS.md (Decision #10)

-- Add audit trail columns
ALTER TABLE postings 
    ADD COLUMN IF NOT EXISTS created_by_interaction_id BIGINT REFERENCES interactions(interaction_id) ON DELETE SET NULL;

ALTER TABLE postings 
    ADD COLUMN IF NOT EXISTS updated_by_interaction_id BIGINT REFERENCES interactions(interaction_id) ON DELETE SET NULL;

ALTER TABLE postings 
    ADD COLUMN IF NOT EXISTS created_by_staging_id BIGINT REFERENCES postings_staging(staging_id) ON DELETE SET NULL;

-- Add invalidation flag
ALTER TABLE postings 
    ADD COLUMN IF NOT EXISTS invalidated BOOLEAN DEFAULT FALSE;

ALTER TABLE postings 
    ADD COLUMN IF NOT EXISTS invalidated_reason TEXT;

ALTER TABLE postings 
    ADD COLUMN IF NOT EXISTS invalidated_at TIMESTAMPTZ;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_postings_created_by_interaction ON postings(created_by_interaction_id);
CREATE INDEX IF NOT EXISTS idx_postings_staging ON postings(created_by_staging_id);
CREATE INDEX IF NOT EXISTS idx_postings_invalidated ON postings(invalidated) WHERE invalidated = TRUE;

-- Comments
COMMENT ON COLUMN postings.created_by_interaction_id IS 'Interaction that created this posting (audit trail)';
COMMENT ON COLUMN postings.updated_by_interaction_id IS 'Last interaction that updated this posting';
COMMENT ON COLUMN postings.created_by_staging_id IS 'Staging record that was promoted to create this posting';
COMMENT ON COLUMN postings.invalidated IS 'Is this posting invalid/corrupt? (NOT deletion)';
COMMENT ON COLUMN postings.invalidated_reason IS 'Why was this posting invalidated? (duplicate, bad data, etc.)';
