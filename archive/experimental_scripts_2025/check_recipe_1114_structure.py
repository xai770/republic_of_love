#!/usr/bin/env python3
"""
Check Recipe 1114 current structure
"""

import psycopg2
import psycopg2.extras

DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost',
    'port': '5432'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("📋 Recipe 1114 Current Structure:")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            rs.recipe_session_id,
            rs.execution_order,
            s.session_id,
            s.session_name,
            s.actor_id,
            rs.execute_condition,
            rs.on_success_action,
            rs.on_failure_action
        FROM recipe_sessions rs
        JOIN sessions s ON rs.session_id = s.session_id
        WHERE rs.recipe_id = 1114
        ORDER BY rs.execution_order
    """)
    
    sessions = cursor.fetchall()
    
    for sess in sessions:
        print(f"\nSession {sess['execution_order']}: {sess['session_name']}")
        print(f"  Session ID: {sess['session_id']}")
        print(f"  Recipe Session ID: {sess['recipe_session_id']}")
        print(f"  Actor: {sess['actor_id']}")
        print(f"  Condition: {sess['execute_condition']}")
        print(f"  On Success: {sess['on_success_action']}")
        print(f"  On Failure: {sess['on_failure_action']}")
    
    print(f"\n{'='*80}")
    print(f"Total: {len(sessions)} sessions")
    
    conn.close()

if __name__ == '__main__':
    main()
