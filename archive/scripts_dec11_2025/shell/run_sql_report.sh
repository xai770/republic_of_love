#!/bin/bash
# LLMCore SQL Report Runner
# Execute SQL queries against the LLMCore database

DB_PATH="data/llmcore.db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="llmcore_sql_report_${TIMESTAMP}.txt"

echo "🚀 Running LLMCore SQL Report Queries"
echo "======================================"
echo "Database: $DB_PATH"
echo "Output: $OUTPUT_FILE"
echo ""

# Execute SQL queries and save to file
{
    echo "=================================================================================="
    echo "🏆 LLMCore SQL Execution Report"
    echo "=================================================================================="
    echo "Generated: $(date)"
    echo ""
    
    # Run the SQL queries from the file
    sqlite3 "$DB_PATH" < llmcore_execution_report_queries.sql
    
} > "$OUTPUT_FILE"

echo "✅ SQL report generated: $OUTPUT_FILE"
echo ""
echo "📋 Report preview (first 50 lines):"
echo "------------------------------------"
head -50 "$OUTPUT_FILE"