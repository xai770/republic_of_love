#!/bin/bash
# Apply Migration 016: Operational Observability
# Run this to add error tracking and performance views to Turing

set -e

echo "=================================================="
echo "Migration 016: Operational Observability"
echo "=================================================="
echo ""
echo "This migration adds:"
echo "  • workflow_errors table (error tracking)"
echo "  • actor_performance_summary view (performance metrics)"
echo "  • workflow_health view (real-time status)"
echo "  • error_summary view (error aggregations)"
echo "  • conversation_performance view (bottleneck detection)"
echo "  • Helper functions for queries"
echo ""
read -p "Apply migration? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

PGPASSWORD=base_yoga_secure_2025 psql -U base_admin -d turing -h localhost \
    -f /home/xai/Documents/ty_learn/sql/migrations/016_operational_observability.sql

echo ""
echo "✅ Migration 016 applied successfully!"
echo ""
echo "Try these queries:"
echo "  • SELECT * FROM workflow_health ORDER BY started_at DESC;"
echo "  • SELECT * FROM error_summary;"
echo "  • SELECT * FROM get_workflow_errors(20920);"
echo "  • SELECT * FROM get_slowest_actors(7, 10);"
echo ""
