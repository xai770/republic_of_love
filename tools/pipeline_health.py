#!/usr/bin/env python3
"""
Pipeline Health Check

Quick overview of pipeline status:
- What ran and when
- Timing comparisons with historical runs
- Data anomalies
- Current pending work

Usage:
    python3 tools/pipeline_health.py              # Full report
    python3 tools/pipeline_health.py --quick      # Just the summary
    python3 tools/pipeline_health.py --json       # JSON for API
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from core.database import get_connection


def get_last_pipeline_run() -> dict:
    """Parse the turing_fetch.log to find last run info."""
    log_path = Path('/home/xai/Documents/ty_learn/logs/turing_fetch.log')
    
    if not log_path.exists():
        return {'error': 'Log file not found'}
    
    # Read last 200 lines
    with open(log_path) as f:
        lines = f.readlines()[-200:]
    
    result = {
        'log_file': str(log_path),
        'start_time': None,
        'end_time': None,
        'steps_completed': [],
        'errors': [],
    }
    
    for line in lines:
        line = line.strip()
        
        # Look for timestamps
        if line.startswith('[20'):
            try:
                ts_str = line[1:20]
                ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                if result['start_time'] is None:
                    result['start_time'] = ts
                result['end_time'] = ts
            except (KeyError, ValueError, TypeError):
                pass
        
        # Look for step completions  
        # Format: [n/5] step name, or ✅ ... complete, or Pipeline complete
        if re.search(r'\[\d+/5\]', line) or \
           ('✅' in line and 'complete' in line.lower()) or \
           'Pipeline complete' in line:
            result['steps_completed'].append(line)
        
        # Look for errors
        if 'ERROR' in line or 'Exception' in line or 'Traceback' in line:
            result['errors'].append(line[:100])
    
    if result['start_time'] and result['end_time']:
        result['duration_minutes'] = (result['end_time'] - result['start_time']).total_seconds() / 60
        result['start_time'] = result['start_time'].isoformat()
        result['end_time'] = result['end_time'].isoformat()
    
    return result


def get_pending_work() -> dict:
    """Count work items pending in each stage."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Postings without job_description
        cur.execute("""
            SELECT COUNT(*) as cnt FROM postings 
            WHERE (job_description IS NULL OR job_description = '')
              AND invalidated = false
        """)
        no_description = cur.fetchone()['cnt']
        
        # AA postings not yet processed by berufenet actor
        # Note: berufenet_verified IS NULL means unprocessed
        # berufenet_verified = 'null' means processed but no match found
        cur.execute("""
            SELECT COUNT(*) as cnt FROM postings 
            WHERE source = 'arbeitsagentur'
              AND job_title IS NOT NULL
              AND berufenet_verified IS NULL
              AND invalidated = false
        """)
        need_berufenet = cur.fetchone()['cnt']
        
        # DB postings without extracted_summary
        cur.execute("""
            SELECT COUNT(*) as cnt FROM postings 
            WHERE source = 'db'
              AND job_description IS NOT NULL
              AND (extracted_summary IS NULL OR extracted_summary = '')
              AND invalidated = false
        """)
        need_summary = cur.fetchone()['cnt']
        
        # Postings without embeddings (must match work_query normalization)
        cur.execute(r"""
            SELECT COUNT(*) as cnt
            FROM postings_for_matching p
            WHERE NOT EXISTS (
                SELECT 1 FROM embeddings e WHERE e.text = normalize_text_python(p.match_text)
            )
        """)
        need_embedding = cur.fetchone()['cnt']
        
        return {
            'no_description': no_description,
            'need_berufenet': need_berufenet,
            'need_summary': need_summary,
            'need_embedding': need_embedding,
        }


