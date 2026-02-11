#!/usr/bin/env python3
"""
Table Health Analyzer
=====================

Analyzes each column in a table to determine if it contains useful data.

Reports:
- NULL percentage
- Unique value count
- Most common values
- Data entropy (is it always the same?)
- Recommendation: KEEP, REMOVE, or CONSOLIDATE

This helps identify:
- Dead columns (100% NULL)
- Useless columns (100% same value)
- Redundant columns (data already in JSON)
- Low-cardinality columns (only 2-3 values)

Author: Arden & xai
Date: November 7, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
from collections import Counter

def analyze_column(cur, table_name: str, column_name: str, total_rows: int) -> dict:
    """
    Analyze a single column and return statistics.
    """
    stats = {
        'column_name': column_name,
        'total_rows': total_rows,
        'null_count': 0,
        'null_pct': 0.0,
        'unique_count': 0,
        'most_common': [],
        'recommendation': 'UNKNOWN',
        'reason': ''
    }
    
    # Get NULL count
    cur.execute(f"""
        SELECT COUNT(*) as null_count
        FROM {table_name}
        WHERE {column_name} IS NULL
    """)
    stats['null_count'] = cur.fetchone()['null_count']
    stats['null_pct'] = (stats['null_count'] / total_rows * 100) if total_rows > 0 else 0
    
    # Get unique value count
    cur.execute(f"""
        SELECT COUNT(DISTINCT {column_name}) as unique_count
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
    """)
    stats['unique_count'] = cur.fetchone()['unique_count']
    
    # Get most common values (limit to top 5)
    cur.execute(f"""
        SELECT {column_name} as value, COUNT(*) as count
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
        GROUP BY {column_name}
        ORDER BY count DESC
        LIMIT 5
    """)
    stats['most_common'] = [(row['value'], row['count']) for row in cur.fetchall()]
    
    # Calculate filled rows
    filled_count = total_rows - stats['null_count']
    filled_pct = (filled_count / total_rows * 100) if total_rows > 0 else 0
    
    # Make recommendation
    if stats['null_pct'] == 100:
        stats['recommendation'] = '🗑️  REMOVE'
        stats['reason'] = 'Always NULL (0% filled)'
    
    elif stats['null_pct'] > 95:
        stats['recommendation'] = '⚠️  REMOVE'
        stats['reason'] = f'Nearly empty ({filled_pct:.1f}% filled)'
    
    elif stats['unique_count'] == 0:
        stats['recommendation'] = '🗑️  REMOVE'
        stats['reason'] = 'No values'
    
    elif stats['unique_count'] == 1 and filled_count > 0:
        # All non-NULL values are the same
        same_value = stats['most_common'][0][0] if stats['most_common'] else 'unknown'
        stats['recommendation'] = '🗑️  REMOVE'
        stats['reason'] = f'Always same value: "{same_value}"'
    
    elif stats['unique_count'] == filled_count and filled_count > 10:
        # Every row has unique value (likely ID or unique field)
        stats['recommendation'] = '✅ KEEP'
        stats['reason'] = f'Unique identifier ({stats["unique_count"]} unique values)'
    
    elif stats['unique_count'] <= 3 and filled_pct > 50:
        # Very low cardinality
        values = ', '.join([f'"{v[0]}"' for v in stats['most_common'][:3]])
        stats['recommendation'] = '🔄 CONSOLIDATE'
        stats['reason'] = f'Low cardinality: {values}'
    
    elif filled_pct < 30:
        stats['recommendation'] = '⚠️  REMOVE'
        stats['reason'] = f'Mostly empty ({filled_pct:.1f}% filled)'
    
    else:
        stats['recommendation'] = '✅ KEEP'
        stats['reason'] = f'{stats["unique_count"]} unique, {filled_pct:.1f}% filled'
    
    return stats


def analyze_table(table_name: str, filter_clause: str = None):
    """
    Analyze all columns in a table.
    """
    print()
    print("=" * 90)
    print(f"📊 TABLE HEALTH ANALYZER: {table_name}")
    print("=" * 90)
    print()
    
    conn = psycopg2.connect(
        dbname='turing',
        user='base_admin',
        password=os.getenv('DB_PASSWORD', ''),
        host='localhost',
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()
    
    # Get total row count
    where_clause = f"WHERE {filter_clause}" if filter_clause else ""
    cur.execute(f"SELECT COUNT(*) as total FROM {table_name} {where_clause}")
    total_rows = cur.fetchone()['total']
    
    print(f"📋 Analyzing {total_rows:,} rows")
    if filter_clause:
        print(f"🔍 Filter: {filter_clause}")
    print()
    
    # Get all columns
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    
    columns = cur.fetchall()
    
    print(f"Found {len(columns)} columns\n")
    print("Analyzing columns...")
    print()
    
    results = []
    for col in columns:
        col_name = col['column_name']
        col_type = col['data_type']
        
        print(f"  Analyzing: {col_name} ({col_type})...")
        
        try:
            stats = analyze_column(cur, table_name, col_name, total_rows)
            stats['data_type'] = col_type
            results.append(stats)
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
            continue
    
    conn.close()
    
    # Print results
    print()
    print("=" * 90)
    print("📊 ANALYSIS RESULTS")
    print("=" * 90)
    print()
    
    # Group by recommendation
    remove_cols = [r for r in results if '🗑️' in r['recommendation']]
    warning_cols = [r for r in results if '⚠️' in r['recommendation']]
    consolidate_cols = [r for r in results if '🔄' in r['recommendation']]
    keep_cols = [r for r in results if '✅' in r['recommendation']]
    
    # Print summary
    print(f"✅ KEEP: {len(keep_cols)} columns")
    print(f"🗑️  REMOVE: {len(remove_cols)} columns")
    print(f"⚠️  WARNING: {len(warning_cols)} columns")
    print(f"🔄 CONSOLIDATE: {len(consolidate_cols)} columns")
    print()
    
    # Print details for columns to remove
    if remove_cols:
        print("=" * 90)
        print("🗑️  COLUMNS TO REMOVE")
        print("=" * 90)
        for col in remove_cols:
            print(f"\n📍 {col['column_name']} ({col['data_type']})")
            print(f"   Reason: {col['reason']}")
            print(f"   NULL: {col['null_pct']:.1f}%")
            if col['most_common']:
                print(f"   Most common: {col['most_common'][:3]}")
    
    # Print warning columns
    if warning_cols:
        print("\n" + "=" * 90)
        print("⚠️  WARNING COLUMNS (Consider Removing)")
        print("=" * 90)
        for col in warning_cols:
            print(f"\n📍 {col['column_name']} ({col['data_type']})")
            print(f"   Reason: {col['reason']}")
            print(f"   NULL: {col['null_pct']:.1f}% | Unique: {col['unique_count']}")
            if col['most_common']:
                print(f"   Most common: {col['most_common'][:3]}")
    
    # Print consolidate columns
    if consolidate_cols:
        print("\n" + "=" * 90)
        print("🔄 COLUMNS TO CONSOLIDATE (Low Cardinality)")
        print("=" * 90)
        for col in consolidate_cols:
            print(f"\n📍 {col['column_name']} ({col['data_type']})")
            print(f"   Reason: {col['reason']}")
            print(f"   NULL: {col['null_pct']:.1f}% | Unique values: {col['unique_count']}")
            print(f"   Values: {col['most_common']}")
    
    # Print keep columns
    if keep_cols:
        print("\n" + "=" * 90)
        print("✅ COLUMNS TO KEEP (Useful Data)")
        print("=" * 90)
        for col in keep_cols:
            print(f"\n📍 {col['column_name']} ({col['data_type']})")
            print(f"   {col['reason']}")
            print(f"   NULL: {col['null_pct']:.1f}% | Unique: {col['unique_count']:,}")
            if col['most_common'] and len(col['most_common']) <= 5:
                print(f"   Top values: {col['most_common']}")
    
    # Generate SQL to remove dead columns
    print("\n" + "=" * 90)
    print("🔧 SUGGESTED SQL")
    print("=" * 90)
    print()
    
    if remove_cols or warning_cols:
        print("-- Remove dead/useless columns:")
        print(f"ALTER TABLE {table_name}")
        cols_to_drop = remove_cols + [c for c in warning_cols if c['null_pct'] > 90]
        for i, col in enumerate(cols_to_drop):
            comma = "," if i < len(cols_to_drop) - 1 else ";"
            print(f"  DROP COLUMN {col['column_name']}{comma}  -- {col['reason']}")
        print()
    
    if consolidate_cols:
        print("-- Consider consolidating low-cardinality columns into ENUM or lookup table")
        for col in consolidate_cols:
            print(f"-- {col['column_name']}: {col['unique_count']} values")
    
    print()
    print("✨ Analysis complete!")
    print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze table column health')
    parser.add_argument('table', help='Table name to analyze')
    parser.add_argument('--filter', help='WHERE clause filter (optional)', default=None)
    
    args = parser.parse_args()
    
    analyze_table(args.table, args.filter)


if __name__ == '__main__':
    main()
