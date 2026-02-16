-- Migration: unique_active_external_id_20260216.sql
-- Prevent duplicate active postings with the same external_id.
--
-- Logic: a yogi can only apply to one posting per external_id, regardless
-- of whether the data provider published slightly different versions.
-- We keep historical duplicates (invalidated) for audit trail.
--
-- Already applied on production 2026-02-16.

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_postings_external_id_active
ON postings (external_id)
WHERE external_id IS NOT NULL AND invalidated = false AND enabled = true;
