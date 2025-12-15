#!/bin/bash
# Restore base.yoga (BY) from backup
# Usage: ./restore_by.sh <backup_file>

if [ $# -eq 0 ]; then
    echo "❌ Error: No backup file specified"
    echo ""
    echo "Usage: ./restore_by.sh <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh /home/xai/Documents/ty_learn/backups/by_*.backup 2>/dev/null || echo "  (no backups found)"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="base_yoga"
DB_USER="base_admin"
DB_PASSWORD="base_yoga_secure_2025"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will DROP and RECREATE base_yoga database!"
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🔧 Restoring base.yoga (BY)..."
echo ""

# Drop and recreate database
echo "1. Dropping existing database..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "2. Creating fresh database..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Restore from backup
echo "3. Restoring from backup..."
PGPASSWORD="$DB_PASSWORD" pg_restore \
    -h localhost \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -v \
    "$BACKUP_FILE"

echo ""
echo "✅ Restore complete!"
echo ""
echo "Verify:"
echo "  PGPASSWORD='$DB_PASSWORD' psql -h localhost -U $DB_USER -d $DB_NAME -c '\dt'"
