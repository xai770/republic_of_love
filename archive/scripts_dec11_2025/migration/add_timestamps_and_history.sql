-- ================================================================
-- LLMCore Timestamp and History Table Migration
-- Adds timestamps to all tables and creates corresponding history tables
-- ================================================================

-- Step 1: Add missing timestamp columns (SQLite workaround)
-- ================================================================

-- Add timestamp to canonicals table (without default first)
ALTER TABLE canonicals ADD COLUMN updated_at TIMESTAMP;

-- Add timestamp to models table (without default first)
ALTER TABLE models ADD COLUMN updated_at TIMESTAMP;

-- Set initial timestamps for existing records
UPDATE canonicals SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;
UPDATE models SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;

-- Step 2: Create History Tables
-- ================================================================

-- Canonicals History Table
CREATE TABLE canonicals_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_code TEXT NOT NULL,
    facet_id TEXT NOT NULL,
    capability_description TEXT,
    processing_instructions TEXT,
    processing_payload TEXT,
    processing_expected_response TEXT NOT NULL,
    qa_instructions TEXT,
    qa_scoring TEXT,
    review_notes TEXT,
    enabled INTEGER DEFAULT 1 CHECK(enabled IN (0, 1)),
    qa_model TEXT DEFAULT 'llama3.2:latest',
    updated_at TIMESTAMP,  -- Original timestamp when this version was active
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When archived
    change_reason TEXT     -- Optional: why this change was made
);

-- Facets History Table
CREATE TABLE facets_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    facet_id TEXT NOT NULL,
    parent_id TEXT,
    short_description TEXT,
    remarks TEXT,
    enabled INTEGER CHECK(enabled IN (0, 1)) DEFAULT 1,
    timestamp TIMESTAMP,   -- Original timestamp
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT,
    FOREIGN KEY(parent_id) REFERENCES facets(facet_id)
);

-- Models History Table
CREATE TABLE models_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    provider TEXT,
    enabled INTEGER,
    remarks TEXT,
    updated_at TIMESTAMP,  -- Original timestamp
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Skills History Table
CREATE TABLE skills_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER,
    test_id INTEGER NOT NULL,
    canonical_code REAL NOT NULL,
    facet_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    capability_description TEXT,
    processing_instructions TEXT,
    processing_payload_test TEXT,
    processing_received_response TEXT,
    qa_model TEXT,
    qa_instructions TEXT,
    qa_scoring TEXT,
    review_notes TEXT,
    latency_seconds REAL DEFAULT 0.0,
    timestamp TIMESTAMP,   -- Original timestamp
    enabled INTEGER DEFAULT 1 CHECK(enabled IN (0, 1)),
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Tasks History Table
CREATE TABLE tasks_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    skill_id TEXT NOT NULL,
    processing_payload TEXT NOT NULL,
    timestamp TIMESTAMP,   -- Original timestamp
    latency_seconds INTEGER NOT NULL,
    processing_received_response TEXT,
    remarks TEXT,
    processing_received_error TEXT,
    qa_score TEXT,
    qa_pass INTEGER DEFAULT 0 CHECK(qa_pass IN (0, 1)),
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Test Runs History Table
CREATE TABLE test_runs_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id INTEGER,
    test_id INTEGER NOT NULL,
    processing_payload_test_run TEXT NOT NULL,
    processing_received_response_test_run TEXT,
    processing_latency_test_run INTEGER,
    qa_latency_test_run REAL,
    qa_received_response_test_run TEXT,
    qa_score_test_run TEXT,
    remarks TEXT,
    timestamp TIMESTAMP,   -- Original timestamp
    enabled INTEGER DEFAULT 1 CHECK(enabled IN (0, 1)),
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Tests History Table
CREATE TABLE tests_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER,
    facet_id TEXT NOT NULL,
    canonical_code TEXT NOT NULL,
    capability_description TEXT,
    processing_model_name TEXT NOT NULL,
    processing_instructions TEXT,
    processing_payload_canonical TEXT,
    processing_expected_response_canonical TEXT,
    processing_received_response_canonical INTEGER,
    processing_latency_canonical REAL DEFAULT 0.0,
    qa_model_name TEXT,
    qa_instructions TEXT,
    qa_received_response TEXT,
    qa_scoring TEXT,
    qa_latency REAL,
    timestamp TIMESTAMP,   -- Original timestamp
    review_notes TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP,  -- Original creation timestamp
    executed_at TIMESTAMP, -- Original execution timestamp
    enabled INTEGER DEFAULT 1 CHECK(enabled IN (0, 1)),
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Step 3: Create Triggers for Automatic History Archiving
-- ================================================================

