-- ============================================================================
-- MIGRATION 002: Geography Proof of Concept
-- ============================================================================
-- Author: Sandy
-- Date: 2025-12-07
-- Purpose: Test UEO schema with well-defined, verifiable data
--          Munich → Bavaria → Germany → Europe is objectively correct or wrong
-- ============================================================================

BEGIN;

-- ============================================================================
-- CONTINENTS
-- ============================================================================

INSERT INTO entities (entity_type, canonical_name, created_by, metadata)
VALUES 
  ('continent', 'europe', 'migration_002', '{"population": 750000000}'),
  ('continent', 'north_america', 'migration_002', '{"population": 580000000}'),
  ('continent', 'asia', 'migration_002', '{"population": 4700000000}')
ON CONFLICT (entity_type, canonical_name) DO NOTHING;

-- Continent names
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Europe', true FROM entities WHERE canonical_name = 'europe' AND entity_type = 'continent'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Europa', true FROM entities WHERE canonical_name = 'europe' AND entity_type = 'continent'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'North America', true FROM entities WHERE canonical_name = 'north_america' AND entity_type = 'continent'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Asia', true FROM entities WHERE canonical_name = 'asia' AND entity_type = 'continent'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- COUNTRIES
-- ============================================================================

INSERT INTO entities (entity_type, canonical_name, created_by, metadata)
VALUES 
  ('country', 'germany', 'migration_002', '{"iso_code": "DE", "population": 83000000}'),
  ('country', 'france', 'migration_002', '{"iso_code": "FR", "population": 67000000}'),
  ('country', 'united_kingdom', 'migration_002', '{"iso_code": "GB", "population": 67000000}'),
  ('country', 'united_states', 'migration_002', '{"iso_code": "US", "population": 331000000}'),
  ('country', 'switzerland', 'migration_002', '{"iso_code": "CH", "population": 8700000}'),
  ('country', 'austria', 'migration_002', '{"iso_code": "AT", "population": 9000000}')
ON CONFLICT (entity_type, canonical_name) DO NOTHING;

-- Country names in multiple languages
-- Germany
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Germany', true FROM entities WHERE canonical_name = 'germany' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Deutschland', true FROM entities WHERE canonical_name = 'germany' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'fr', 'Allemagne', true FROM entities WHERE canonical_name = 'germany' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- France
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'France', true FROM entities WHERE canonical_name = 'france' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Frankreich', true FROM entities WHERE canonical_name = 'france' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- UK
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'United Kingdom', true FROM entities WHERE canonical_name = 'united_kingdom' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Vereinigtes Königreich', true FROM entities WHERE canonical_name = 'united_kingdom' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- USA
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'United States', true FROM entities WHERE canonical_name = 'united_states' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Vereinigte Staaten', true FROM entities WHERE canonical_name = 'united_states' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- Switzerland  
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Switzerland', true FROM entities WHERE canonical_name = 'switzerland' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Schweiz', true FROM entities WHERE canonical_name = 'switzerland' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'fr', 'Suisse', true FROM entities WHERE canonical_name = 'switzerland' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- Austria
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Austria', true FROM entities WHERE canonical_name = 'austria' AND entity_type = 'country'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Österreich', true FROM entities WHERE canonical_name = 'austria' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- GERMAN STATES (Bundesländer)
-- ============================================================================

INSERT INTO entities (entity_type, canonical_name, created_by, metadata)
VALUES 
  ('state', 'bavaria', 'migration_002', '{"de_name": "Bayern", "capital": "Munich"}'),
  ('state', 'hesse', 'migration_002', '{"de_name": "Hessen", "capital": "Wiesbaden"}'),
  ('state', 'berlin', 'migration_002', '{"de_name": "Berlin", "is_city_state": true}'),
  ('state', 'north_rhine_westphalia', 'migration_002', '{"de_name": "Nordrhein-Westfalen", "capital": "Düsseldorf"}'),
  ('state', 'baden_wuerttemberg', 'migration_002', '{"de_name": "Baden-Württemberg", "capital": "Stuttgart"}')
ON CONFLICT (entity_type, canonical_name) DO NOTHING;

