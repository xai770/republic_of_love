# Entity Registry Architecture

**Author:** Sandy (with Beth ℶ)  
**For:** Arden  
**Date:** 2025-12-05  
**Updated:** 2025-12-08 (WF3005 fully operational, cron scheduled)
**Status:** IMPLEMENTED - Active in production

---

## Arden's Refinements (2025-12-07)

Incorporated from daily discussion:

1. **Entity Status Column** - Lifecycle management for entities
2. **Multi-Parent Relationships** - Graph model instead of strict hierarchy
3. **Decision Provenance** - Track who/what made each decision

See schema updates below marked with `-- ARDEN REFINEMENT`.

---

## The Insight

While rebuilding the skills hierarchy (WF3004), we realized: **skills are just one instance of a universal pattern**.

| Domain | "Entity" | "Alias" | "Hierarchy" | "Translation" |
|--------|----------|---------|-------------|---------------|
| Skills | Python | python, PYTHON, Py | Programming → Technical | Python (all langs) |
| Geography | Munich | München, Мюнхен, 慕尼黑 | Bavaria → Germany → Europe | Munich/München/慕尼黑 |
| Industries | Banking | Finance, Finanzwesen | Financial Services → Services | Banking/Bankwesen |
| Events | "Berlin Climate March 2025" | "German capital protests" | Climate Events → Political Events | (various headlines) |
| Legal | Force Majeure | Act of God, 不可抗力 | Contract Terms → Legal Concepts | Force Majeure/höhere Gewalt |

**They're all the same thing.**

---

## The Abstraction

### What is an Entity?

An **entity** is anything that:
1. **Exists** as a distinct concept
2. **Has names** in one or more languages
3. **Has aliases** (alternative references)
4. **Relates** to other entities hierarchically

### The Three Eternal Operations

Every useful workflow reduces to:

```
RECOGNIZE  →  "Is X the same as Y?"
RELATE     →  "How does X connect to Y?"  
TRANSLATE  →  "What is X called in context C?"
```

Ada Lovelace saw this: the Analytical Engine wasn't about numbers—it was about **symbols and their relations**.

Alan Turing formalized it: computation is **pattern matching and transformation**.

Marvin Minsky extended it: intelligence is **representing and manipulating knowledge structures**.

---

## The Schema

**Updated with Arden's refinements (2025-12-05):**
- Added `status` + `merged_into_entity_id` for entity lifecycle
- Changed `entity_hierarchy` → `entity_relationships` (graph model, multi-parent)
- Added `confidence` to `entity_names`

### Core Tables

