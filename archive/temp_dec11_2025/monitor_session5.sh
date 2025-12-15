#!/bin/bash
# Monitor Session 5 (llama3.2:1b) grading progress

while true; do
    clear
    echo "========================================================================"
    echo "📊 SESSION 5 PROGRESS (llama3.2:1b - Small Fast Grader)"
    echo "========================================================================"
    echo ""
    
    # Overall progress
    sqlite3 /home/xai/Documents/ty_learn/data/llmcore.db "
    SELECT 
        'Progress: ' || COUNT(*) || '/575 (' || ROUND(COUNT(*)*100.0/575, 1) || '%)'
    FROM session_runs 
    WHERE session_number = 5 AND status = 'SUCCESS'
    "
    
    echo ""
    
    # Performance metrics
    sqlite3 /home/xai/Documents/ty_learn/data/llmcore.db "
    SELECT 
        '⚡ Avg Speed: ' || ROUND(AVG(ir.latency_ms)/1000.0, 2) || 's per joke'
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 5 AND ir.status = 'SUCCESS'
    "
    
    # Grading distribution preview
    echo ""
    echo "🎭 Grading Distribution:"
    sqlite3 /home/xai/Documents/ty_learn/data/llmcore.db "
    SELECT 
        '  ' ||
        CASE 
            WHEN response_received LIKE '%IS_JOKE: YES%' THEN 'IS_JOKE: YES'
            ELSE 'IS_JOKE: NO'
        END || ' | ' ||
        CASE 
            WHEN response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
            ELSE 'UNKNOWN'
        END || ': ' || COUNT(*)
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 5 AND ir.status = 'SUCCESS'
    GROUP BY 
        CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 'YES' ELSE 'NO' END,
        CASE 
            WHEN response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
            WHEN response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
            WHEN response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
            WHEN response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
            ELSE 'UNKNOWN'
        END
    ORDER BY 
        CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 2 END,
        CASE 
            WHEN response_received LIKE '%QUALITY: EXCELLENT%' THEN 1
            WHEN response_received LIKE '%QUALITY: GOOD%' THEN 2
            WHEN response_received LIKE '%QUALITY: MEDIOCRE%' THEN 3
            WHEN response_received LIKE '%QUALITY: BAD%' THEN 4
            ELSE 5
        END
    "
    
    echo ""
    echo "========================================================================"
    echo "⏱️  Refreshing every 5 seconds... (Ctrl+C to stop)"
    echo "========================================================================"
    
    sleep 5
done
