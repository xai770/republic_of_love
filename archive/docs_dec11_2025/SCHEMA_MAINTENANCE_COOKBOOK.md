# Schema Maintenance Cookbook

**Purpose:** Keep the database clean, focused, and maintainable  
**Philosophy:** Every table, column, and index should have a clear purpose  
**Cadence:** Review quarterly or after major feature changes

---

## 🎯 Why We Do This

Like a well-organized apartment, a clean schema:
- **Reduces cognitive load** - Less noise when reading code
- **Improves performance** - Fewer unused indexes/columns to maintain
- **Prevents bugs** - No hidden dependencies on deprecated fields
- **Enables confidence** - Drop things without fear because you KNOW what uses them

**Marie Kondo Rule:** If it doesn't serve a clear purpose, remove it.

---

## 📋 Maintenance Checklist

### Step 1: Generate Dependency Analysis

Run the full table analysis:

```bash
cd /home/xai/Documents/ty_learn
./scripts/analyze_table_dependencies.sh
```

**Output:** `docs/TABLE_DEPENDENCY_ANALYSIS.md`

**Review:**
- ⚠️ UNUSED tables (0 refs) → Candidates for immediate removal
- 📊 SCHEMA ONLY tables (no Python refs) → Review if still needed
- ✅ ACTIVE tables → Proceed to Step 2 for column analysis

---

### Step 2: Analyze Column Usage (per table)

For each table (especially SCHEMA ONLY or legacy tables):

```bash
./scripts/analyze_column_usage.sh <table_name>
```

**Example:**
```bash
./scripts/analyze_column_usage.sh conversation_runs
./scripts/analyze_column_usage.sh llm_interactions
./scripts/analyze_column_usage.sh posting_state_snapshots
```

**Output:** `docs/COLUMN_USAGE_ANALYSIS_<table>.md`

**Review:**
- Columns with 0 Python references
- Columns only in SELECT * (lazy queries)
- Columns in CREATE TABLE but never populated

---

### Step 3: Decision Matrix

For each unused/questionable element:

| Element Type | Python Refs | SQL Refs | Views | FKs | Decision |
|--------------|-------------|----------|-------|-----|----------|
| **Table** | 0 | 0 | 0 | 0 | 🗑️ DROP immediately |
| **Table** | 0 | 0-10 | 0 | 0 | 🗑️ DROP (just SQL scaffolding) |
| **Table** | 0 | 10+ | 0-2 | 0 | ⚠️ Review if views still needed |
| **Table** | 0 | Any | Any | 1+ | 📝 Document why schema-only, keep for now |
| **Column** | 0 | 0 | 0 | 0 | 🗑️ DROP via migration |
| **Column** | 0 | SELECT * only | 0 | 0 | 🗑️ DROP (lazy query artifact) |
| **Column** | 0 | INSERT but never SELECT | 0 | 0 | 🗑️ DROP (write-only waste) |

---

### Step 4: Create Migration

Template for dropping table:

```sql
-- Migration XXX: Drop unused table <table_name>
-- Date: YYYY-MM-DD
-- Reason: No code references, serves no purpose
--
-- Analysis:
--   Python refs: 0
--   SQL refs: <count>
--   Views: <count>
--   Foreign keys: <count>

BEGIN;

-- Check dependencies first
SELECT 
    tc.table_name, kcu.column_name, ccu.table_name AS foreign_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND (tc.table_name = '<table_name>' OR ccu.table_name = '<table_name>');

-- Drop table
DROP TABLE IF EXISTS <table_name> CASCADE;

-- Verify views still work
-- (list any views that might have referenced this table)

COMMIT;
```

Template for dropping column:

```sql
-- Migration XXX: Drop unused column <table>.<column>
-- Date: YYYY-MM-DD
-- Reason: No code references, never populated
--
-- Analysis:
--   Python refs: 0
--   SQL refs: 0
--   Last populated: NEVER / 2023-05-01

BEGIN;

-- Verify column is truly unused
SELECT COUNT(*) FROM <table> WHERE <column> IS NOT NULL;

-- Drop column
ALTER TABLE <table> DROP COLUMN IF EXISTS <column>;

COMMIT;
```

