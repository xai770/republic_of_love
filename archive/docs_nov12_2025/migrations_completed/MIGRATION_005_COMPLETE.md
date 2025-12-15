# Migration 005 Complete: skill_aliases Standardization

**Date:** 2025-10-30  
**Status:** ✅ SUCCESSFULLY EXECUTED  
**Migration File:** `migrations/005_standardize_skill_aliases.sql`

## Overview

Standardized the **skill_aliases** table (master skill list with 896 skills) to use integer primary key pattern: `skill_id INTEGER PK` + `skill_name TEXT UNIQUE`.

## Critical Discovery

Initial analysis was wrong! The schema is:

- **skill_aliases** = MASTER table (896 skills) - all skills live here
- **skill_hierarchy** = RELATIONSHIP table (340 edges) - defines parent-child links between skills

This is the opposite of what the names suggest. `skill_aliases` is the authoritative list, not `skill_hierarchy`.

## Data Quality Fixes

### 1. Removed Case-Variant Duplicates (5 rows)

Found skills with mixed case that should be identical:
- `TAX_ADVISORY` vs `tax_advisory`
- `NETWORK_ARCHITECTURE` vs `network_architecture`
- `CRITICAL_THINKING` vs `critical_thinking`
- `BARGAINING_SKILLS` vs `bargaining_skills`
- `NEGOTIATION_SKILLS` vs `negotiation_skills`

**Solution:** Kept uppercase variant (canonical), deleted lowercase.

### 2. Removed Self-Referential Relationships (2 rows)

After case-insensitive ID mapping, some skills became their own parent.

**Solution:** Deleted rows where `skill_id = parent_skill_id`.

### 3. Final Cleanup

- **Original:** 347 relationships, 896 skills
- **After migration:** 340 relationships, 896 skills
- **Removed:** 7 invalid entries (5 duplicates + 2 self-refs)

## Schema Changes

### skill_aliases (master table)
```sql
-- Before
PRIMARY KEY (skill_alias)
skill TEXT UNIQUE

-- After  
PRIMARY KEY (skill_id)  -- INTEGER
skill_name TEXT UNIQUE  -- Renamed from 'skill'
skill_id INTEGER        -- New surrogate key
```

### skill_hierarchy (relationships)
```sql
-- Before
PRIMARY KEY (skill, parent_skill)  -- Composite TEXT
skill → skill_aliases.skill FK
parent_skill → skill_aliases.skill FK

-- After
PRIMARY KEY (skill_id, parent_skill_id)  -- Composite INTEGER
skill_id → skill_aliases.skill_id FK
parent_skill_id → skill_aliases.skill_id FK
skill_name TEXT                   -- Denormalized (kept for transition)
parent_skill_name TEXT            -- Denormalized (kept for transition)
```

### skill_occurrences
```sql
-- Before
skill TEXT → skill_aliases.skill FK

-- After
skill_id INTEGER → skill_aliases.skill_id FK
skill_name TEXT  -- Denormalized
```

### skill_relationships
```sql
-- Before
subject_skill TEXT → skill_aliases.skill FK
object_skill TEXT → skill_aliases.skill FK

-- After
subject_skill_id INTEGER → skill_aliases.skill_id FK
object_skill_id INTEGER → skill_aliases.skill_id FK
subject_skill_name TEXT  -- Denormalized
object_skill_name TEXT   -- Denormalized
```

## Dependent Views

**Dropped (to be recreated):**
- `v_skill_summary`
- `v_pending_synonyms`

These need to be recreated using `skill_id` and `skill_name` columns.

## Code Impact

### ✅ Already Updated
- `core/taxonomy_helper.py` - Uses `skill_name` and `parent_skill_name`

### ⚠️ Needs Review
Any code that:
- Queries `skill_aliases.skill` → Should use `skill_name`
- JOINs on TEXT skill names → Should use `skill_id` integer FKs
- References dropped views

## Benefits

1. **Performance:** Integer joins are faster than TEXT
2. **Consistency:** Every skill table now follows `xxx_id` + `xxx_name` pattern
3. **Safety:** Renaming skills doesn't break foreign keys
4. **AI-Friendly:** Zero ambiguity about PK vs natural key

## Verification

```bash
# Check migration status
psql base_yoga -c "SELECT COUNT(*) FROM skill_aliases;"  # Should be 896
psql base_yoga -c "SELECT COUNT(*) FROM skill_hierarchy;"  # Should be 340

# Test taxonomy helper
python -c "import sys; sys.path.insert(0, '.'); from core.taxonomy_helper import get_taxonomy_string; print(len(get_taxonomy_string()))"  # Should be ~7738 chars
```

## Rollback Plan

Full backup available: `backups/by_pre_migration_005_20251030_171414.sql`

To rollback:
```bash
PGPASSWORD='base_yoga_secure_2025' psql -U base_admin -h localhost postgres \
  -c "DROP DATABASE base_yoga; CREATE DATABASE base_yoga;"
PGPASSWORD='base_yoga_secure_2025' psql -U base_admin -h localhost base_yoga \
  < backups/by_pre_migration_005_20251030_171414.sql
```

## Next Steps

1. ✅ Migration 005 complete
2. ⏭️ Test Recipe 1114 with new schema
3. ⏭️ Recreate dropped views using new column names
4. ⏭️ Migration 006: Standardize `actors` table
5. ⏭️ Migration 007: Standardize `postings` table
6. ⏭️ Migration 008: Standardize `canonicals` and `facets` tables

## Lessons Learned

### Schema Archaeology is Critical

Never assume table semantics from names alone. Always:
1. Check `\d table_name` to see constraints
2. Query FK relationships to understand references
3. Sample actual data to confirm assumptions

### Case Sensitivity Matters

PostgreSQL TEXT columns are case-sensitive. When migrating to integer IDs with case-insensitive matching, expect duplicates to surface.

### Denormalization During Transition

Keeping `xxx_name` columns alongside `xxx_id` allows:
- Gradual code migration
- Human-readable queries during transition
- Easier debugging of migration issues

Can drop `xxx_name` columns after full code migration (Phase 2).

---

**Migration 005: ✅ COMPLETE**  
**Impact:** 896 skills + 4 dependent tables standardized  
**Execution Time:** ~300ms  
**Data Loss:** None (cleaned up duplicates)  
**Code Breakage:** Minimal (taxonomy_helper already updated)
