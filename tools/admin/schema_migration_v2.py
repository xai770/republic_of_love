#!/usr/bin/env python3
"""
MemBridge Schema Migration v2
============================
A cleaner approach to migrating the schema that handles dependencies properly.
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/membridge.db")
BACKUP_PATH = Path(f"data/membridge_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")

def migrate_schema():
    """Execute the schema migration"""
    
    print("🚀 MemBridge Schema Migration v2")
    print("=" * 50)
    
    # Create backup
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"✅ Database backed up to: {BACKUP_PATH}")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Step 1: Drop all dependent views first
        print("\n📋 Step 1: Dropping dependent views...")
        views_to_drop = [
            'prompts_with_history',
            'prompts_versions_summary', 
            'prompt_versions_summary',
            'template_status'
        ]
        
        for view in views_to_drop:
            try:
                cursor.execute(f"DROP VIEW IF EXISTS {view};")
                print(f"  ✅ Dropped view: {view}")
            except Exception as e:
                print(f"  ⚠️  Could not drop {view}: {e}")
        
        # Step 2: Create new admin logs table
        print("\n📋 Step 2: Creating admin logs table...")
        cursor.execute("""
            CREATE TABLE admin_logs_temp (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                table_affected TEXT,
                success BOOLEAN DEFAULT 1
            );
        """)
        
        # Step 3: Rename logs → calls and migrate data
        print("\n📋 Step 3: Migrating logs → calls...")
        
        # Check if logs table exists and what columns it has
        cursor.execute("PRAGMA table_info(logs);")
        logs_columns = [col[1] for col in cursor.fetchall()]
        print(f"  Current logs columns: {logs_columns}")
        
        # Create calls table with cleaned structure
        cursor.execute("""
            CREATE TABLE calls (
                call_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                input_data TEXT,
                response TEXT,
                capability TEXT,
                duration INTEGER,
                success BOOLEAN,
                error_message TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES templates(template_id)
            );
        """)
        
        # Migrate data from logs to calls (excluding model and test_type)
        if logs_columns:
            # Build dynamic INSERT based on available columns
            available_cols = []
            values_cols = []
            
            col_mapping = {
                'log_id': 'call_id',
                'template_id': 'template_id',
                'input_data': 'input_data', 
                'response': 'response',
                'capability': 'capability',
                'duration': 'duration',
                'success': 'success',
                'error_message': 'error_message',
                'timestamp': 'timestamp'
            }
            
            for old_col, new_col in col_mapping.items():
                if old_col in logs_columns:
                    available_cols.append(new_col)
                    values_cols.append(old_col)
            
            if available_cols:
                insert_cols = ', '.join(available_cols)
                select_cols = ', '.join(values_cols)
                cursor.execute(f"""
                    INSERT INTO calls ({insert_cols})
                    SELECT {select_cols} FROM logs;
                """)
                
                cursor.execute("SELECT COUNT(*) FROM calls;")
                count = cursor.fetchone()[0]
                print(f"  ✅ Migrated {count} records to calls table")
        
        # Drop old logs table
        cursor.execute("DROP TABLE IF EXISTS logs;")
        
        # Rename admin logs to logs
        cursor.execute("ALTER TABLE admin_logs_temp RENAME TO logs;")
        print("  ✅ Created new admin logs table")
        
        # Step 4: Update prompts table (remove name, file_path)
        print("\n📋 Step 4: Updating prompts table...")
        
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
        
        cursor.execute("""
            INSERT INTO prompts_new (prompt_id, description, content, version, created_at, updated_at, tags)
            SELECT prompt_id, description, content, version, created_at, updated_at, tags
            FROM prompts;
        """)
        
        # Update prompts_history table too
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
        
        # Replace old tables
        cursor.execute("DROP TABLE prompts;")
        cursor.execute("DROP TABLE prompts_history;")
        cursor.execute("ALTER TABLE prompts_new RENAME TO prompts;")
        cursor.execute("ALTER TABLE prompts_history_new RENAME TO prompts_history;")
        
        print("  ✅ Prompts table updated (removed name, file_path)")
        
        # Step 5: Update templates table (remove call_number if it exists)
        print("\n📋 Step 5: Updating templates table...")
        
        cursor.execute("PRAGMA table_info(templates);")
        templates_columns = [col[1] for col in cursor.fetchall()]
        print(f"  Current templates columns: {templates_columns}")
        
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
        
        # Copy data excluding call_number
        copy_cols = [col for col in templates_columns if col != 'call_number']
        insert_cols = ', '.join(copy_cols)
        select_cols = ', '.join(copy_cols)
        
        cursor.execute(f"""
            INSERT INTO templates_new ({insert_cols})
            SELECT {select_cols} FROM templates;
        """)
        
        cursor.execute("DROP TABLE templates;")
        cursor.execute("ALTER TABLE templates_new RENAME TO templates;")
        print("  ✅ Templates table updated")
        
        # Step 6: Recreate indexes and triggers
        print("\n📋 Step 6: Recreating indexes and triggers...")
        
        # Prompts indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_content ON prompts(content);")
        
        # Prompts history indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_history_prompt_id ON prompts_history(prompt_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_history_version ON prompts_history(version);") 
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompts_history_archived_at ON prompts_history(archived_at);")
        
        # Templates indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_model ON templates(model);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_prompt_id ON templates(prompt_id);")
        
        # Calls indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_template_id ON calls(template_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_timestamp ON calls(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calls_capability ON calls(capability);")
        
        # Recreate versioning triggers
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
        
        print("  ✅ Indexes and triggers recreated")
        
        # Step 7: Recreate useful views
        print("\n📋 Step 7: Recreating useful views...")
        
        cursor.execute("""
            CREATE VIEW prompts_versions_summary AS
            SELECT 
                p.prompt_id,
                SUBSTR(p.description, 1, 50) as description_preview,
                p.version as current_version,
                p.updated_at as last_updated,
                COUNT(h.history_id) as archived_versions,
                (COUNT(h.history_id) + 1) as total_versions
            FROM prompts p
            LEFT JOIN prompts_history h ON p.prompt_id = h.prompt_id
            GROUP BY p.prompt_id, p.description, p.version, p.updated_at;
        """)
        
        print("  ✅ Views recreated")
        
        # Step 8: Log this migration in the new logs table
        cursor.execute("""
            INSERT INTO logs (actor, action, details, table_affected, success)
            VALUES (
                'Arden (schema_migration_v2.py)',
                'Schema Migration',
                'Renamed logs→calls, removed unnecessary columns, updated table structures, recreated indexes/triggers/views',
                'logs,calls,prompts,prompts_history,templates',
                1
            );
        """)
        
        print("  ✅ Migration logged")
        
        # Step 9: Show final summary
        print("\n📊 Final Schema Summary:")
        
        # Check table structures
        tables = ['prompts', 'prompts_history', 'templates', 'calls', 'logs', 'models']
        for table in tables:
            try:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [col[1] for col in cursor.fetchall()]
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"  {table}: {len(columns)} columns, {count} records")
            except Exception:
                print(f"  {table}: not found")
        
        # Check models table defaults
        print("\n📋 Model defaults info:")
        cursor.execute("SELECT name, max_tokens, temperature FROM models LIMIT 3;")
        for row in cursor.fetchall():
            print(f"  {row[0]}: max_tokens={row[1]}, temperature={row[2]}")
        print("  Note: max_tokens=4096 and temperature=0.2 appear to be Ollama defaults")
        
        conn.commit()
        print("\n🎉 Migration completed successfully!")

if __name__ == "__main__":
    migrate_schema()
