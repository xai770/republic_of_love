-- Migration 000: Migration Log System
-- =====================================
-- Track which migrations have been applied to the database
-- Philosophy: Know thy state. Every change documented.
--
-- Purpose:
--   - Track migration execution history
--   - Prevent duplicate migrations
--   - Enable rollback capability
--   - Audit trail for schema changes
--   - Foundation for automated migration runner

-- Create migration_log table
CREATE TABLE IF NOT EXISTS migration_log (
    migration_id SERIAL PRIMARY KEY,
    migration_number VARCHAR(10) NOT NULL UNIQUE,
    migration_name VARCHAR(255) NOT NULL,
    migration_file VARCHAR(255),
    
    -- Execution tracking
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(100),
    duration_ms INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'SUCCESS', -- SUCCESS, FAILED, ROLLED_BACK
    error_message TEXT,
    
    -- Context
    database_version VARCHAR(50),
    notes TEXT,
    
    -- Dependencies
    depends_on VARCHAR(10)[], -- Other migration numbers required first
    
    -- Metadata
    is_data_migration BOOLEAN DEFAULT false,
    is_reversible BOOLEAN DEFAULT true,
    rollback_sql TEXT
);

-- Create index for fast lookups
CREATE INDEX idx_migration_log_number ON migration_log(migration_number);
CREATE INDEX idx_migration_log_date ON migration_log(applied_at DESC);
CREATE INDEX idx_migration_log_status ON migration_log(status);

-- View: Migration history
CREATE OR REPLACE VIEW v_migration_history AS
SELECT 
    migration_number,
    migration_name,
    applied_at,
    duration_ms,
    status,
    CASE 
        WHEN error_message IS NOT NULL THEN '❌ ERROR'
        WHEN status = 'ROLLED_BACK' THEN '⏮️ ROLLED BACK'
        ELSE '✅ SUCCESS'
    END as status_icon
FROM migration_log
ORDER BY migration_number;

-- View: Current database state
CREATE OR REPLACE VIEW v_database_state AS
SELECT 
    COUNT(*) as total_migrations,
    COUNT(*) FILTER (WHERE status = 'SUCCESS') as successful_migrations,
    COUNT(*) FILTER (WHERE status = 'FAILED') as failed_migrations,
    MAX(migration_number) as latest_migration,
    MAX(applied_at) as last_migration_date
FROM migration_log;

-- Function: Check if migration already applied
CREATE OR REPLACE FUNCTION migration_applied(p_migration_number VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM migration_log 
        WHERE migration_number = p_migration_number 
        AND status = 'SUCCESS'
    ) INTO v_exists;
    
    RETURN v_exists;
END;
$$ LANGUAGE plpgsql;

-- Function: Record migration
CREATE OR REPLACE FUNCTION record_migration(
    p_migration_number VARCHAR,
    p_migration_name VARCHAR,
    p_status VARCHAR DEFAULT 'SUCCESS',
    p_duration_ms INTEGER DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_migration_id INTEGER;
BEGIN
    INSERT INTO migration_log (
        migration_number,
        migration_name,
        migration_file,
        status,
        duration_ms,
        error_message,
        notes,
        applied_by
    ) VALUES (
        p_migration_number,
        p_migration_name,
        p_migration_number || '_' || regexp_replace(lower(p_migration_name), '[^a-z0-9]+', '_', 'g') || '.sql',
        p_status,
        p_duration_ms,
        p_error_message,
        p_notes,
        current_user
    )
    ON CONFLICT (migration_number) DO UPDATE
    SET 
        status = EXCLUDED.status,
        error_message = EXCLUDED.error_message,
        notes = CASE 
            WHEN migration_log.notes IS NULL THEN EXCLUDED.notes
            ELSE migration_log.notes || E'\n' || EXCLUDED.notes
        END
    RETURNING migration_id INTO v_migration_id;
    
    RETURN v_migration_id;
END;
$$ LANGUAGE plpgsql;

-- Seed with migration 000 (this migration)
SELECT record_migration(
    '000',
    'Migration Log System',
    'SUCCESS',
    NULL,
    NULL,
    'Foundation migration - tracks all subsequent migrations'
);

-- Grant permissions
GRANT SELECT ON migration_log TO base_admin;
GRANT INSERT, UPDATE ON migration_log TO base_admin;
GRANT SELECT ON v_migration_history TO base_admin;
GRANT SELECT ON v_database_state TO base_admin;

COMMIT;

-- Summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Migration 000: Migration Log System - COMPLETE';
    RAISE NOTICE '=================================================================';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '  - migration_log table (track all migrations)';
    RAISE NOTICE '  - Functions: migration_applied(), record_migration()';
    RAISE NOTICE '  - Views: v_migration_history, v_database_state';
    RAISE NOTICE '';
    RAISE NOTICE 'Purpose: Know what migrations have been applied and when';
    RAISE NOTICE 'Usage: SELECT * FROM v_migration_history;';
    RAISE NOTICE '';
    RAISE NOTICE 'Philosophy: Know thy state. Every change documented.';
    RAISE NOTICE '=================================================================';
END $$;
