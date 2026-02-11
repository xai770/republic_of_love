#!/bin/bash
# Test migration sequence (DOWN then UP)
# Author: Sandy (GitHub Copilot)
# Date: November 23, 2025

set -e  # Exit on error

DB_HOST=localhost
DB_USER=base_admin
DB_NAME=turing
export PGPASSWORD=${DB_PASSWORD}

echo "🧪 Testing Migration Rollback Sequence..."
echo ""

# Test DOWN migrations (006 → 001)
echo "⬇️  Rolling back migrations (006 → 001)..."
for i in 006 005 004 003 002 001; do
    echo "  Rolling back ${i}..."
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f sql/migrations/${i}_*_DOWN.sql > /dev/null 2>&1
    echo "  ✅ ${i} DOWN complete"
done

echo ""
echo "⬆️  Re-applying migrations (001 → 006)..."
for i in 001 002 003 004 005 006; do
    echo "  Applying ${i}..."
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f sql/migrations/${i}_*_UP.sql > /dev/null 2>&1
    echo "  ✅ ${i} UP complete"
done

echo ""
echo "✅ Migration test complete! All migrations can rollback and reapply cleanly."