-- Canonicals Update Trigger
CREATE TRIGGER canonicals_history_trigger
    BEFORE UPDATE ON canonicals
    FOR EACH ROW
BEGIN
    INSERT INTO canonicals_history (
        canonical_code, facet_id, capability_description,
        processing_instructions, processing_payload, processing_expected_response,
        qa_instructions, qa_scoring, review_notes, enabled, qa_model, updated_at
    ) VALUES (
        OLD.canonical_code, OLD.facet_id, OLD.capability_description,
        OLD.processing_instructions, OLD.processing_payload, OLD.processing_expected_response,
        OLD.qa_instructions, OLD.qa_scoring, OLD.review_notes, OLD.enabled, OLD.qa_model, OLD.updated_at
    );
    
    -- Update timestamp in main table
    UPDATE canonicals SET updated_at = CURRENT_TIMESTAMP WHERE canonical_code = NEW.canonical_code;
END;

-- Facets Update Trigger
CREATE TRIGGER facets_history_trigger
    BEFORE UPDATE ON facets
    FOR EACH ROW
BEGIN
    INSERT INTO facets_history (
        facet_id, parent_id, short_description, remarks, enabled, timestamp
    ) VALUES (
        OLD.facet_id, OLD.parent_id, OLD.short_description, OLD.remarks, OLD.enabled, OLD.timestamp
    );
    
    -- Update timestamp in main table
    UPDATE facets SET timestamp = CURRENT_TIMESTAMP WHERE facet_id = NEW.facet_id;
END;

-- Models Update Trigger
CREATE TRIGGER models_history_trigger
    BEFORE UPDATE ON models
    FOR EACH ROW
BEGIN
    INSERT INTO models_history (
        model_name, provider, enabled, remarks, updated_at
    ) VALUES (
        OLD.model_name, OLD.provider, OLD.enabled, OLD.remarks, OLD.updated_at
    );
    
    -- Update timestamp in main table
    UPDATE models SET updated_at = CURRENT_TIMESTAMP WHERE model_name = NEW.model_name;
END;

-- Skills Update Trigger
CREATE TRIGGER skills_history_trigger
    BEFORE UPDATE ON skills
    FOR EACH ROW
BEGIN
    INSERT INTO skills_history (
        skill_id, test_id, canonical_code, facet_id, model_name,
        capability_description, processing_instructions, processing_payload_test,
        processing_received_response, qa_model, qa_instructions, qa_scoring,
        review_notes, latency_seconds, timestamp, enabled
    ) VALUES (
        OLD.skill_id, OLD.test_id, OLD.canonical_code, OLD.facet_id, OLD.model_name,
        OLD.capability_description, OLD.processing_instructions, OLD.processing_payload_test,
        OLD.processing_received_response, OLD.qa_model, OLD.qa_instructions, OLD.qa_scoring,
        OLD.review_notes, OLD.latency_seconds, OLD.timestamp, OLD.enabled
    );
    
    -- Update timestamp in main table
    UPDATE skills SET timestamp = CURRENT_TIMESTAMP WHERE skill_id = NEW.skill_id;
END;

-- Tasks Update Trigger
CREATE TRIGGER tasks_history_trigger
    BEFORE UPDATE ON tasks
    FOR EACH ROW
