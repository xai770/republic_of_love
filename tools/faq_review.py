#!/usr/bin/env python3
"""
FAQ Review CLI Tool

Review and manage FAQ candidates stored in mira_faq_candidates.

Commands:
    python tools/faq_review.py list           # List pending candidates
    python tools/faq_review.py review <id>    # Review a specific candidate
    python tools/faq_review.py promote <id>   # Promote to FAQ corpus
    python tools/faq_review.py reject <id>    # Mark as rejected
    python tools/faq_review.py stats          # Show statistics

Author: Arden
Date: 2026-02-09
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from textwrap import wrap

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def show_candidate(row: dict, detailed: bool = False) -> None:
    """Pretty print a candidate."""
    print(f"\n{'='*70}")
    print(f"ID: {row['id']:<6} | Reason: {row['flagged_reason']:<20} | {row['created_at'].strftime('%Y-%m-%d %H:%M')}")
    print(f"User ID: {row['user_id'] or 'N/A'}")
    if row['user_feedback']:
        print(f"User Feedback: {row['user_feedback']}")
    print(f"{'-'*70}")
    print("USER MESSAGE:")
    for line in wrap(row['user_message'], width=68):
        print(f"  {line}")
    print(f"{'-'*70}")
    print("MIRA RESPONSE:")
    for line in wrap(row['mira_response'], width=68):
        print(f"  {line}")
    print(f"{'='*70}")


def list_candidates(conn, limit: int = 20, include_reviewed: bool = False) -> None:
    """List FAQ candidates."""
    with conn.cursor() as cur:
        if include_reviewed:
            cur.execute("""
                SELECT * FROM mira_faq_candidates 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
        else:
            cur.execute("""
                SELECT * FROM mira_faq_candidates 
                WHERE reviewed_at IS NULL
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
        
        rows = cur.fetchall()
        
        if not rows:
            print("No pending FAQ candidates.")
            return
        
        print(f"\n📋 FAQ Candidates ({len(rows)} shown)")
        print(f"{'ID':<6} {'Reason':<20} {'User Message (preview)':<40} {'Date'}")
        print("-" * 80)
        
        for row in rows:
            preview = row['user_message'][:37] + "..." if len(row['user_message']) > 40 else row['user_message']
            preview = preview.replace('\n', ' ')
            date_str = row['created_at'].strftime('%m-%d %H:%M')
            print(f"{row['id']:<6} {row['flagged_reason']:<20} {preview:<40} {date_str}")
        
        print(f"\nUse 'faq_review.py review <id>' to see full details")


def review_candidate(conn, candidate_id: int) -> None:
    """Show detailed view of a candidate."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM mira_faq_candidates WHERE id = %s", (candidate_id,))
        row = cur.fetchone()
        
        if not row:
            print(f"Candidate #{candidate_id} not found.")
            return
        
        show_candidate(row, detailed=True)
        
        if row['reviewed_at']:
            print(f"\n⚠️  Already reviewed: {row['review_decision']} on {row['reviewed_at']}")
            if row['review_notes']:
                print(f"   Notes: {row['review_notes']}")
        else:
            print("\nActions:")
            print("  faq_review.py promote <id> [--as 'faq_xxx']  # Promote to FAQ")
            print("  faq_review.py reject <id> [--reason '...']  # Reject")
            print("  faq_review.py defer <id>                     # Review later")


