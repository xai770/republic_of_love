#!/bin/bash
# Count rows in all tables and find empty ones
# Usage: ./count_all_tables.sh

echo "Counting rows in all tables..."
echo ""

./scripts/q.sh "
DO \$\$
DECLARE
    r RECORD;
    row_count INTEGER;
BEGIN
    CREATE TEMP TABLE IF NOT EXISTS table_counts (
        table_name TEXT,
        row_count INTEGER
    );
    
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        EXECUTE 'SELECT COUNT(*) FROM ' || quote_ident(r.tablename) INTO row_count;
        INSERT INTO table_counts VALUES (r.tablename, row_count);
    END LOOP;
END \$\$;

SELECT 
    table_name,
    row_count,
    CASE 
        WHEN row_count = 0 THEN 'EMPTY'
        WHEN row_count < 10 THEN 'FEW'
        WHEN row_count < 100 THEN 'SOME'
        WHEN row_count < 1000 THEN 'MANY'
        ELSE 'LOTS'
    END as size_category
FROM table_counts
ORDER BY row_count ASC, table_name;
"
