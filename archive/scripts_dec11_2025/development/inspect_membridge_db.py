#!/usr/bin/env python3
"""
MemBridge Database Inspector
===========================

Check what's currently in the MemBridge database tables.
"""

import sys
import sqlite3
from pathlib import Path

def inspect_database() -> None:
    """Check what's in the MemBridge database"""
    
    db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print("🔍 MemBridge Database Inspector")
    print("=" * 40)
    print(f"📊 Database: {db_path}")
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Check tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📋 Tables found: {len(tables)}")
        for table in tables:
            print(f"   • {table}")
        
        # Check each table content
        for table in ['prompt_registry', 'mb_template_registry', 'mb_log']:
            if table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"\n📊 {table}: {count} rows")
                
                if count > 0:
                    cursor = conn.execute(f"SELECT * FROM {table} LIMIT 3")
                    rows = cursor.fetchall()
                    for i, row in enumerate(rows, 1):
                        print(f"   Row {i}: {dict(row)}")
                    if count > 3:
                        print(f"   ... and {count - 3} more rows")

if __name__ == "__main__":
    inspect_database()
