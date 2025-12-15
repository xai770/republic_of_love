# Schema Improvements - October 30, 2025

## Overview

Comprehensive schema and code improvements to eliminate naming inconsistencies, simplify dual-mode logic, and improve documentation.

## Changes Made

### 1. ✅ Standardized Naming Conventions

**Problem:** Inconsistent column names across tables caused confusion and bugs.

**Solution:** Unified naming for common concepts:

| Concept | Old Names | **Standardized To** |
|---------|-----------|-------------------|
| Completion time | `ended_at`, `completed_at` | **`completed_at`** |
| Error info | `error_message`, `error_details` | **`error_details`** |
| Session order | `execution_order`, `session_number` | **`execution_order`** |

**Impact:**
- Code can now use consistent field names
- Reduces mental overhead when working across tables
- Prevents "column does not exist" errors

---

### 2. ✅ Simplified Session Runs Table

**Problem:** `session_runs` table had confusing dual-mode with two mutually exclusive FKs:
```sql
-- OLD (confusing!)
recipe_run_id (for testing)
production_run_id (for production)
CHECK: exactly one must be non-NULL
```

**Solution:** Unified into single run concept:
```sql
-- NEW (clean!)
run_id INTEGER NOT NULL
run_type TEXT CHECK (run_type IN ('testing', 'production'))
```

**Migration:**
```sql
-- Add new columns
ALTER TABLE session_runs ADD COLUMN run_id INTEGER;
ALTER TABLE session_runs ADD COLUMN run_type TEXT;

-- Populate from existing data
UPDATE session_runs 
SET run_id = recipe_run_id,
    run_type = 'testing'
WHERE recipe_run_id IS NOT NULL;

UPDATE session_runs 
SET run_id = production_run_id,
    run_type = 'production'
WHERE production_run_id IS NOT NULL;

-- Drop old columns after validation
ALTER TABLE session_runs DROP COLUMN recipe_run_id;
ALTER TABLE session_runs DROP COLUMN production_run_id;

-- Add constraints
ALTER TABLE session_runs ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE session_runs ALTER COLUMN run_type SET NOT NULL;
ALTER TABLE session_runs ADD CONSTRAINT session_runs_run_type_check 
  CHECK (run_type IN ('testing', 'production'));
```

**Benefits:**
- Simpler queries: no more `WHERE recipe_run_id IS NOT NULL` conditionals
- Clearer semantics: a "run" is a "run" regardless of mode
- Easier to add new run types in future (e.g., 'experiment', 'debug')

---

### 3. ✅ Fixed Table Name Mismatch

**Problem:** Code queried non-existent `session_instructions` table.

**Root Cause:** Table is actually just `instructions` with `session_id` FK.

**Solution:** Updated `recipe_engine.py` to query `instructions` directly:
```python
# OLD (broken)
FROM session_instructions si

# NEW (correct)
FROM instructions i
WHERE i.session_id = %s
```

**Why the confusion happened:**
- Many-to-many relationships typically use junction tables
- But `instructions` already belongs to exactly one session via FK
- No junction table needed!

---

### 4. 📖 Improved Actor Delegation Documentation

**Problem:** Helper/delegate pattern wasn't clear from schema alone.

**Context:** 
- Sessions belong to a **primary actor** (LLM)
- Instructions can **delegate** to helpers (database, web search, skill_gopher)
- Previous session outputs available to primary actor
- Delegation is temporary - returns control to primary actor

**Solution:** Enhanced schema comments and created visual documentation.

### Helper/Delegate Pattern Explained

```
┌─────────────────────────────────────────────────────┐
│ SESSION (Primary Actor: qwen2.5:7b)               │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Instruction 1: "Extract skills from posting"       │
│  ├─ Actor: qwen2.5:7b (primary - inherited)       │
│  └─ Output: ["Python", "SQL", "AWS"]              │
│                                                      │
│  Instruction 2: "Map to taxonomy"                   │
│  ├─ Actor: skill_gopher (DELEGATED helper)        │
│  ├─ Input: ["Python", "SQL", "AWS"]              │
│  ├─ skill_gopher queries database hierarchy       │
│  ├─ skill_gopher returns canonical matches        │
│  └─ Output: ["PYTHON", "SQL", "AWS_CLOUD"]       │
│                                                      │
│  Instruction 3: "Format as summary"                 │
│  ├─ Actor: qwen2.5:7b (primary - back in control) │
│  ├─ Has access to ALL previous outputs:           │
│  │   • Instruction 1 output (raw skills)          │
│  │   • Instruction 2 output (mapped skills)       │
│  └─ Output: Formatted summary with taxonomy       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Key Principles:**

1. **Session Context Persistence**
   - Primary actor has access to ALL previous instruction outputs in session
   - Helper outputs become part of session context
   - Enables multi-step reasoning chains

2. **Delegation is Temporary**
   - Helper executes ONE instruction
   - Returns control to primary actor
   - Primary actor can use helper's output in next instruction

3. **Helpers are Specialized**
   ```
   skill_gopher    → Taxonomy queries & hierarchy navigation
   db_query        → Database reads/writes
   web_search      → Internet research
   validator       → Data quality checks
   python_script   → Custom data processing
   ```

4. **Fallback Logic**
   ```python
   # Execution resolution:
   if instruction.delegate_actor_id is not None:
       actor = get_actor(instruction.delegate_actor_id)
   else:
       actor = session.primary_actor  # Default
   ```

**Recipe 1114 Example:**

```
Session 1: Extract Summary (primary: gemma3:1b)
  ├─ Instruction 1: Extract with gemma3
  
Session 8: Extract Skills (primary: qwen2.5:7b)
  ├─ Instruction 1: Extract raw skills (qwen does this)
  
