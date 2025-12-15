-- Migration: Unified Entity Ontology - Phase 1 (Tables Only)
-- Date: 2025-12-05
-- Author: Sandy (reviewed by Arden)
-- Status: READY FOR REVIEW
--
-- This migration creates the new unified entity tables.
-- It does NOT touch existing tables or data.
-- Zero risk - purely additive.

BEGIN;

-- ============================================================================
-- CORE ENTITY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS entities (
    entity_id            SERIAL PRIMARY KEY,
    entity_type          TEXT NOT NULL,           -- 'skill', 'city', 'country', 'region', 'industry', 'event'
    canonical_name       TEXT NOT NULL,           -- Immutable reference key (lowercase, underscored)
    status               TEXT DEFAULT 'active',   -- 'active', 'deprecated', 'merged'
    merged_into_entity_id INT REFERENCES entities(entity_id),
    created_at           TIMESTAMP DEFAULT now(),
    created_by           TEXT,
    metadata             JSONB,                   -- Type-specific data (ISO codes, coordinates, etc.)
    
    UNIQUE(entity_type, canonical_name),
    CHECK (status IN ('active', 'deprecated', 'merged')),
    CHECK (status != 'merged' OR merged_into_entity_id IS NOT NULL)
);

COMMENT ON TABLE entities IS 'Universal registry of things that exist - skills, places, concepts';
COMMENT ON COLUMN entities.canonical_name IS 'The One True Name - never displayed, only referenced internally';
COMMENT ON COLUMN entities.status IS 'Lifecycle: active (normal), deprecated (historical), merged (redirects to merged_into)';
COMMENT ON COLUMN entities.metadata IS 'Type-specific data: {"iso_code": "DE"} for countries, {"coordinates": [lat, lon]} for cities';

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_status ON entities(status) WHERE status != 'active';
CREATE INDEX idx_entities_merged ON entities(merged_into_entity_id) WHERE merged_into_entity_id IS NOT NULL;


-- ============================================================================
-- ENTITY NAMES (Multilingual Display Names)
-- ============================================================================

