-- Schema Change Audit Table
-- Automatically logs DDL changes for governance tracking
-- Date: 2026-02-03

-- Table to track schema changes
CREATE TABLE IF NOT EXISTS schema_changes (
    id SERIAL PRIMARY KEY,
    changed_at TIMESTAMP DEFAULT NOW(),
    change_type TEXT,  -- ADD_COLUMN, DROP_COLUMN, CREATE_TABLE, etc.
    table_name TEXT,
    column_name TEXT,
    ddl_command TEXT,
    changed_by TEXT DEFAULT current_user
);

COMMENT ON TABLE schema_changes IS 'Audit log for DDL changes. Auto-populated by event trigger.';

-- Event trigger function to log DDL
CREATE OR REPLACE FUNCTION log_ddl_changes()
RETURNS event_trigger AS $$
DECLARE
    obj record;
BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands()
    LOOP
        -- Only log table/column changes, skip indexes etc
        IF obj.object_type IN ('table', 'table column') THEN
            INSERT INTO schema_changes (change_type, table_name, ddl_command)
            VALUES (
                obj.command_tag,
                obj.object_identity,
                current_query()
            );
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create event trigger (requires superuser, so wrapped in exception)
DO $$
BEGIN
    DROP EVENT TRIGGER IF EXISTS schema_change_trigger;
    CREATE EVENT TRIGGER schema_change_trigger
        ON ddl_command_end
        EXECUTE FUNCTION log_ddl_changes();
    RAISE NOTICE 'Schema audit trigger installed';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Skipping event trigger (requires superuser)';
END $$;

-- Quick view for recent changes
CREATE OR REPLACE VIEW recent_schema_changes AS
SELECT 
    changed_at,
    change_type,
    table_name,
    changed_by,
    LEFT(ddl_command, 100) as ddl_preview
FROM schema_changes
ORDER BY changed_at DESC
LIMIT 50;
