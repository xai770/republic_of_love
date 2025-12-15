#!/bin/bash
# Parallel IHL Analysis Runner
# Processes postings in parallel batches for faster completion

POSTING_IDS=(1 2 3 4 6 7 9 10 11 12 13 14 16 17 18 19 20 21 22 23 24 26 27 28 29 30 31 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76)

PARALLEL_JOBS=3  # Run 3 at a time
TOTAL=${#POSTING_IDS[@]}

echo "🚀 Starting Parallel IHL Analysis"
echo "📊 Processing $TOTAL postings ($PARALLEL_JOBS at a time)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Function to run analysis for one posting
run_analysis() {
    local POSTING_ID=$1
    local INDEX=$2
    echo "[$INDEX/$TOTAL] Starting posting #$POSTING_ID..."
    
    python3 /home/xai/Documents/ty_learn/scripts/by_recipe_runner.py \
        --recipe-id 1124 \
        --job-id "$POSTING_ID" \
        > "/tmp/ihl_${POSTING_ID}.log" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "[$INDEX/$TOTAL] ✅ Completed posting #$POSTING_ID"
    else
        echo "[$INDEX/$TOTAL] ⚠️  Error on posting #$POSTING_ID (see /tmp/ihl_${POSTING_ID}.log)"
    fi
}

# Export function so GNU parallel can use it
export -f run_analysis
export TOTAL

# Use GNU parallel if available, otherwise fall back to sequential
if command -v parallel &> /dev/null; then
    echo "Using GNU parallel for faster processing..."
    printf "%s\n" "${POSTING_IDS[@]}" | nl | parallel --colsep '\t' -j $PARALLEL_JOBS run_analysis {2} {1}
else
    echo "GNU parallel not found, running sequentially..."
    INDEX=0
    for POSTING_ID in "${POSTING_IDS[@]}"; do
        INDEX=$((INDEX + 1))
        run_analysis "$POSTING_ID" "$INDEX"
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Batch run complete!"
echo ""
echo "📈 Run analysis:"
echo "   python3 tools/generate_ihl_report.py"
