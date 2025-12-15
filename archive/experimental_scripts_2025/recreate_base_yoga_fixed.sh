#!/bin/bash
# Recreate base.yoga database with corrected schema
# Fixes:
#  1. Removed batches → production_runs (batches are TEST-ONLY)
#  2. Removed instruction_run_status lookup table (using CHECK constraints instead)
#  3. Added CHECK constraints for status fields and counters

echo "🔧 Recreating base.yoga database with fixes..."
echo ""
echo "Changes:"
echo "  ✅ batches FK removed from production_runs (TEST-ONLY concept)"
echo "  ✅ instruction_run_status table removed (CHECK constraints instead)"
echo "  ✅ Added CHECK constraints: status enums, quality_score, counters"
echo ""
echo "Running SQL..."

sudo -u postgres psql << 'EOSQL'
DROP DATABASE IF EXISTS base_yoga;
CREATE DATABASE base_yoga OWNER base_admin;
\c base_yoga
\i /home/xai/Documents/ty_learn/sql/schema_v4_base_yoga.sql
EOSQL

echo ""
echo "✅ Database recreated!"
echo ""
echo "Next: Re-run migration:"
echo "  /home/xai/Documents/ty_learn/venv/bin/python scripts/migrate_to_base_yoga.py"
