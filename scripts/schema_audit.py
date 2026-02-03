#!/usr/bin/env python3
"""
Schema Audit Tool - Analyze column usage and health across tables

Usage:
    python scripts/schema_audit.py                    # Audit all tables
    python scripts/schema_audit.py --table postings   # Audit specific table
    python scripts/schema_audit.py --dead             # Show only dead columns (< 5% fill)
    python scripts/schema_audit.py --recommend        # Show drop recommendations

Author: Arden
Date: 2026-02-03
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection
import psycopg2.extras


# Tables to audit (core data tables, not system tables)
AUDIT_TABLES = [
    'postings',
    'profiles', 
    'skills',
    'profile_skills',
    'embeddings',
    'tickets',
]

# Columns that are intentionally sparse (don't flag as dead)
SPARSE_BY_DESIGN = {
    'postings': [
        'invalidated_at',      # Only set when invalidated
        'invalidated_reason',  # Only set when invalidated
        'extracted_summary',   # Only for Deutsche Bank
    ],
    'profiles': [
        'deleted_at',          # Soft delete marker
    ],
}

# Fill rate thresholds
THRESHOLD_DEAD = 5       # Below this = probably dead
THRESHOLD_SPARSE = 50    # Below this = consider JSONB instead


def audit_table(conn, table_name: str, show_all: bool = True) -> list:
    """Audit a single table's column fill rates."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get columns
    cur.execute('''
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    ''', (table_name,))
    columns = cur.fetchall()
    
    if not columns:
        print(f"  ⚠️  Table '{table_name}' not found")
        return []
    
    # Get row count
    cur.execute(f'SELECT COUNT(*) as cnt FROM {table_name}')
    total = cur.fetchone()['cnt']
    
    if total == 0:
        print(f"  ⚠️  Table '{table_name}' is empty")
        return []
    
    results = []
    sparse_whitelist = SPARSE_BY_DESIGN.get(table_name, [])
    
    for col in columns:
        col_name = col['column_name']
        try:
            cur.execute(f'''
                SELECT 
                    COUNT(*) FILTER (WHERE "{col_name}" IS NOT NULL) as filled,
                    COUNT(*) FILTER (WHERE "{col_name}" IS NOT NULL 
                                     AND "{col_name}"::text != ''
                                     AND "{col_name}"::text != '{{}}') as meaningful
                FROM {table_name}
            ''')
            row = cur.fetchone()
            fill_pct = (row['filled'] / total * 100)
            meaningful_pct = (row['meaningful'] / total * 100)
            
            # Determine status
            is_whitelisted = col_name in sparse_whitelist
            if fill_pct < THRESHOLD_DEAD and not is_whitelisted:
                status = 'DEAD'
                indicator = '🔴'
            elif fill_pct < THRESHOLD_SPARSE:
                status = 'SPARSE'
                indicator = '🟡'
            else:
                status = 'HEALTHY'
                indicator = '🟢'
            
            if is_whitelisted:
                indicator = '⚪'  # Whitelisted - intentionally sparse
                status = 'SPARSE_OK'
            
            results.append({
                'column': col_name,
                'type': col['data_type'],
                'fill_pct': fill_pct,
                'meaningful_pct': meaningful_pct,
                'status': status,
                'indicator': indicator,
                'whitelisted': is_whitelisted,
            })
        except Exception as e:
            results.append({
                'column': col_name,
                'type': col['data_type'],
                'fill_pct': -1,
                'meaningful_pct': -1,
                'status': 'ERROR',
                'indicator': '❓',
                'error': str(e),
            })
    
    return results


def print_table_report(table_name: str, results: list, dead_only: bool = False):
    """Print formatted report for a table."""
    # Sort by fill rate
    results.sort(key=lambda x: x['fill_pct'])
    
    if dead_only:
        results = [r for r in results if r['status'] == 'DEAD']
        if not results:
            return
    
    print(f"\n{'='*75}")
    print(f"  {table_name.upper()} ({len(results)} columns)")
    print(f"{'='*75}")
    print(f"{'Status':<8} {'Column':<30} {'Fill %':>8} {'Meaningful %':>12} {'Type':<15}")
    print(f"{'-'*75}")
    
    for r in results:
        print(f"{r['indicator']:<8} {r['column']:<30} {r['fill_pct']:>7.1f}% {r['meaningful_pct']:>11.1f}% {r['type']:<15}")


