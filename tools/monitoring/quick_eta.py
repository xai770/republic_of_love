#!/usr/bin/env python3
"""
Quick ETA script for current workflow progress
Reads log files and calculates ETAs for all steps
"""

import json
import glob
import os
from datetime import datetime, timedelta

def format_duration(seconds):
    """Format seconds into human-readable duration"""
    if seconds < 60:
        return f'{seconds:.0f}s'
    elif seconds < 3600:
        return f'{seconds/60:.1f}min'
    elif seconds < 86400:
        hours = seconds / 3600
        return f'{hours:.1f}h'
    else:
        days = seconds / 86400
        return f'{days:.1f}d'

def format_eta(dt):
    """Format ETA datetime nicely"""
    now = datetime.now(dt.tzinfo if dt.tzinfo else None)
    diff = (dt - now).total_seconds()
    
    if diff < 3600:  # Less than 1 hour
        return dt.strftime('%H:%M')
    elif diff < 86400:  # Same day
        return dt.strftime('%H:%M today')
    elif diff < 172800:  # Tomorrow  
        return dt.strftime('%H:%M tomorrow')
    else:
        return dt.strftime('%a %d %b %H:%M')

# Find latest log
log_pattern = '/home/xai/Documents/ty_wave/logs/workflow_3001_*.log'
log_files = sorted(glob.glob(log_pattern), key=lambda x: os.path.getmtime(x), reverse=True)

if not log_files:
    print("No log files found")
    exit(1)

log_file = log_files[0]
print(f"Reading: {os.path.basename(log_file)}\n")

# Parse events
batches = {}
with open(log_file, 'r') as f:
    for line in f:
        try:
            entry = json.loads(line.strip())
            msg = entry.get('message')
            
            if msg == 'model_batch_started':
                actor_id = entry.get('actor_id')
                batches[actor_id] = {
                    'actor_name': entry.get('actor_name'),
                    'start': datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')),
                    'request_count': entry.get('request_count'),
                    'wave': entry.get('wave_number')
                }
            
            elif msg == 'model_batch_completed':
                actor_id = entry.get('actor_id')
                if actor_id in batches:
                    batches[actor_id]['end'] = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    batches[actor_id]['processed'] = entry.get('processed')
                    batches[actor_id]['duration_sec'] = entry.get('duration_sec')
                    batches[actor_id]['avg_per_request'] = entry.get('avg_per_request')
        except (json.JSONDecodeError, KeyError, ValueError):
            continue

# Display results
print("="*80)
print("WORKFLOW 3001 - ETA ANALYSIS")
print("="*80)
print()

for actor_id in sorted(batches.keys()):
    batch = batches[actor_id]
    actor_name = batch['actor_name']
    total = batch['request_count']
    
    if 'end' in batch:
        # Completed
        duration = batch['duration_sec']
        print(f"✅ {actor_name} (Actor {actor_id}):")
        print(f"   Completed: {batch['processed']:,}/{total:,}")
        print(f"   Duration: {format_duration(duration)}")
        print(f"   Rate: {batch['processed']/duration*60:.1f} postings/min")
        print(f"   Avg: {batch['avg_per_request']:.1f}s per posting")
    else:
        # In progress
        elapsed = (datetime.now(batch['start'].tzinfo) - batch['start']).total_seconds()
        
        # Get current progress from monitor
        import sys
        sys.path.insert(0, '/home/xai/Documents/ty_wave')
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Count completed for this wave
        cursor.execute("""
            SELECT COUNT(*) as completed
            FROM execution_events
            WHERE event_timestamp > %s
        """, (batch['start'],))
        
        result = cursor.fetchone()
        completed = result['completed'] if result else 0
        conn.close()
        
        rate = completed / elapsed if elapsed > 0 else 0
        remaining = total - completed
        
        print(f"🔄 {actor_name} (Actor {actor_id}):")
        print(f"   Progress: {completed:,}/{total:,} ({completed*100//total}%)")
        print(f"   Elapsed: {format_duration(elapsed)}")
        print(f"   Rate: {rate*60:.1f} postings/min")
        
        if rate > 0:
            eta_seconds = remaining / rate
            eta_time = datetime.now(batch['start'].tzinfo) + timedelta(seconds=eta_seconds)
            print(f"   Remaining: {remaining:,} postings")
            print(f"   ETA: {format_duration(eta_seconds)}")
            print(f"   Complete at: {format_eta(eta_time)}")
    
    print()

print("="*80)