---

### Step 5: Update Documentation

After dropping tables/columns:

1. **Re-run analysis**:
   ```bash
   ./scripts/analyze_table_dependencies.sh
   git add docs/TABLE_DEPENDENCY_ANALYSIS.md
   ```

2. **Update schema docs**:
   - `sql/event_store_schema.sql` - Remove dropped tables
   - `README.md` - Update table counts
   - Any architecture docs mentioning dropped tables

3. **Commit with context**:
   ```bash
   git commit -m "Schema cleanup: Dropped <table_name> (0 refs, unused)"
   ```

---

## 🔍 Column Usage Analysis Script

**File:** `scripts/analyze_column_usage.sh`

```bash
#!/bin/bash
# Analyze which columns of a table are actually used in code
# Usage: ./analyze_column_usage.sh <table_name>

TABLE_NAME="$1"
DB_NAME="turing"
PROJECT_ROOT="/home/xai/Documents/ty_learn"
OUTPUT_FILE="$PROJECT_ROOT/docs/COLUMN_USAGE_ANALYSIS_${TABLE_NAME}.md"

if [ -z "$TABLE_NAME" ]; then
    echo "Usage: ./analyze_column_usage.sh <table_name>"
    exit 1
fi

echo "🔍 Analyzing column usage for table: $TABLE_NAME"
echo ""

# Get all columns from table
COLUMNS=$(sudo -u postgres psql -d $DB_NAME -t -c "
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = '$TABLE_NAME' 
    ORDER BY ordinal_position;
" | grep -v '^$' | sed 's/^[ \t]*//')

# Start report
cat > "$OUTPUT_FILE" <<EOF
# Column Usage Analysis: \`$TABLE_NAME\`

**Generated:** $(date)
**Database:** $DB_NAME

---

## Summary

| Column | Python Refs | SQL Refs | Status |
|--------|-------------|----------|--------|
EOF

# Analyze each column
while IFS= read -r column; do
    [ -z "$column" ] && continue
    
    # Count Python references (exact word boundary match)
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    # Count SQL references
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    # Determine status
    TOTAL=$((PYTHON_COUNT + SQL_COUNT))
    if [ $TOTAL -eq 0 ]; then
        STATUS="🗑️ UNUSED"
    elif [ $PYTHON_COUNT -eq 0 ]; then
        STATUS="📊 SCHEMA ONLY"
    else
        STATUS="✅ ACTIVE"
    fi
    
    echo "| $column | $PYTHON_COUNT | $SQL_COUNT | $STATUS |" >> "$OUTPUT_FILE"
    
done <<< "$COLUMNS"

cat >> "$OUTPUT_FILE" <<EOF

---

## Recommendations

### Columns to Drop (UNUSED)
EOF

# List unused columns
while IFS= read -r column; do
    [ -z "$column" ] && continue
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    TOTAL=$((PYTHON_COUNT + SQL_COUNT))
    
    if [ $TOTAL -eq 0 ]; then
        echo "- \`$column\`" >> "$OUTPUT_FILE"
    fi
done <<< "$COLUMNS"

cat >> "$OUTPUT_FILE" <<EOF

### Columns to Review (SCHEMA ONLY)
EOF

# List schema-only columns
while IFS= read -r column; do
    [ -z "$column" ] && continue
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    if [ $PYTHON_COUNT -eq 0 ] && [ $SQL_COUNT -gt 0 ]; then
        echo "- \`$column\` (SQL refs: $SQL_COUNT)" >> "$OUTPUT_FILE"
    fi
done <<< "$COLUMNS"

cat >> "$OUTPUT_FILE" <<EOF

---

## Migration Template

\`\`\`sql
-- Migration: Drop unused columns from $TABLE_NAME
BEGIN;

-- Verify columns are truly unused
EOF

# Add verification queries for unused columns
while IFS= read -r column; do
    [ -z "$column" ] && continue
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    TOTAL=$((PYTHON_COUNT + SQL_COUNT))
    
    if [ $TOTAL -eq 0 ]; then
        echo "SELECT COUNT(*) FROM $TABLE_NAME WHERE $column IS NOT NULL;" >> "$OUTPUT_FILE"
    fi
done <<< "$COLUMNS"

cat >> "$OUTPUT_FILE" <<EOF

-- Drop unused columns
EOF

# Add ALTER TABLE statements
while IFS= read -r column; do
    [ -z "$column" ] && continue
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    TOTAL=$((PYTHON_COUNT + SQL_COUNT))
    
    if [ $TOTAL -eq 0 ]; then
        echo "ALTER TABLE $TABLE_NAME DROP COLUMN IF EXISTS $column;" >> "$OUTPUT_FILE"
    fi
done <<< "$COLUMNS"

cat >> "$OUTPUT_FILE" <<EOF

COMMIT;
\`\`\`
EOF

echo "✅ Analysis complete!"
echo "Report: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "  1. Review report: cat $OUTPUT_FILE"
echo "  2. Create migration if dropping columns"
echo "  3. Test in dev environment"
echo "  4. Apply to production"
```

