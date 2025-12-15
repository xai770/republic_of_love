#!/bin/bash
# Batch process remaining 49 jobs through Recipe 1114
# Creates concise, formatted job summaries and saves to postings.extracted_summary

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌙 OVERNIGHT BATCH: Recipe 1114 - Self-Healing Job Summary Extraction"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Started: $(date)"
echo

# Get all jobs WITHOUT extracted summaries
JOBS=$(psql -h localhost -U base_admin -d base_yoga -t -c \
    "SELECT job_id FROM postings WHERE extracted_summary IS NULL ORDER BY LENGTH(job_description)")

TOTAL=$(echo "$JOBS" | wc -l)
CURRENT=0
SUCCESS=0
FAILED=0

echo "📋 Found $TOTAL job postings needing summaries"
echo "🎯 Recipe: 1114 (8 sessions: extract → grade → improve → format → save)"
echo

# Create log directory
mkdir -p logs/recipe_1114

for JOB_ID in $JOBS; do
    CURRENT=$((CURRENT + 1))
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$CURRENT/$TOTAL] Processing Job: $JOB_ID"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏰ Time: $(date '+%H:%M:%S')"
    
    # Check if already completed successfully
    EXISTS=$(psql -h localhost -U base_admin -d base_yoga -t -c \
        "SELECT COUNT(*) FROM recipe_runs rr 
         JOIN variations v ON rr.variation_id = v.variation_id 
         WHERE rr.recipe_id = 1114 
         AND v.test_data->>'job_id' = '$JOB_ID' 
         AND rr.status = 'SUCCESS'")
    
    if [ "$EXISTS" -gt 0 ]; then
        # Check if summary was actually saved
        SAVED=$(psql -h localhost -U base_admin -d base_yoga -t -c \
            "SELECT LENGTH(extracted_summary) FROM postings WHERE job_id = '$JOB_ID'")
        
        if [ ! -z "$SAVED" ] && [ "$SAVED" -gt 100 ]; then
            echo "✓ Already completed with summary ($SAVED chars) - skipping"
            SUCCESS=$((SUCCESS + 1))
            echo
            continue
        fi
    fi
    
    # Run Recipe 1114
    START_TIME=$(date +%s)
    LOG_FILE="logs/recipe_1114/job_${JOB_ID}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "📝 Running 8-session pipeline..."
    
    if python3 scripts/by_recipe_runner.py \
        --recipe-id 1114 \
        --job-id "$JOB_ID" \
        > "$LOG_FILE" 2>&1; then
        
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        # Verify summary was saved
        SUMMARY_LENGTH=$(psql -h localhost -U base_admin -d base_yoga -t -c \
            "SELECT LENGTH(extracted_summary) FROM postings WHERE job_id = '$JOB_ID'")
        
        if [ ! -z "$SUMMARY_LENGTH" ] && [ "$SUMMARY_LENGTH" -gt 100 ]; then
            echo "✅ SUCCESS (${DURATION}s) - Summary: $SUMMARY_LENGTH chars"
            
            # Show preview
            PREVIEW=$(psql -h localhost -U base_admin -d base_yoga -t -c \
                "SELECT LEFT(extracted_summary, 120) FROM postings WHERE job_id = '$JOB_ID'" | head -1)
            echo "   Preview: $PREVIEW..."
            
            SUCCESS=$((SUCCESS + 1))
        else
            echo "⚠️  Recipe succeeded but summary not saved properly"
            echo "   Log: $LOG_FILE"
            FAILED=$((FAILED + 1))
        fi
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        echo "❌ FAILED (${DURATION}s)"
        echo "   Log: $LOG_FILE"
        FAILED=$((FAILED + 1))
        
        # Show last few lines of error log
        echo "   Error preview:"
        tail -5 "$LOG_FILE" | sed 's/^/   | /'
    fi
    
    echo
    
    # Progress summary every 5 jobs
    if [ $((CURRENT % 5)) -eq 0 ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 Progress: $CURRENT/$TOTAL jobs processed"
        echo "   ✅ Success: $SUCCESS"
        echo "   ❌ Failed: $FAILED"
        echo "   ⏱️  Estimated remaining: $(( (TOTAL - CURRENT) * 45 / 60 )) minutes"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo
    fi
    
    # Brief pause between jobs to avoid overwhelming Ollama
    sleep 2
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 BATCH COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Completed: $(date)"
echo
echo "📊 Final Summary:"
echo "   Total jobs: $TOTAL"
echo "   ✅ Successful: $SUCCESS"
echo "   ❌ Failed: $FAILED"
echo "   📈 Success rate: $(( SUCCESS * 100 / TOTAL ))%"
echo

# Show summary statistics from database
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 Database Statistics:"
psql -h localhost -U base_admin -d base_yoga <<SQL
SELECT 
    COUNT(*) as total_jobs,
    COUNT(extracted_summary) as with_summaries,
    ROUND(100.0 * COUNT(extracted_summary) / COUNT(*), 1) || '%' as completion_rate,
    ROUND(AVG(LENGTH(extracted_summary))::numeric, 0) as avg_summary_length
FROM postings;
SQL

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Next Step: Run batch_run_recipe_1121.py to extract skills from all summaries"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