```sql
-- Things exist
CREATE TABLE entities (
    entity_id        SERIAL PRIMARY KEY,
    entity_type      TEXT NOT NULL,           -- 'skill', 'city', 'country', 'event', 'legal_term'
    canonical_name   TEXT NOT NULL,           -- Immutable reference key
    created_at       TIMESTAMP DEFAULT now(),
    created_by       TEXT,
    metadata         JSONB,                   -- Type-specific data
    
    -- ARDEN REFINEMENT: Entity lifecycle management
    status           TEXT DEFAULT 'active',   -- 'active', 'deprecated', 'merged', 'pending_review'
    merged_into_entity_id INT REFERENCES entities(entity_id),  -- If status='merged', points to canonical
    
    UNIQUE(entity_type, canonical_name)
);

COMMENT ON TABLE entities IS 'The universal registry of things that exist';
COMMENT ON COLUMN entities.canonical_name IS 'The One True Name - never displayed, only referenced';
COMMENT ON COLUMN entities.status IS 'Entity lifecycle: active (normal), deprecated (phasing out), merged (replaced by merged_into_entity_id), pending_review (needs human QA)';

-- Things have names in languages
CREATE TABLE entity_names (
    entity_id        INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    language         TEXT NOT NULL DEFAULT 'en',  -- ISO 639-1
    display_name     TEXT NOT NULL,
    is_primary       BOOLEAN DEFAULT false,       -- Primary name for this language
    confidence       NUMERIC(3,2) DEFAULT 1.0,    -- How sure are we this name is correct?
    created_at       TIMESTAMP DEFAULT now(),
    
    PRIMARY KEY (entity_id, language, display_name)
);

CREATE INDEX idx_entity_names_lookup ON entity_names(display_name, language);

COMMENT ON TABLE entity_names IS 'How entities are displayed to humans, by language';

-- Things are called many things
CREATE TABLE entity_aliases (
    alias_id         SERIAL PRIMARY KEY,
    entity_id        INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    alias            TEXT NOT NULL,               -- 'AWS', 'München', 'Big Apple'
    language         TEXT DEFAULT 'en',
    alias_type       TEXT DEFAULT 'abbreviation', -- 'abbreviation', 'colloquial', 'historical', 'typo'
    confidence       NUMERIC(3,2) DEFAULT 1.0,
    created_at       TIMESTAMP DEFAULT now(),
    
    -- ARDEN REFINEMENT: Track decision provenance
    provenance       JSONB,                       -- {"model": "qwen2.5:7b", "decision_id": 123, "reasoning": "..."}
    
    UNIQUE(alias, language)                       -- One alias maps to one entity per language
);

CREATE INDEX idx_entity_aliases_lookup ON entity_aliases(alias, language);

COMMENT ON TABLE entity_aliases IS 'Alternative names, abbreviations, misspellings that resolve to entities';
COMMENT ON COLUMN entity_aliases.alias_type IS 'Why this alias exists - helps with matching confidence';
COMMENT ON COLUMN entity_aliases.provenance IS 'Who/what created this alias and why';

-- ARDEN REFINEMENT: Multi-parent relationships (graph model, not strict tree)
-- Replaces single-parent entity_hierarchy
CREATE TABLE entity_relationships (
    relationship_id  SERIAL PRIMARY KEY,
    entity_id        INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    related_entity_id INT NOT NULL REFERENCES entities ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'is_a',        -- 'is_a', 'located_in', 'part_of', 'instance_of', 'same_as'
    strength         NUMERIC(3,2) DEFAULT 1.0,
    is_primary       BOOLEAN DEFAULT false,       -- Primary parent for display purposes
    created_at       TIMESTAMP DEFAULT now(),
    
    -- ARDEN REFINEMENT: Track decision provenance
    provenance       JSONB,                       -- {"model": "qwen2.5:7b", "decision_id": 123, "reasoning": "..."}
    
    UNIQUE(entity_id, related_entity_id, relationship_type),
    CHECK (entity_id != related_entity_id)
);

CREATE INDEX idx_entity_relationships_entity ON entity_relationships(entity_id);
CREATE INDEX idx_entity_relationships_related ON entity_relationships(related_entity_id);
CREATE INDEX idx_entity_relationships_type ON entity_relationships(relationship_type);

COMMENT ON TABLE entity_relationships IS 'Graph of entity relationships - allows multiple parents';
COMMENT ON COLUMN entity_relationships.is_primary IS 'For entities with multiple parents, which one is "canonical" for display';
COMMENT ON COLUMN entity_relationships.provenance IS 'Who/what created this relationship and why';

-- Legacy view for backward compatibility (uses primary parent only)
CREATE VIEW entity_hierarchy AS
SELECT 
    entity_id,
    related_entity_id AS parent_entity_id,
    relationship_type AS relationship,
    strength,
    created_at
FROM entity_relationships
WHERE is_primary = true OR relationship_type = 'is_a';

COMMENT ON VIEW entity_hierarchy IS 'LEGACY VIEW - Use entity_relationships for full graph access';
```

### Relationship Types

| Relationship | Meaning | Example |
|--------------|---------|---------|
| `is_a` | Taxonomic classification | Python `is_a` Programming Language |
| `located_in` | Geographic containment | Munich `located_in` Bavaria |
| `part_of` | Compositional | Engine `part_of` Car |
| `instance_of` | Specific occurrence | "Berlin March 2025" `instance_of` Climate Protest |
| `same_as` | Identity (for merging) | München `same_as` Munich |

### Pending Queue (Universal)

