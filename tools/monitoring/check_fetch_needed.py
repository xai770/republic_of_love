#!/usr/bin/env python3
"""
Script Actor: Check if Job Fetcher Needs to Run

Purpose: Pre-flight check to avoid running rate-limited fetcher unnecessarily
Returns: [SKIP_FETCH] or [RUN_FETCH] based on last fetch time

Input (JSON via stdin): {"user_id": 1}
Output (JSON to stdout): {"status": "SKIP_FETCH|RUN_FETCH", "last_run": "...", "hours_since": 12.3}
"""

import json
import sys
from datetime import datetime
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.database import get_connection

def check_fetch_needed():
    """Check if fetcher needs to run based on 24h rate limit"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get last fetch time from posting_fetch_runs
        cursor.execute("""
            SELECT MAX(started_at) as last_fetch
            FROM posting_fetch_runs
            WHERE status = 'SUCCESS'
        """)
        
        result = cursor.fetchone()
        last_fetch = result['last_fetch'] if result else None
        
        if not last_fetch:
            return {
                "status": "RUN_FETCH",
                "last_run": None,
                "hours_since": None,
                "message": "No previous fetch found"
            }
        
        now = datetime.now()
        time_diff = now - last_fetch
        hours_since = time_diff.total_seconds() / 3600
        
        # Rate limit: 24 hours
        if hours_since < 24:
            return {
                "status": "SKIP_FETCH",
                "last_run": last_fetch.isoformat(),
                "hours_since": round(hours_since, 1),
                "hours_remaining": round(24 - hours_since, 1),
                "message": f"Fetcher ran {hours_since:.1f}h ago, skip until 24h elapsed"
            }
        else:
            return {
                "status": "RUN_FETCH",
                "last_run": last_fetch.isoformat(),
                "hours_since": round(hours_since, 1),
                "message": f"Last fetch was {hours_since:.1f}h ago, safe to run"
            }
            
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        # Read input (not used, but required for actor contract)
        input_data = json.loads(sys.stdin.read())
        
        # Check fetch status
        result = check_fetch_needed()
        
        # Output with branch signal
        output = {
            **result,
            "branch": f"[{result['status']}]"
        }
        
        print(json.dumps(output))
        sys.exit(0)
        
    except Exception as e:
        error_output = {
            "status": "ERROR",
            "error": str(e),
            "branch": "[ERROR]"
        }
        print(json.dumps(error_output))
        sys.exit(1)
