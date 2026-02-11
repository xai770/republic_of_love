#!/usr/bin/env python3
"""
bi_dashboard.py - Business Intelligence Dashboard for talent.yoga

Generates a comprehensive overview of platform data including:
- Posting volumes by source
- Berufenet coverage & qualification levels  
- Embedding coverage
- IHL (legitimacy) scores
- Geographic distribution
- User activity

Usage:
    python3 tools/bi_dashboard.py              # Print to terminal
    python3 tools/bi_dashboard.py --html       # Generate HTML report
    python3 tools/bi_dashboard.py --json       # Output JSON for API

Author: Arden
Date: 2026-02-05
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any

import psycopg2.extras

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection_raw, return_connection


def get_overview_stats(conn) -> Dict[str, Any]:
    """Get high-level platform statistics."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            (SELECT COUNT(*) FROM postings) AS total_postings,
            (SELECT COUNT(*) FROM postings WHERE source = 'arbeitsagentur') AS aa_postings,
            (SELECT COUNT(*) FROM postings WHERE source = 'deutsche_bank') AS db_postings,
            (SELECT COUNT(*) FROM postings WHERE extracted_summary IS NOT NULL) AS with_summary,
            (SELECT COUNT(*) FROM postings WHERE job_description IS NOT NULL) AS with_description,
            (SELECT COUNT(*) FROM embeddings) AS total_embeddings,
            (SELECT COUNT(*) FROM owl WHERE owl_type = 'berufenet') AS berufenet_professions,
            (SELECT COUNT(*) FROM owl_names n JOIN owl o ON n.owl_id = o.owl_id WHERE o.owl_type = 'berufenet') AS owl_berufenet_names,
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM user_posting_interactions) AS interactions,
            (SELECT COUNT(*) FROM yogi_messages) AS messages,
            (SELECT COUNT(*) FROM yogi_newsletters) AS newsletters
    """)
    row = cur.fetchone()
    return dict(row)


def get_qualification_distribution(conn) -> list:
    """Get posting distribution by qualification level (from actor-written column)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            qualification_level,
            CASE qualification_level
                WHEN 1 THEN 'Helfer (unskilled)'
                WHEN 2 THEN 'Fachkraft (skilled)'
                WHEN 3 THEN 'Spezialist (specialist)'
                WHEN 4 THEN 'Experte (expert)'
            END AS level_name,
            COUNT(*) AS posting_count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
        FROM postings
        WHERE qualification_level IS NOT NULL
        GROUP BY qualification_level
        ORDER BY qualification_level
    """)
    return [
        {'level': row['qualification_level'], 'name': row['level_name'], 'count': row['posting_count'], 'pct': float(row['pct'])}
        for row in cur.fetchall()
    ]


def get_berufenet_coverage(conn) -> Dict[str, Any]:
    """Get berufenet matching statistics (using actor-written berufenet_id)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Total postings with job_title
    cur.execute("SELECT COUNT(*) AS cnt FROM postings WHERE job_title IS NOT NULL")
    total = cur.fetchone()['cnt']
    
    # Classified (has berufenet_id)
    cur.execute("SELECT COUNT(*) AS cnt FROM postings WHERE berufenet_id IS NOT NULL")
    classified = cur.fetchone()['cnt']
    
    # With domain_gate
    cur.execute("SELECT COUNT(*) AS cnt FROM postings WHERE domain_gate IS NOT NULL")
    with_domain = cur.fetchone()['cnt']
    
    # Classification breakdown
    cur.execute("""
        SELECT berufenet_verified, COUNT(*) AS cnt
        FROM postings
        WHERE job_title IS NOT NULL
        GROUP BY berufenet_verified
        ORDER BY cnt DESC
    """)
    breakdown = {(row['berufenet_verified'] or 'unprocessed'): row['cnt'] for row in cur.fetchall()}
    
    return {
        'total': total,
        'classified': classified,
        'with_domain': with_domain,
        'unclassified': total - classified,
        'classify_rate': round(100.0 * classified / total, 1) if total > 0 else 0,
        'domain_rate': round(100.0 * with_domain / total, 1) if total > 0 else 0,
        'breakdown': breakdown
    }


def get_top_unmatched_berufe(conn, limit: int = 20) -> list:
    """Get top unclassified job titles that need berufenet matching."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT job_title, COUNT(*) AS cnt
        FROM postings
        WHERE job_title IS NOT NULL
          AND berufenet_id IS NULL
          AND (berufenet_verified IS NULL OR berufenet_verified IN ('null', 'pending_llm'))
        GROUP BY job_title
        ORDER BY cnt DESC
        LIMIT %s
    """, (limit,))
    return [{'beruf': row['job_title'], 'count': row['cnt']} for row in cur.fetchall()]


def get_ihl_distribution(conn) -> list:
    """Get IHL (legitimacy) score distribution."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            CASE 
                WHEN ihl_score IS NULL THEN 'not_scored'
                WHEN ihl_score <= 3 THEN 'genuine'
                WHEN ihl_score <= 6 THEN 'borderline'
                WHEN ihl_score <= 9 THEN 'suspicious'
                ELSE 'likely_fake'
            END AS category,
            COUNT(*) AS count
        FROM postings
        GROUP BY 1
        ORDER BY 1
    """)
    return [{'category': row['category'], 'count': row['count']} for row in cur.fetchall()]