CREATE TABLE IF NOT EXISTS entity_names (
    entity_id            INT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    language             TEXT NOT NULL DEFAULT 'en',  -- ISO 639-1: 'en', 'de', 'ru', 'zh', 'ar'
    display_name         TEXT NOT NULL,
    is_primary           BOOLEAN DEFAULT false,       -- Primary name for this language
    confidence           NUMERIC(3,2) DEFAULT 1.0,    -- How sure are we? (Arden's suggestion)
    created_at           TIMESTAMP DEFAULT now(),
    created_by           TEXT,
    
    PRIMARY KEY (entity_id, language, display_name),
    CHECK (confidence >= 0 AND confidence <= 1)
);

COMMENT ON TABLE entity_names IS 'How entities are displayed to humans, by language';
COMMENT ON COLUMN entity_names.is_primary IS 'If true, this is THE name to show for this entity in this language';
COMMENT ON COLUMN entity_names.confidence IS 'Translation confidence: 1.0 = verified, 0.8 = LLM suggested, etc.';

CREATE INDEX idx_entity_names_lookup ON entity_names(display_name, language);
CREATE INDEX idx_entity_names_primary ON entity_names(entity_id, language) WHERE is_primary = true;


-- ============================================================================
-- ENTITY ALIASES (Alternative References)
-- ============================================================================

CREATE TABLE IF NOT EXISTS entity_aliases (
    alias_id             SERIAL PRIMARY KEY,
    entity_id            INT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    alias                TEXT NOT NULL,               -- 'AWS', 'München', 'Big Apple', 'JS'
    language             TEXT DEFAULT 'en',
    alias_type           TEXT DEFAULT 'standard',     -- 'abbreviation', 'colloquial', 'historical', 'typo', 'standard'
    confidence           NUMERIC(3,2) DEFAULT 1.0,
    created_at           TIMESTAMP DEFAULT now(),
    created_by           TEXT,
    
    UNIQUE(alias, language),                          -- One alias maps to one entity per language
    CHECK (confidence >= 0 AND confidence <= 1)
);

COMMENT ON TABLE entity_aliases IS 'Alternative names, abbreviations, misspellings that resolve to entities';
COMMENT ON COLUMN entity_aliases.alias_type IS 'Why this alias exists - helps with matching confidence';

CREATE INDEX idx_entity_aliases_lookup ON entity_aliases(lower(alias), language);
CREATE INDEX idx_entity_aliases_entity ON entity_aliases(entity_id);


-- ============================================================================
-- ENTITY RELATIONSHIPS (Multi-Parent Graph)
-- ============================================================================
-- Arden's refinement: Graph model instead of tree model.
-- Allows: Munich located_in Bavaria AND located_in Germany
-- Allows: DevOps is_a Skill AND is_a JobFunction

CREATE TABLE IF NOT EXISTS entity_relationships (
    entity_id            INT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    related_entity_id    INT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    relationship         TEXT NOT NULL,               -- 'is_a', 'located_in', 'part_of', 'same_as', 'related_to'
    strength             NUMERIC(3,2) DEFAULT 1.0,    -- Relationship strength
    created_at           TIMESTAMP DEFAULT now(),
    created_by           TEXT,
    notes                TEXT,
    
    PRIMARY KEY (entity_id, related_entity_id, relationship),
    CHECK (entity_id != related_entity_id),
    CHECK (strength >= 0 AND strength <= 1)
);

COMMENT ON TABLE entity_relationships IS 'How entities relate to each other - graph model, not tree';
COMMENT ON COLUMN entity_relationships.relationship IS 'is_a (taxonomy), located_in (geography), part_of (composition), same_as (identity), related_to (loose)';

CREATE INDEX idx_entity_relationships_related ON entity_relationships(related_entity_id);
CREATE INDEX idx_entity_relationships_type ON entity_relationships(relationship);


-- ============================================================================
-- ENTITIES PENDING (Resolution Queue)
-- ============================================================================

CREATE TABLE IF NOT EXISTS entities_pending (
    pending_id           SERIAL PRIMARY KEY,
    entity_type          TEXT NOT NULL,               -- Expected type: 'skill', 'city', etc.
    raw_value            TEXT NOT NULL,               -- What we received: "München", "python3"
    source_language      TEXT DEFAULT 'en',           -- Detected or assumed language
    source_context       JSONB,                       -- Where it came from: {"posting_id": 123, "field": "location"}
    status               TEXT DEFAULT 'pending',      -- 'pending', 'approved', 'rejected', 'merged'
    resolved_entity_id   INT REFERENCES entities(entity_id),
    resolution_notes     TEXT,                        -- Why approved/rejected
    created_at           TIMESTAMP DEFAULT now(),
    processed_at         TIMESTAMP,
    processed_by         TEXT,                        -- Actor or human who resolved it
    
    CHECK (status IN ('pending', 'approved', 'rejected', 'merged')),
    CHECK (status = 'pending' OR processed_at IS NOT NULL)
);

COMMENT ON TABLE entities_pending IS 'Unresolved entity references awaiting human/AI classification';
COMMENT ON COLUMN entities_pending.raw_value IS 'Exact text received - may be misspelled, foreign language, etc.';
COMMENT ON COLUMN entities_pending.source_context IS 'Provenance: where did this come from?';

CREATE INDEX idx_entities_pending_status ON entities_pending(status) WHERE status = 'pending';
CREATE INDEX idx_entities_pending_type ON entities_pending(entity_type, status);


-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: Get primary display name for an entity in a language (with fallback to English)
CREATE OR REPLACE VIEW v_entity_display AS
SELECT 
    e.entity_id,
    e.entity_type,
    e.canonical_name,
    e.status,
    COALESCE(n.display_name, n_en.display_name, e.canonical_name) as display_name,
    COALESCE(n.language, n_en.language, 'en') as language
FROM entities e
LEFT JOIN entity_names n ON e.entity_id = n.entity_id AND n.is_primary = true
LEFT JOIN entity_names n_en ON e.entity_id = n_en.entity_id AND n_en.language = 'en' AND n_en.is_primary = true
WHERE e.status = 'active';

COMMENT ON VIEW v_entity_display IS 'Primary display name per entity with English fallback';


-- ============================================================================
-- RELATIONSHIP TYPE REFERENCE (Documentation)
-- ============================================================================

-- This is just documentation, not enforced in schema
COMMENT ON TABLE entity_relationships IS '
RELATIONSHIP TYPES:
  is_a        - Taxonomic: Python is_a Programming_Language
  located_in  - Geographic: Munich located_in Germany  
  part_of     - Compositional: Engine part_of Car
  instance_of - Specific: "Berlin_March_2025" instance_of Climate_Protest
  same_as     - Identity: München same_as Munich (for merging)
  related_to  - Loose association: Python related_to Data_Science
  requires    - Dependency: Kubernetes requires Docker (skills)
  succeeds    - Temporal: Python3 succeeds Python2
';


COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (Run after migration)
-- ============================================================================

-- SELECT 'entities' as tbl, count(*) from entities
-- UNION ALL SELECT 'entity_names', count(*) from entity_names
-- UNION ALL SELECT 'entity_aliases', count(*) from entity_aliases
-- UNION ALL SELECT 'entity_relationships', count(*) from entity_relationships
-- UNION ALL SELECT 'entities_pending', count(*) from entities_pending;
