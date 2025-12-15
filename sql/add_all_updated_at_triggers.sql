-- Add updated_at triggers to ALL tables that have updated_at column
-- The function update_updated_at_column() already exists from previous migration

-- List of tables needing triggers (27 total, 5 already have them)
DO $$
DECLARE
    tbl TEXT;
    tables_to_update TEXT[] := ARRAY[
        'actors',
        'capabilities',
        'capabilities_history',
        'conversation_dialogue',
        'conversations',
        'conversations_history',
        'instruction_steps',
        'instructions',
        'instructions_history',
        'job_skills',
        'job_sources',
        'organizations',
        'placeholder_definitions',
        'posting_sources',
        'test_cases',
        'test_cases_history',
        'user_preferences',
        'validated_prompts',
        'validated_prompts_history',
        'workflow_variables',
        'workflows',
        'workflows_history'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables_to_update
    LOOP
        -- Drop trigger if exists (idempotent)
        EXECUTE format('DROP TRIGGER IF EXISTS set_updated_at ON %I', tbl);
        
        -- Create trigger
        EXECUTE format('
            CREATE TRIGGER set_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
        ', tbl);
        
        RAISE NOTICE 'Created trigger for table: %', tbl;
    END LOOP;
END $$;

-- Verify all tables now have triggers
SELECT 
    t.table_name,
    COUNT(tr.trigger_name) as trigger_count
FROM information_schema.tables t
LEFT JOIN information_schema.columns c 
    ON c.table_name = t.table_name 
    AND c.column_name = 'updated_at'
LEFT JOIN information_schema.triggers tr 
    ON tr.event_object_table = t.table_name 
    AND tr.trigger_name = 'set_updated_at'
WHERE t.table_schema = 'public'
  AND c.column_name IS NOT NULL
GROUP BY t.table_name
ORDER BY trigger_count, t.table_name;
