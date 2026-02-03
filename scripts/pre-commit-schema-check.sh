#!/bin/bash
# Pre-commit hook for schema governance and route inventory
# Install: ln -sf ../../scripts/pre-commit-schema-check.sh .git/hooks/pre-commit

set -e
cd "$(git rev-parse --show-toplevel)"

# ============================================================================
# CHECK 1: Route inventory auto-update
# ============================================================================
ROUTE_FILES=$(git diff --cached --name-only | grep -E "(api/routers/|api/main\.py|frontend/templates/)" || true)

if [ -n "$ROUTE_FILES" ]; then
    echo "🔄 Route files changed, regenerating ROUTES.md..."
    source venv/bin/activate 2>/dev/null || true
    python3 scripts/generate_route_inventory.py 2>/dev/null || true
    git add docs/ROUTES.md 2>/dev/null || true
fi

# ============================================================================
# CHECK 2: Schema governance
# ============================================================================
# Only run if schema-related files changed
SCHEMA_FILES=$(git diff --cached --name-only | grep -E "(migrations/|\.sql$|database\.py|_CU\.py|_C\.py)" || true)

if [ -z "$SCHEMA_FILES" ]; then
    exit 0  # No schema changes, skip
fi

echo "🔍 Schema changes detected, running governance checks..."

# Check 1: Migration file exists for new columns
NEW_COLUMNS=$(git diff --cached | grep -E "^\+.*ADD COLUMN|^\+.*ALTER TABLE.*ADD" || true)
if [ -n "$NEW_COLUMNS" ]; then
    MIGRATION_EXISTS=$(git diff --cached --name-only | grep "migrations/.*\.sql" || true)
    if [ -z "$MIGRATION_EXISTS" ]; then
        echo "❌ BLOCKED: Adding columns without migration file"
        echo "   Create: data/migrations/YYYYMMDD_description.sql"
        exit 1
    fi
fi

# Check 2: Data dictionary updated for new columns
if [ -n "$NEW_COLUMNS" ]; then
    DICT_UPDATED=$(git diff --cached --name-only | grep "data_dictionary" || true)
    if [ -z "$DICT_UPDATED" ]; then
        echo "⚠️  WARNING: New columns without data dictionary update"
        echo "   Update: docs/data_dictionary_postings.md"
        # Warning only, don't block (yet)
    fi
fi

# Check 3: Run quick schema audit on postings table
source venv/bin/activate 2>/dev/null || true
DEAD_COUNT=$(python3 scripts/schema_audit.py --table postings --dead 2>/dev/null | grep -c "🔴" || echo "0")

if [ "$DEAD_COUNT" -gt 12 ]; then  # Threshold: current 10 + buffer
    echo "❌ BLOCKED: Dead column count increased ($DEAD_COUNT > 12)"
    echo "   Run: python scripts/schema_audit.py --recommend"
    exit 1
fi

echo "✅ Schema governance checks passed"
