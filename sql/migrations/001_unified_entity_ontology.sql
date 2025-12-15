-- ============================================================================
-- MIGRATION 001: Unified Entity Ontology
-- ============================================================================
-- Author: Sandy (with Arden's refinements)
-- Date: 2025-12-07
-- Status: Phase 1 - Schema Only (No Data Migration)
--
-- Purpose: Create universal entity registry for RAQ-compliant matching
--          (Repeatability, Auditability, QA)
--
-- See: docs/architecture/UNIFIED_ENTITY_ONTOLOGY.md
--      docs/daily/2025-12-07_turing_registry.md
-- ============================================================================

BEGIN;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Things exist
CREATE TABLE IF NOT EXISTS entities (
    entity_id             SERIAL PRIMARY KEY,
    entity_type           TEXT NOT NULL,           -- 'skill', 'city', 'country', 'event', 'legal_term'
    canonical_name        TEXT NOT NULL,           -- Immutable reference key (lowercase, underscored)
    created_at            TIMESTAMP DEFAULT now(),
    created_by            TEXT,
    metadata              JSONB,                   -- Type-specific data
    
    -- ARDEN REFINEMENT: Entity lifecycle management
    status                TEXT DEFAULT 'active',   -- 'active', 'deprecated', 'merged', 'pending_review'
    merged_into_entity_id INT REFERENCES entities(entity_id),  -- If status='merged', points to canonical
    
    UNIQUE(entity_type, canonical_name)
);

COMMENT ON TABLE entities IS 'The universal registry of things that exist';
COMMENT ON COLUMN entities.canonical_name IS 'The One True Name - never displayed, only referenced. Lowercase with underscores.';
COMMENT ON COLUMN entities.status IS 'Entity lifecycle: active (normal), deprecated (phasing out), merged (replaced by merged_into_entity_id), pending_review (needs human QA)';

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_status ON entities(status);
CREATE INDEX idx_entities_canonical ON entities(canonical_name);

-- ============================================================================

-- Things have names in languages
CREATE TABLE IF NOT EXISTS entity_names (
    entity_id        INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    language         TEXT NOT NULL DEFAULT 'en',  -- ISO 639-1
    display_name     TEXT NOT NULL,               -- Human-readable name with spaces
    is_primary       BOOLEAN DEFAULT false,       -- Primary name for this language
    confidence       NUMERIC(3,2) DEFAULT 1.0,    -- How sure are we this name is correct?
    created_at       TIMESTAMP DEFAULT now(),
    
    PRIMARY KEY (entity_id, language, display_name)
);

CREATE INDEX idx_entity_names_lookup ON entity_names(display_name, language);
CREATE INDEX idx_entity_names_primary ON entity_names(entity_id, language) WHERE is_primary = true;

COMMENT ON TABLE entity_names IS 'How entities are displayed to humans, by language';
COMMENT ON COLUMN entity_names.display_name IS 'Human-readable name with proper spacing and capitalization';

-- ============================================================================

-- Things are called many things
CREATE TABLE IF NOT EXISTS entity_aliases (
    alias_id         SERIAL PRIMARY KEY,
    entity_id        INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    alias            TEXT NOT NULL,               -- 'AWS', 'München', 'Big Apple'
    language         TEXT DEFAULT 'en',
    alias_type       TEXT DEFAULT 'abbreviation', -- 'abbreviation', 'colloquial', 'historical', 'typo', 'acronym'
    confidence       NUMERIC(3,2) DEFAULT 1.0,
    created_at       TIMESTAMP DEFAULT now(),
    
    -- ARDEN REFINEMENT: Track decision provenance
    provenance       JSONB,                       -- {"model": "qwen2.5:7b", "decision_id": 123, "reasoning": "..."}
    
    UNIQUE(alias, language)                       -- One alias maps to one entity per language
);

CREATE INDEX idx_entity_aliases_lookup ON entity_aliases(alias, language);
CREATE INDEX idx_entity_aliases_entity ON entity_aliases(entity_id);

COMMENT ON TABLE entity_aliases IS 'Alternative names, abbreviations, misspellings that resolve to entities';
COMMENT ON COLUMN entity_aliases.alias_type IS 'Why this alias exists - helps with matching confidence';
COMMENT ON COLUMN entity_aliases.provenance IS 'Who/what created this alias and why (JSON with model, decision_id, reasoning)';

-- ============================================================================

-- ARDEN REFINEMENT: Multi-parent relationships (graph model, not strict tree)
CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id   SERIAL PRIMARY KEY,
    entity_id         INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    related_entity_id INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'is_a',        -- 'is_a', 'located_in', 'part_of', 'instance_of', 'same_as'
    strength          NUMERIC(3,2) DEFAULT 1.0,
    is_primary        BOOLEAN DEFAULT false,      -- Primary parent for display purposes
    created_at        TIMESTAMP DEFAULT now(),
    
    -- ARDEN REFINEMENT: Track decision provenance
    provenance        JSONB,                      -- {"model": "qwen2.5:7b", "decision_id": 123, "reasoning": "..."}
    
    UNIQUE(entity_id, related_entity_id, relationship_type),
    CHECK (entity_id != related_entity_id)
);

CREATE INDEX idx_entity_relationships_entity ON entity_relationships(entity_id);
CREATE INDEX idx_entity_relationships_related ON entity_relationships(related_entity_id);
CREATE INDEX idx_entity_relationships_type ON entity_relationships(relationship_type);
CREATE INDEX idx_entity_relationships_primary ON entity_relationships(entity_id) WHERE is_primary = true;

