#!/bin/bash
# Batch IHL Analysis Runner
# Processes all non-test postings through Workflow 1124 (Fake Job Detector)

POSTING_IDS=(1 2 3 4 6 7 9 10 11 12 13 14 16 17 18 19 20 21 22 23 24 26 27 28 29 30 31 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76)

TOTAL=${#POSTING_IDS[@]}
CURRENT=0

echo "🚀 Starting IHL Analysis Batch Run"
echo "📊 Processing $TOTAL postings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for POSTING_ID in "${POSTING_IDS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "[$CURRENT/$TOTAL] Processing posting #$POSTING_ID..."
    
    python3 /home/xai/Documents/ty_learn/scripts/by_recipe_runner.py \
        --recipe-id 1124 \
        --job-id "$POSTING_ID" \
        2>&1 | grep -E "(✅|❌|🚀|IHL|Error)" || echo "  ⏳ Processing..."
    
    if [ $? -eq 0 ]; then
        echo "  ✅ Completed"
    else
        echo "  ⚠️  Error occurred"
    fi
    
    # Small delay to avoid overwhelming the system
    sleep 1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Batch run complete!"
echo "📈 Run this to see results:"
echo "   psql ... -c \"SELECT COUNT(*), AVG(ihl_score)::int FROM postings WHERE ihl_score IS NOT NULL;\""
