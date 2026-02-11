#!/usr/bin/env python3
"""
Database Connection Utilities
==============================

Provides centralized database connection management for Base Yoga system.

Features:
- Connection pooling for performance (reuse connections instead of creating new ones)
- Thread-safe connection management
- Automatic connection lifecycle management
- RealDictCursor for dict-like row access
- Cursor-agnostic utilities (fetch_scalar, get_column) to prevent cursor type bugs

Performance Impact:
- Without pooling: ~100-200ms per checkpoint (new connection each time)
- With pooling: ~5-10ms per checkpoint (10-20x faster!)

⚠️  IMPORTANT - CURSOR TYPE WARNING ⚠️
======================================
This system uses RealDictCursor by default, which returns rows as DICTS, not tuples.

    ❌ WRONG:  count = cursor.fetchone()[0]        # KeyError with RealDictCursor!
    ✅ RIGHT:  count = fetch_scalar(cursor)        # Works with any cursor type
    
    ❌ WRONG:  name = row[1]                       # KeyError with RealDictCursor!
    ✅ RIGHT:  name = row['canonical_name']        # Dict access
    ✅ RIGHT:  name = get_column(row, 1, 'name')   # Works with any cursor type

Always use fetch_scalar() for COUNT(*), MAX(), and other single-value queries.
"""

import os
import atexit
from contextlib import contextmanager
from typing import Optional
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection configuration
DEFAULT_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'turing'),
    'user': os.getenv('DB_USER', 'base_admin'),
    'password': os.getenv('DB_PASSWORD')  # No default - must be in .env
}

# Global connection pool (initialized on first use)
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def _get_pool() -> pool.ThreadedConnectionPool:
    """
    Get or create the connection pool (lazy initialization).
    
    Pool configuration:
    - minconn=2: Keep 2 connections alive at all times
    - maxconn=20: Allow up to 20 concurrent connections
    - Thread-safe: Multiple threads can get connections simultaneously
    
    Returns:
        ThreadedConnectionPool instance
    """
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=5,
            maxconn=50,  # Increased from 20 - wave processor needs many concurrent connections
            cursor_factory=psycopg2.extras.RealDictCursor,
            **DEFAULT_CONFIG
        )
        
        # Register cleanup on exit
        atexit.register(_close_pool)
    
    return _connection_pool


def _close_pool():
    """Close all connections in pool (called on exit)"""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None


@contextmanager
def get_connection():
    """
    Get database connection from pool with RealDictCursor.
    
    MUST be used as context manager to ensure connection is returned to pool:
    
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recipes WHERE recipe_id = %s", (1121,))
            recipe = cursor.fetchone()
            # Connection automatically returned to pool
    
    CRITICAL: Do NOT call conn.close() - it destroys the connection instead of
    returning it to the pool, causing pool exhaustion!
    
    Returns:
        psycopg2.connection: Database connection with dict-like row access
    """
    pool_instance = _get_pool()
    conn = pool_instance.getconn()
    try:
        yield conn
    finally:
        pool_instance.putconn(conn)


def get_connection_raw():
    """
    Get database connection WITHOUT context manager.
    
    WARNING: You MUST call return_connection(conn) when done!
    Prefer get_connection() context manager instead.
    
    Returns:
        psycopg2.connection: Database connection (caller must return to pool!)
    """
    pool_instance = _get_pool()
    return pool_instance.getconn()


def return_connection(conn):
    """
    Explicitly return connection to pool.
    
    CRITICAL: Use this instead of conn.close()!
    In psycopg2 pools, conn.close() DESTROYS the connection.
    Only putconn() returns it to the pool.
    
    Args:
        conn: Connection to return to pool
    """
    pool_instance = _get_pool()
    pool_instance.putconn(conn)


# =============================================================================
# ROW ACCESS UTILITIES - Cursor-agnostic helpers
# =============================================================================
# These utilities work with BOTH RealDictCursor (returns dicts) and 
# regular cursors (returns tuples). This eliminates the recurring bug where
# code uses `row[0]` but the cursor returns dicts.
#
# RECOMMENDED PATTERNS:
#   scalar = fetch_scalar(cursor)           # For COUNT(*), single values
#   value = get_column(row, 0, 'col_name')  # For accessing row data
# =============================================================================

def fetch_scalar(cursor):
    """
    Fetch a single scalar value from cursor (e.g., COUNT(*), MAX(), etc.)
    
    Works with both RealDictCursor and regular tuple cursor.
    
    Usage:
        cursor.execute("SELECT COUNT(*) FROM owl")
        count = fetch_scalar(cursor)
        
        cursor.execute("SELECT MAX(owl_id) FROM owl")
        max_id = fetch_scalar(cursor)
    
    Returns:
        The first column of the first row, or None if no rows
    """
    row = cursor.fetchone()
    if row is None:
        return None
    
    # Handle dict-like rows (RealDictCursor)
    if hasattr(row, 'keys'):
        # Get first key's value
        first_key = list(row.keys())[0]
        return row[first_key]
    
    # Handle tuple-like rows (regular cursor)
    return row[0]


def get_column(row, index_or_name, fallback_name=None):
    """
    Get a column value from a row, handling both dict and tuple rows.
    
    Args:
        row: A row from cursor.fetchone() or cursor.fetchall()
        index_or_name: Column index (int) or column name (str)
        fallback_name: If index fails, try this column name (for mixed codebases)
    
    Usage:
        # Works with both cursor types:
        for row in cursor.fetchall():
            owl_id = get_column(row, 0, 'owl_id')
            name = get_column(row, 'canonical_name')
    
    Returns:
        The column value
    
    Raises:
        KeyError/IndexError if column not found
    """
    # If row is dict-like
    if hasattr(row, 'keys'):
        if isinstance(index_or_name, str):
            return row[index_or_name]
        elif fallback_name:
            return row[fallback_name]
        else:
            # index_or_name is int, get by position in dict
            keys = list(row.keys())
            return row[keys[index_or_name]]
    
    # If row is tuple-like
    if isinstance(index_or_name, int):
        return row[index_or_name]
    elif fallback_name and isinstance(fallback_name, int):
        return row[fallback_name]
    else:
        raise TypeError(f"Row is tuple-like but got string key '{index_or_name}'. Use integer index.")
