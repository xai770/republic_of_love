#!/usr/bin/env python3
"""
Database Context Manager
========================

Clean, simple database connection management with automatic cleanup.
Use this instead of manually managing connections.
"""

from contextlib import contextmanager
from core.database import get_connection, return_connection


@contextmanager
def db_transaction(commit=True):
    """
    Context manager for database operations with automatic connection management.
    
    Args:
        commit: If True, commits on success. If False, no commit (read-only).
    
    Yields:
        cursor: Database cursor ready to use
    
    Usage:
        # Read operation
        with db_transaction(commit=False) as cursor:
            cursor.execute("SELECT * FROM postings WHERE posting_id = %s", (123,))
            posting = cursor.fetchone()
        
        # Write operation
        with db_transaction() as cursor:
            cursor.execute("UPDATE postings SET status = %s WHERE posting_id = %s", 
                          ('processed', 123))
        
        # Multiple operations in one transaction
        with db_transaction() as cursor:
            cursor.execute("INSERT INTO workflow_runs (...) VALUES (...)")
            run_id = cursor.fetchone()['workflow_run_id']
            
            cursor.execute("INSERT INTO task_type_runs (...) VALUES (...)", 
                          (run_id, ...))
    
    Features:
        - Automatic connection acquisition from pool
        - Automatic cursor creation and cleanup
        - Automatic connection return to pool (CRITICAL: uses putconn, not close)
        - Automatic rollback on exception
        - Automatic commit on success (if commit=True)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        try:
            yield cursor
            
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    finally:
        return_connection(conn)  # CRITICAL: Use putconn(), not close()!


@contextmanager
def db_connection():
    """
    Context manager for raw connection access (for advanced use cases).
    
    Yields:
        conn: Database connection
    
    Usage:
        with db_connection() as conn:
            cursor1 = conn.cursor()
            cursor2 = conn.cursor()
            # ... manual transaction management
            conn.commit()
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        return_connection(conn)  # CRITICAL: Use putconn(), not close()!
