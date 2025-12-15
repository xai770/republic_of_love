#!/bin/bash
# Batch process all 71 German postings through Recipe 1120
# Run overnight: extracts skills, builds German synonyms, expands taxonomy

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌙 OVERNIGHT BATCH: Recipe 1120 - SkillBridge Skills Extraction"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Started: $(date)"
echo

# Get all 71 job IDs
JOBS=$(psql -h localhost -U base_admin -d base_yoga -t -c "SELECT job_id FROM postings ORDER BY LENGTH(job_description)")

TOTAL=$(echo "$JOBS" | wc -l)
CURRENT=0
SUCCESS=0
FAILED=0

echo "📋 Found $TOTAL job postings to process"
echo

for JOB_ID in $JOBS; do
    CURRENT=$((CURRENT + 1))
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$CURRENT/$TOTAL] Processing Job: $JOB_ID"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check if already completed successfully
    EXISTS=$(psql -h localhost -U base_admin -d base_yoga -t -c \
        "SELECT COUNT(*) FROM recipe_runs rr 
         JOIN variations v ON rr.variation_id = v.variation_id 
         WHERE rr.recipe_id = 1120 
         AND v.test_data->>'job_id' = '$JOB_ID' 
         AND rr.status = 'SUCCESS'")
    
    if [ "$EXISTS" -gt 0 ]; then
        echo "✓ Already completed - skipping"
        SUCCESS=$((SUCCESS + 1))
        echo
        continue
    fi
    
    # Run Recipe 1120
    START_TIME=$(date +%s)
    
    if python3 scripts/by_recipe_runner.py \
        --recipe-id 1120 \
        --job-id "$JOB_ID" \
        --execution-mode production \
        --target-batch-count 1 \
        >> /tmp/recipe_1120_batch_$(date +%Y%m%d).log 2>&1; then
        
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        echo "✅ SUCCESS (${DURATION}s)"
        SUCCESS=$((SUCCESS + 1))
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        echo "❌ FAILED (${DURATION}s)"
        FAILED=$((FAILED + 1))
    fi
    
    echo "📊 Progress: $SUCCESS success, $FAILED failed, $((TOTAL - CURRENT)) remaining"
    echo
    
    # Small delay to avoid overwhelming Ollama
    sleep 2
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 BATCH COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Finished: $(date)"
echo
echo "📊 Final Statistics:"
echo "   Total jobs: $TOTAL"
echo "   Successful: $SUCCESS"
echo "   Failed: $FAILED"
echo
echo "🔍 View results:"
echo "   psql -h localhost -U base_admin -d base_yoga -f sql/check_recipe_1120_progress.sql"
echo
echo "📝 Full log:"
echo "   tail -f /tmp/recipe_1120_batch_$(date +%Y%m%d).log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