Session 9: Map to Taxonomy (primary: qwen2.5:7b)
  ├─ Instruction 1: Translate & map to taxonomy
  │   • Gets session 8 output via {session_8_output}
  │   • Uses hardcoded taxonomy in prompt (OLD)
  │   • OR uses {taxonomy} for dynamic (NEW!)
```

**Updated Schema Comments:**

```sql
COMMENT ON COLUMN instructions.delegate_actor_id IS 
'Optional: Override session primary actor for THIS INSTRUCTION ONLY.

Use Cases:
- Query skill_gopher for taxonomy navigation
- Execute SQL scripts for data operations  
- Run validators for quality checks
- Call Python scripts for transformations

Execution Logic:
IF delegate_actor_id IS NOT NULL:
    Execute with delegated actor
ELSE:
    Execute with session.actor_id (primary)

Context Inheritance:
- Delegated helper receives same session context
- Helper output added to session_outputs
- Primary actor can reference helper output in next instruction
- Example: {session_2_output} works whether session 2 used helper or not

Example:
  session.actor_id = "qwen2.5:7b"            (primary)
  instruction.delegate_actor_id = "skill_gopher" (helper)
  
  → Instruction executed by skill_gopher
  → Output stored in session_outputs
  → Next instruction (primary actor) can use it';
```

---

### 5. 📁 Schema File Management

**Current State:** Multiple schema exports without clear "latest"

**Solution:** Using `ls -lt` works, but added convention:

**Convention:**
```
Primary Source:   backups/by_schema_only_YYYYMMDD_HHMMSS.sql
Latest Symlink:   data/base_yoga_schema_current.sql → latest backup
Auto-Cleanup:     Keep last 30 days of backups only
```

**Implementation:**
```bash
# Update symlink after each backup
ln -sf /home/xai/Documents/ty_learn/backups/by_schema_only_$(date +%Y%m%d)_*.sql \
       /home/xai/Documents/ty_learn/data/base_yoga_schema_current.sql

# Cleanup old backups (keep 30 days)
find /home/xai/Documents/ty_learn/backups/ -name "by_schema_only_*.sql" \
  -mtime +30 -delete
```

**Benefits:**
- Always know which is current: `data/base_yoga_schema_current.sql`
- Historical versions preserved in `backups/`
- Automatic cleanup prevents disk bloat
- Works with RFA Documents_Versions system

---

## Implementation Status

### ✅ Completed
- [x] Analyzed schema inconsistencies
- [x] Documented helper/delegate pattern
- [x] Fixed recipe_engine.py column name bugs
- [x] Created migration SQL scripts

### 🚧 In Progress
- [ ] Execute schema migrations
- [ ] Update all queries to use standardized names
- [ ] Add enhanced schema comments

### 📋 TODO
- [ ] Test with Recipe 1122 (dynamic taxonomy)
- [ ] Update all recipe runners to use new column names
- [ ] Validate session_runs dual-mode removal
- [ ] Update schema diagrams

---

## Testing Strategy

### Phase 1: Schema Migration
```bash
# Backup first!
pg_dump base_yoga > pre_migration_backup.sql

# Execute migrations
psql base_yoga < migrations/001_standardize_naming.sql
psql base_yoga < migrations/002_unify_session_runs.sql
psql base_yoga < migrations/003_update_comments.sql
```

### Phase 2: Code Updates
```bash
# Update recipe_engine.py
# Update all runners in runners/
# Update test scripts
```

### Phase 3: Validation
```bash
# Run Recipe 1122 with dynamic taxonomy
python3 runners/run_recipe.py --recipe-id 1122 --profile-id 3 --mode testing

# Verify session_runs queries work
psql base_yoga -c "SELECT * FROM session_runs WHERE run_type = 'testing' LIMIT 5;"

# Check for any remaining old column references
grep -r "ended_at\|error_message\|session_number" core/ runners/ scripts/
```

---

## Documentation for Future Arden

### Quick Reference: Standard Names

When working with this database, **always use**:

| Concept | Use This | NOT These |
|---------|----------|-----------|
| When execution finished | `completed_at` | ~~ended_at~~ |
| Error information | `error_details` | ~~error_message~~ |
| Session sequence | `execution_order` | ~~session_number~~ |
| Run identifier | `run_id` + `run_type` | ~~recipe_run_id, production_run_id~~ |

### Helper Pattern Checklist

When you see `delegate_actor_id` in an instruction:

1. ✅ Expect helper actor to execute (not primary)
2. ✅ Helper gets session context as input
3. ✅ Helper output stored in `session_outputs`
4. ✅ Next instruction (primary actor) can reference it
5. ✅ Helper doesn't maintain state between instructions

### Finding Latest Schema

```bash
# Method 1: Use symlink
cat data/base_yoga_schema_current.sql

# Method 2: Latest backup
ls -lt backups/by_schema_only_*.sql | head -1

# Method 3: From database directly
pg_dump --schema-only base_yoga > /tmp/current_schema.sql
```

---

## Files Modified

- `/home/xai/Documents/ty_learn/core/recipe_engine.py` - Fixed column names
- `/home/xai/Documents/ty_learn/core/prompt_renderer.py` - Added {taxonomy} support
- `/home/xai/Documents/ty_learn/core/taxonomy_helper.py` - Created (dynamic taxonomy)
- `/home/xai/Documents/ty_learn/docs/SCHEMA_IMPROVEMENTS_20251030.md` - This doc

## Next Steps

1. **Execute migrations** (after review)
2. **Test Recipe 1122** with dynamic taxonomy
3. **Update remaining code** to use standard names
4. **Generate updated schema diagrams**

---

**Collaborators:** xai (architect), Arden (implementation)
**Date:** 2025-10-30
**Status:** Documentation complete, migrations ready for execution
