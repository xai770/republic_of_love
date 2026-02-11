import os
"""
Database connection management for LLMCore V3.1 Admin GUI
PostgreSQL (base.yoga) connection
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Generator

# PostgreSQL connection details for base.yoga (BY)
DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': os.getenv('DB_PASSWORD', ''),
    'host': 'localhost',
    'port': '5432'
}

@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for PostgreSQL database connections with proper cleanup
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.cursor_factory = psycopg2.extras.RealDictCursor  # Enable dict-like access to rows
    
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def test_connection() -> bool:
    """Test database connectivity"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()['count']
            print(f"✅ base.yoga (BY) connected - {table_count} tables found")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False