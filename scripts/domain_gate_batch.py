#!/usr/bin/env python3
"""
Domain Gate Batch Processor - Manual backfill script

For ongoing processing, use the daemon actor (postings__domain_gate_U.py).
This script is for bulk backfills only.

Usage:
    python3 scripts/domain_gate_batch.py [--limit N]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from actors.postings__domain_gate_U import DomainGateDetector, build_domain_centroids
from core.database import get_connection


def main():
    parser = argparse.ArgumentParser(description='Batch backfill domain_gate')
    parser.add_argument('--limit', type=int, default=5000, help='Max postings to process')
    args = parser.parse_args()

    with get_connection() as conn:
        cur = conn.cursor()
        
        # Use the same view as the daemon
        cur.execute("""
            SELECT posting_id FROM postings_for_matching
            WHERE domain_gate IS NULL
            ORDER BY first_seen_at DESC
            LIMIT %s
        """, (args.limit,))
        
        posting_ids = [row['posting_id'] for row in cur.fetchall()]
        total = len(posting_ids)
        
        if total == 0:
            print("No unprocessed postings found")
            return
        
        print(f"Processing {total} postings...")
        print("Building domain centroids (one-time)...")
        centroids = build_domain_centroids(conn)
        print(f"Loaded {len(centroids)} domain centroids")
        
        # Create one actor instance, reuse centroids
        actor = DomainGateDetector(conn)
        actor._centroids = centroids  # Inject pre-built centroids
        
        processed = 0
        errors = 0
        
        for i, posting_id in enumerate(posting_ids):
            if i % 100 == 0 and i > 0:
                print(f"Progress: {i}/{total} ({100*i/total:.1f}%) - {processed} ok, {errors} errors")
            
            try:
                actor.input_data = {'posting_id': posting_id}
                result = actor.process()
                if result.get('success'):
                    processed += 1
                else:
                    errors += 1
                    if errors < 10:
                        print(f"  {posting_id}: {result.get('error', result.get('skip_reason', 'unknown'))}")
            except Exception as e:
                errors += 1
                print(f"  Error on {posting_id}: {e}")
        
        print(f"\nDone! Processed: {processed}, Errors: {errors}")


if __name__ == "__main__":
    main()
