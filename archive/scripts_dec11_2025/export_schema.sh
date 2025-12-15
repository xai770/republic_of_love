#!/bin/bash
# Daily schema export for Turing database
# Exports current schema to sql/schema_export_YYYYMMDD.sql
# Keeps only last 7 days of exports

set -e

# Configuration
EXPORT_DIR="/home/xai/Documents/ty_learn/sql"
TIMESTAMP=$(date +%Y%m%d)
EXPORT_FILE="$EXPORT_DIR/schema_export_${TIMESTAMP}.sql"

# Export schema only (no data) - using postgres superuser
echo "📋 Exporting Turing schema..."
sudo -u postgres pg_dump -d turing -s > "$EXPORT_FILE"

FILE_SIZE=$(du -h "$EXPORT_FILE" | cut -f1)
echo "✅ Schema exported: schema_export_${TIMESTAMP}.sql ($FILE_SIZE)"

# Clean up old exports (keep last 7 days)
echo "🧹 Cleaning old exports..."
find "$EXPORT_DIR" -name "schema_export_*.sql" -mtime +7 -delete
echo "✅ Cleanup complete (kept last 7 days)"

# Create symlink to latest
ln -sf "schema_export_${TIMESTAMP}.sql" "$EXPORT_DIR/schema_latest.sql"
echo "✅ Symlink updated: schema_latest.sql -> schema_export_${TIMESTAMP}.sql"