def get_location_distribution(conn) -> list:
    """Get postings by German state."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            COALESCE(NULLIF(location_state, ''), 'Unknown') AS state,
            COUNT(*) AS postings
        FROM postings
        WHERE source = 'arbeitsagentur'
        GROUP BY 1
        ORDER BY COUNT(*) DESC
    """)
    return [{'state': row['state'], 'count': row['postings']} for row in cur.fetchall()]


def get_top_job_categories(conn, limit: int = 15) -> list:
    """Get top job categories by volume (using actor-written berufenet_name)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            berufenet_name,
            qualification_level,
            COUNT(*) AS postings
        FROM postings
        WHERE berufenet_name IS NOT NULL
        GROUP BY berufenet_name, qualification_level
        ORDER BY COUNT(*) DESC
        LIMIT %s
    """, (limit,))
    return [
        {'name': row['berufenet_name'], 'qualification_level': row['qualification_level'], 'count': row['postings']}
        for row in cur.fetchall()
    ]


def get_recent_activity(conn, days: int = 7) -> list:
    """Get posting activity over recent days."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 
            DATE(first_seen_at) AS date,
            source,
            COUNT(*) AS new_postings
        FROM postings
        WHERE first_seen_at >= NOW() - INTERVAL '%s days'
        GROUP BY DATE(first_seen_at), source
        ORDER BY date DESC
    """, (days,))
    return [
        {'date': str(row['date']), 'source': row['source'], 'count': row['new_postings']}
        for row in cur.fetchall()
    ]


def collect_all_metrics() -> Dict[str, Any]:
    """Collect all BI metrics."""
    conn = get_connection_raw()
    try:
        return {
            'generated_at': datetime.now().isoformat(),
            'overview': get_overview_stats(conn),
            'qualification_distribution': get_qualification_distribution(conn),
            'berufenet_coverage': get_berufenet_coverage(conn),
            'top_unmatched_berufe': get_top_unmatched_berufe(conn, 20),
            'ihl_distribution': get_ihl_distribution(conn),
            'location_distribution': get_location_distribution(conn),
            'top_job_categories': get_top_job_categories(conn, 15),
            'recent_activity': get_recent_activity(conn, 7)
        }
    finally:
        return_connection(conn)


def print_terminal_dashboard(data: Dict[str, Any]):
    """Print a nice ASCII dashboard."""
    o = data['overview']
    
    print("\n" + "=" * 70)
    print("  🧘 TALENT.YOGA BI DASHBOARD")
    print(f"  Generated: {data['generated_at'][:19]}")
    print("=" * 70)
    
    # Overview
    print("\n📊 OVERVIEW")
    print("-" * 40)
    print(f"  Total Postings:     {o['total_postings']:,}")
    print(f"    ├─ Arbeitsagentur: {o['aa_postings']:,}")
    print(f"    └─ Deutsche Bank:  {o['db_postings']:,}")
    print(f"  With Description:   {o['with_description']:,}")
    print(f"  With Summary:       {o['with_summary']:,}")
    print(f"  Total Embeddings:   {o['total_embeddings']:,}")
    
    # Berufenet
    bc = data['berufenet_coverage']
    print("\n🎯 BERUFENET COVERAGE")
    print("-" * 40)
    print(f"  Classified (has berufenet_id): {bc['classified']:,} / {bc['total']:,} ({bc['classify_rate']}%)")
    print(f"  With domain_gate:              {bc['with_domain']:,} ({bc['domain_rate']}%)")
    print(f"  Unclassified:                  {bc['unclassified']:,}")
    print(f"  OWL berufenet names:           {o['owl_berufenet_names']:,}")
    if bc.get('breakdown'):
        print("  Classification breakdown:")
        for status, cnt in sorted(bc['breakdown'].items(), key=lambda x: -x[1]):
            print(f"    {status:15} {cnt:>7,}")
    
    # Qualification levels
    print("\n📈 QUALIFICATION LEVELS (matched postings)")
    print("-" * 40)
    emojis = {1: '🟢', 2: '🔵', 3: '🟡', 4: '🔴'}
    for q in data['qualification_distribution']:
        bar = '█' * int(q['pct'] / 2)
        print(f"  {emojis.get(q['level'], '⚪')} {q['name']:<25} {q['count']:>6,} ({q['pct']:>5.1f}%) {bar}")
    
    # Top job categories
    print("\n🏆 TOP JOB CATEGORIES")
    print("-" * 40)
    for i, cat in enumerate(data['top_job_categories'][:10], 1):
        emoji = emojis.get(cat['qualification_level'], '⚪')
        name = cat['name'][:40] + '...' if len(cat['name']) > 40 else cat['name']
        print(f"  {i:>2}. {emoji} {name:<45} {cat['count']:>5,}")
    
    # Top unmatched (need classification)
    print("\n⚠️  TOP UNCLASSIFIED (need berufenet match)")
    print("-" * 40)
    for b in data['top_unmatched_berufe'][:10]:
        name = b['beruf'][:45] + '...' if len(b['beruf']) > 45 else b['beruf']
        print(f"  {name:<50} {b['count']:>5,}")
    
    # Location
    print("\n🗺️  BY GERMAN STATE")
    print("-" * 40)
    for loc in data['location_distribution'][:10]:
        state = loc['state'][:25]
        print(f"  {state:<25} {loc['count']:>6,}")
    
    # Users & Activity
    print("\n👥 USERS & ACTIVITY")
    print("-" * 40)
    print(f"  Users:            {o['total_users']}")
    print(f"  Interactions:     {o['interactions']}")
    print(f"  Messages:         {o['messages']}")
    print(f"  Newsletters:      {o['newsletters']}")
    
    # IHL
    print("\n🔍 IHL (Job Legitimacy)")
    print("-" * 40)
    for ihl in data['ihl_distribution']:
        labels = {
            'genuine': '🟢 Genuine',
            'borderline': '🟡 Borderline', 
            'suspicious': '🟠 Suspicious',
            'likely_fake': '🔴 Likely Fake',
            'not_scored': '⚪ Not Scored'
        }
        print(f"  {labels.get(ihl['category'], ihl['category']):<20} {ihl['count']:>6,}")
    
    print("\n" + "=" * 70)


