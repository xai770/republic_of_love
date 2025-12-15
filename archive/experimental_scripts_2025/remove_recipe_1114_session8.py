#!/usr/bin/env python3
"""
Remove Session 8 from Recipe 1114 completely
Database updates are now handled automatically by by_recipe_runner.py
"""

import psycopg2

DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost',
    'port': '5432'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cursor = conn.cursor()
    
    try:
        # First, delete any session_runs for Session 8
        cursor.execute("""
            DELETE FROM session_runs
            WHERE recipe_session_id IN (
                SELECT recipe_session_id 
                FROM recipe_sessions 
                WHERE recipe_id = 1114 AND execution_order = 8
            )
        """)
        deleted_runs = cursor.rowcount
        print(f"🗑️  Deleted {deleted_runs} session_run records for Session 8")
        
        # Delete Session 8 from recipe_sessions (execution_order = 8)
        cursor.execute("""
            DELETE FROM recipe_sessions
            WHERE recipe_id = 1114
              AND execution_order = 8
            RETURNING recipe_session_id, session_id
        """)
        
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Removed Session 8 from Recipe 1114:")
            print(f"   Recipe Session ID: {result[0]}")
            print(f"   Session ID: {result[1]}")
            
            # Note: We're NOT deleting the session itself (session_id 3345) or its instructions
            # in case it's used elsewhere or needs to be referenced later
            print(f"\n✅ Session definition kept in database for reference")
            print(f"✅ Database updates now handled automatically by by_recipe_runner.py")
            print(f"\n📋 Recipe 1114 now has 7 sessions (1-7)")
            
            conn.commit()
        else:
            print("⚠️  No Session 8 found in Recipe 1114")
            conn.rollback()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