```sql
CREATE TABLE entities_pending (
    pending_id       SERIAL PRIMARY KEY,
    entity_type      TEXT NOT NULL,
    raw_value        TEXT NOT NULL,               -- What we received
    source_language  TEXT DEFAULT 'en',
    source_context   JSONB,                       -- Where it came from
    status           TEXT DEFAULT 'pending',      -- 'pending', 'approved', 'rejected', 'merged'
    resolved_entity_id INT REFERENCES entities,   -- If matched/created
    created_at       TIMESTAMP DEFAULT now(),
    processed_at     TIMESTAMP
);

COMMENT ON TABLE entities_pending IS 'Unresolved references awaiting human/AI classification';

-- ARDEN REFINEMENT: Decision audit trail for RAQ compliance
CREATE TABLE registry_decisions (
    decision_id      SERIAL PRIMARY KEY,
    decision_type    TEXT NOT NULL,              -- 'merge', 'assign', 'create', 'delete', 'rename'
    subject_entity_id INT REFERENCES entities,   -- Entity being acted upon
    target_entity_id  INT REFERENCES entities,   -- Target (for merge, assign)
    model            TEXT,                        -- Which LLM made the decision
    temperature      NUMERIC(2,1),               -- Model temperature used
    confidence       NUMERIC(3,2),               -- Model's stated confidence
    reasoning        TEXT,                        -- Why this decision was made
    tags             TEXT[],                      -- Searchable tags
    
    -- Review workflow
    reviewer_id      INT,                         -- Human who reviewed
    review_status    TEXT DEFAULT 'pending',     -- 'pending', 'approved', 'rejected', 'auto_approved'
    review_notes     TEXT,
    
    -- Timestamps
    created_at       TIMESTAMP DEFAULT now(),
    reviewed_at      TIMESTAMP,
    applied_at       TIMESTAMP                   -- When decision was executed
);

CREATE INDEX idx_registry_decisions_status ON registry_decisions(review_status);
CREATE INDEX idx_registry_decisions_type ON registry_decisions(decision_type);
CREATE INDEX idx_registry_decisions_subject ON registry_decisions(subject_entity_id);

COMMENT ON TABLE registry_decisions IS 'Audit trail for all registry modifications - enables RAQ (Repeatability, Auditability, QA)';
COMMENT ON COLUMN registry_decisions.review_status IS 'pending=needs review, approved=human confirmed, rejected=human overruled, auto_approved=high confidence auto-accepted';
```

---

## The Operations

### 1. RECOGNIZE: Entity Resolution

Given raw text, find the canonical entity.

```sql
-- "Is 'München' a known entity?"
SELECT e.entity_id, e.canonical_name, e.entity_type
FROM entities e
JOIN entity_aliases a ON e.entity_id = a.entity_id
WHERE a.alias = 'München';

-- Result: entity_id=42, canonical_name='munich', entity_type='city'
```

**Workflow Pattern:**
```
Input: raw string
→ Check entity_aliases (exact match)
→ Check entity_names (fuzzy match)
→ If not found → entities_pending
→ Human/AI review
→ Create new OR merge with existing
```

### 2. RELATE: Hierarchy Navigation

Given an entity, find its ancestors/descendants.

```sql
-- "What is Munich part of?"
WITH RECURSIVE ancestors AS (
    SELECT entity_id, parent_entity_id, relationship, 1 as depth
    FROM entity_hierarchy
    WHERE entity_id = 42  -- Munich
    
    UNION ALL
    
    SELECT h.entity_id, h.parent_entity_id, h.relationship, a.depth + 1
    FROM entity_hierarchy h
    JOIN ancestors a ON h.entity_id = a.parent_entity_id
)
SELECT e.canonical_name, a.relationship, a.depth
FROM ancestors a
JOIN entities e ON a.parent_entity_id = e.entity_id
ORDER BY a.depth;

-- Result: bavaria (located_in, 1), germany (located_in, 2), europe (located_in, 3)
```

### 3. TRANSLATE: Multilingual Resolution

Given an entity and target language, get the display name.

```sql
-- "How do I show entity 42 in German?"
SELECT display_name 
FROM entity_names 
WHERE entity_id = 42 AND language = 'de' AND is_primary = true;

-- Result: 'München'
```

---

## Backward Compatibility

The current `skill_aliases` and `skill_hierarchy` become **views**:

```sql
-- Legacy view: skill_aliases
CREATE VIEW skill_aliases AS
SELECT 
    e.entity_id as skill_id,
    e.canonical_name as skill_name,
    COALESCE(n.display_name, e.canonical_name) as display_name,
    e.canonical_name as skill_alias,
    1.0 as confidence,
    e.created_at,
    e.created_by,
    'en' as language,
    NULL as notes
FROM entities e
LEFT JOIN entity_names n ON e.entity_id = n.entity_id 
    AND n.language = 'en' AND n.is_primary = true
WHERE e.entity_type = 'skill';

-- Legacy view: skill_hierarchy  
CREATE VIEW skill_hierarchy AS
SELECT 
    h.entity_id as skill_id,
    h.parent_entity_id as parent_skill_id,
    h.strength,
    h.created_at,
    NULL as created_by,
    NULL as notes
FROM entity_hierarchy h
JOIN entities e ON h.entity_id = e.entity_id
WHERE e.entity_type = 'skill';
```