**Setup:**
```bash
chmod +x scripts/analyze_column_usage.sh
```

---

## 🗂️ Table Categories

### Core Business Logic (Never Delete)
- `postings` - Job postings
- `profiles` - User profiles
- `users` - Authentication
- `workflows` - Workflow definitions
- `conversations` - Conversation definitions
- `actors` - LLM/script actors
- `instructions` - Actor instructions

### Event Sourcing (Critical)
- `execution_events` - Immutable event log
- `posting_state_projection` - Materialized view
- `posting_state_snapshots` - Performance optimization

### Workflow Execution (Legacy - Under Review)
- ~~`workflow_runs`~~ - DROPPED (Migration 052)
- ~~`conversation_runs`~~ - **Candidate for removal**
- ~~`llm_interactions`~~ - **Candidate for removal**

### History Tables (Keep for Audit Trail)
- `capabilities_history`
- `conversations_history`
- `instructions_history`
- `workflows_history`

### User Features (Future - No Python Yet)
- `user_posting_decisions`
- `user_posting_preferences`
- `user_saved_postings`

---

## 🚨 Warning Signs

### Red Flags for Tables
- Created > 6 months ago, never populated
- Python refs = 0, SQL refs < 5 (just CREATE TABLE)
- No foreign keys, no views, no triggers
- "_temp" or "_backup" in name (forgot to clean up)

### Red Flags for Columns
- `created_at` exists but `updated_at` always NULL (no updates)
- JSONB column always `{}` or `null` (never used)
- Foreign key to dropped table (broken reference)
- Column name doesn't match naming convention

---

## 📊 Metrics to Track

After each cleanup session:

