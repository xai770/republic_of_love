#!/usr/bin/env python3
"""
QA Column Coverage Report

Shows data density for every column in the postings table.
Identifies gaps, anomalies, and data quality issues.

Usage:
    python3 tools/qa_column_report.py              # Full report
    python3 tools/qa_column_report.py --json       # JSON for API
    python3 tools/qa_column_report.py --html       # HTML report
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any

sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection


def get_column_stats() -> list[dict]:
    """Get fill rate and stats for each column in postings."""
    
    columns_to_check = [
        # Core identity
        ('posting_id', 'integer', 'Primary key'),
        ('posting_name', 'text', 'Display name'),
        ('job_title', 'text', 'Job title from source'),
        ('external_job_id', 'text', 'Source ID'),
        ('external_url', 'text', 'Link to original'),
        ('source', 'varchar', 'Data source (aa, db)'),
        
        # Content
        ('job_description', 'text', 'Full job description'),
        ('extracted_summary', 'text', 'LLM-generated summary'),
        
        # Location
        ('location_city', 'text', 'City'),
        ('location_state', 'varchar', 'German state'),
        ('location_country', 'text', 'Country'),
        ('location_postal_code', 'varchar', 'Postal code'),
        
        # Classification
        ('beruf', 'text', 'Raw profession from AA'),
        ('berufenet_id', 'integer', 'Berufenet FK'),
        ('berufenet_name', 'text', 'Canonical profession name'),
        ('qualification_level', 'integer', 'KLDB level 1-4'),
        
        # Status
        ('enabled', 'boolean', 'Active posting'),
        ('invalidated', 'boolean', 'Marked as dead'),
        ('posting_status', 'text', 'Status string'),
        
        # Timestamps
        ('first_seen_at', 'timestamp', 'When first fetched'),
        ('last_seen_at', 'timestamp', 'Last confirmed live'),
        ('updated_at', 'timestamp', 'Last modified'),
    ]
    
    results = []
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get total count
        cur.execute("SELECT COUNT(*) as cnt FROM postings")
        total = cur.fetchone()['cnt']
        
        for col_name, col_type, description in columns_to_check:
            try:
                # Count non-null
                if col_type == 'text':
                    # For text, also check empty strings
                    cur.execute(f"""
                        SELECT 
                            COUNT(*) FILTER (WHERE {col_name} IS NOT NULL AND {col_name} != '') as filled,
                            COUNT(DISTINCT {col_name}) as distinct_vals
                        FROM postings
                    """)
                else:
                    cur.execute(f"""
                        SELECT 
                            COUNT(*) FILTER (WHERE {col_name} IS NOT NULL) as filled,
                            COUNT(DISTINCT {col_name}) as distinct_vals
                        FROM postings
                    """)
                
                row = cur.fetchone()
                filled = row['filled']
                distinct = row['distinct_vals']
                
                fill_pct = round(100 * filled / total, 1) if total > 0 else 0
                
                # Determine status
                if fill_pct >= 95:
                    status = '✅'
                elif fill_pct >= 70:
                    status = '🟡'
                elif fill_pct >= 30:
                    status = '🟠'
                else:
                    status = '🔴'
                
                results.append({
                    'column': col_name,
                    'type': col_type,
                    'description': description,
                    'filled': filled,
                    'missing': total - filled,
                    'fill_pct': fill_pct,
                    'distinct': distinct,
                    'status': status,
                })
                
            except Exception as e:
                results.append({
                    'column': col_name,
                    'type': col_type,
                    'description': description,
                    'error': str(e),
                    'status': '❌',
                })
        
        # Add embedding coverage
        # Embeddings are content-addressed by text, not posting_id
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM postings_for_matching p
            WHERE EXISTS (
                SELECT 1 FROM embeddings e WHERE e.text = p.match_text
            )
        """)
        embedded = cur.fetchone()['cnt']
        
        results.append({
            'column': 'embedding (content)',
            'type': 'match',
            'description': 'Has embedding vector',
            'filled': embedded,
            'missing': total - embedded,
            'fill_pct': round(100 * embedded / total, 1) if total > 0 else 0,
            'distinct': embedded,
            'status': '✅' if embedded >= total * 0.95 else '🟡',
        })
        
    return results, total


def get_beruf_gaps() -> list[dict]:
    """Find unmatched beruf values (no berufenet_id)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT beruf, COUNT(*) as cnt
            FROM postings
            WHERE beruf IS NOT NULL 
              AND berufenet_id IS NULL
            GROUP BY beruf
            ORDER BY cnt DESC
            LIMIT 20
        """)
        return [{'beruf': r['beruf'], 'count': r['cnt']} for r in cur.fetchall()]