-- State names
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Bavaria', true FROM entities WHERE canonical_name = 'bavaria' AND entity_type = 'state'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Bayern', true FROM entities WHERE canonical_name = 'bavaria' AND entity_type = 'state'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Hesse', true FROM entities WHERE canonical_name = 'hesse' AND entity_type = 'state'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Hessen', true FROM entities WHERE canonical_name = 'hesse' AND entity_type = 'state'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Berlin', true FROM entities WHERE canonical_name = 'berlin' AND entity_type = 'state'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Berlin', true FROM entities WHERE canonical_name = 'berlin' AND entity_type = 'state'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'North Rhine-Westphalia', true FROM entities WHERE canonical_name = 'north_rhine_westphalia' AND entity_type = 'state'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Nordrhein-Westfalen', true FROM entities WHERE canonical_name = 'north_rhine_westphalia' AND entity_type = 'state'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Baden-Württemberg', true FROM entities WHERE canonical_name = 'baden_wuerttemberg' AND entity_type = 'state'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Baden-Württemberg', true FROM entities WHERE canonical_name = 'baden_wuerttemberg' AND entity_type = 'state'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- MAJOR CITIES
-- ============================================================================

INSERT INTO entities (entity_type, canonical_name, created_by, metadata)
VALUES 
  ('city', 'munich', 'migration_002', '{"population": 1500000}'),
  ('city', 'frankfurt', 'migration_002', '{"population": 750000, "note": "Financial capital"}'),
  ('city', 'berlin_city', 'migration_002', '{"population": 3600000, "note": "Capital"}'),
  ('city', 'dusseldorf', 'migration_002', '{"population": 620000}'),
  ('city', 'cologne', 'migration_002', '{"population": 1080000}'),
  ('city', 'stuttgart', 'migration_002', '{"population": 635000}'),
  ('city', 'london', 'migration_002', '{"population": 8900000}'),
  ('city', 'paris', 'migration_002', '{"population": 2100000}'),
  ('city', 'zurich', 'migration_002', '{"population": 420000}'),
  ('city', 'new_york', 'migration_002', '{"population": 8300000}')
ON CONFLICT (entity_type, canonical_name) DO NOTHING;

-- City names (English and German)
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Munich', true FROM entities WHERE canonical_name = 'munich' AND entity_type = 'city'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'München', true FROM entities WHERE canonical_name = 'munich' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Frankfurt', true FROM entities WHERE canonical_name = 'frankfurt' AND entity_type = 'city'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Frankfurt am Main', true FROM entities WHERE canonical_name = 'frankfurt' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Berlin', true FROM entities WHERE canonical_name = 'berlin_city' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Düsseldorf', true FROM entities WHERE canonical_name = 'dusseldorf' AND entity_type = 'city'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Düsseldorf', true FROM entities WHERE canonical_name = 'dusseldorf' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Cologne', true FROM entities WHERE canonical_name = 'cologne' AND entity_type = 'city'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Köln', true FROM entities WHERE canonical_name = 'cologne' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Stuttgart', true FROM entities WHERE canonical_name = 'stuttgart' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'London', true FROM entities WHERE canonical_name = 'london' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Paris', true FROM entities WHERE canonical_name = 'paris' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'Zurich', true FROM entities WHERE canonical_name = 'zurich' AND entity_type = 'city'
ON CONFLICT DO NOTHING;
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Zürich', true FROM entities WHERE canonical_name = 'zurich' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'en', 'New York', true FROM entities WHERE canonical_name = 'new_york' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- ALIASES
-- ============================================================================

-- Munich aliases
INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'München', 'de', 'local_name', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'munich' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

-- New York aliases
INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'NYC', 'en', 'abbreviation', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'new_york' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'Big Apple', 'en', 'colloquial', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'new_york' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

-- Frankfurt aliases (distinguish from Frankfurt Oder)
INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'Frankfurt/Main', 'en', 'disambiguation', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'frankfurt' AND entity_type = 'city'
ON CONFLICT DO NOTHING;

-- UK aliases
INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'UK', 'en', 'abbreviation', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'united_kingdom' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'Britain', 'en', 'colloquial', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'united_kingdom' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- USA aliases
INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'USA', 'en', 'abbreviation', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'united_states' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'US', 'en', 'abbreviation', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'united_states' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

INSERT INTO entity_aliases (entity_id, alias, language, alias_type, provenance)
SELECT entity_id, 'America', 'en', 'colloquial', '{"source": "migration_002"}'
FROM entities WHERE canonical_name = 'united_states' AND entity_type = 'country'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- RELATIONSHIPS (located_in hierarchy)
-- ============================================================================

