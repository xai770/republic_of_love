#!/usr/bin/env python3
"""
daily_match.py — Scheduled job matching

Runs daily to match:
1. New postings against all profiles with matching enabled
2. New/updated profiles against all active postings

Designed to be run via cron at 06:00 daily.

Usage:
    python3 scripts/daily_match.py
    python3 scripts/daily_match.py --dry-run
    python3 scripts/daily_match.py --profile 1  # Single profile
    python3 scripts/daily_match.py --posting 123  # Single posting

Cron setup:
    0 6 * * * cd /home/xai/Documents/ty_learn && python3 scripts/daily_match.py >> logs/matching.log 2>&1
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


def get_matchable_profiles(conn, profile_id: int = None) -> List[dict]:
    """Get profiles that should receive matches."""
    with conn.cursor() as cur:
        if profile_id:
            cur.execute("""
                SELECT profile_id, full_name
                FROM profiles
                WHERE profile_id = %s
                  AND matching_enabled IS NOT FALSE
            """, (profile_id,))
        else:
            cur.execute("""
                SELECT profile_id, full_name
                FROM profiles
                WHERE matching_enabled IS NOT FALSE
                ORDER BY profile_id
            """)
        return [dict(r) for r in cur.fetchall()]


def get_active_postings(conn, posting_id: int = None, since_days: int = 7) -> List[dict]:
    """Get active postings to match against."""
    since = datetime.now() - timedelta(days=since_days)
    
    with conn.cursor() as cur:
        if posting_id:
            cur.execute("""
                SELECT posting_id, job_title
                FROM postings
                WHERE posting_id = %s
            """, (posting_id,))
        else:
            # Get postings updated recently or marked as active
            cur.execute("""
                SELECT posting_id, job_title
                FROM postings
                WHERE (updated_at >= %s OR first_seen_at >= %s)
                  AND invalidated IS NOT TRUE
                  AND enabled IS NOT FALSE
                ORDER BY posting_id
            """, (since, since))
        return [dict(r) for r in cur.fetchall()]


def get_existing_matches(conn, profile_ids: List[int], posting_ids: List[int]) -> set:
    """Get existing profile-posting match pairs to skip."""
    if not profile_ids or not posting_ids:
        return set()
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT profile_id, posting_id
            FROM profile_posting_matches
            WHERE profile_id = ANY(%s)
              AND posting_id = ANY(%s)
        """, (profile_ids, posting_ids))
        return {(r['profile_id'], r['posting_id']) for r in cur.fetchall()}


def compute_match(profile_id: int, posting_id: int) -> Tuple[bool, str]:
    """
    Compute match using profile_matcher.
    Returns (success, message).
    """
    import subprocess
    
    result = subprocess.run(
        ["python3", "tools/profile_matcher.py", "match", 
         str(profile_id), str(posting_id)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120
    )
    
    if result.returncode == 0:
        return True, result.stdout.strip()
    else:
        return False, result.stderr.strip()[:200]


def run_matching(
    conn,
    profile_id: int = None,
    posting_id: int = None,
    dry_run: bool = False,
    since_days: int = 7
) -> dict:
    """
    Run the matching process.
    
    Returns:
        dict with stats: computed, skipped, failed
    """
    stats = {'computed': 0, 'skipped': 0, 'failed': 0, 'pairs': [], 'by_user': {}}
    
    # Get profiles and postings
    profiles = get_matchable_profiles(conn, profile_id)
    postings = get_active_postings(conn, posting_id, since_days)
    
    if not profiles:
        log.warning("No matchable profiles found")
        return stats
    
    if not postings:
        log.warning("No active postings found")
        return stats
    
    log.info(f"Found {len(profiles)} profiles and {len(postings)} postings")
    
    # Get existing matches to skip
    profile_ids = [p['profile_id'] for p in profiles]
    posting_ids = [p['posting_id'] for p in postings]
    existing = get_existing_matches(conn, profile_ids, posting_ids)
    
    log.info(f"Existing matches to skip: {len(existing)}")
    
    # Compute new matches
    total_pairs = len(profiles) * len(postings)
    processed = 0
    
    for profile in profiles:
        for posting in postings:
            pair = (profile['profile_id'], posting['posting_id'])
            processed += 1
            
            if pair in existing:
                stats['skipped'] += 1
                continue
            
            if dry_run:
                log.info(f"[DRY RUN] Would compute: {profile['full_name']} ↔ {posting['job_title']}")
                stats['computed'] += 1
                continue
            
            # Compute match
            success, msg = compute_match(profile['profile_id'], posting['posting_id'])
            
            if success:
                stats['computed'] += 1
                stats['pairs'].append(pair)
                # Track per-user for notifications
                user_id = get_user_for_profile(conn, profile['profile_id'])
                if user_id:
                    if user_id not in stats['by_user']:
                        stats['by_user'][user_id] = []
                    stats['by_user'][user_id].append(pair)
                if stats['computed'] % 10 == 0:
                    log.info(f"Progress: {processed}/{total_pairs} ({stats['computed']} computed)")
            else:
                stats['failed'] += 1
                log.warning(f"Match failed: {profile['profile_id']} ↔ {posting['posting_id']}: {msg}")
    
    return stats


def get_user_for_profile(conn, profile_id: int) -> int:
    """Get user_id for a profile."""
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM profiles WHERE profile_id = %s", (profile_id,))
        row = cur.fetchone()
        return row['user_id'] if row else None


def create_match_notifications(conn, stats: dict):
    """Create notifications for users who got new matches."""
    from api.routers.notifications import notify_new_matches
    
    for user_id, pairs in stats.get('by_user', {}).items():
        if pairs:
            notify_new_matches(conn, user_id, len(pairs))
            log.info(f"Created notification for user {user_id}: {len(pairs)} new matches")
    
    return stats


def add_matching_enabled_column(conn):
    """Add matching_enabled column if not exists."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'profiles' 
              AND column_name = 'matching_enabled'
        """)
        if not cur.fetchone():
            log.info("Adding matching_enabled column to profiles")
            cur.execute("""
                ALTER TABLE profiles 
                ADD COLUMN matching_enabled BOOLEAN DEFAULT TRUE
            """)
            conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Daily job matching")
    parser.add_argument("--profile", type=int, help="Match only this profile")
    parser.add_argument("--posting", type=int, help="Match only this posting")
    parser.add_argument("--dry-run", action="store_true", help="Don't compute, just show pairs")
    parser.add_argument("--since", type=int, default=7, help="Postings from last N days (default: 7)")
    args = parser.parse_args()
    
    log.info("=" * 60)
    log.info("Daily Matching Job Started")
    log.info("=" * 60)
    
    start_time = datetime.now()
    
    with get_connection() as conn:
        # Ensure schema is ready
        add_matching_enabled_column(conn)
        
        # Run matching
        stats = run_matching(
            conn,
            profile_id=args.profile,
            posting_id=args.posting,
            dry_run=args.dry_run,
            since_days=args.since
        )
        
        # Create notifications for users (skip in dry-run)
        if not args.dry_run and stats['computed'] > 0:
            create_match_notifications(conn, stats)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    log.info("-" * 60)
    log.info(f"Matching complete in {elapsed:.1f}s")
    log.info(f"  Computed: {stats['computed']}")
    log.info(f"  Skipped (existing): {stats['skipped']}")
    log.info(f"  Failed: {stats['failed']}")
    log.info("=" * 60)
    
    return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
