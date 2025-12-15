#!/bin/bash
# Backup script for base.yoga (BY)
# Creates timestamped backup files in backups/ directory

# Configuration
DB_NAME="base_yoga"
DB_USER="base_admin"
DB_PASSWORD="base_yoga_secure_2025"
BACKUP_DIR="/home/xai/Documents/ty_learn/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🗄️  Backing up base.yoga (BY)..."
echo "Timestamp: $TIMESTAMP"
echo ""

# Option 1: Full database dump (schema + data)
echo "1. Creating full backup (schema + data)..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h localhost \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -F c \
    -b \
    -v \
    -f "$BACKUP_DIR/by_full_${TIMESTAMP}.backup"

FULL_SIZE=$(du -h "$BACKUP_DIR/by_full_${TIMESTAMP}.backup" | cut -f1)
echo "   ✅ Full backup: by_full_${TIMESTAMP}.backup ($FULL_SIZE)"

# Option 2: SQL dump (human-readable, can review)
echo ""
echo "2. Creating SQL dump (human-readable)..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h localhost \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -F p \
    -f "$BACKUP_DIR/by_sql_${TIMESTAMP}.sql"

SQL_SIZE=$(du -h "$BACKUP_DIR/by_sql_${TIMESTAMP}.sql" | cut -f1)
echo "   ✅ SQL dump: by_sql_${TIMESTAMP}.sql ($SQL_SIZE)"

# Option 3: Data-only dump (for migration testing)
echo ""
echo "3. Creating data-only backup..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h localhost \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -F c \
    -a \
    -f "$BACKUP_DIR/by_data_only_${TIMESTAMP}.backup"

DATA_SIZE=$(du -h "$BACKUP_DIR/by_data_only_${TIMESTAMP}.backup" | cut -f1)
echo "   ✅ Data-only: by_data_only_${TIMESTAMP}.backup ($DATA_SIZE)"

# Option 4: Schema-only dump (for reference)
echo ""
echo "4. Creating schema-only backup..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h localhost \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -F p \
    -s \
    -f "$BACKUP_DIR/by_schema_only_${TIMESTAMP}.sql"

SCHEMA_SIZE=$(du -h "$BACKUP_DIR/by_schema_only_${TIMESTAMP}.sql" | cut -f1)
echo "   ✅ Schema-only: by_schema_only_${TIMESTAMP}.sql ($SCHEMA_SIZE)"

echo ""
echo "============================================"
echo "✅ Backup Complete!"
echo "============================================"
echo "Location: $BACKUP_DIR"
echo ""
echo "Files created:"
echo "  📦 by_full_${TIMESTAMP}.backup       - Full backup (use this for restore!)"
echo "  📄 by_sql_${TIMESTAMP}.sql           - Human-readable SQL"
echo "  📊 by_data_only_${TIMESTAMP}.backup  - Data only (no schema)"
echo "  📋 by_schema_only_${TIMESTAMP}.sql   - Schema only (no data)"
echo ""
echo "💡 To restore:"
echo "   pg_restore -h localhost -U base_admin -d base_yoga -c $BACKUP_DIR/by_full_${TIMESTAMP}.backup"
echo ""
echo "💡 To list old backups:"
echo "   ls -lh $BACKUP_DIR/"
echo ""
echo "💡 To clean old backups (keep last 7 days):"
echo "   find $BACKUP_DIR -name 'by_*.backup' -mtime +7 -delete"
