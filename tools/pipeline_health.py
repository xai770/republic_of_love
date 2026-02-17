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
    
    # Read entire file and find the LAST run (starts with [1/5])
    with open(log_path) as f:
        all_lines = f.readlines()
    
    # Find the last occurrence of [1/5] to isolate the most recent run
    last_run_start = 0
    for i, line in enumerate(all_lines):
        if '[1/5]' in line:
            last_run_start = i
    
    lines = all_lines[last_run_start:]
    
    result = {
        'log_file': str(log_path),
        'start_time': None,
        'end_time': None,
        'step_checklist': {},  # step_key -> {name, status, timestamp}
        'steps_completed': [],  # backward compat
        'errors': [],
    }
    
    # Canonical pipeline steps — order matters
    PIPELINE_STEPS = [
        ('1', 'AA fetch'),
        ('2', 'DB fetch'),
        ('3', 'Berufenet classification'),
        ('3b', 'Domain cascade'),
        ('3c', 'Geo state'),
        ('3d', 'Qualification backfill'),
        ('4', 'Enrichment daemon'),
        ('5', 'Description retry'),
    ]
    
    # Initialize checklist
    for key, name in PIPELINE_STEPS:
        result['step_checklist'][key] = {'name': name, 'status': 'not_seen'}
    
    # Track step start times for ETA estimation
    step_timestamps = {}
    
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
        
        # Match step markers: [1/5], [3b/5], etc.
        step_match = re.search(r'\[(\d+[a-z]?)/5\]', line)
        if step_match:
            step_key = step_match.group(1)
            if step_key in result['step_checklist']:
                result['step_checklist'][step_key]['status'] = 'started'
                # Extract timestamp if present
                ts_match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                if ts_match:
                    step_timestamps[step_key] = datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S')
            result['steps_completed'].append(line)
        
        # Match completion markers: ✅ ... complete
        if '✅' in line and 'complete' in line.lower():
            result['steps_completed'].append(line)
            # Try to match which step completed
            for key, name in PIPELINE_STEPS:
                if any(word in line.lower() for word in name.lower().split()[:2]):
                    result['step_checklist'][key]['status'] = 'done'
        
        # Pipeline complete marker
        if 'Pipeline complete' in line:
            # Mark all started steps as done
            for key in result['step_checklist']:
                if result['step_checklist'][key]['status'] == 'started':
                    result['step_checklist'][key]['status'] = 'done'
            result['steps_completed'].append(line)
        
        # Look for errors
        if 'ERROR' in line or 'Exception' in line or 'Traceback' in line:
            result['errors'].append(line[:100])
    
    if result['start_time'] and result['end_time']:
        result['duration_minutes'] = (result['end_time'] - result['start_time']).total_seconds() / 60
        result['start_time'] = result['start_time'].isoformat()
        result['end_time'] = result['end_time'].isoformat()
    
    # Calculate step durations for ETA estimation
    step_keys = [k for k, _ in PIPELINE_STEPS]
    step_durations = {}
    for i, key in enumerate(step_keys):
        if key in step_timestamps:
            # Duration = time to next step (or end)
            next_ts = None
            for j in range(i + 1, len(step_keys)):
                if step_keys[j] in step_timestamps:
                    next_ts = step_timestamps[step_keys[j]]
                    break
            if next_ts is None and result.get('end_time'):
                next_ts = datetime.fromisoformat(result['end_time'])
            if next_ts:
                step_durations[key] = (next_ts - step_timestamps[key]).total_seconds()
    
    result['step_durations'] = step_durations
    
    return result


def get_pending_work() -> dict:
    """Count work items pending in each stage."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Postings without job_description — split retryable vs permanently failed
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE COALESCE(processing_failures, 0) < 2) as retryable,
                COUNT(*) FILTER (WHERE COALESCE(processing_failures, 0) >= 2) as given_up
            FROM postings 
            WHERE (job_description IS NULL OR job_description = '')
              AND invalidated = false
        """)
        row = cur.fetchone()
        no_desc_retryable = row['retryable']
        no_desc_given_up = row['given_up']
        
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
            'no_desc_retryable': no_desc_retryable,
            'no_desc_given_up': no_desc_given_up,
            'need_berufenet': need_berufenet,
            'need_summary': need_summary,
            'need_embedding': need_embedding,
        }


