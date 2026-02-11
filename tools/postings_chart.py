#!/usr/bin/env python3
"""
Postings by Day Chart Generator

Generates ASCII and HTML charts showing posting volume over time.
For the management console at talent.yoga/console.

Usage:
    python3 tools/postings_chart.py              # ASCII chart (last 14 days)
    python3 tools/postings_chart.py --days 30   # Last 30 days
    python3 tools/postings_chart.py --html       # HTML output
    python3 tools/postings_chart.py --json       # JSON for API
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection


def get_postings_by_day(days: int = 14) -> list[dict]:
    """Fetch posting counts by day."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                DATE(first_seen_at) as date,
                COUNT(*) as new_postings,
                COUNT(*) FILTER (WHERE invalidated = true) as invalidated,
                COUNT(*) FILTER (WHERE berufenet_id IS NOT NULL) as with_berufenet,
                COUNT(*) FILTER (WHERE job_description IS NOT NULL AND job_description != '') as with_description
            FROM postings 
            WHERE first_seen_at > NOW() - INTERVAL '%s days'
            GROUP BY DATE(first_seen_at)
            ORDER BY date ASC
        """, (days,))
        
        rows = cur.fetchall()
        return [
            {
                'date': row['date'].strftime('%Y-%m-%d') if row['date'] else None,
                'date_short': row['date'].strftime('%m-%d') if row['date'] else None,
                'weekday': row['date'].strftime('%a') if row['date'] else None,
                'new_postings': row['new_postings'],
                'invalidated': row['invalidated'],
                'with_berufenet': row['with_berufenet'],
                'with_description': row['with_description'],
            }
            for row in rows
        ]


def get_totals() -> dict:
    """Get current totals for context."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) as cnt FROM postings")
        total = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM postings WHERE invalidated = true")
        invalidated = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM postings WHERE berufenet_id IS NOT NULL")
        with_berufenet = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM postings WHERE job_description IS NOT NULL AND job_description != ''")
        with_desc = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM embeddings")
        embeddings = cur.fetchone()['cnt']
        
        return {
            'total_postings': total,
            'active_postings': total - invalidated,
            'invalidated': invalidated,
            'with_berufenet': with_berufenet,
            'berufenet_pct': round(100 * with_berufenet / total, 1) if total else 0,
            'with_description': with_desc,
            'description_pct': round(100 * with_desc / total, 1) if total else 0,
            'embeddings': embeddings,
        }


def render_ascii_chart(data: list[dict], totals: dict) -> str:
    """Render ASCII bar chart."""
    if not data:
        return "No data available."
    
    max_count = max(d['new_postings'] for d in data)
    bar_width = 40
    
    lines = []
    lines.append("=" * 70)
    lines.append("📊 POSTINGS BY DAY")
    lines.append("=" * 70)
    lines.append("")
    
    for d in data:
        count = d['new_postings']
        bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = '█' * bar_len
        
        # Color coding by weekday
        day_marker = '🔴' if d['weekday'] in ('Sat', 'Sun') else '🟢'
        
        lines.append(f"{d['date_short']} {d['weekday']} {day_marker} {bar} {count:,}")
    
    lines.append("")
    lines.append("-" * 70)
    lines.append("📈 TOTALS")
    lines.append("-" * 70)
    lines.append(f"  Total postings:    {totals['total_postings']:,}")
    lines.append(f"  Active:            {totals['active_postings']:,}")
    lines.append(f"  With berufenet:    {totals['with_berufenet']:,} ({totals['berufenet_pct']}%)")
    lines.append(f"  With description:  {totals['with_description']:,} ({totals['description_pct']}%)")
    lines.append(f"  Embeddings:        {totals['embeddings']:,}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return '\n'.join(lines)


def render_html_chart(data: list[dict], totals: dict) -> str:
    """Render HTML chart with CSS styling."""
    max_count = max(d['new_postings'] for d in data) if data else 1
    
    bars_html = []
    for d in data:
        pct = int((d['new_postings'] / max_count) * 100) if max_count > 0 else 0
        weekend_class = 'weekend' if d['weekday'] in ('Sat', 'Sun') else ''
        bars_html.append(f'''
        <div class="bar-row">
            <span class="date">{d['date_short']} {d['weekday']}</span>
            <div class="bar-container">
                <div class="bar {weekend_class}" style="width: {pct}%"></div>
            </div>
            <span class="count">{d['new_postings']:,}</span>
        </div>''')
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Postings by Day - talent.yoga</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 800px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .chart {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .bar-row {{ display: flex; align-items: center; margin: 8px 0; }}
        .date {{ width: 80px; font-size: 12px; color: #666; }}
        .bar-container {{ flex: 1; height: 24px; background: #eee; border-radius: 4px; margin: 0 10px; }}
        .bar {{ height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 4px; 
               transition: width 0.3s ease; }}
        .bar.weekend {{ background: linear-gradient(90deg, #f093fb, #f5576c); }}
        .count {{ width: 60px; text-align: right; font-weight: bold; color: #333; }}
        .totals {{ margin-top: 30px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }}
        .stat {{ background: white; padding: 15px; border-radius: 8px; text-align: center; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .timestamp {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>📊 Postings by Day</h1>
    <div class="chart">
        {''.join(bars_html)}
    </div>
    <div class="totals">
        <div class="stat">
            <div class="stat-value">{totals['total_postings']:,}</div>
            <div class="stat-label">Total Postings</div>
        </div>
        <div class="stat">
            <div class="stat-value">{totals['berufenet_pct']}%</div>
            <div class="stat-label">Berufenet Coverage</div>
        </div>
        <div class="stat">
            <div class="stat-value">{totals['embeddings']:,}</div>
            <div class="stat-label">Embeddings</div>
        </div>
    </div>
    <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description='Postings by day chart')
    parser.add_argument('--days', type=int, default=14, help='Number of days to show')
    parser.add_argument('--html', action='store_true', help='Output HTML instead of ASCII')
    parser.add_argument('--json', action='store_true', help='Output JSON for API')
    parser.add_argument('-o', '--output', help='Write to file instead of stdout')
    args = parser.parse_args()
    
    data = get_postings_by_day(args.days)
    totals = get_totals()
    
    if args.json:
        output = json.dumps({
            'generated_at': datetime.now().isoformat(),
            'days': args.days,
            'daily_data': data,
            'totals': totals
        }, indent=2)
    elif args.html:
        output = render_html_chart(data, totals)
    else:
        output = render_ascii_chart(data, totals)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
