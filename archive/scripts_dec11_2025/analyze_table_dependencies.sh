#!/bin/bash
# analyze_table_dependencies.sh
# 
# Analyzes all tables in the database for code/schema dependencies
# Usage: ./analyze_table_dependencies.sh [table_name]
#        If table_name provided, analyzes only that table
#        If no argument, analyzes ALL tables

DB_NAME="turing"
PROJECT_ROOT="/home/xai/Documents/ty_learn"
OUTPUT_FILE="$PROJECT_ROOT/docs/TABLE_DEPENDENCY_ANALYSIS.md"

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🔍 Database Table Dependency Analyzer"
echo "======================================"
echo ""

# Get list of tables
if [ -n "$1" ]; then
    TABLES="$1"
    echo "Analyzing single table: $TABLES"
else
    echo "Fetching all tables from database '$DB_NAME'..."
    TABLES=$(sudo -u postgres psql -d $DB_NAME -t -c "
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename;
    " | grep -v '^$' | sed 's/^[ \t]*//')
    
    TABLE_COUNT=$(echo "$TABLES" | wc -l)
    echo "Found $TABLE_COUNT tables"
fi

# Initialize markdown report
cat > "$OUTPUT_FILE" <<'EOF'
# Database Table Dependency Analysis

**Generated:** $(date)
**Database:** turing
**Project:** ty_learn

This report shows all references to each database table across the codebase.

---

## Summary

| Table | Python Refs | SQL Refs | Views | Foreign Keys | Status |
|-------|-------------|----------|-------|--------------|--------|
EOF

# Temporary file for summary data
SUMMARY_FILE=$(mktemp)

echo ""
echo "Analyzing dependencies..."
echo ""

# Process each table
while IFS= read -r table; do
    # Skip empty lines
    [ -z "$table" ] && continue
    
    echo -e "${BLUE}Analyzing: $table${NC}"
    
    # Count Python references
    PYTHON_COUNT=$(grep -r "\b$table\b" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    # Count SQL references
    SQL_COUNT=$(grep -r "\b$table\b" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | wc -l)
    
    # Check if table is referenced in views
    VIEW_COUNT=$(sudo -u postgres psql -d $DB_NAME -t -c "
        SELECT COUNT(*) 
        FROM information_schema.views 
        WHERE view_definition ILIKE '%$table%'
    " | tr -d ' ')
    
    # Check foreign key constraints
    FK_COUNT=$(sudo -u postgres psql -d $DB_NAME -t -c "
        SELECT COUNT(*)
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY'
            AND (tc.table_name = '$table' OR ccu.table_name = '$table')
    " | tr -d ' ')
    
    # Determine status
    TOTAL=$((PYTHON_COUNT + SQL_COUNT + VIEW_COUNT + FK_COUNT))
    if [ $TOTAL -eq 0 ]; then
        STATUS="⚠️ UNUSED"
        COLOR=$YELLOW
    elif [ $PYTHON_COUNT -eq 0 ]; then
        STATUS="📊 SCHEMA ONLY"
        COLOR=$GREEN
    else
        STATUS="✅ ACTIVE"
        COLOR=$GREEN
    fi
    
    # Add to summary
    echo "| $table | $PYTHON_COUNT | $SQL_COUNT | $VIEW_COUNT | $FK_COUNT | $STATUS |" >> "$SUMMARY_FILE"
    
    echo -e "  Python: $PYTHON_COUNT | SQL: $SQL_COUNT | Views: $VIEW_COUNT | FKs: $FK_COUNT | ${COLOR}${STATUS}${NC}"
    
done <<< "$TABLES"

# Append summary to report
cat "$SUMMARY_FILE" >> "$OUTPUT_FILE"
rm "$SUMMARY_FILE"

# Now generate detailed analysis for each table
cat >> "$OUTPUT_FILE" <<'EOF'

---

## Detailed Analysis

EOF

while IFS= read -r table; do
    [ -z "$table" ] && continue
    
    cat >> "$OUTPUT_FILE" <<EOF

### \`$table\`

EOF
    
    # Python references
    echo "#### Python References" >> "$OUTPUT_FILE"
    PYTHON_REFS=$(grep -rn "\b$table\b" --include="*.py" "$PROJECT_ROOT" 2>/dev/null | head -20)
    if [ -z "$PYTHON_REFS" ]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo '```' >> "$OUTPUT_FILE"
        echo "$PYTHON_REFS" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
    
    # SQL references
    echo "#### SQL References" >> "$OUTPUT_FILE"
    SQL_REFS=$(grep -rn "\b$table\b" --include="*.sql" "$PROJECT_ROOT" 2>/dev/null | head -20)
    if [ -z "$SQL_REFS" ]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo '```' >> "$OUTPUT_FILE"
        echo "$SQL_REFS" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
    
    # Views
    echo "#### Database Views" >> "$OUTPUT_FILE"
    VIEWS=$(sudo -u postgres psql -d $DB_NAME -t -c "
        SELECT table_name 
        FROM information_schema.views 
        WHERE view_definition ILIKE '%$table%'
    " | grep -v '^$' | sed 's/^[ \t]*//')
    if [ -z "$VIEWS" ]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo '```' >> "$OUTPUT_FILE"
        echo "$VIEWS" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
    
    # Foreign keys
    echo "#### Foreign Key Constraints" >> "$OUTPUT_FILE"
    FK_DETAILS=$(sudo -u postgres psql -d $DB_NAME -t -c "
        SELECT 
            tc.table_name || '.' || kcu.column_name || ' -> ' || 
            ccu.table_name || '.' || ccu.column_name AS constraint_detail
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY'
            AND (tc.table_name = '$table' OR ccu.table_name = '$table')
    " | grep -v '^$' | sed 's/^[ \t]*//')
    if [ -z "$FK_DETAILS" ]; then
        echo "None found." >> "$OUTPUT_FILE"
    else
        echo '```' >> "$OUTPUT_FILE"
        echo "$FK_DETAILS" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
    
    echo "---" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
done <<< "$TABLES"

echo ""
echo -e "${GREEN}✅ Analysis complete!${NC}"
echo "Report saved to: $OUTPUT_FILE"
echo ""
echo "Summary:"
grep "⚠️ UNUSED" "$OUTPUT_FILE" | wc -l | xargs -I {} echo "  Unused tables: {}"
grep "📊 SCHEMA ONLY" "$OUTPUT_FILE" | wc -l | xargs -I {} echo "  Schema-only tables: {}"
grep "✅ ACTIVE" "$OUTPUT_FILE" | wc -l | xargs -I {} echo "  Active tables: {}"
echo ""
echo "Open report with: cat $OUTPUT_FILE"