def get_recent_activity() -> dict:
    """Get counts of recent activity."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Postings created/updated in last 24h
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE first_seen_at > NOW() - INTERVAL '24 hours') as new_24h,
                COUNT(*) FILTER (WHERE updated_at > NOW() - INTERVAL '24 hours') as updated_24h,
                COUNT(*) FILTER (WHERE invalidated_at > NOW() - INTERVAL '24 hours') as invalidated_24h
            FROM postings
        """)
        row = cur.fetchone()
        
        # Embeddings created in last 24h
        cur.execute("""
            SELECT COUNT(*) as cnt FROM embeddings 
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        embeds_24h = cur.fetchone()['cnt']
        
        return {
            'new_postings_24h': row['new_24h'],
            'updated_postings_24h': row['updated_24h'],
            'invalidated_24h': row['invalidated_24h'],
            'embeddings_24h': embeds_24h,
        }


def get_data_anomalies() -> list:
    """Check for data anomalies."""
    anomalies = []
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Check for duplicate external_ids
        cur.execute("""
            SELECT external_id, COUNT(*) as cnt
            FROM postings
            WHERE external_id IS NOT NULL
            GROUP BY external_id
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        dupes = cur.fetchall()
        if dupes:
            anomalies.append(f"⚠️ {len(dupes)} duplicate external_ids (showing first 5)")
        
        # Check for postings with berufenet_id but no qualification_level
        cur.execute("""
            SELECT COUNT(*) as cnt FROM postings 
            WHERE berufenet_id IS NOT NULL AND qualification_level IS NULL
        """)
        if cur.fetchone()['cnt'] > 0:
            anomalies.append("⚠️ Postings with berufenet_id but no qualification_level")
        
        # Check for very old non-invalidated postings
        cur.execute("""
            SELECT COUNT(*) as cnt FROM postings 
            WHERE first_seen_at < NOW() - INTERVAL '30 days'
              AND last_seen_at < NOW() - INTERVAL '7 days'
              AND invalidated = false
        """)
        stale = cur.fetchone()['cnt']
        if stale > 1000:
            anomalies.append(f"⚠️ {stale:,} stale postings (first seen >30d, last seen >7d, not invalidated)")
        
        # Check embedding gap (must match work_query normalization)
        cur.execute(r"""
            SELECT COUNT(*) as cnt
            FROM postings_for_matching p
            WHERE NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.text = normalize_text_python(p.match_text))
        """)
        embed_gap = cur.fetchone()['cnt']
        if embed_gap > 500:
            anomalies.append(f"⚠️ {embed_gap:,} postings missing embeddings")
    
    return anomalies if anomalies else ["✅ No anomalies detected"]


def get_totals() -> dict:
    """Get current totals."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) as cnt FROM postings")
        total = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM postings WHERE invalidated = false")
        active = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM embeddings")
        embeds = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM berufenet_synonyms")
        synonyms = cur.fetchone()['cnt']
        
        return {
            'total_postings': total,
            'active_postings': active,
            'total_embeddings': embeds,
            'berufenet_synonyms': synonyms,
        }


def render_ascii(last_run: dict, pending: dict, activity: dict, anomalies: list, totals: dict) -> str:
    """Render ASCII report."""
    lines = []
    lines.append("=" * 70)
    lines.append("🏥 PIPELINE HEALTH CHECK")
    lines.append(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    
    # Last run info
    lines.append("")
    lines.append("📅 LAST PIPELINE RUN")
    lines.append("-" * 70)
    if 'error' in last_run:
        lines.append(f"   ❌ {last_run['error']}")
    else:
        if last_run.get('start_time'):
            lines.append(f"   Started:  {last_run['start_time']}")
            lines.append(f"   Ended:    {last_run.get('end_time', 'unknown')}")
            if last_run.get('duration_minutes'):
                lines.append(f"   Duration: {last_run['duration_minutes']:.1f} minutes")
        lines.append(f"   Steps completed: {len(last_run.get('steps_completed', []))}")
        if last_run.get('errors'):
            lines.append(f"   ⚠️ Errors found: {len(last_run['errors'])}")
    
    # Recent activity
    lines.append("")
    lines.append("📊 ACTIVITY (Last 24 Hours)")
    lines.append("-" * 70)
    lines.append(f"   New postings:      {activity['new_postings_24h']:,}")
    lines.append(f"   Updated postings:  {activity['updated_postings_24h']:,}")
    lines.append(f"   Invalidated:       {activity['invalidated_24h']:,}")
    lines.append(f"   New embeddings:    {activity['embeddings_24h']:,}")
    
    # Pending work
    lines.append("")
    lines.append("⏳ PENDING WORK")
    lines.append("-" * 70)
    
    def status_icon(count, threshold=100):
        return "🟢" if count == 0 else ("🟡" if count < threshold else "🔴")
    
    lines.append(f"   {status_icon(pending['no_description'], 500)} Missing descriptions:     {pending['no_description']:,}")
    lines.append(f"   {status_icon(pending['need_berufenet'], 500)} Need berufenet match:     {pending['need_berufenet']:,}")
    lines.append(f"   {status_icon(pending['need_summary'], 100)} Need LLM summary:         {pending['need_summary']:,}")
    lines.append(f"   {status_icon(pending['need_embedding'], 500)} Need embedding:           {pending['need_embedding']:,}")
    
    # Anomalies
    lines.append("")
    lines.append("🔍 DATA QUALITY")
    lines.append("-" * 70)
    for a in anomalies:
        lines.append(f"   {a}")
    
    # Totals
    lines.append("")
    lines.append("📈 TOTALS")
    lines.append("-" * 70)
    lines.append(f"   Total postings:        {totals['total_postings']:,}")
    lines.append(f"   Active postings:       {totals['active_postings']:,}")
    lines.append(f"   Total embeddings:      {totals['total_embeddings']:,}")
    lines.append(f"   Berufenet synonyms:    {totals['berufenet_synonyms']:,}")
    
    return '\n'.join(lines)


def render_json(last_run: dict, pending: dict, activity: dict, anomalies: list, totals: dict) -> str:
    """Render JSON report."""
    return json.dumps({
        'generated_at': datetime.now().isoformat(),
        'last_run': last_run,
        'pending_work': pending,
        'activity_24h': activity,
        'anomalies': anomalies,
        'totals': totals,
    }, indent=2, default=str)


def send_pipeline_summary_message(summary_text: str):
    """Post pipeline health summary as a system message to all admin users in yogi_messages.
    
    Everyone is a citizen: the pipeline itself is a citizen that reports status.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            # Find admin users (or all users if none marked admin)
            cur.execute("""
                SELECT user_id FROM users 
                WHERE user_id IN (SELECT DISTINCT user_id FROM profiles)
                LIMIT 10
            """)
            users = cur.fetchall()
            
            for user in users:
                cur.execute("""
                    INSERT INTO yogi_messages 
                    (user_id, sender_type, message_type, subject, body)
                    VALUES (%s, 'system', 'pipeline_report', %s, %s)
                """, (
                    user['user_id'],
                    f"Pipeline Report {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    summary_text
                ))
            
            conn.commit()
            print(f"✅ Pipeline summary sent to {len(users)} user(s) in talent.yoga")
    except Exception as e:
        print(f"❌ Failed to send pipeline message: {e}")


def main():
    parser = argparse.ArgumentParser(description='Pipeline Health Check')
    parser.add_argument('--quick', action='store_true', help='Quick summary only')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--notify', action='store_true', help='Send summary as message in talent.yoga')
    parser.add_argument('-o', '--output', help='Write to file')
    args = parser.parse_args()
    
    last_run = get_last_pipeline_run()
    pending = get_pending_work()
    activity = get_recent_activity()
    anomalies = get_data_anomalies()
    totals = get_totals()
    
    if args.json:
        output = render_json(last_run, pending, activity, anomalies, totals)
    else:
        output = render_ascii(last_run, pending, activity, anomalies, totals)
    
    if args.notify:
        send_pipeline_summary_message(output)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
