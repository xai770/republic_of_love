#!/usr/bin/env python3
"""
Hierarchy Resetter - WF3004 Step 1

Backs up and clears the skill_hierarchy table.
Does NOT create hardcoded categories - those will be determined
dynamically based on the actual skills in the system.

This workflow is domain-agnostic: works for IT skills, pedagogy,
healthcare, arts, or any profession.
"""

import json
import sys
import os
from datetime import datetime
import psycopg2
from dotenv import load_dotenv


def reset_hierarchy() -> dict:
    """
    Backup hierarchy and clear it.
    
    Categories are NOT hardcoded - will be determined by analyzing
    the actual skills in the database.
    """
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    try:
        cursor = conn.cursor()
        
        # 1. Check current state
        cursor.execute("SELECT COUNT(*) FROM skill_hierarchy")
        current_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM skill_aliases")
        total_skills = cursor.fetchone()[0]
        
        # 2. Backup to timestamped table
        backup_table = f"skill_hierarchy_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute(f"""
            CREATE TABLE {backup_table} AS 
            SELECT * FROM skill_hierarchy
        """)
        
        # 3. Clear skill_hierarchy
        cursor.execute("DELETE FROM skill_hierarchy")
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        return {
            "status": "success",
            "backup_table": backup_table,
            "deleted_hierarchy_entries": deleted_count,
            "previous_hierarchy_count": current_count,
            "total_skills_to_classify": total_skills,
            "message": f"Hierarchy reset complete. Backed up {current_count} entries to {backup_table}. Ready to classify {total_skills} skills."
        }
        
    except Exception as e:
        conn.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


def main():
    """CLI entry point."""
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            pass
    
    result = reset_hierarchy()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
