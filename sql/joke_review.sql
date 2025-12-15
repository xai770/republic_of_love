-- ======================================================================
-- JOKE REVIEW - See actual jokes and their grades
-- ======================================================================
-- Purpose: Review the jokes generated and how gemma3:1b graded them
-- Usage: sqlite3 -column -header data/llmcore.db < sql/joke_review.sql
-- ======================================================================

SELECT 
    a.actor_id as comedian,
    v.variations_param_1 as topic,
    rr.batch_id,
    rr.recipe_run_id,
    -- The joke itself
    SUBSTR(ir_gen.response_received, 1, 300) as joke,
    -- The grade
    CASE 
        WHEN ir_grade.response_received LIKE '%IS_JOKE: YES%' THEN 'YES'
        WHEN ir_grade.response_received LIKE '%IS_JOKE: NO%' THEN 'NO'
        ELSE 'UNKNOWN'
    END as is_joke,
    CASE 
        WHEN ir_grade.response_received LIKE '%QUALITY: EXCELLENT%' THEN 'EXCELLENT'
        WHEN ir_grade.response_received LIKE '%QUALITY: GOOD%' THEN 'GOOD'
        WHEN ir_grade.response_received LIKE '%QUALITY: MEDIOCRE%' THEN 'MEDIOCRE'
        WHEN ir_grade.response_received LIKE '%QUALITY: BAD%' THEN 'BAD'
        ELSE 'UNKNOWN'
    END as quality,
    -- Extract the reason from the grade
    SUBSTR(
        ir_grade.response_received,
        INSTR(ir_grade.response_received, 'REASON:') + 8,
        200
    ) as reason,
    ir_gen.latency_ms as gen_time_ms,
    ir_grade.latency_ms as grade_time_ms
FROM recipe_runs rr
JOIN recipes r ON rr.recipe_id = r.recipe_id
JOIN sessions s ON r.recipe_id = s.recipe_id AND s.session_number = 1
JOIN actors a ON s.actor_id = a.actor_id
JOIN variations v ON rr.variation_id = v.variation_id
JOIN session_runs sr_gen ON rr.recipe_run_id = sr_gen.recipe_run_id AND sr_gen.session_number = 1
JOIN instruction_runs ir_gen ON sr_gen.session_run_id = ir_gen.session_run_id
JOIN session_runs sr_grade ON rr.recipe_run_id = sr_grade.recipe_run_id AND sr_grade.session_number = 2
JOIN instruction_runs ir_grade ON sr_grade.session_run_id = ir_grade.session_run_id
WHERE r.canonical_code = 'og_generate_and_grade_joke'
    AND rr.status = 'SUCCESS'
ORDER BY 
    CASE quality
        WHEN 'EXCELLENT' THEN 1
        WHEN 'GOOD' THEN 2
        WHEN 'MEDIOCRE' THEN 3
        WHEN 'BAD' THEN 4
        ELSE 5
    END,
    a.actor_id,
    v.variations_param_1;