def generate_html_dashboard(data: Dict[str, Any]) -> str:
    """Generate HTML dashboard."""
    o = data['overview']
    bc = data['berufenet_coverage']
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>talent.yoga BI Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #2d3748; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; 
                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #4a5568; }}
        .metric-label {{ color: #718096; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f7fafc; }}
        .bar {{ background: #4299e1; height: 20px; border-radius: 4px; }}
        .timestamp {{ color: #a0aec0; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>🧘 talent.yoga BI Dashboard</h1>
    <p class="timestamp">Generated: {data['generated_at'][:19]}</p>
    
    <div class="card">
        <h2>📊 Overview</h2>
        <div class="metric">
            <div class="metric-value">{o['total_postings']:,}</div>
            <div class="metric-label">Total Postings</div>
        </div>
        <div class="metric">
            <div class="metric-value">{o['total_embeddings']:,}</div>
            <div class="metric-label">Embeddings</div>
        </div>
        <div class="metric">
            <div class="metric-value">{o['owl_berufenet_names']:,}</div>
            <div class="metric-label">OWL Berufenet Names</div>
        </div>
        <div class="metric">
            <div class="metric-value">{o['total_users']}</div>
            <div class="metric-label">Users</div>
        </div>
    </div>
    
    <div class="card">
        <h2>🎯 Berufenet Coverage</h2>
        <table>
            <tr><td>Classified (has berufenet_id)</td><td><strong>{bc['classified']:,}</strong> / {bc['total']:,} ({bc['classify_rate']}%)</td></tr>
            <tr><td>With domain_gate</td><td><strong>{bc['with_domain']:,}</strong> ({bc['domain_rate']}%)</td></tr>
            <tr><td>Unclassified</td><td><strong>{bc['unclassified']:,}</strong></td></tr>
        </table>
    </div>
    
    <div class="card">
        <h2>📈 Qualification Levels</h2>
        <table>
            <tr><th>Level</th><th>Count</th><th>Distribution</th></tr>
"""
    
    emojis = {1: '🟢', 2: '🔵', 3: '🟡', 4: '🔴'}
    for q in data['qualification_distribution']:
        html += f"""
            <tr>
                <td>{emojis.get(q['level'], '⚪')} {q['name']}</td>
                <td>{q['count']:,}</td>
                <td><div class="bar" style="width: {q['pct']}%"></div> {q['pct']}%</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
    
    <div class="card">
        <h2>🏆 Top Job Categories</h2>
        <table>
            <tr><th>#</th><th>Category</th><th>Level</th><th>Postings</th></tr>
"""
    
    for i, cat in enumerate(data['top_job_categories'][:15], 1):
        html += f"""
            <tr>
                <td>{i}</td>
                <td>{cat['name']}</td>
                <td>{emojis.get(cat['qualification_level'], '⚪')}</td>
                <td>{cat['count']:,}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
    
    <div class="card">
        <h2>⚠️ Top Unclassified Titles (need berufenet match)</h2>
        <table>
            <tr><th>Beruf</th><th>Count</th></tr>
"""
    
    for b in data['top_unmatched_berufe'][:15]:
        html += f"""
            <tr><td>{b['beruf']}</td><td>{b['count']:,}</td></tr>
"""
    
    html += """
        </table>
    </div>
    
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="talent.yoga BI Dashboard")
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--output', '-o', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    data = collect_all_metrics()
    
    if args.json:
        output = json.dumps(data, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output)
            print(f"JSON saved to {args.output}")
        else:
            print(output)
    
    elif args.html:
        output = generate_html_dashboard(data)
        if args.output:
            Path(args.output).write_text(output)
            print(f"HTML saved to {args.output}")
        else:
            print(output)
    
    else:
        print_terminal_dashboard(data)


if __name__ == '__main__':
    main()
