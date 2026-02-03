#!/usr/bin/env python3
"""
Schema Review Tool
==================

Analyze Turing database for:
1. Obsolete tables (not in code, no recent access)
2. Low-information columns (all NULL, single value)
3. Redundant tables (duplicate data)
4. Missing comments

Usage:
    python3 tools/schema_review.py
    python3 tools/schema_review.py --drop-deprecated  # Generate DROP statements
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection

PROJECT_ROOT = Path(__file__).parent.parent


def get_tables_from_code() -> Set[str]:
    """Find all table names referenced in Python code."""
    table_refs = set()
    
    patterns = [
        r'FROM\s+(\w+)',
        r'JOIN\s+(\w+)',
        r'INTO\s+(\w+)',
        r'UPDATE\s+(\w+)',
        r'DELETE\s+FROM\s+(\w+)',
        r'TRUNCATE\s+(\w+)',
    ]
    
    # Skip these directories
    skip_dirs = {'__pycache__', 'venv', '.git', 'logs', 'backups', 'node_modules'}
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for f in files:
            if f.endswith('.py'):
                try:
                    content = open(os.path.join(root, f)).read()
                    for pat in patterns:
                        for m in re.finditer(pat, content, re.IGNORECASE):
                            table = m.group(1).lower()
                            # Filter out Python keywords and common false positives
                            if (table not in ['select', 'where', 'set', 'values', 
                                             'information_schema', 'from', 'import',
                                             'the', 'this', 'that', 'json', 'datetime',
                                             'a', 'b', 'c', 'x', 'y', 'core', 'tools']
                                and not table.startswith('pg_')
                                and len(table) > 2):
                                table_refs.add(table)
                except:
                    pass
    
    return table_refs


def analyze_tables(conn) -> List[Dict]:
    """Get comprehensive table analysis."""
    cur = conn.cursor()
    
    # Get all tables with stats
    cur.execute("""
        SELECT 
            t.tablename as table_name,
            pg_relation_size(quote_ident(t.tablename)::regclass) as size_bytes,
            COALESCE(s.n_live_tup, 0) as row_count,
            s.last_vacuum,
            s.last_analyze,
            obj_description(quote_ident(t.tablename)::regclass::oid) as table_comment
        FROM pg_tables t
        LEFT JOIN pg_stat_user_tables s ON t.tablename = s.relname
        WHERE t.schemaname = 'public'
        ORDER BY t.tablename
    """)
    
    tables = []
    for row in cur.fetchall():
        tables.append({
            'name': row['table_name'],
            'size_bytes': row['size_bytes'] or 0,
            'row_count': row['row_count'] or 0,
            'last_vacuum': row['last_vacuum'],
            'last_analyze': row['last_analyze'],
            'comment': row['table_comment'],
        })
    
    return tables


def analyze_columns(conn, table_name: str) -> List[Dict]:
    """Analyze columns in a table for information density."""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name, data_type, is_nullable,
               col_description((table_schema || '.' || table_name)::regclass::oid, ordinal_position) as comment
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position
    """, (table_name,))
    
    columns = []
    for row in cur.fetchall():
        col_name = row['column_name']
        
        # Get distinct count
        try:
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT {col_name}) as distinct_values,
                    COUNT({col_name}) as non_null
                FROM {table_name}
            """)
            stats = cur.fetchone()
            
            columns.append({
                'name': col_name,
                'data_type': row['data_type'],
                'nullable': row['is_nullable'] == 'YES',
                'comment': row['comment'],
                'total': stats['total'],
                'distinct': stats['distinct_values'],
                'non_null': stats['non_null'],
            })
        except Exception as e:
            columns.append({
                'name': col_name,
                'data_type': row['data_type'],
                'nullable': row['is_nullable'] == 'YES',
                'comment': row['comment'],
                'error': str(e),
            })
    
    return columns


def categorize_table(name: str) -> str:
    """Categorize a table by name."""
    if name.startswith('_deprecated') or name.startswith('_archive'):
        return 'deprecated'
    elif 'backup' in name or 'history' in name:
        return 'backup'
    elif name.startswith('raq_'):
        return 'raq_test'
    elif name.startswith('mv_') or name.startswith('v_'):
        return 'view'
    else:
        return 'active'


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Schema review tool')
    parser.add_argument('--drop-deprecated', action='store_true', 
                        help='Generate DROP statements for deprecated tables')
    parser.add_argument('--table', type=str, help='Analyze specific table')
    args = parser.parse_args()
    
    with get_connection() as conn:
        # Get tables from database
        tables = analyze_tables(conn)
        
        # Get tables referenced in code
        code_tables = get_tables_from_code()
        
        # Categorize
        deprecated = []
        backup = []
        active = []
        orphaned = []  # In DB but not in code
        
        for t in tables:
            t['category'] = categorize_table(t['name'])
            t['in_code'] = t['name'] in code_tables
            
            if t['category'] == 'deprecated':
                deprecated.append(t)
            elif t['category'] in ['backup', 'raq_test']:
                backup.append(t)
            elif not t['in_code'] and t['row_count'] > 0:
                orphaned.append(t)
            else:
                active.append(t)
        
        # Specific table analysis
        if args.table:
            print(f"\n📊 DETAILED ANALYSIS: {args.table}")
            print("=" * 80)
            cols = analyze_columns(conn, args.table)
            for c in cols:
                if 'error' in c:
                    status = f"ERROR: {c['error'][:30]}"
                elif c['total'] == 0:
                    status = "empty table"
                elif c['non_null'] == 0:
                    status = "🔴 ALL NULL"
                elif c['distinct'] == 1:
                    status = "🟡 SINGLE VALUE"
                elif c['distinct'] == c['total']:
                    status = "🟢 unique"
                else:
                    status = f"🔵 {c['distinct']}/{c['total']} distinct"
                
                comment = f"  # {c['comment']}" if c['comment'] else ""
                print(f"  {c['name']:<30} {c['data_type']:<15} {status:<25}{comment}")
            return
        
        # Summary Report
        print("=" * 80)
        print("SCHEMA REVIEW REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 80)
        
        # Deprecated tables
        print(f"\n🔴 DEPRECATED/ARCHIVE TABLES ({len(deprecated)}) - {sum(t['size_bytes'] for t in deprecated) / 1024 / 1024:.1f} MB")
        print("-" * 60)
        for t in sorted(deprecated, key=lambda x: -x['size_bytes']):
            size_mb = t['size_bytes'] / 1024 / 1024
            print(f"  {t['name']:<45} {t['row_count']:>8} rows  {size_mb:>6.1f} MB")
        
        # Backup tables
        print(f"\n🟡 BACKUP/RAQ TABLES ({len(backup)}) - {sum(t['size_bytes'] for t in backup) / 1024 / 1024:.1f} MB")
        print("-" * 60)
        for t in sorted(backup, key=lambda x: -x['size_bytes'])[:10]:
            size_mb = t['size_bytes'] / 1024 / 1024
            print(f"  {t['name']:<45} {t['row_count']:>8} rows  {size_mb:>6.1f} MB")
        if len(backup) > 10:
            print(f"  ... and {len(backup) - 10} more")
        
        # Orphaned (in DB but not in code)
        if orphaned:
            print(f"\n⚪ ORPHANED TABLES (not in code) ({len(orphaned)})")
            print("-" * 60)
            for t in sorted(orphaned, key=lambda x: -x['row_count']):
                print(f"  {t['name']:<45} {t['row_count']:>8} rows")
        
        # Generate DROP statements
        if args.drop_deprecated:
            print("\n" + "=" * 80)
            print("DROP STATEMENTS (copy with caution!)")
            print("=" * 80)
            print("\n-- Deprecated tables")
            for t in deprecated:
                print(f"DROP TABLE IF EXISTS {t['name']} CASCADE;")
            
            total_freed = sum(t['size_bytes'] for t in deprecated) / 1024 / 1024
            print(f"\n-- Total space to be freed: {total_freed:.1f} MB")
        
        # Summary
        total_tables = len(tables)
        total_size = sum(t['size_bytes'] for t in tables) / 1024 / 1024
        deprecated_size = sum(t['size_bytes'] for t in deprecated) / 1024 / 1024
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"  Total tables:     {total_tables}")
        print(f"  Total size:       {total_size:.1f} MB")
        print(f"  Deprecated size:  {deprecated_size:.1f} MB ({deprecated_size/total_size*100:.0f}%)")
        print(f"  Active tables:    {len(active)}")
        print(f"  Backup tables:    {len(backup)}")
        print(f"  Tables in code:   {len(code_tables)}")


if __name__ == '__main__':
    main()