COMMENT ON TABLE entity_relationships IS 'Graph of entity relationships - allows multiple parents (multi-parent graph, not strict tree)';
COMMENT ON COLUMN entity_relationships.relationship_type IS 'Nature of relationship: is_a (taxonomy), located_in (geography), part_of (composition), instance_of (occurrence), same_as (identity/merge)';
COMMENT ON COLUMN entity_relationships.is_primary IS 'For entities with multiple parents, which one is "canonical" for display/navigation';
COMMENT ON COLUMN entity_relationships.provenance IS 'Who/what created this relationship and why';

-- ============================================================================

-- Pending queue for unresolved references
CREATE TABLE IF NOT EXISTS entities_pending (
    pending_id        SERIAL PRIMARY KEY,
    entity_type       TEXT NOT NULL,
    raw_value         TEXT NOT NULL,               -- What we received
    source_language   TEXT DEFAULT 'en',
    source_context    JSONB,                       -- Where it came from (posting_id, profile_id, etc.)
    status            TEXT DEFAULT 'pending',      -- 'pending', 'approved', 'rejected', 'merged'
    resolved_entity_id INT REFERENCES entities,    -- If matched/created
    created_at        TIMESTAMP DEFAULT now(),
    processed_at      TIMESTAMP,
    processed_by      TEXT                         -- Human or model that resolved it
);

CREATE INDEX idx_entities_pending_status ON entities_pending(status);
CREATE INDEX idx_entities_pending_type ON entities_pending(entity_type);
CREATE INDEX idx_entities_pending_value ON entities_pending(raw_value);

COMMENT ON TABLE entities_pending IS 'Unresolved references awaiting human/AI classification';

-- ============================================================================

-- ARDEN REFINEMENT: Decision audit trail for RAQ compliance
CREATE TABLE IF NOT EXISTS registry_decisions (
    decision_id       SERIAL PRIMARY KEY,
    decision_type     TEXT NOT NULL,              -- 'merge', 'assign', 'create', 'delete', 'rename', 'relate'
    subject_entity_id INT REFERENCES entities,    -- Entity being acted upon
    target_entity_id  INT REFERENCES entities,    -- Target (for merge, assign, relate)
    
    -- Model/Actor info
    model             TEXT,                        -- Which LLM made the decision
    temperature       NUMERIC(2,1),               -- Model temperature used
    confidence        NUMERIC(3,2),               -- Model's stated confidence
    reasoning         TEXT,                        -- Why this decision was made
    tags              TEXT[],                      -- Searchable tags
    raw_response      TEXT,                        -- Full LLM response for debugging
    
    -- ARDEN REFINEMENT: Reviewer can be human OR model (grader pattern)
    reviewer_id       TEXT,                        -- 'xai', 'gershon', 'qwen2.5:7b'
    reviewer_type     TEXT,                        -- 'human' or 'model'
    review_status     TEXT DEFAULT 'pending',     -- 'pending', 'approved', 'rejected', 'auto_approved'
    review_notes      TEXT,
    
    -- Timestamps
    created_at        TIMESTAMP DEFAULT now(),
    reviewed_at       TIMESTAMP,
    applied_at        TIMESTAMP                   -- When decision was executed
);

CREATE INDEX idx_registry_decisions_status ON registry_decisions(review_status);
CREATE INDEX idx_registry_decisions_type ON registry_decisions(decision_type);
CREATE INDEX idx_registry_decisions_subject ON registry_decisions(subject_entity_id);
CREATE INDEX idx_registry_decisions_pending ON registry_decisions(review_status) WHERE review_status = 'pending';

COMMENT ON TABLE registry_decisions IS 'Audit trail for all registry modifications - enables RAQ (Repeatability, Auditability, QA)';
COMMENT ON COLUMN registry_decisions.reviewer_id IS 'Who reviewed: human username or model name';
COMMENT ON COLUMN registry_decisions.reviewer_type IS 'Whether reviewer was human or model (grader pattern allows model-reviews-model)';
COMMENT ON COLUMN registry_decisions.review_status IS 'pending=needs review, approved=confirmed, rejected=overruled, auto_approved=high confidence auto-accepted';

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- Legacy-compatible view: entity_hierarchy (single-parent view for backward compatibility)
CREATE OR REPLACE VIEW entity_hierarchy AS
SELECT 
    entity_id,
    related_entity_id AS parent_entity_id,
    relationship_type AS relationship,
    strength,
    created_at
FROM entity_relationships
WHERE is_primary = true 
   OR (relationship_type = 'is_a' AND is_primary IS NULL);

COMMENT ON VIEW entity_hierarchy IS 'LEGACY VIEW - Single-parent hierarchy for backward compatibility. Use entity_relationships for full graph access.';

-- ============================================================================
-- RELATIONSHIP TYPE REFERENCE
-- ============================================================================

COMMENT ON TABLE entity_relationships IS 
'Relationship types:
  - is_a: Taxonomic classification (Python is_a Programming Language)
  - located_in: Geographic containment (Munich located_in Bavaria)
  - part_of: Compositional (Engine part_of Car)
  - instance_of: Specific occurrence ("Berlin March 2025" instance_of Climate Protest)
  - same_as: Identity for merging (München same_as Munich)
';

-- ============================================================================
-- DONE
-- ============================================================================

COMMIT;

-- Verification queries (run manually after migration)
-- SELECT 'entities' as tbl, COUNT(*) FROM entities
-- UNION ALL SELECT 'entity_names', COUNT(*) FROM entity_names
-- UNION ALL SELECT 'entity_aliases', COUNT(*) FROM entity_aliases  
-- UNION ALL SELECT 'entity_relationships', COUNT(*) FROM entity_relationships
-- UNION ALL SELECT 'entities_pending', COUNT(*) FROM entities_pending
-- UNION ALL SELECT 'registry_decisions', COUNT(*) FROM registry_decisions;
