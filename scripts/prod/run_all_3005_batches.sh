#!/bin/bash
# Run WF3005 in a loop until all orphan skills have decisions
# Usage: ./scripts/prod/run_all_3005_batches.sh
#
# Runs batches of 25 skills each until:
# - All orphans have decisions, OR
# - Max batches reached (default 20)
#
# Author: Sandy
# Date: December 7, 2025

set -e

cd /home/xai/Documents/ty_wave

MAX_BATCHES=${1:-20}
BATCH=1

echo "🔄 Starting WF3005 batch runner (max $MAX_BATCHES batches)"
echo "   Each batch processes ~25 orphan skills"
echo ""

while [ $BATCH -le $MAX_BATCHES ]; do
    # Check how many orphans still need decisions
    ORPHANS_NEED_DECISIONS=$(sudo -u postgres psql -d turing -t -c "
        SELECT COUNT(*) FROM entities e
        WHERE e.entity_type = 'skill' 
          AND e.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er 
              WHERE er.entity_id = e.entity_id AND er.relationship = 'child_of'
          )
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er 
              WHERE er.related_entity_id = e.entity_id AND er.relationship = 'child_of'
          )
          AND NOT EXISTS (
              SELECT 1 FROM registry_decisions rd
              WHERE rd.subject_entity_id = e.entity_id
                AND rd.decision_type = 'assign'
          )
    " | tr -d ' ')
    
    echo "📊 Batch $BATCH: $ORPHANS_NEED_DECISIONS orphans still need decisions"
    
    if [ "$ORPHANS_NEED_DECISIONS" -eq 0 ]; then
        echo "✅ All orphans have decisions! Stopping."
        break
    fi
    
    echo "🚀 Running batch $BATCH..."
    /home/xai/Documents/ty_wave/venv/bin/python scripts/prod/run_workflow_3005.py --max-iterations 5
    
    echo ""
    BATCH=$((BATCH + 1))
    
    # Small pause between batches
    sleep 2
done

# Final stats
echo ""
echo "=" * 70
TOTAL_DECISIONS=$(sudo -u postgres psql -d turing -t -c "SELECT COUNT(*) FROM registry_decisions WHERE decision_type = 'assign'" | tr -d ' ')
PENDING=$(sudo -u postgres psql -d turing -t -c "SELECT COUNT(*) FROM registry_decisions WHERE decision_type = 'assign' AND review_status = 'pending'" | tr -d ' ')
AUTO=$(sudo -u postgres psql -d turing -t -c "SELECT COUNT(*) FROM registry_decisions WHERE decision_type = 'assign' AND review_status = 'auto_approved'" | tr -d ' ')

echo "📊 Final Results:"
echo "   Total decisions: $TOTAL_DECISIONS"
echo "   Auto-approved: $AUTO"
echo "   Pending QA: $PENDING"
echo "   Batches run: $((BATCH - 1))"