def get_eta_prediction(pending: dict) -> dict:
    """Predict ETA for pending work based on historical ticket throughput.
    
    Queries the last 7 days of completed tickets to calculate per-subject
    processing rates, then multiplies by current pending counts.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                tt.task_type_name,
                ROUND(AVG(
                    CASE WHEN (t.output->>'success_count')::int > 0
                    THEN EXTRACT(EPOCH FROM (t.completed_at - t.started_at))
                         / (t.output->>'success_count')::int
                    END
                )::numeric, 3) AS secs_per_subject
            FROM tickets t
            JOIN task_types tt ON t.task_type_id = tt.task_type_id
            WHERE t.status = 'completed'
              AND t.started_at > NOW() - INTERVAL '7 days'
              AND t.completed_at IS NOT NULL
              AND (t.output->>'success_count')::int > 0
            GROUP BY tt.task_type_name
        """)
        rates = {row['task_type_name']: float(row['secs_per_subject']) for row in cur.fetchall()}

    # Map pending work to task_type rates
    estimates = {}
    mapping = {
        'job_description_backfill': ('no_desc_retryable', pending.get('no_desc_retryable', 0)),
        'owl_pending_auto_triage': ('need_berufenet', pending.get('need_berufenet', 0)),
        'extracted_summary': ('need_summary', pending.get('need_summary', 0)),
        'embedding_generator': ('need_embedding', pending.get('need_embedding', 0)),
    }

    total_secs = 0
    for task_name, (label, count) in mapping.items():
        rate = rates.get(task_name, 0)
        if rate and count:
            est_secs = rate * count
            estimates[label] = {'count': count, 'rate': rate, 'est_secs': est_secs}
            total_secs += est_secs

    return {'estimates': estimates, 'total_secs': total_secs, 'rates': rates}


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
        
        # Step checklist
        checklist = last_run.get('step_checklist', {})
        step_durations = last_run.get('step_durations', {})
        if checklist:
            lines.append("")
            for key in ['1', '2', '3', '3b', '3c', '3d', '4', '5']:
                step = checklist.get(key, {})
                name = step.get('name', f'Step {key}')
                status = step.get('status', 'not_seen')
                icon = '✅' if status == 'done' else ('🔄' if status == 'started' else '⬜')
                dur = step_durations.get(key)
                dur_str = f" ({dur:.0f}s)" if dur else ""
                lines.append(f"   {icon} [{key}/5] {name}{dur_str}")
        
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
    
    lines.append(f"   {status_icon(pending['no_desc_retryable'], 100)} Missing descriptions:     {pending['no_desc_retryable']:,} retryable")
    if pending['no_desc_given_up'] > 0:
        lines.append(f"   ⚫ Given up (≥2 failures):   {pending['no_desc_given_up']:,}")
    lines.append(f"   {status_icon(pending['need_berufenet'], 500)} Need berufenet match:     {pending['need_berufenet']:,}")
    lines.append(f"   {status_icon(pending['need_summary'], 100)} Need LLM summary:         {pending['need_summary']:,}")
    lines.append(f"   {status_icon(pending['need_embedding'], 500)} Need embedding:           {pending['need_embedding']:,}")
    
    # ETA predictions
    eta = get_eta_prediction(pending)
    if eta['total_secs'] > 0:
        lines.append("")
        lines.append("⏱️  ETA (based on last 7 days throughput)")
        lines.append("-" * 70)
        for label, est in eta['estimates'].items():
            mins = est['est_secs'] / 60
            if mins < 60:
                time_str = f"{mins:.0f}m"
            else:
                time_str = f"{mins/60:.1f}h"
            lines.append(f"   {label}: {est['count']:,} × {est['rate']:.2f}s/ea = ~{time_str}")
        total_mins = eta['total_secs'] / 60
        if total_mins < 60:
            lines.append(f"   Total: ~{total_mins:.0f} minutes")
        else:
            lines.append(f"   Total: ~{total_mins/60:.1f} hours")
    
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
