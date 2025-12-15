-- Migration 014: Rename facets → capabilities
-- Date: October 31, 2025
-- Reason: More intuitive, self-documenting name for cognitive capability taxonomy
-- Historical note: Previously called "facets" - see rfa_latest/rfa_facets.md for full story

-- ============================================================================
-- PART 1: RENAME TABLES
-- ============================================================================

-- Rename main table
ALTER TABLE facets RENAME TO capabilities;

-- Rename history table
ALTER TABLE facets_history RENAME TO capabilities_history;

-- ============================================================================
-- PART 2: RENAME COLUMNS
-- ============================================================================

-- Rename primary key column
ALTER TABLE capabilities RENAME COLUMN facet_id TO capability_id;
ALTER TABLE capabilities RENAME COLUMN facet_name TO capability_name;
ALTER TABLE capabilities RENAME COLUMN parent_facet_name TO parent_capability_name;

-- Rename in history table
ALTER TABLE capabilities_history RENAME COLUMN facet_id TO capability_id;
ALTER TABLE capabilities_history RENAME COLUMN facet_name TO capability_name;
ALTER TABLE capabilities_history RENAME COLUMN parent_facet_name TO parent_capability_name;

-- ============================================================================
-- PART 3: RENAME SEQUENCES
-- ============================================================================

ALTER SEQUENCE facets_facet_id_seq RENAME TO capabilities_capability_id_seq;

-- ============================================================================
-- PART 4: RENAME CONSTRAINTS AND INDEXES
-- ============================================================================

-- Primary key constraint
ALTER TABLE capabilities RENAME CONSTRAINT facets_pkey TO capabilities_pkey;

-- Unique constraint
ALTER TABLE capabilities RENAME CONSTRAINT facets_facet_name_unique TO capabilities_capability_name_unique;

-- Foreign key constraint (self-referencing)
ALTER TABLE capabilities RENAME CONSTRAINT facets_parent_id_fkey TO capabilities_parent_id_fkey;

-- Indexes
ALTER INDEX idx_facets_enabled RENAME TO idx_capabilities_enabled;
ALTER INDEX idx_facets_parent RENAME TO idx_capabilities_parent;

-- ============================================================================
-- PART 5: UPDATE FOREIGN KEY IN CANONICALS TABLE
-- ============================================================================

-- Rename the FK constraint
ALTER TABLE canonicals RENAME CONSTRAINT canonicals_facet_id_fkey TO canonicals_capability_id_fkey;

-- Rename the column
ALTER TABLE canonicals RENAME COLUMN facet_id TO capability_id;

-- ============================================================================
-- PART 6: RENAME TRIGGER AND FUNCTION
-- ============================================================================

-- Drop old trigger
DROP TRIGGER IF EXISTS facets_history_trigger ON capabilities;

-- Rename the archive function
ALTER FUNCTION archive_facets() RENAME TO archive_capabilities;

-- Recreate trigger with new name
CREATE TRIGGER capabilities_history_trigger
    BEFORE UPDATE ON capabilities
    FOR EACH ROW
    EXECUTE FUNCTION archive_capabilities();

-- ============================================================================
-- PART 7: UPDATE COMMENTS WITH HISTORICAL REFERENCE
-- ============================================================================

COMMENT ON TABLE capabilities IS 
'Hierarchical taxonomy of cognitive/computational capabilities (74 entries).
HISTORICAL NOTE: Previously named "facets" - see rfa_latest/rfa_facets.md for the conceptual foundation.

PURPOSE: Theoretical framework for decomposing intelligence into measurable primitives.
- Classify what operations DO (reason, extract, follow rules, etc.)
- Map recipes to required cognitive capabilities
- Track LLM performance across fundamental ability categories
- Enable systematic capability-based recipe discovery

STRUCTURE: 9 root capabilities (single letters) + 65 child capabilities (2+ chars)
ROOT CAPABILITIES:
  c - Clean (normalize, filter, extract, audit)
  f - Fulfill (execute prompts, follow rules exactly)
  g - Group (categorize, cluster)
  k - Know (factual knowledge, recall)
  l - Learn (adapt, improve)
  m - Memory (context retention)
  o - Output (format, structure results)
  p - Plan (strategize, sequence)
  r - Reason (logic, inference)

DESIGN PRINCIPLE: Start from theoretical clarity - this is the periodic table of AI capabilities.
Links to canonicals table for standard test cases per capability.

Pattern: capability_id (INTEGER PK) + capability_name (TEXT UNIQUE).
Self-referencing: parent_id → capability_id.
Standardized 2025-10-30. Renamed from facets 2025-10-31.';

COMMENT ON COLUMN capabilities.capability_name IS 
'Unique capability identifier (natural key).
Examples: c, r, ce_char_extract, ff_exact_format_brackets, dynatax_skills
Naming: Root = 1 char, child = 2+ chars (parent prefix + descriptor)
Historical: previously facet_name';

COMMENT ON COLUMN capabilities.parent_capability_name IS 
'Parent capability for hierarchical capability organization.
NULL for root capabilities (c, f, g, k, l, m, o, p, r).
Child capabilities inherit and specialize parent capabilities.
Historical: previously parent_facet_name';

COMMENT ON COLUMN capabilities.short_description IS 
'Human-readable description of the cognitive capability.
Examples: "Clean", "Reason", "Extract characters / count target letter"';

COMMENT ON COLUMN capabilities.remarks IS 
'Additional notes, usage patterns, or design rationale for this capability.';

COMMENT ON COLUMN capabilities.enabled IS 
'Active flag - FALSE to disable capability from recipes/testing without deletion.
All 74 capabilities currently enabled (TRUE).';

COMMENT ON COLUMN capabilities.capability_id IS 
'Surrogate key - stable integer identifier for foreign key joins.
Used by canonicals table to link test cases to capabilities.
Historical: previously facet_id';

COMMENT ON COLUMN capabilities.parent_id IS 
'Self-referencing FK to parent capability (NULL for root capabilities).
Enables hierarchical queries and capability inheritance tracking.';

COMMENT ON TABLE capabilities_history IS 
'Archive of all changes to capabilities table.
Historical: previously facets_history.
See rfa_latest/rfa_facets.md for conceptual foundation.';

-- ============================================================================
-- PART 8: UPDATE CANONICALS COMMENTS
-- ============================================================================

COMMENT ON COLUMN canonicals.capability_id IS 
'FK to capabilities table - associates this canonical with a cognitive capability.
Historical: previously facet_id.';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify rename success
\echo '=== VERIFICATION ==='
\echo 'Checking capabilities table exists...'
SELECT COUNT(*) as total_capabilities FROM capabilities;

\echo ''
\echo 'Checking canonicals FK updated...'
SELECT COUNT(*) as canonicals_with_capabilities 
FROM canonicals 
WHERE capability_id IS NOT NULL;

\echo ''
\echo 'Checking history table...'
SELECT COUNT(*) as history_records FROM capabilities_history;

\echo ''
\echo 'Checking root capabilities...'
SELECT capability_name, short_description 
FROM capabilities 
WHERE parent_capability_name IS NULL 
ORDER BY capability_name;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

\echo ''
\echo '✅ Migration 014 complete: facets → capabilities'
\echo 'Historical reference: See rfa_latest/rfa_facets.md'
