#!/usr/bin/env python3
"""
Disable Session 8 in Recipe 1114 (database update is now handled automatically by by_recipe_runner.py)
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
    cursor = conn.cursor()
    
    try:
        # Disable Session 8 (database update now handled by runner)
        cursor.execute("""
            UPDATE recipe_sessions
            SET enabled = FALSE
            WHERE recipe_id = 1114
              AND execution_order = 8
            RETURNING recipe_session_id, execution_order
        """)
        
        result = cursor.fetchone()
        conn.commit()
        
        if result:
            print(f"✅ Disabled Session 8 in Recipe 1114:")
            print(f"   Recipe Session ID: {result[0]}")
            print(f"   Execution Order: {result[1]}")
            print(f"\n✅ Database updates now handled automatically by by_recipe_runner.py")
        else:
            print("⚠️  No Session 8 found (might already be disabled)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
