-- Curated Schema Cleanup Migration
-- Generated: 2025-11-30
-- Author: Arden
-- 
-- This migration drops ONLY truly dead columns, preserving:
-- - Future feature scaffolding (interaction_lineage, workflow_triggers, profile matching)
-- - Self-documenting metadata (input_format, output_format, example_call)
-- - Event sourcing fields (invalidation_reason)
--
-- Categories:
-- 1. CONSTANT columns with no business value (always same value)
-- 2. EMPTY columns in tables that ARE being used
-- 3. Deprecated tracking columns superseded by better designs
--
-- EXCLUDES (intentionally kept):
-- - interaction_lineage.* (future: causation graphs)
-- - workflow_dependencies.* (future: cross-workflow orchestration)
-- - workflow_triggers.* (future: event-driven workflows)
-- - actors.input_format/output_format/example_call (contract documentation)
-- - execution_events.invalidation_reason (event sourcing correction)
-- - profile_*.* (future: user profile matching)

BEGIN;

-- ============================================================
-- SECTION 1: Constant columns with no business value
-- These always have the same value - no information content
-- ============================================================

-- conversation_runs: run_type always 'production', dialogue_round always 1
ALTER TABLE conversation_runs DROP COLUMN IF EXISTS run_type;
ALTER TABLE conversation_runs DROP COLUMN IF EXISTS dialogue_round;

-- conversations: app_scope always 'talent'
ALTER TABLE conversations DROP COLUMN IF EXISTS app_scope;

-- execution_events: event_version always 1 (we don't version events)
ALTER TABLE execution_events DROP COLUMN IF EXISTS event_version;

-- ============================================================
-- SECTION 2: Empty columns in active tables
-- Tables are used, but these specific columns never populated
-- ============================================================

-- actor_rate_control: single test row, columns never used
ALTER TABLE actor_rate_control DROP COLUMN IF EXISTS next_allowed_at;

-- human_tasks: timeout not implemented
ALTER TABLE human_tasks DROP COLUMN IF EXISTS timeout_at;

-- conversation_dialogue: reads_from_step_ids never populated
ALTER TABLE conversation_dialogue DROP COLUMN IF EXISTS reads_from_step_ids;

-- llm_interactions: dialogue tracking never implemented
ALTER TABLE llm_interactions DROP COLUMN IF EXISTS dialogue_step_run_id;

-- ============================================================
-- SECTION 3: Deprecated tracking in posting_processing_status
-- This table duplicates what's now tracked better elsewhere
-- These boolean flags are superseded by postings.* columns
-- ============================================================

ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS summary_extracted;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS summary_workflow_run_id;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS skills_extracted_at;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS skills_workflow_run_id;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS ihl_analyzed;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS candidates_matched;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS candidates_matched_at;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS matching_workflow_run_id;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS processing_complete;
ALTER TABLE posting_processing_status DROP COLUMN IF EXISTS last_processed_at;

-- ============================================================
-- SECTION 4: Empty metadata columns in job_sources
-- Source is configured, but these fields never populated
-- ============================================================

ALTER TABLE job_sources DROP COLUMN IF EXISTS next_fetch_at;

-- ============================================================
-- SECTION 5: Empty state tracking in posting_state_*
-- Event sourcing replaces these with execution_events
-- ============================================================

ALTER TABLE posting_state_projection DROP COLUMN IF EXISTS conversation_history;
ALTER TABLE posting_state_projection DROP COLUMN IF EXISTS total_duration_ms;
ALTER TABLE posting_state_projection DROP COLUMN IF EXISTS last_event_id;
ALTER TABLE posting_state_projection DROP COLUMN IF EXISTS projection_version;

ALTER TABLE posting_state_snapshots DROP COLUMN IF EXISTS aggregate_version;
ALTER TABLE posting_state_snapshots DROP COLUMN IF EXISTS snapshot_data;

-- ============================================================
-- SECTION 6: Empty field mapping columns
-- Schema exists but feature not implemented
-- ============================================================

ALTER TABLE posting_field_mappings DROP COLUMN IF EXISTS source_query;
ALTER TABLE posting_field_mappings DROP COLUMN IF EXISTS default_value;
ALTER TABLE posting_field_mappings DROP COLUMN IF EXISTS source_field_name;
ALTER TABLE posting_field_mappings DROP COLUMN IF EXISTS target_field_name;
ALTER TABLE posting_field_mappings DROP COLUMN IF EXISTS transformation_rule;

-- ============================================================
-- SECTION 7: Empty placeholder columns
-- Feature designed but not implemented
-- ============================================================

ALTER TABLE placeholder_definitions DROP COLUMN IF EXISTS default_value;

-- ============================================================
-- SECTION 8: Organizations table (completely empty)
-- Keep table structure but drop empty metadata columns
-- ============================================================

ALTER TABLE organizations DROP COLUMN IF EXISTS organization_type;
ALTER TABLE organizations DROP COLUMN IF EXISTS contact_email;
ALTER TABLE organizations DROP COLUMN IF EXISTS contact_phone;
ALTER TABLE organizations DROP COLUMN IF EXISTS website_url;

-- ============================================================
-- VERIFY
-- ============================================================

-- Count columns after cleanup
SELECT 
    'Tables' as metric,
    COUNT(DISTINCT table_name)::text as count
FROM information_schema.columns 
WHERE table_schema = 'public'
UNION ALL
SELECT 
    'Columns' as metric,
    COUNT(*)::text as count
FROM information_schema.columns 
WHERE table_schema = 'public';

COMMIT;

-- ============================================================
-- SUMMARY
-- ============================================================
-- Dropped: ~40 columns
-- Preserved: ~850 columns
-- 
-- Kept for future features:
-- - interaction_lineage (causation graphs)
-- - workflow_dependencies (meta-workflows)
-- - workflow_triggers (event-driven)
-- - profile_* tables (user matching)
-- - actors.input_format/output_format (contracts)
-- - stored_scripts.* (script versioning)
--
-- Run: sudo -u postgres psql -d turing -f sql/migrations/055_curated_schema_cleanup.sql