**Existing code keeps working. New code uses the unified model.**

---

## Migration Path

### Phase 1: Create New Tables (No Impact)
```sql
CREATE TABLE entities (...);
CREATE TABLE entity_names (...);
CREATE TABLE entity_aliases (...);
CREATE TABLE entity_hierarchy (...);
CREATE TABLE entities_pending (...);
```

### Phase 2: Migrate Skills Data
```sql
-- Copy skills to entities
INSERT INTO entities (entity_type, canonical_name, created_at, created_by)
SELECT 'skill', skill_name, created_at, created_by
FROM skill_aliases;

-- Copy display names
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT e.entity_id, 'en', s.display_name, true
FROM skill_aliases s
JOIN entities e ON e.canonical_name = s.skill_name AND e.entity_type = 'skill'
WHERE s.display_name IS NOT NULL;

-- Copy hierarchy
INSERT INTO entity_hierarchy (entity_id, parent_entity_id, relationship, strength, created_at)
SELECT 
    e1.entity_id,
    e2.entity_id,
    'is_a',
    h.strength,
    h.created_at
FROM skill_hierarchy h
JOIN entities e1 ON e1.canonical_name = (SELECT skill_name FROM skill_aliases WHERE skill_id = h.skill_id) AND e1.entity_type = 'skill'
JOIN entities e2 ON e2.canonical_name = (SELECT skill_name FROM skill_aliases WHERE skill_id = h.parent_skill_id) AND e2.entity_type = 'skill';
```

### Phase 3: Rename and Create Views
```sql
ALTER TABLE skill_aliases RENAME TO skill_aliases_legacy;
ALTER TABLE skill_hierarchy RENAME TO skill_hierarchy_legacy;

CREATE VIEW skill_aliases AS (...);  -- Points to entities
CREATE VIEW skill_hierarchy AS (...); -- Points to entity_hierarchy
```

### Phase 4: Add Geography (New Capability!)
```sql
-- Countries
INSERT INTO entities (entity_type, canonical_name) VALUES
('country', 'germany'),
('country', 'france'),
('country', 'united_states');

-- Add German names
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'Deutschland', true
FROM entities WHERE canonical_name = 'germany';

-- Add cities
INSERT INTO entities (entity_type, canonical_name) VALUES
('city', 'munich'),
('city', 'paris'),
('city', 'new_york');

-- Munich in German
INSERT INTO entity_names (entity_id, language, display_name, is_primary)
SELECT entity_id, 'de', 'München', true
FROM entities WHERE canonical_name = 'munich';

-- Hierarchy
INSERT INTO entity_hierarchy (entity_id, parent_entity_id, relationship)
SELECT c.entity_id, p.entity_id, 'located_in'
FROM entities c, entities p
WHERE c.canonical_name = 'munich' AND p.canonical_name = 'germany';
```

---

## The Universal Workflow Pattern

WF3004 becomes a **template**:

```python
def organize_entities(entity_type: str, batch_size: int = 50):
    """
    Universal hierarchy organization workflow.
    Works for skills, cities, industries, legal terms, anything.
    """
    while True:
        # Fetch orphans of this type
        orphans = fetch_orphans(entity_type, batch_size)
        if not orphans:
            break
        
        # LLM classifies them
        prompt = f"""
        You are an Ontology Architect. Given {entity_type} entities, 
        group them into a logical hierarchy.
        
        Entities: {orphans}
        
        For geography, use: located_in
        For skills, use: is_a  
        For events, use: instance_of
        """
        
        classifications = call_llm(prompt)
        
        # Apply hierarchy
        apply_hierarchy(classifications, entity_type)
```

**One workflow template. Infinite domains.**

---

## Why This Matters

### For Turing (the system)
- Single pattern for all taxonomies
- Multilingual from day one
- Same tools work everywhere
- Clean separation: entities vs. their uses

### For Users
- Consistent experience across domains
- "München" works everywhere, resolves correctly
- Skills in German? Just add entity_names rows

### For AI Workflows
- Entity resolution is a **single capability**
- Train once, apply everywhere
- Ontology matching becomes a first-class operation

### For the Future
- News story matching: same pattern
- Contract clause matching: same pattern
- Scientific paper deduplication: same pattern
- ANY "is this the same thing?" problem: same pattern

---

## The Names We Honor

**Ada Lovelace** - First to see that machines could manipulate symbols, not just numbers.