BEGIN
    INSERT INTO tasks_history (
        task_id, skill_id, processing_payload, timestamp, latency_seconds,
        processing_received_response, remarks, processing_received_error, qa_score, qa_pass
    ) VALUES (
        OLD.task_id, OLD.skill_id, OLD.processing_payload, OLD.timestamp, OLD.latency_seconds,
        OLD.processing_received_response, OLD.remarks, OLD.processing_received_error, OLD.qa_score, OLD.qa_pass
    );
    
    -- Update timestamp in main table (if timestamp column exists)
    -- Note: Tasks table has timestamp but no default, so we set it explicitly
    UPDATE tasks SET timestamp = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
END;

-- Test Runs Update Trigger
CREATE TRIGGER test_runs_history_trigger
    BEFORE UPDATE ON test_runs
    FOR EACH ROW
BEGIN
    INSERT INTO test_runs_history (
        test_run_id, test_id, processing_payload_test_run, processing_received_response_test_run,
        processing_latency_test_run, qa_latency_test_run, qa_received_response_test_run,
        qa_score_test_run, remarks, timestamp, enabled
    ) VALUES (
        OLD.test_run_id, OLD.test_id, OLD.processing_payload_test_run, OLD.processing_received_response_test_run,
        OLD.processing_latency_test_run, OLD.qa_latency_test_run, OLD.qa_received_response_test_run,
        OLD.qa_score_test_run, OLD.remarks, OLD.timestamp, OLD.enabled
    );
    
    -- Update timestamp in main table
    UPDATE test_runs SET timestamp = CURRENT_TIMESTAMP WHERE test_run_id = NEW.test_run_id;
END;

-- Tests Update Trigger
CREATE TRIGGER tests_history_trigger
    BEFORE UPDATE ON tests
    FOR EACH ROW
BEGIN
    INSERT INTO tests_history (
        test_id, facet_id, canonical_code, capability_description, processing_model_name,
        processing_instructions, processing_payload_canonical, processing_expected_response_canonical,
        processing_received_response_canonical, processing_latency_canonical, qa_model_name,
        qa_instructions, qa_received_response, qa_scoring, qa_latency, timestamp,
        review_notes, status, created_at, executed_at, enabled
    ) VALUES (
        OLD.test_id, OLD.facet_id, OLD.canonical_code, OLD.capability_description, OLD.processing_model_name,
        OLD.processing_instructions, OLD.processing_payload_canonical, OLD.processing_expected_response_canonical,
        OLD.processing_received_response_canonical, OLD.processing_latency_canonicaal, OLD.qa_model_name,
        OLD.qa_instructions, OLD.qa_received_response, OLD.qa_scoring, OLD.qa_latency, OLD.timestamp,
        OLD.review_notes, OLD.status, OLD.created_at, OLD.executed_at, OLD.enabled
    );
    
    -- Update timestamp in main table
    UPDATE tests SET timestamp = CURRENT_TIMESTAMP WHERE test_id = NEW.test_id;
END;

-- Step 4: Create utility views for easy history access
-- ================================================================

-- View to see recent changes across all tables
CREATE VIEW recent_changes AS
SELECT 'canonicals' as table_name, canonical_code as record_id, archived_at, change_reason 
FROM canonicals_history
UNION ALL
SELECT 'facets', facet_id, archived_at, change_reason 
FROM facets_history
UNION ALL
SELECT 'models', model_name, archived_at, change_reason 
FROM models_history
UNION ALL
SELECT 'skills', CAST(skill_id AS TEXT), archived_at, change_reason 
FROM skills_history
UNION ALL
SELECT 'tasks', CAST(task_id AS TEXT), archived_at, change_reason 
FROM tasks_history
UNION ALL
SELECT 'test_runs', CAST(test_run_id AS TEXT), archived_at, change_reason 
FROM test_runs_history
UNION ALL
SELECT 'tests', CAST(test_id AS TEXT), archived_at, change_reason 
FROM tests_history
ORDER BY archived_at DESC;

-- ================================================================
-- Migration Complete
-- All tables now have timestamps and automatic history tracking
-- ================================================================
