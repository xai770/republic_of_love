#!/bin/bash
# Session 4 Grading Progress Monitor
# Tracks granite3.1-moe:3b grading progress in real-time

DB="data/llmcore.db"
CLEAR="\033[2J\033[H"  # Clear screen and move to top

while true; do
    echo -e "${CLEAR}"
    echo "========================================================================"
    echo "🌟 SESSION 4 GRADING MONITOR - granite3.1-moe:3b (Generous Grader)"
    echo "========================================================================"
    echo ""
    date '+Last Updated: %Y-%m-%d %H:%M:%S'
    echo ""
    
    # Overall progress
    echo "📊 OVERALL PROGRESS:"
    sqlite3 $DB "
    SELECT 
        '   Total Recipe Runs: ' || COUNT(*) as stat
    FROM recipe_runs
    WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke')
    
    UNION ALL
    
    SELECT 
        '   Session 4 Completed: ' || COUNT(*) || ' (' || 
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM recipe_runs WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke')), 1) || '%)'
    FROM session_runs
    WHERE session_number = 4 AND status = 'SUCCESS'
    
    UNION ALL
    
    SELECT 
        '   Remaining: ' || (
            (SELECT COUNT(*) FROM recipe_runs WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke'))
            - 
            (SELECT COUNT(*) FROM session_runs WHERE session_number = 4 AND status = 'SUCCESS')
        )
    "
    
    echo ""
    echo "⏱️  PERFORMANCE METRICS:"
    sqlite3 $DB "
    SELECT 
        '   Avg Response Time: ' || ROUND(AVG(latency_ms)) || 'ms' as stat
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 4
    
    UNION ALL
    
    SELECT 
        '   Fastest: ' || MIN(latency_ms) || 'ms   Slowest: ' || MAX(latency_ms) || 'ms'
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 4
    "
    
    echo ""
    echo "🎭 GRADING PREVIEW (Session 4 - granite3.1-moe:3b):"
    sqlite3 $DB "
    SELECT 
        '   IS_JOKE YES: ' || SUM(CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 0 END) ||
        ' (' || ROUND(100.0 * SUM(CASE WHEN response_received LIKE '%IS_JOKE: YES%' THEN 1 ELSE 0 END) / COUNT(*), 1) || '%)'
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 4 AND ir.status = 'SUCCESS'
    "
    
    sqlite3 $DB "
    SELECT 
        '   EXCELLENT: ' || SUM(CASE WHEN response_received LIKE '%QUALITY: EXCELLENT%' THEN 1 ELSE 0 END) ||
        '   GOOD: ' || SUM(CASE WHEN response_received LIKE '%QUALITY: GOOD%' THEN 1 ELSE 0 END) ||
        '   MEDIOCRE: ' || SUM(CASE WHEN response_received LIKE '%QUALITY: MEDIOCRE%' THEN 1 ELSE 0 END) ||
        '   BAD: ' || SUM(CASE WHEN response_received LIKE '%QUALITY: BAD%' THEN 1 ELSE 0 END)
    FROM instruction_runs ir
    JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
    WHERE sr.session_number = 4 AND ir.status = 'SUCCESS'
    "
    
    echo ""
    echo "🏆 TOP 5 COMEDIANS SO FAR (by Session 4 ratings):"
    sqlite3 $DB "
    WITH comedian_scores AS (
        SELECT 
            s1.actor_id as comedian,
            AVG(CASE 
                WHEN ir4.response_received LIKE '%QUALITY: EXCELLENT%' THEN 4
                WHEN ir4.response_received LIKE '%QUALITY: GOOD%' THEN 3
                WHEN ir4.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 2
                WHEN ir4.response_received LIKE '%QUALITY: BAD%' THEN 1
            END) as avg_score,
            COUNT(*) as joke_count
        FROM recipe_runs rr
        JOIN recipes r ON rr.recipe_id = r.recipe_id
        JOIN sessions s1 ON s1.recipe_id = r.recipe_id AND s1.session_number = 1
        JOIN session_runs sr4 ON sr4.recipe_run_id = rr.recipe_run_id AND sr4.session_number = 4
        JOIN instruction_runs ir4 ON ir4.session_run_id = sr4.session_run_id
        WHERE r.canonical_code = 'og_generate_and_grade_joke'
          AND ir4.status = 'SUCCESS'
        GROUP BY s1.actor_id
        HAVING COUNT(*) >= 3
    )
    SELECT 
        '   ' || comedian || ': ' || ROUND(avg_score, 2) || '/4.0 (' || joke_count || ' jokes)'
    FROM comedian_scores
    ORDER BY avg_score DESC
    LIMIT 5
    "
    
    echo ""
    echo "📈 ESTIMATED TIME REMAINING:"
    sqlite3 $DB "
    WITH progress AS (
        SELECT 
            COUNT(*) as completed,
            (SELECT COUNT(*) FROM recipe_runs WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke')) as total,
            ROUND(AVG(latency_ms) / 1000.0, 1) as avg_seconds
        FROM session_runs sr
        JOIN instruction_runs ir ON ir.session_run_id = sr.session_run_id
        WHERE sr.session_number = 4 AND sr.status = 'SUCCESS'
    )
    SELECT 
        '   ' || (total - completed) || ' jokes remaining × ' || avg_seconds || 's = ' ||
        ROUND((total - completed) * avg_seconds / 60.0, 1) || ' minutes'
    FROM progress
    "
    
    echo ""
    echo "📋 RECIPE RUN STATUS:"
    sqlite3 $DB "
    SELECT 
        '   ' || status || ': ' || COUNT(*)
    FROM recipe_runs
    WHERE recipe_id IN (SELECT recipe_id FROM recipes WHERE canonical_code = 'og_generate_and_grade_joke')
    GROUP BY status
    ORDER BY status
    "
    
    echo ""
    echo "========================================================================"
    echo "Press Ctrl+C to stop monitoring | Refreshing every 5 seconds..."
    echo "========================================================================"
    
    sleep 5
done
