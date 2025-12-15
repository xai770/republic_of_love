#!/bin/bash
# Automated PostgreSQL backup script for base_yoga
# Creates full, schema-only, and data-only backups
# Retains last 7 days of backups

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/home/xai/Documents/ty_learn/backups"
DB_NAME="base_yoga"
DB_USER="base_admin"
DB_HOST="localhost"
export PGPASSWORD="base_yoga_secure_2025"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "====================================="
echo "PostgreSQL Backup Started: $TIMESTAMP"
echo "====================================="

# 1. Full backup (schema + data, custom format - best for restore)
echo "Creating full backup..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -Fc \
  -f "$BACKUP_DIR/by_full_${TIMESTAMP}.backup"

if [ $? -eq 0 ]; then
    echo "✓ Full backup complete: by_full_${TIMESTAMP}.backup"
else
    echo "✗ Full backup FAILED!"
    exit 1
fi

# 2. Schema-only backup (SQL format - human readable)
echo "Creating schema-only backup..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -s \
  -f "$BACKUP_DIR/by_schema_only_${TIMESTAMP}.sql"

if [ $? -eq 0 ]; then
    echo "✓ Schema backup complete: by_schema_only_${TIMESTAMP}.sql"
else
    echo "✗ Schema backup FAILED!"
fi

# 3. Data-only backup (custom format)
echo "Creating data-only backup..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -a -Fc \
  -f "$BACKUP_DIR/by_data_only_${TIMESTAMP}.backup"

if [ $? -eq 0 ]; then
    echo "✓ Data-only backup complete: by_data_only_${TIMESTAMP}.backup"
else
    echo "✗ Data-only backup FAILED!"
fi

# 4. Plain SQL backup (for version control/inspection)
echo "Creating SQL backup..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  -f "$BACKUP_DIR/by_sql_${TIMESTAMP}.sql"

if [ $? -eq 0 ]; then
    echo "✓ SQL backup complete: by_sql_${TIMESTAMP}.sql"
else
    echo "✗ SQL backup FAILED!"
fi

# 5. Cleanup old backups (keep last 7 days)
echo "Cleaning up old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -name "by_*" -type f -mtime +7 -delete
echo "✓ Cleanup complete"

# 6. Show disk usage
echo ""
echo "Backup directory size:"
du -sh "$BACKUP_DIR"
echo ""
echo "Recent backups:"
ls -lh "$BACKUP_DIR" | tail -10

echo ""
echo "====================================="
echo "Backup Complete: $(date)"
echo "====================================="

unset PGPASSWORD