```sql
-- Before/After comparison
SELECT 
    COUNT(*) as table_count,
    SUM(pg_total_relation_size(schemaname||'.'||tablename)::bigint) as total_size_bytes
FROM pg_tables 
WHERE schemaname = 'public';

-- Unused indexes
SELECT 
    schemaname || '.' || tablename AS table,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Goal:** Reduce table count by 10-20% per year through thoughtful cleanup.

---

## 🎯 Success Criteria

After cleanup, you should be able to:

1. **Explain every table's purpose** in one sentence
2. **List all tables from memory** (if < 50 tables)
3. **Navigate schema confidently** without constant `\d` checks
4. **Drop tables without fear** because analysis tools proved they're unused

**Quote:** "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry

---

## 📅 Quarterly Review Cadence

**Q1 (January):** Full table analysis
**Q2 (April):** Column usage analysis for top 20 tables
**Q3 (July):** Index usage review
**Q4 (October):** View/function cleanup

**Ad-hoc:** After dropping legacy features, before major refactors

---

## 🛠️ Tools Reference

| Tool | Purpose | Output |
|------|---------|--------|
| `schema_code_sync_analyzer.py` | **Primary tool** - Bidirectional sync analysis with FK checking | `SCHEMA_CODE_SYNC_ANALYSIS.md` + migration |
| `analyze_table_dependencies.sh` | Find all code references to tables | `TABLE_DEPENDENCY_ANALYSIS.md` |
| `analyze_column_usage.sh <table>` | Find all code references to columns | `COLUMN_USAGE_ANALYSIS_<table>.md` |
| `psql \d+ <table>` | Show table structure with indexes | Terminal output |
| `psql \df+ <function>` | Show function definition | Terminal output |
| `git grep -w <table_name>` | Search codebase for exact matches | Terminal output |

---

## 🧹 Cleanup Examples

### Example 1: Dropped `workflow_runs` Table

**Analysis:**
- 47,434 orphaned records (database pollution)
- Python refs: 23 (all legacy code)
- Event sourcing made it obsolete

**Action:**
1. Moved old executors to `.OLD`
2. Created Migration 052
3. Dropped with CASCADE (18 dependent objects)
4. Recreated views from event sourcing

**Result:** Clean event-sourced architecture, no legacy pollution

### Example 2: Column Cleanup (Hypothetical)

**Analysis:** `postings.legacy_rating` column
- Created: 2023-02-15
- Python refs: 0
- SQL refs: 1 (CREATE TABLE only)
- Last populated: NULL (never used)

**Action:**
```sql
ALTER TABLE postings DROP COLUMN legacy_rating;
```

**Result:** One less column to maintain, cleaner schema

---

## 🤖 Automated Cleanup Workflow

**The `schema_code_sync_analyzer.py` does it all:**

1. **Scans database** - Gets all tables and columns
2. **Searches code** - Finds references in Python/SQL files
3. **Peeks inside** - Checks actual data (empty? constant? sparse?)
4. **Checks constraints** - Detects FK/PK constraints (won't break schema)
5. **Validates views** - Two-level check: column→view→code
6. **Tracks staleness** - Shows when column was last referenced
7. **Generates migration** - Auto-creates safe DROP statements
8. **Finds orphans** - Code references to deleted tables

**Usage:**
```bash
./scripts/schema_code_sync_analyzer.py
```

**Output:**
- `SCHEMA_CODE_SYNC_ANALYSIS.md` - Full report with verdicts
- `auto_generated_drop_unused_columns.sql` - Safe migration (skips FKs)

**Verdicts:**
- `DELETE_EMPTY` - 0 rows, auto-deletable
- `DELETE_CONSTANT` - Only 1 value, useless
- `DELETE_SPARSE` - < 5 rows, negligible
- `REVIEW_HAS_DATA` - Manual review needed

---

## 🔮 The Curated Approach: Preserving Sparks of Genius

**Philosophy:** Not all "unused" columns are dead weight. Some are **future scaffolding** - intentional designs waiting for implementation.

### The Problem with Blind Cleanup

Running `schema_code_sync_analyzer.py` found 222 "unused" columns (24% of schema). But deleting them all would destroy valuable architectural decisions:

- `interaction_lineage` → Designed for **causation graphs** ("what influenced what")
- `actors.input_format/output_format` → Designed for **contract validation**
- `workflow_dependencies` → Designed for **meta-workflows** (MUST_COMPLETE, MUST_SUCCEED)
- `workflow_triggers` → Designed for **event-driven automation**

### Step 0: Archaeological Investigation

**Before dropping anything, grep your version history:**

```bash
# Search Documents_Versions for design context
grep -r "interaction_lineage" ~/Documents_Versions/ty_learn/
grep -r "workflow_dependencies" ~/Documents_Versions/ty_learn/
grep -r "input_format.*output_format" ~/Documents_Versions/ty_learn/
```

**What you're looking for:**
- Comments explaining "why" not just "what"
- Design docs referencing the column
- TODO comments with future plans
- Old migration files with context

### Curated Migration Template

```sql
-- Migration 055: Curated Schema Cleanup
-- Date: 2025-11-30
-- Philosophy: Delete the dead, preserve the future
--
-- DROPPED (truly dead):
--   - conversation_runs.run_type (constant 'workflow')
--   - conversation_runs.dialogue_round (never used)
--   - conversations.app_scope (constant 'internal')
--   - llm_interactions.error_message (empty)
--
-- PRESERVED (future features):
--   - interaction_lineage (causation graphs)
--   - workflow_dependencies (meta-workflows)
--   - actors.input_format/output_format (contract validation)

