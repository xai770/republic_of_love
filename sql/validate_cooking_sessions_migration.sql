-- Validation script for cooking_sessions migration
-- Date: 2025-10-05
-- Purpose: Verify the migration was successful

.headers on
.mode column

SELECT '=== MIGRATION VALIDATION REPORT ===' as report_section;

SELECT '' as spacer;
SELECT 'Table Existence Check:' as check_type;

-- Check that cooking_sessions table exists
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ cooking_sessions table exists'
        ELSE '❌ cooking_sessions table missing'
    END as status
FROM sqlite_master 
WHERE type='table' AND name='cooking_sessions';

-- Check that runs table was dropped
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ runs table successfully dropped'
        ELSE '❌ runs table still exists'
    END as status
FROM sqlite_master 
WHERE type='table' AND name='runs';

SELECT '' as spacer;
SELECT 'Data Migration Check:' as check_type;

-- Check cooking_sessions data
SELECT '✅ Cooking sessions migrated: ' || COUNT(*) || ' sessions' as status
FROM cooking_sessions;

-- Check dishes have session_id
SELECT '✅ Dishes with session_id: ' || COUNT(*) || ' dishes' as status
FROM dishes WHERE session_id IS NOT NULL;

SELECT '' as spacer;
SELECT 'Foreign Key Relationships:' as check_type;

-- Check cooking_sessions → recipes relationship
SELECT '✅ Cooking sessions linked to recipes: ' || COUNT(*) as status
FROM cooking_sessions cs
JOIN recipes r ON cs.recipe_id = r.recipe_id;

-- Check dishes → cooking_sessions relationship  
SELECT '✅ Dishes linked to cooking sessions: ' || COUNT(*) as status
FROM dishes d
JOIN cooking_sessions cs ON d.session_id = cs.session_id;

SELECT '' as spacer;
SELECT 'Schema Validation:' as check_type;

-- Check dishes table has restaurant column names
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ Restaurant schema columns present'
        ELSE '❌ Restaurant schema columns missing'
    END as status
FROM pragma_table_info('dishes')
WHERE name IN ('processing_payload_dish', 'processing_received_response_dish', 'processing_latency_dish');

SELECT '' as spacer;
SELECT 'Sample Data:' as check_type;

SELECT 'Sample cooking session:' as data_type;
SELECT session_id, recipe_id, session_name, started_at 
FROM cooking_sessions 
LIMIT 1;

SELECT '' as spacer;
SELECT 'Sample dish with session:' as data_type;
SELECT dish_id, ingredient_id, session_id, model_name 
FROM dishes 
WHERE session_id IS NOT NULL 
LIMIT 1;

SELECT '' as spacer;
SELECT '=== MIGRATION COMPLETE ✅ ===' as report_section;