def promote_candidate(conn, candidate_id: int, faq_id: str = None, reviewer_id: int = None) -> None:
    """Mark candidate as promoted (actual FAQ file editing done separately)."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM mira_faq_candidates WHERE id = %s", (candidate_id,))
        row = cur.fetchone()
        
        if not row:
            print(f"Candidate #{candidate_id} not found.")
            return
        
        # Generate FAQ ID if not provided
        if not faq_id:
            cur.execute("SELECT COUNT(*) as cnt FROM mira_faq_candidates WHERE promoted_at IS NOT NULL")
            count = cur.fetchone()['cnt']
            faq_id = f"faq_promoted_{(count + 1):04d}"
        
        cur.execute("""
            UPDATE mira_faq_candidates 
            SET reviewed_at = NOW(),
                reviewed_by = %s,
                review_decision = 'promote',
                promoted_at = NOW(),
                promoted_faq_id = %s
            WHERE id = %s
        """, (reviewer_id, faq_id, candidate_id))
        conn.commit()
        
        print(f"✅ Candidate #{candidate_id} marked for promotion as '{faq_id}'")
        print(f"\n📝 Add to config/mira_faq.md:")
        print(f"\n### {faq_id}")
        print(f"**category:** (choose category)")
        print(f"**question_variants:**")
        print(f"- {row['user_message']}")
        print(f"\n**answer_de:**")
        print(f"{row['mira_response']}")
        print(f"\n**answer_en:**")
        print(f"(translate)")


def reject_candidate(conn, candidate_id: int, reason: str = None, reviewer_id: int = None) -> None:
    """Mark candidate as rejected."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE mira_faq_candidates 
            SET reviewed_at = NOW(),
                reviewed_by = %s,
                review_decision = 'reject',
                review_notes = %s
            WHERE id = %s
        """, (reviewer_id, reason, candidate_id))
        conn.commit()
        
        print(f"❌ Candidate #{candidate_id} rejected.")


def defer_candidate(conn, candidate_id: int, reviewer_id: int = None) -> None:
    """Mark candidate for later review."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE mira_faq_candidates 
            SET review_decision = 'defer',
                review_notes = 'Deferred for later review'
            WHERE id = %s
        """, (candidate_id,))
        conn.commit()
        
        print(f"⏸️  Candidate #{candidate_id} deferred.")


def show_stats(conn) -> None:
    """Show FAQ candidate statistics."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE reviewed_at IS NULL) as pending,
                COUNT(*) FILTER (WHERE review_decision = 'promote') as promoted,
                COUNT(*) FILTER (WHERE review_decision = 'reject') as rejected,
                COUNT(*) FILTER (WHERE review_decision = 'defer') as deferred
            FROM mira_faq_candidates
        """)
        stats = cur.fetchone()
        
        cur.execute("""
            SELECT flagged_reason, COUNT(*) as cnt
            FROM mira_faq_candidates
            GROUP BY flagged_reason
            ORDER BY cnt DESC
        """)
        by_reason = cur.fetchall()
        
        print("\n📊 FAQ Candidate Statistics")
        print("=" * 40)
        print(f"Total candidates:  {stats['total']}")
        print(f"Pending review:    {stats['pending']}")
        print(f"Promoted:          {stats['promoted']}")
        print(f"Rejected:          {stats['rejected']}")
        print(f"Deferred:          {stats['deferred']}")
        print("\nBy reason:")
        for row in by_reason:
            print(f"  {row['flagged_reason']:<20} {row['cnt']}")


def main():
    parser = argparse.ArgumentParser(description="FAQ Candidate Review Tool")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List
    list_parser = subparsers.add_parser('list', help='List pending candidates')
    list_parser.add_argument('--limit', '-n', type=int, default=20, help='Max results')
    list_parser.add_argument('--all', '-a', action='store_true', help='Include reviewed')
    
    # Review
    review_parser = subparsers.add_parser('review', help='Review a candidate')
    review_parser.add_argument('id', type=int, help='Candidate ID')
    
    # Promote
    promote_parser = subparsers.add_parser('promote', help='Promote to FAQ')
    promote_parser.add_argument('id', type=int, help='Candidate ID')
    promote_parser.add_argument('--as', dest='faq_id', help='Custom FAQ ID')
    
    # Reject
    reject_parser = subparsers.add_parser('reject', help='Reject candidate')
    reject_parser.add_argument('id', type=int, help='Candidate ID')
    reject_parser.add_argument('--reason', '-r', help='Rejection reason')
    
    # Defer
    defer_parser = subparsers.add_parser('defer', help='Defer for later')
    defer_parser.add_argument('id', type=int, help='Candidate ID')
    
    # Stats
    subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    from core.database import get_connection
    
    with get_connection() as conn:
        if args.command == 'list':
            list_candidates(conn, limit=args.limit, include_reviewed=args.all)
        elif args.command == 'review':
            review_candidate(conn, args.id)
        elif args.command == 'promote':
            promote_candidate(conn, args.id, faq_id=args.faq_id)
        elif args.command == 'reject':
            reject_candidate(conn, args.id, reason=args.reason)
        elif args.command == 'defer':
            defer_candidate(conn, args.id)
        elif args.command == 'stats':
            show_stats(conn)


if __name__ == '__main__':
    main()
