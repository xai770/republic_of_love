#!/bin/bash
# Execute all schema standardization migrations (006-012)
# Date: 2025-10-30
# Safe: Each migration is transaction-wrapped with rollback on error

set -e  # Exit on any error

DB_NAME="turing"
DB_USER="base_admin"
DB_PASSWORD="base_yoga_secure_2025"  # Password name unchanged for compatibility
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================================================="
echo "Schema Standardization: Migrations 006-012"
echo "=========================================================================="
echo ""

# Step 1: Create backup
echo "📦 Creating pre-migration backup..."
BACKUP_FILE="${BACKUP_DIR}/by_pre_migrations_006_012_${TIMESTAMP}.sql"
PGPASSWORD="${DB_PASSWORD}" pg_dump -U ${DB_USER} -h localhost ${DB_NAME} > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"
else
    echo "❌ Backup failed! Aborting migrations."
    exit 1
fi

echo ""
echo "=========================================================================="
echo "Executing Migrations"
echo "=========================================================================="
echo ""

# Function to run a migration
run_migration() {
    local migration_file=$1
    local migration_name=$(basename ${migration_file} .sql)
    
    echo "⏳ Running ${migration_name}..."
    
    PGPASSWORD="${DB_PASSWORD}" psql -U ${DB_USER} -h localhost ${DB_NAME} \
        -f "${migration_file}" \
        -v ON_ERROR_STOP=1 \
        --quiet
    
    if [ $? -eq 0 ]; then
        echo "✅ ${migration_name} completed successfully"
    else
        echo "❌ ${migration_name} FAILED!"
        echo ""
        echo "=========================================================================="
        echo "ROLLBACK INSTRUCTIONS"
        echo "=========================================================================="
        echo ""
        echo "To restore database to pre-migration state:"
        echo ""
        echo "  PGPASSWORD='${DB_PASSWORD}' psql -U ${DB_USER} -h localhost postgres \\"
        echo "    -c 'DROP DATABASE ${DB_NAME}; CREATE DATABASE ${DB_NAME};'"
        echo ""
        echo "  PGPASSWORD='${DB_PASSWORD}' psql -U ${DB_USER} -h localhost ${DB_NAME} \\"
        echo "    < ${BACKUP_FILE}"
        echo ""
        exit 1
    fi
    echo ""
}

# Execute migrations in order
run_migration "migrations/006_standardize_canonicals.sql"
run_migration "migrations/007_cleanup_skill_tables.sql"
run_migration "migrations/008_standardize_skills_pending.sql"
run_migration "migrations/009_standardize_schema_documentation.sql"
run_migration "migrations/010_standardize_actors.sql"
run_migration "migrations/011_standardize_facets.sql"
run_migration "migrations/012_standardize_postings.sql"

echo "=========================================================================="
echo "✅ ALL MIGRATIONS COMPLETE!"
echo "=========================================================================="
echo ""
echo "Summary:"
echo "  - 7 migrations executed successfully"
echo "  - Tables standardized: canonicals, facets, actors, postings, skill_*, schema_documentation"
echo "  - Backup available: ${BACKUP_FILE}"
echo ""
echo "Next steps:"
echo "  1. Test Recipe 1114: python runners/run_recipe.py --recipe-id 1114 --test-data 'test'"
echo "  2. Review schema: psql ${DB_NAME} -c '\\dt'"
echo "  3. Update any code referencing old column names"
echo ""