BEGIN;

-- Drop truly dead columns (constants, empty tracking, deprecated)
ALTER TABLE conversation_runs DROP COLUMN IF EXISTS run_type;
ALTER TABLE conversation_runs DROP COLUMN IF EXISTS dialogue_round;
ALTER TABLE conversations DROP COLUMN IF EXISTS app_scope;
-- ... more truly dead columns

-- Explicitly NOT dropping (documented futures):
-- ALTER TABLE llm_interactions DROP COLUMN IF EXISTS interaction_lineage;  -- KEEP: causation graphs
-- ALTER TABLE workflows DROP COLUMN IF EXISTS workflow_dependencies;        -- KEEP: meta-workflows

COMMIT;
```

### Decision Matrix: Curated Edition

| Column Status | Code Refs | Historical Context | Decision |
|---------------|-----------|-------------------|----------|
| Unused | 0 | No mentions in Versions | 🗑️ DROP |
| Unused | 0 | Mentioned as "TODO" | 🔮 PRESERVE |
| Unused | 0 | Was working, now deprecated | 🗑️ DROP |
| Constant | N/A | Enum with only 1 value | 🗑️ DROP |
| Sparse | <5 | Test data artifacts | 🗑️ DROP |
| Has data | Any | Working feature | ⚠️ REVIEW |

### Example: Migration 055 Results

**Before:** 896 columns  
**After:** 881 columns  
**Dropped:** 15 truly dead columns  
**Preserved:** 200+ future scaffolding columns  

**Dropped columns (confirmed dead):**
- `run_type`, `dialogue_round`, `app_scope` (constants)
- `error_message`, `model_parameters` (empty tracking)
- `processing_complete`, `source_query` (deprecated)

**Preserved columns (future features):**
- `interaction_lineage` → Causation graph: "which prior interactions influenced this one"
- `workflow_dependencies` → Meta-workflows: run workflow A only after B completes
- `workflow_triggers` → Event-driven: automatically start workflow on event
- `actors.input_format/output_format` → Contract validation: validate I/O against schema

### When to Use Curated vs Aggressive Cleanup

| Scenario | Approach |
|----------|----------|
| New project (<6 months) | Aggressive - nothing historical yet |
| Mature project (>1 year) | **Curated** - preserve design intent |
| Before major refactor | Curated - understand what was planned |
| After deprecation | Aggressive - old feature is truly dead |
| Legacy code cleanup | Curated - archaeology before demolition |

---

## 💡 Pro Tips

1. **Use `grep -w` for exact word boundaries** - Prevents false positives
2. **Check git history** - `git log -S 'table_name'` shows when table was last modified
3. **Trust the analyzer** - FK checking prevents cascade failures
4. **Document migrations** - Future you will thank present you
5. **Batch similar changes** - Group column drops into single migration
6. **Run analysis BEFORE and AFTER** - Prove cleanup reduced complexity
7. **Archive migrations** - They hide schema waste once executed
8. **Grep Documents_Versions** - Catch sparks of genius before deleting
9. **Read the comments** - Schema comments often explain "why"
10. **Curate, don't massacre** - 15 columns > 222 columns when future matters

---

## 🔗 Related Documentation

- `docs/EVENT_SOURCING_IMPLEMENTATION_PLAN.md` - Event sourcing migration
- `docs/WORKFLOW_3001_STUCK_RUNS_ISSUE.md` - Example of database pollution
- `sql/event_store_schema.sql` - Current schema definition
- `migrations/` - All schema changes with context

---

**Remember:** A clean schema is a reflection of a clean mind. Every table removed is cognitive space freed up for solving real problems. 🧘