def render_ascii(stats: list[dict], total: int, beruf_gaps: list[dict]) -> str:
    """Render ASCII report."""
    lines = []
    lines.append("=" * 80)
    lines.append("📋 QA COLUMN COVERAGE REPORT")
    lines.append(f"   Total postings: {total:,}")
    lines.append(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"{'Column':<25} {'Type':<10} {'Filled':>10} {'Fill %':>8} {'Status':<3}")
    lines.append("-" * 80)
    
    for s in stats:
        if 'error' in s:
            lines.append(f"{s['column']:<25} {s['type']:<10} {'ERROR':>10} {'-':>8} {s['status']}")
        else:
            lines.append(f"{s['column']:<25} {s['type']:<10} {s['filled']:>10,} {s['fill_pct']:>7}% {s['status']}")
    
    # Beruf gaps section
    if beruf_gaps:
        lines.append("")
        lines.append("=" * 80)
        lines.append("🔍 TOP UNMATCHED PROFESSIONS (need synonyms)")
        lines.append("=" * 80)
        lines.append("")
        for gap in beruf_gaps[:10]:
            lines.append(f"  {gap['count']:>6,}  {gap['beruf']}")
    
    # Summary
    lines.append("")
    lines.append("-" * 80)
    critical = [s for s in stats if s.get('status') in ('🔴', '🟠')]
    if critical:
        lines.append("⚠️  NEEDS ATTENTION:")
        for s in critical:
            lines.append(f"   - {s['column']}: {s.get('fill_pct', 0)}% ({s.get('missing', '?'):,} missing)")
    else:
        lines.append("✅ All columns have good coverage!")
    
    return '\n'.join(lines)


def render_html(stats: list[dict], total: int, beruf_gaps: list[dict]) -> str:
    """Render HTML report."""
    rows_html = []
    for s in stats:
        status_color = {
            '✅': '#4caf50',
            '🟡': '#ff9800',
            '🟠': '#ff5722',
            '🔴': '#f44336',
            '❌': '#9e9e9e',
        }.get(s['status'], '#666')
        
        if 'error' in s:
            rows_html.append(f'''
            <tr>
                <td>{s['column']}</td>
                <td>{s['type']}</td>
                <td>{s['description']}</td>
                <td colspan="3" style="color: red;">ERROR: {s['error']}</td>
            </tr>''')
        else:
            bar_width = s['fill_pct']
            rows_html.append(f'''
            <tr>
                <td><strong>{s['column']}</strong></td>
                <td><code>{s['type']}</code></td>
                <td>{s['description']}</td>
                <td>{s['filled']:,}</td>
                <td>
                    <div class="bar-bg">
                        <div class="bar" style="width: {bar_width}%; background: {status_color};"></div>
                    </div>
                </td>
                <td>{s['fill_pct']}%</td>
            </tr>''')
    
    gaps_html = ''.join([
        f'<tr><td>{g["count"]:,}</td><td>{g["beruf"]}</td></tr>'
        for g in beruf_gaps[:15]
    ])
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>QA Column Report - talent.yoga</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 1000px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
        h1, h2 {{ color: #333; }}
        table {{ width: 100%; border-collapse: collapse; background: white; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #667eea; color: white; }}
        code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
        .bar-bg {{ width: 100px; height: 12px; background: #eee; border-radius: 6px; }}
        .bar {{ height: 100%; border-radius: 6px; }}
        .timestamp {{ color: #999; font-size: 12px; margin-top: 20px; text-align: center; }}
        .section {{ margin-top: 40px; }}
    </style>
</head>
<body>
    <h1>📋 QA Column Coverage Report</h1>
    <p>Total postings: <strong>{total:,}</strong></p>
    
    <table>
        <tr>
            <th>Column</th>
            <th>Type</th>
            <th>Description</th>
            <th>Filled</th>
            <th>Coverage</th>
            <th>%</th>
        </tr>
        {''.join(rows_html)}
    </table>
    
    <div class="section">
        <h2>🔍 Top Unmatched Professions</h2>
        <p>These need synonym mappings in <code>berufenet_synonyms</code>:</p>
        <table>
            <tr><th>Count</th><th>Profession (beruf)</th></tr>
            {gaps_html}
        </table>
    </div>
    
    <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description='QA Column Coverage Report')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--html', action='store_true', help='Output HTML')
    parser.add_argument('-o', '--output', help='Write to file')
    args = parser.parse_args()
    
    stats, total = get_column_stats()
    beruf_gaps = get_beruf_gaps()
    
    if args.json:
        output = json.dumps({
            'generated_at': datetime.now().isoformat(),
            'total_postings': total,
            'columns': stats,
            'unmatched_professions': beruf_gaps,
        }, indent=2)
    elif args.html:
        output = render_html(stats, total, beruf_gaps)
    else:
        output = render_ascii(stats, total, beruf_gaps)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