def generate_recommendations(all_results: dict) -> list:
    """Generate actionable recommendations."""
    recommendations = []
    
    for table, results in all_results.items():
        for r in results:
            if r['status'] == 'DEAD':
                recommendations.append({
                    'action': 'DROP',
                    'priority': 'HIGH',
                    'table': table,
                    'column': r['column'],
                    'fill_pct': r['fill_pct'],
                    'reason': f"Column is {r['fill_pct']:.1f}% filled - appears unused",
                })
            elif r['status'] == 'SPARSE' and r['fill_pct'] < 20:
                recommendations.append({
                    'action': 'REVIEW',
                    'priority': 'MEDIUM',
                    'table': table,
                    'column': r['column'],
                    'fill_pct': r['fill_pct'],
                    'reason': f"Only {r['fill_pct']:.1f}% filled - consider JSONB or verify intent",
                })
    
    return recommendations


def print_recommendations(recommendations: list):
    """Print actionable recommendations."""
    if not recommendations:
        print("\n✅ No recommendations - schema looks healthy!")
        return
    
    # Sort by priority, then fill rate
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    recommendations.sort(key=lambda x: (priority_order[x['priority']], x['fill_pct']))
    
    print(f"\n{'='*80}")
    print("  RECOMMENDATIONS")
    print(f"{'='*80}")
    
    # Group by action
    drops = [r for r in recommendations if r['action'] == 'DROP']
    reviews = [r for r in recommendations if r['action'] == 'REVIEW']
    
    if drops:
        print(f"\n🗑️  CANDIDATES FOR DROP ({len(drops)} columns):")
        print(f"   These columns are <{THRESHOLD_DEAD}% filled and likely unused.\n")
        for r in drops:
            print(f"   ALTER TABLE {r['table']} DROP COLUMN {r['column']};")
            print(f"   -- {r['reason']}\n")
    
    if reviews:
        print(f"\n🔍 REVIEW NEEDED ({len(reviews)} columns):")
        print(f"   These columns are sparsely populated. Verify if intentional.\n")
        for r in reviews:
            print(f"   • {r['table']}.{r['column']} ({r['fill_pct']:.1f}%)")
            print(f"     {r['reason']}\n")


def main():
    parser = argparse.ArgumentParser(description='Audit database schema for column health')
    parser.add_argument('--table', '-t', help='Audit specific table only')
    parser.add_argument('--dead', '-d', action='store_true', help='Show only dead columns (<5% fill)')
    parser.add_argument('--recommend', '-r', action='store_true', help='Show drop/review recommendations')
    parser.add_argument('--all', '-a', action='store_true', help='Show all columns (including healthy)')
    args = parser.parse_args()
    
    print(f"Schema Audit - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Thresholds: DEAD < {THRESHOLD_DEAD}%, SPARSE < {THRESHOLD_SPARSE}%")
    
    with get_connection() as conn:
        tables = [args.table] if args.table else AUDIT_TABLES
        all_results = {}
        
        for table in tables:
            results = audit_table(conn, table)
            if results:
                all_results[table] = results
                if not args.recommend:  # Don't print table details if showing recommendations
                    print_table_report(table, results, dead_only=args.dead)
        
        if args.recommend:
            recommendations = generate_recommendations(all_results)
            print_recommendations(recommendations)
        
        # Summary
        total_dead = sum(1 for r in sum(all_results.values(), []) if r['status'] == 'DEAD')
        total_cols = sum(len(r) for r in all_results.values())
        print(f"\n📊 Summary: {total_dead} dead columns out of {total_cols} total ({total_dead/total_cols*100:.1f}%)")


if __name__ == '__main__':
    main()
