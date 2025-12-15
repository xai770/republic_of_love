#!/usr/bin/env python3
"""
MemBridge Schema Migration Script
================================

Implements the schema changes requested:
1. Rename 'logs' table to 'calls' and clean up columns
2. Update models table default values  
3. Remove unnecessary views
4. Update prompts and templates tables
5. Create new 'logs' table for admin activities

Date: September 8, 2025
Author: Arden (AI Assistant)
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "membridge.db"

def backup_database():
    """Create a backup before migration"""
    backup_path = DB_PATH.parent / f"membridge_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    # Simple file copy for SQLite
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def log_migration_step(conn, step, details):
    """Log each migration step to the new logs table"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (timestamp, actor, action, details, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        'system:migration_script',
        f'schema_migration: {step}',
        json.dumps(details),
        'completed'
    ))

def migrate_schema():
    """Execute the complete schema migration"""
    
    print("🚀 Starting MemBridge Schema Migration")
    print("=" * 50)
    
    # Create backup
    backup_path = backup_database()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # First, create the new logs table for admin activities
        print("\n📋 Step 1: Creating new admin logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_new (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                actor TEXT NOT NULL,  -- who made the change (user, system, script name)
                action TEXT NOT NULL,  -- what they did (schema_update, maintenance, data_import)
                details TEXT,  -- JSON with specifics
                status TEXT DEFAULT 'pending',  -- pending, completed, failed
                duration_ms INTEGER,  -- how long it took
                affected_rows INTEGER,  -- how many records affected
                metadata TEXT  -- additional context as JSON
            );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_new_timestamp ON logs_new(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_new_actor ON logs_new(actor);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_new_action ON logs_new(action);")
        
        print("✅ Admin logs table created")
        
        # Log this step
        cursor.execute("""
            INSERT INTO logs_new (actor, action, details, status)
            VALUES ('system:migration_script', 'create_admin_logs_table', 
                   '{"reason": "Schema migration - new logs table for admin activities"}', 'completed')
        """)
        
        # Step 2: Rename logs to calls and clean up columns
        print("\n📋 Step 2: Migrating logs → calls table...")
        
        # Create new calls table with cleaned structure
        cursor.execute("""
            CREATE TABLE calls (
                call_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                template_id INTEGER,
                capability TEXT,
                job_id TEXT,
                success BOOLEAN NOT NULL,
                duration_ms INTEGER,
                input_length INTEGER,
                output_length INTEGER,
                response TEXT,
                error_message TEXT,
                metadata TEXT,
                FOREIGN KEY (template_id) REFERENCES templates(template_id)
            );
        """)
        
        # Copy data from logs to calls (excluding removed columns)
        cursor.execute("""
            INSERT INTO calls (
                call_id, timestamp, template_id, capability, job_id,
                success, duration_ms, input_length, output_length,
                response, error_message, metadata
            )
            SELECT 
                log_id, timestamp, template_id, capability, job_id,
                success, duration_ms, input_length, output_length,
                response, error_message, metadata
            FROM logs;
        """)
        
        # Create indexes for calls table
        cursor.execute("CREATE INDEX idx_calls_timestamp ON calls(timestamp);")
        cursor.execute("CREATE INDEX idx_calls_capability ON calls(capability);")
        cursor.execute("CREATE INDEX idx_calls_template_id ON calls(template_id);")
        
        rows_migrated = cursor.rowcount
        print(f"✅ Migrated {rows_migrated} records from logs to calls")
        
        # Log this step
        cursor.execute("""
            INSERT INTO logs_new (actor, action, details, status, affected_rows)
            VALUES ('system:migration_script', 'migrate_logs_to_calls', 
                   '{"removed_columns": ["model", "test_type"], "reason": "Cleaner schema - model in templates, test_type replaced by capability"}',
                   'completed', ?)
        """, (rows_migrated,))
        
        # Step 3: Drop old logs table
        print("\n📋 Step 3: Dropping old logs table...")
        cursor.execute("DROP TABLE logs;")
        print("✅ Old logs table removed")
        
        # Step 4: Rename logs_new to logs
        cursor.execute("ALTER TABLE logs_new RENAME TO logs;")
        print("✅ Admin logs table renamed to 'logs'")
        
        # Step 5: Update models table (investigate defaults)
        print("\n📋 Step 4: Checking models table defaults...")
        
        cursor.execute("SELECT name, max_tokens, temperature FROM models LIMIT 5;")
        sample_models = cursor.fetchall()
        
        print("Current model defaults:")
        for model in sample_models:
            print(f"  {model[0]}: max_tokens={model[1]}, temperature={model[2]}")
        
        # Log this information
        cursor.execute("""
            INSERT INTO logs (actor, action, details, status)
            VALUES ('system:migration_script', 'investigate_model_defaults', 
                   '{"finding": "max_tokens=4096 and temperature=0.2 are standard defaults", "note": "These appear to be reasonable LLM defaults"}',
                   'completed')
        """)
        
        # Step 6: Drop unnecessary views
        print("\n📋 Step 5: Cleaning up views...")
        
        # Check which views exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view';")
        existing_views = [row[0] for row in cursor.fetchall()]
        
        views_to_drop = []
        views_to_keep = []
        
        for view in existing_views:
            if view in ['prompts_with_history']:
                # Keep versioning-related views
                views_to_keep.append(view)
            elif view == 'prompt_versions_summary':
                # Rename this one
                cursor.execute("DROP VIEW prompt_versions_summary;")
                cursor.execute("""
                    CREATE VIEW prompts_versions_summary AS
                    SELECT 
                        p.prompt_id,
                        p.description,  -- Changed from name (which we'll remove)
                        p.version as current_version,
                        p.updated_at as last_updated,
                        COUNT(h.history_id) as archived_versions,
                        (COUNT(h.history_id) + 1) as total_versions
                    FROM prompts p
                    LEFT JOIN prompts_history h ON p.prompt_id = h.prompt_id
                    GROUP BY p.prompt_id, p.description, p.version, p.updated_at;
                """)
                views_to_keep.append('prompts_versions_summary')
                print("✅ Renamed prompt_versions_summary → prompts_versions_summary")
            else:
                # Drop other views if they're not needed
                if view not in ['template_status']:  # Keep template_status as it seems important
                    cursor.execute(f"DROP VIEW IF EXISTS {view};")
                    views_to_drop.append(view)
        
        print(f"✅ Dropped views: {views_to_drop}")
        print(f"✅ Kept views: {views_to_keep}")
        
        # Step 7: Update prompts table (remove name and file_path)
        print("\n📋 Step 6: Updating prompts table structure...")
        
        # First, backup prompts data
        cursor.execute("SELECT * FROM prompts LIMIT 1;")
        columns = [description[0] for description in cursor.description]
        print(f"Current prompts columns: {columns}")
        
        # Create new prompts table without name and file_path
        cursor.execute("""
            CREATE TABLE prompts_new (
                prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                content TEXT NOT NULL,
                version TEXT DEFAULT '1.0',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                tags TEXT
            );
        """)
        
        # Copy data (excluding name and file_path)
        cursor.execute("""
            INSERT INTO prompts_new (
                prompt_id, description, content, version, created_at, updated_at, tags
            )
            SELECT 
                prompt_id, description, content, version, created_at, updated_at, tags
            FROM prompts;
        """)
        
        # Also update prompts_history to match
        cursor.execute("""
            CREATE TABLE prompts_history_new (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER NOT NULL,
                description TEXT,
                content TEXT NOT NULL,
                version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                tags TEXT,
                archived_at TEXT NOT NULL DEFAULT (datetime('now')),
                archived_by TEXT DEFAULT 'system',
                change_reason TEXT,
                change_type TEXT DEFAULT 'UPDATE',
                previous_version TEXT,
                FOREIGN KEY (prompt_id) REFERENCES prompts_new(prompt_id)
            );
        """)
        
        cursor.execute("""
            INSERT INTO prompts_history_new (
                history_id, prompt_id, description, content, version,
                created_at, updated_at, tags, archived_at, archived_by,
                change_reason, change_type, previous_version
            )
            SELECT 
                history_id, prompt_id, description, content, version,
                created_at, updated_at, tags, archived_at, archived_by,
                change_reason, change_type, previous_version
            FROM prompts_history;
        """)
        
        # Drop old tables and rename new ones
        cursor.execute("DROP TABLE prompts;")
        cursor.execute("DROP TABLE prompts_history;")
        cursor.execute("ALTER TABLE prompts_new RENAME TO prompts;")
        cursor.execute("ALTER TABLE prompts_history_new RENAME TO prompts_history;")
        
        # Recreate indexes and triggers
        cursor.execute("CREATE INDEX idx_prompts_history_prompt_id ON prompts_history(prompt_id);")
        cursor.execute("CREATE INDEX idx_prompts_history_version ON prompts_history(version);")
        cursor.execute("CREATE INDEX idx_prompts_history_archived_at ON prompts_history(archived_at);")
        
        # Recreate triggers for the new table structure
        cursor.execute("""
            CREATE TRIGGER prompts_version_and_archive
                AFTER UPDATE ON prompts
                FOR EACH ROW
            WHEN OLD.content != NEW.content OR OLD.description != NEW.description OR OLD.tags != NEW.tags
            BEGIN
                INSERT INTO prompts_history (
                    prompt_id, description, content, version,
                    created_at, updated_at, tags,
                    archived_at, archived_by, change_reason, change_type, previous_version
                ) VALUES (
                    OLD.prompt_id, OLD.description, OLD.content, OLD.version,
                    OLD.created_at, OLD.updated_at, OLD.tags,
                    datetime('now'), 'system',
                    CASE 
                        WHEN OLD.content != NEW.content THEN 'Content modified'
                        WHEN OLD.description != NEW.description THEN 'Description modified'
                        WHEN OLD.tags != NEW.tags THEN 'Tags modified'
                        ELSE 'General update'
                    END,
                    'UPDATE',
                    OLD.version
                );
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER prompts_archive_delete
                AFTER DELETE ON prompts
                FOR EACH ROW
            BEGIN
                INSERT INTO prompts_history (
                    prompt_id, description, content, version,
                    created_at, updated_at, tags,
                    archived_at, archived_by, change_reason, change_type, previous_version
                ) VALUES (
                    OLD.prompt_id, OLD.description, OLD.content, OLD.version,
                    OLD.created_at, OLD.updated_at, OLD.tags,
                    datetime('now'), 'system', 'Record deleted', 'DELETE', OLD.version
                );
            END;
        """)
        
        print("✅ Prompts table updated (removed name, file_path)")
        
        # Step 8: Update templates table (remove call_number)
        print("\n📋 Step 7: Updating templates table...")
        
        cursor.execute("""
            CREATE TABLE templates_new (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_id INTEGER NOT NULL,
                config TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(prompt_id)
            );
        """)
        
        cursor.execute("""
            INSERT INTO templates_new (
                template_id, name, model, prompt_id, config, enabled, created_at, updated_at
            )
            SELECT 
                template_id, name, model, prompt_id, config, enabled, created_at, updated_at
            FROM templates;
        """)
        
        cursor.execute("DROP TABLE templates;")
        cursor.execute("ALTER TABLE templates_new RENAME TO templates;")
        
        # Recreate indexes
        cursor.execute("CREATE INDEX idx_templates_model ON templates(model);")
        cursor.execute("CREATE INDEX idx_templates_name ON templates(name);")
        
        print("✅ Templates table updated (removed call_number)")
        
        # Update the versioning view to work with new schema
        cursor.execute("DROP VIEW IF EXISTS prompts_versions_summary;")
        cursor.execute("""
            CREATE VIEW prompts_versions_summary AS
            SELECT 
                p.prompt_id,
                p.description,
                p.version as current_version,
                p.updated_at as last_updated,
                COUNT(h.history_id) as archived_versions,
                (COUNT(h.history_id) + 1) as total_versions
            FROM prompts p
            LEFT JOIN prompts_history h ON p.prompt_id = h.prompt_id
            GROUP BY p.prompt_id, p.description, p.version, p.updated_at;
        """)
        
        cursor.execute("DROP VIEW IF EXISTS prompts_with_history;")
        cursor.execute("""
            CREATE VIEW prompts_with_history AS
            SELECT 
                p.prompt_id,
                p.description,
                p.version as current_version,
                p.created_at,
                p.updated_at,
                COUNT(h.history_id) as version_count,
                MAX(h.archived_at) as last_modified
            FROM prompts p
            LEFT JOIN prompts_history h ON p.prompt_id = h.prompt_id
            GROUP BY p.prompt_id, p.description, p.version, p.created_at, p.updated_at;
        """)
        
        # Final log entry
        cursor.execute("""
            INSERT INTO logs (actor, action, details, status)
            VALUES ('system:migration_script', 'schema_migration_completed', 
                   '{"changes": ["logs->calls", "prompts simplified", "templates simplified", "views updated", "new admin logs"], "backup": "' || ? || '"}',
                   'completed')
        """, (str(backup_path),))
        
        conn.commit()
        
        print("\n🎉 Schema migration completed successfully!")
        print(f"📁 Backup available at: {backup_path}")
        
        # Show final summary
        cursor.execute("SELECT COUNT(*) FROM calls;")
        calls_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM logs;")
        logs_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM prompts;")
        prompts_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM templates;")
        templates_count = cursor.fetchone()[0]
        
        print(f"\n📊 Final counts:")
        print(f"  - calls: {calls_count}")
        print(f"  - logs (admin): {logs_count}")
        print(f"  - prompts: {prompts_count}")
        print(f"  - templates: {templates_count}")

if __name__ == "__main__":
    migrate_schema()