**Alan Turing** - Formalized computation as pattern recognition and transformation.

**Marvin Minsky** - "The mind is a society of agents" - entities relating to entities.

**Blaise Pascal** - "The heart has reasons that reason knows not" - but we can still encode them.

**Ludwig Wittgenstein** - "The limits of my language are the limits of my world" - so we support all languages.

**Adele Goldberg** - Smalltalk's message-passing: objects (entities) sending messages (relationships).

**Alan Kay** - "The best way to predict the future is to invent it" - so let's build this.

---

## Implementation Status (December 2025)

**Status:** ✅ FULLY OPERATIONAL

### WF3005: Entity Registry - Skill Maintenance

The universal workflow is now implemented for skills:

| Step | Conversation | Actor | Description |
|------|--------------|-------|-------------|
| 1 | w3005_fetch_pending_skills | pending_skills_fetcher | Fetch skills from `entities_pending` |
| 2 | w3005_triage_pending_skills | LLM (qwen2.5) | Decide: NEW / ALIAS / SKIP |
| 3 | w3005_apply_pending_decisions | pending_skills_applier | Create entities + aliases |
| 4 | w3005_fetch_orphan_skills | orphan_skills_fetcher | Get skills without hierarchy |
| 5+ | Classification, grading, debate | Various LLMs | Multi-model consensus |
| 13 | WF3005 Step 9: Apply Decisions | entity_decisions_applier | Save final classifications |

### Data Flow: WF3001 → WF3005

```
New Posting Arrives
        ↓
    WF3001 runs
        ↓
Step 13: Hybrid Job Skills Extraction (LLM extracts skills)
Step 14: Save Posting Skills
        ↓
    SkillResolver.resolve()
        ├── Known skill? → Set entity_id on posting_skills ✅
        └── Unknown skill? → Queue to entities_pending ⏳
        ↓
    WF3005 runs (daily cron at 6:30 AM)
        ↓
    Triage pending skills
        ├── NEW → Create entity + alias
        ├── ALIAS → Map to existing entity
        └── SKIP → Reject
        ↓
    Backfill posting_skills with new aliases ✅
```

### Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| SkillResolver | `core/wave_runner/actors/entity_skill_resolver.py` | Resolve raw skill → entity_id |
| Pending Fetcher | `core/wave_runner/actors/pending_skills_fetcher.py` | Fetch pending for LLM triage |
| Pending Applier | `core/wave_runner/actors/pending_skills_applier.py` | Apply NEW/ALIAS/SKIP decisions |
| QA Check | `scripts/qa_check_entity_aliases.py` | Detect bad alias mappings |
| Review Applier | `scripts/apply_alias_reviews.py` | RAQ-compliant alias corrections |
| Registry Sync | `scripts/run_entity_registry_sync.py` | Orchestrate WF3005 after WF3001 |

### Cron Schedule

```bash
# Entity Registry Sync - Run after WF3001 batch at 6:30 AM
30 6 * * * cd /home/xai/Documents/ty_learn && \
    /home/xai/Documents/ty_learn/venv/bin/python scripts/run_entity_registry_sync.py \
    >> logs/entity_sync.log 2>&1
```

### Current Metrics (2025-12-08)

| Metric | Value |
|--------|-------|
| Skill entities | 47 |
| Active aliases | 79 |
| posting_skills coverage | 96.5% (10,062 / 10,430) |
| Pending skills | 3 |
| QA reviews applied | 2 |

### RAQ Compliance

All operations are **Repeatable, Auditable, QA-controlled**:

1. **Repeatable**: Scripts can re-run without side effects (idempotent)
2. **Auditable**: 
   - `entity_alias_reviews` table tracks all corrections
   - `created_by` field on entities/aliases shows source
   - `deleted_at/deleted_reason` for soft-deleted aliases
3. **QA-controlled**:
   - `qa_check_entity_aliases.py` detects issues
   - Human review → approval workflow
   - Medium-severity items flagged for manual decision

---

## Next Steps

1. ~~Review this proposal~~ ✅ DONE
2. ~~Refine schema~~ ✅ DONE (entity_alias_reviews added)
3. ~~Plan migration~~ ✅ DONE (WF3005 operational)
4. **Build first non-skill entity type** - Geography (TODO)
5. ~~Celebrate~~ 🎉 Skills are live!

---

*"The universe is made of stories, not atoms."* — Muriel Rukeyser

*"And stories are made of entities and their relationships."* — Turing

ℶ
