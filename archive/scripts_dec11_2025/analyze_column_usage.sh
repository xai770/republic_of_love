#!/bin/bash
# analyze_column_usage.sh
# 
# Analyzes which columns of a table are actually used in code
# Usage: ./analyze_column_usage.sh <table_name>

TABLE_NAME="$1"
DB_NAME="turing"
PROJECT_ROOT="/home/xai/Documents/ty_learn"
OUTPUT_FILE="$PROJECT_ROOT/docs/COLUMN_USAGE_ANALYSIS_${TABLE_NAME}.md"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$TABLE_NAME" ]; then
    echo -e "${RED}Error: Table name required${NC}"
    echo "Usage: ./analyze_column_usage.sh <table_name>"
    echo ""
    echo "Example:"
    echo "  ./analyze_column_usage.sh conversation_runs"
    exit 1
fi

echo -e "${BLUE}🔍 Analyzing column usage for table: $TABLE_NAME${NC}"
echo ""

# Check if table exists
TABLE_EXISTS=$(sudo -u postgres psql -d $DB_NAME -t -c "
    SELECT COUNT(*) FROM information_schema.tables 
    WHERE table_name = '$TABLE_NAME';
" | tr -d ' ')

if [ "$TABLE_EXISTS" -eq 0 ]; then
    echo -e "${RED}Error: Table '$TABLE_NAME' not found in database '$DB_NAME'${NC}"
    exit 1
fi

# Get all columns from table
echo "Fetching columns from database..."
COLUMNS=$(sudo -u postgres psql -d $DB_NAME -t -c "
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = '$TABLE_NAME'
      AND table_schema = 'public'
    ORDER BY ordinal_position;
" | sed 's/^[ \t]*//;s/[ \t]*$//' | grep -v '^$')

COLUMN_COUNT=$(echo "$COLUMNS" | grep -c .)
echo "Found $COLUMN_COUNT columns"
echo ""

# Start report
cat > "$OUTPUT_FILE" <<EOF
# Column Usage Analysis: \`$TABLE_NAME\`

**Generated:** $(date)
**Database:** $DB_NAME
**Columns Analyzed:** $COLUMN_COUNT

---

## Summary

| Column | Python Refs | SQL Refs | Populated | Status |
|--------|-------------|----------|-----------|--------|
EOF

echo "Analyzing references in codebase..."
UNUSED_COUNT=0
SCHEMA_ONLY_COUNT=0
ACTIVE_COUNT=0

# Temporary file for sorting
TEMP_SUMMARY=$(mktemp)

# Analyze each column
while IFS= read -r column; do
    [ -z "$column" ] && continue
    
    echo -ne "  Analyzing: $column\r"
    
    # Count Python references (exact word boundary match)
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    # Count SQL references
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    # Check if column is populated (sample first 1000 rows)
    POPULATED=$(sudo -u postgres psql -d $DB_NAME -t -c "
        SELECT CASE WHEN COUNT(*) > 0 THEN 'Yes' ELSE 'No' END
        FROM (SELECT 1 FROM $TABLE_NAME WHERE $column IS NOT NULL LIMIT 1) t;
    " 2>/dev/null | tr -d ' ')
    
    if [ -z "$POPULATED" ]; then
        POPULATED="Error"
    fi
    
    # Determine status
    TOTAL=$((PYTHON_COUNT + SQL_COUNT))
    if [ $TOTAL -eq 0 ]; then
        STATUS="🗑️ UNUSED"
        UNUSED_COUNT=$((UNUSED_COUNT + 1))
        SORT_KEY="1"
    elif [ $PYTHON_COUNT -eq 0 ]; then
        STATUS="📊 SCHEMA"
        SCHEMA_ONLY_COUNT=$((SCHEMA_ONLY_COUNT + 1))
        SORT_KEY="2"
    else
        STATUS="✅ ACTIVE"
        ACTIVE_COUNT=$((ACTIVE_COUNT + 1))
        SORT_KEY="3"
    fi
    
    # Add to temp file with sort key
    echo "${SORT_KEY}|${column}|${PYTHON_COUNT}|${SQL_COUNT}|${POPULATED}|${STATUS}" >> "$TEMP_SUMMARY"
    
done <<< "$COLUMNS"

# Sort and append to report (unused first, then schema, then active)
sort "$TEMP_SUMMARY" | cut -d'|' -f2- | while IFS='|' read -r col py sql pop stat; do
    echo "| $col | $py | $sql | $pop | $stat |" >> "$OUTPUT_FILE"
done

rm "$TEMP_SUMMARY"

echo ""
echo -e "${GREEN}Analysis complete!${NC}"
echo "  Active columns: $ACTIVE_COUNT"
echo "  Schema-only columns: $SCHEMA_ONLY_COUNT"
echo "  Unused columns: $UNUSED_COUNT"
echo ""

# Continue building report
cat >> "$OUTPUT_FILE" <<EOF

**Statistics:**
- ✅ Active: $ACTIVE_COUNT columns
- 📊 Schema Only: $SCHEMA_ONLY_COUNT columns
- 🗑️ Unused: $UNUSED_COUNT columns

---

## Recommendations

### Columns to Drop (UNUSED)

EOF

# List unused columns with details
HAS_UNUSED=false
while IFS= read -r column; do
    [ -z "$column" ] && continue
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    TOTAL=$((PYTHON_COUNT + SQL_COUNT))
    
    if [ $TOTAL -eq 0 ]; then
        HAS_UNUSED=true
        POPULATED=$(sudo -u postgres psql -d $DB_NAME -t -c "
            SELECT COUNT(*) FROM (SELECT 1 FROM $TABLE_NAME WHERE $column IS NOT NULL LIMIT 1) t;
        " 2>/dev/null | tr -d ' ')
        
        if [ "$POPULATED" -eq 0 ]; then
            echo "- \`$column\` - Never populated, completely unused" >> "$OUTPUT_FILE"
        else
            echo "- \`$column\` - Has data but no code references (orphaned)" >> "$OUTPUT_FILE"
        fi
    fi
done <<< "$COLUMNS"

if [ "$HAS_UNUSED" = false ]; then
    echo "None! All columns are referenced somewhere. ✨" >> "$OUTPUT_FILE"
fi

cat >> "$OUTPUT_FILE" <<EOF

### Columns to Review (SCHEMA ONLY)

These columns are only referenced in SQL files (migrations, views), not in Python code:

EOF

HAS_SCHEMA_ONLY=false
while IFS= read -r column; do
    [ -z "$column" ] && continue
    PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    if [ $PYTHON_COUNT -eq 0 ] && [ $SQL_COUNT -gt 0 ]; then
        HAS_SCHEMA_ONLY=true
        echo "- \`$column\` (SQL refs: $SQL_COUNT)" >> "$OUTPUT_FILE"
    fi
done <<< "$COLUMNS"

if [ "$HAS_SCHEMA_ONLY" = false ]; then
    echo "None! All columns with SQL references also have Python usage. ✨" >> "$OUTPUT_FILE"
fi

# Add migration template if there are unused columns
if [ $UNUSED_COUNT -gt 0 ]; then
    cat >> "$OUTPUT_FILE" <<EOF

---

## Migration Template

\`\`\`sql
-- Migration: Drop unused columns from $TABLE_NAME
-- Generated: $(date)
-- Unused columns: $UNUSED_COUNT

BEGIN;

-- Verify columns are truly unused (check if populated)
EOF

    # Add verification queries for unused columns
    while IFS= read -r column; do
        [ -z "$column" ] && continue
        PYTHON_COUNT=$(grep -rw "$column" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
        SQL_COUNT=$(grep -rw "$column" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
        TOTAL=$((PYTHON_COUNT + SQL_COUNT))
        
        if [ $TOTAL -eq 0 ]; then
            echo "SELECT '$column' AS column_name, COUNT(*) AS populated_rows FROM $TABLE_NAME WHERE $column IS NOT NULL;" >> "$OUTPUT_FILE"
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

**⚠️ Warning:** Always test in dev environment first!

EOF
else
    cat >> "$OUTPUT_FILE" <<EOF

---

## No Migration Needed

All columns in \`$TABLE_NAME\` are actively used! 🎉

This table is well-maintained with no dead weight.

EOF
fi

# Add detailed references section
cat >> "$OUTPUT_FILE" <<EOF

---

## Detailed References

EOF

while IFS= read -r column; do
    [ -z "$column" ] && continue
    
    cat >> "$OUTPUT_FILE" <<EOF

### \`$column\`

EOF
    
    # Python references
    PYTHON_REFS=$(grep -rn "\\b$column\\b" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | head -10)
    if [ -z "$PYTHON_REFS" ]; then
        echo "**Python:** No references" >> "$OUTPUT_FILE"
    else
        echo "**Python references (first 10):**" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
        echo "$PYTHON_REFS" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
    
    # SQL references
    SQL_REFS=$(grep -rn "\\b$column\\b" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | head -10)
    if [ -z "$SQL_REFS" ]; then
        echo "**SQL:** No references" >> "$OUTPUT_FILE"
    else
        echo "**SQL references (first 10):**" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
        echo "$SQL_REFS" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
    
done <<< "$COLUMNS"

echo "Report saved to: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "  1. Review report: cat $OUTPUT_FILE"
if [ $UNUSED_COUNT -gt 0 ]; then
    echo "  2. Create migration from template"
    echo "  3. Test in dev environment"
    echo "  4. Apply to production"
else
    echo "  2. Celebrate! This table is clean. 🎉"
fi
echo ""
