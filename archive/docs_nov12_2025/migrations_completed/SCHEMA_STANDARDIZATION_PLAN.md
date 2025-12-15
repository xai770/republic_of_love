# Schema Standardization Plan
**Date:** 2025-10-30  
**Goal:** Standardize all tables to use `xxx_id INTEGER PK` + `xxx_name TEXT UNIQUE`

## Philosophy

**Consistency over semantic exceptions.**

Every table follows the same contract:
- `xxx_id` INTEGER PRIMARY KEY (auto-increment) - for machines
- `xxx_name` TEXT UNIQUE NOT NULL - for humans

No exceptions. Zero ambiguity. Maximum predictability for both humans and AI.

## Benefits

1. **AI Comprehension** - Arden always knows the pattern
2. **Join Simplicity** - Every join is predictable
3. **Refactoring Safety** - FKs use stable integers
4. **Schema Self-Documentation** - Pattern is instantly recognizable
5. **Future-Proof** - No special cases to remember

## Migration Phases

### Phase 1: Low-Risk Tables (No Dependencies)
**Impact:** Minimal - these have no or few foreign keys

1. **skill_hierarchy** (347 rows, no FKs)
   - Current: `(skill, parent_skill)` composite PK (both TEXT)
   - New: `skill_id INTEGER PK`, `skill_name TEXT UNIQUE`, `parent_skill_id INTEGER`
   
2. **History tables** (5 tables)
   - canonicals_history, facets_history, instructions_history, recipes_history, sessions_history, variations_history
   - Current: `history_id` INTEGER
   - Change to: `{table}_history_id` INTEGER (naming consistency)

### Phase 2: Medium-Risk Tables (3-5 Dependencies)
**Impact:** Moderate - need to update several referencing tables

3. **actors** (47 rows, 3 FKs)
   - Current: `actor_id TEXT PK` (e.g., 'qwen2.5:7b')
   - New: `actor_id INTEGER PK`, `actor_name TEXT UNIQUE`
   - Referenced by: sessions, instructions.delegate_actor_id, human_tasks

4. **canonicals** (62 rows, 1 FK)
   - Current: `canonical_code TEXT PK` (e.g., 'PYTHON_PROGRAMMING')
   - New: `canonical_id INTEGER PK`, `canonical_code TEXT UNIQUE`
   - Referenced by: sessions

5. **facets** (74 rows, 2 FKs)
   - Current: `facet_id TEXT PK` (e.g., 'TECHNICAL_SKILLS')
   - New: `facet_id INTEGER PK`, `facet_name TEXT UNIQUE`
   - Referenced by: canonicals, facets (self-ref)

### Phase 3: High-Risk Tables (Many Dependencies)
**Impact:** Significant - core tables with many references

6. **postings** (76 rows, 3 FKs)
   - Current: `job_id TEXT PK` (mix of '15929' and 'TEST_ORACLE_DBA_001')
   - New: `posting_id INTEGER PK`, `job_name TEXT UNIQUE NULLABLE`
   - Referenced by: job_skills, production_runs.posting_id, profile_job_matches

7. **skill_aliases** (896 rows, 5 FKs to skill_hierarchy)
   - Current: `skill_alias TEXT PK`
   - New: `skill_alias_id INTEGER PK`, `skill_alias_name TEXT UNIQUE`
   - After skill_hierarchy migration

### Phase 4: Cleanup Tables (Minor Fixes)

8. **Composite PK Tables** - Add surrogate keys:
   - skill_relationships: `(subject_skill, relationship_type, object_skill)` → `skill_relationship_id`
   - schema_documentation: `(table_name, column_name)` → `documentation_id`

9. **Naming Fixes**:
   - batches: `batch_id` is correct but verify consistency
   - instruction_branch_executions: `execution_id` → `branch_execution_id`
   - instruction_branches: `branch_id` is correct
   - profile_* tables: Already correct pattern

## Migration Strategy

### For Each Table:

```sql
BEGIN;

-- 1. Add new INTEGER column
ALTER TABLE xxx ADD COLUMN xxx_id_new INTEGER;

-- 2. Create sequence and populate
CREATE SEQUENCE xxx_xxx_id_seq;
UPDATE xxx SET xxx_id_new = nextval('xxx_xxx_id_seq');
ALTER TABLE xxx ALTER COLUMN xxx_id_new SET DEFAULT nextval('xxx_xxx_id_seq');

-- 3. Rename old PK column to xxx_name
ALTER TABLE xxx RENAME COLUMN xxx_id TO xxx_name;

-- 4. Rename new column to xxx_id
ALTER TABLE xxx RENAME COLUMN xxx_id_new TO xxx_id;

-- 5. Update all foreign key references
-- (specific to each table)

-- 6. Set constraints
ALTER TABLE xxx DROP CONSTRAINT xxx_pkey;
ALTER TABLE xxx ADD PRIMARY KEY (xxx_id);
ALTER TABLE xxx ADD CONSTRAINT xxx_name_unique UNIQUE (xxx_name);
ALTER TABLE xxx ALTER COLUMN xxx_name SET NOT NULL;

COMMIT;
```

## Testing Strategy

For each migration:
1. ✅ Run migration on test database
2. ✅ Verify all foreign keys intact
3. ✅ Run Recipe 1114 end-to-end test
4. ✅ Check admin GUI still works
5. ✅ Backup production before applying
6. ✅ Create rollback script

## Priority Order

1. **Week 1:** Phase 1 (history tables, skill_hierarchy) - Low risk, high value
2. **Week 2:** Phase 2 (actors, canonicals, facets) - Medium risk, prepares for Phase 3
3. **Week 3:** Phase 3 (postings, skill_aliases) - High risk, needs careful testing
4. **Week 4:** Phase 4 (cleanup) - Polish and consistency

## Expected Benefits Post-Migration

### Code Simplification
```python
# Before (ambiguous):
cursor.execute("SELECT * FROM actors WHERE actor_id = %s", ('qwen2.5:7b',))  # Is this text or int?

# After (always clear):
cursor.execute("SELECT * FROM actors WHERE actor_id = %s", (5,))  # Always integer
cursor.execute("SELECT * FROM actors WHERE actor_name = %s", ('qwen2.5:7b',))  # Always text
```

### Query Clarity
```sql
-- Before (mixed types):
SELECT s.session_name, a.actor_id 
FROM sessions s 
JOIN actors a ON s.actor_id = a.actor_id  -- Text join, prone to typos

-- After (consistent):
SELECT s.session_name, a.actor_name
FROM sessions s
JOIN actors a ON s.actor_id = a.actor_id  -- Integer join, fast and safe
```

## Rollback Plan

Each migration includes:
1. Pre-migration backup
2. Rollback SQL script
3. Verification queries

If issues arise, restore from backup and investigate before retry.

---

**Next Steps:** Start with Phase 1 (skill_hierarchy) as proof-of-concept?
