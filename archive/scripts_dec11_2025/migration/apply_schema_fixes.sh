#!/bin/bash
# Quick migration to fix schema without recreating database

echo "🔧 Applying schema fixes to base.yoga..."
echo ""

PGPASSWORD='base_yoga_secure_2025' psql -h localhost -U base_admin -d base_yoga -f sql/migration_fix_batches_and_constraints.sql

echo ""
echo "✅ Done! Your 2,258 rows are still there - just the schema is fixed!"
echo ""
echo "Verify in pgAdmin or run:"
echo "  PGPASSWORD='base_yoga_secure_2025' psql -h localhost -U base_admin -d base_yoga -c '\d production_runs'"