-- Countries → Continents
INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'country' AND c.canonical_name = 'germany'
  AND p.entity_type = 'continent' AND p.canonical_name = 'europe'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'country' AND c.canonical_name = 'france'
  AND p.entity_type = 'continent' AND p.canonical_name = 'europe'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'country' AND c.canonical_name = 'united_kingdom'
  AND p.entity_type = 'continent' AND p.canonical_name = 'europe'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'country' AND c.canonical_name = 'switzerland'
  AND p.entity_type = 'continent' AND p.canonical_name = 'europe'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'country' AND c.canonical_name = 'austria'
  AND p.entity_type = 'continent' AND p.canonical_name = 'europe'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'country' AND c.canonical_name = 'united_states'
  AND p.entity_type = 'continent' AND p.canonical_name = 'north_america'
ON CONFLICT DO NOTHING;

-- German States → Germany
INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT s.entity_id, c.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities s, entities c
WHERE s.entity_type = 'state' AND s.canonical_name IN ('bavaria', 'hesse', 'berlin', 'north_rhine_westphalia', 'baden_wuerttemberg')
  AND c.entity_type = 'country' AND c.canonical_name = 'germany'
ON CONFLICT DO NOTHING;

-- Cities → States/Countries
INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, s.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities s
WHERE c.entity_type = 'city' AND c.canonical_name = 'munich'
  AND s.entity_type = 'state' AND s.canonical_name = 'bavaria'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, s.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities s
WHERE c.entity_type = 'city' AND c.canonical_name = 'frankfurt'
  AND s.entity_type = 'state' AND s.canonical_name = 'hesse'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, s.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities s
WHERE c.entity_type = 'city' AND c.canonical_name = 'berlin_city'
  AND s.entity_type = 'state' AND s.canonical_name = 'berlin'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, s.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities s
WHERE c.entity_type = 'city' AND c.canonical_name IN ('dusseldorf', 'cologne')
  AND s.entity_type = 'state' AND s.canonical_name = 'north_rhine_westphalia'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, s.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities s
WHERE c.entity_type = 'city' AND c.canonical_name = 'stuttgart'
  AND s.entity_type = 'state' AND s.canonical_name = 'baden_wuerttemberg'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'city' AND c.canonical_name = 'london'
  AND p.entity_type = 'country' AND p.canonical_name = 'united_kingdom'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'city' AND c.canonical_name = 'paris'
  AND p.entity_type = 'country' AND p.canonical_name = 'france'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'city' AND c.canonical_name = 'zurich'
  AND p.entity_type = 'country' AND p.canonical_name = 'switzerland'
ON CONFLICT DO NOTHING;

INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, is_primary, provenance)
SELECT c.entity_id, p.entity_id, 'located_in', true, '{"source": "migration_002"}'
FROM entities c, entities p
WHERE c.entity_type = 'city' AND c.canonical_name = 'new_york'
  AND p.entity_type = 'country' AND p.canonical_name = 'united_states'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- LOG THE MIGRATION AS A DECISION
-- ============================================================================

INSERT INTO registry_decisions (
    decision_type, 
    model, 
    reasoning, 
    reviewer_id, 
    reviewer_type, 
    review_status,
    applied_at
) VALUES (
    'create',
    'manual_migration',
    'Geography proof-of-concept: Seeded continents, countries, German states, and major cities with multilingual names and located_in relationships',
    'sandy',
    'human',
    'approved',
    now()
);

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (run after migration)
-- ============================================================================

-- Entity counts by type
-- SELECT entity_type, COUNT(*) FROM entities GROUP BY 1 ORDER BY 2 DESC;

-- Test RECOGNIZE: "Is München a known entity?"
-- SELECT e.entity_id, e.canonical_name, e.entity_type
-- FROM entities e
-- JOIN entity_aliases a ON e.entity_id = a.entity_id
-- WHERE a.alias = 'München';

-- Test RELATE: "What is Munich part of?" (recursive)
-- WITH RECURSIVE ancestors AS (
--     SELECT entity_id, related_entity_id, relationship_type, 1 as depth
--     FROM entity_relationships
--     WHERE entity_id = (SELECT entity_id FROM entities WHERE canonical_name = 'munich' AND entity_type = 'city')
--     UNION ALL
--     SELECT r.entity_id, r.related_entity_id, r.relationship_type, a.depth + 1
--     FROM entity_relationships r
--     JOIN ancestors a ON r.entity_id = a.related_entity_id
-- )
-- SELECT e.canonical_name, a.relationship_type, a.depth
-- FROM ancestors a
-- JOIN entities e ON a.related_entity_id = e.entity_id
-- ORDER BY a.depth;

-- Test TRANSLATE: "How do I show Munich in German?"
-- SELECT display_name FROM entity_names 
-- WHERE entity_id = (SELECT entity_id FROM entities WHERE canonical_name = 'munich')
--   AND language = 'de' AND is_primary = true;
