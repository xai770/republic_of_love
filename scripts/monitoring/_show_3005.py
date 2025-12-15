#!/usr/bin/env python3
"""
WF3005 Monitor - Hierarchy Consultation Dashboard

Shows real-time progress of orphan skill categorization with grader pattern.

Usage:
    python3 tools/_show_3005.py [--once]
"""

import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )


def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')


def get_orphan_stats(conn):
    """Get current orphan skill counts."""
    cursor = conn.cursor()
    
    # Total orphans (skills with no parent AND no children in entity_relationships)
    cursor.execute("""
        SELECT COUNT(*)
        FROM entities e
        WHERE e.entity_type = 'skill'
          AND e.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er 
              WHERE er.entity_id = e.entity_id 
              AND er.relationship = 'child_of'
          )
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er 
              WHERE er.related_entity_id = e.entity_id 
              AND er.relationship = 'child_of'
          )
    """)
    total_orphans = cursor.fetchone()[0]
    
    return total_orphans


def get_decision_stats(conn):
    """Get registry_decisions statistics."""
    cursor = conn.cursor()
    
    # Decision counts by status
    cursor.execute("""
        SELECT 
            review_status,
            COUNT(*) as cnt
        FROM registry_decisions
        WHERE decision_type = 'assign'
        GROUP BY review_status
        ORDER BY review_status
    """)
    status_counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Recent decisions
    cursor.execute("""
        SELECT 
            e.canonical_name as skill,
            t.canonical_name as parent,
            rd.confidence,
            rd.review_status,
            rd.created_at
        FROM registry_decisions rd
        JOIN entities e ON rd.subject_entity_id = e.entity_id
        LEFT JOIN entities t ON rd.target_entity_id = t.entity_id
        WHERE rd.decision_type = 'assign'
        ORDER BY rd.created_at DESC
        LIMIT 10
    """)
    recent = cursor.fetchall()
    
    return status_counts, recent


def get_interaction_stats(conn):
    """Get WF3005 interaction counts."""
    cursor = conn.cursor()
    
    # Get conversation IDs for WF3005
    cursor.execute("""
        SELECT c.conversation_id, c.canonical_name
        FROM workflow_conversations wc
        JOIN conversations c ON wc.conversation_id = c.conversation_id
        WHERE wc.workflow_id = 3005
        ORDER BY wc.execution_order
    """)
    conversations = cursor.fetchall()
    
    # Get interaction counts per conversation
    stats = {}
    for conv_id, name in conversations:
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM interactions
            WHERE conversation_id = %s
            GROUP BY status
        """, (conv_id,))
        stats[name] = {row[0]: row[1] for row in cursor.fetchall()}
    
    return stats


def display_dashboard(conn):
    """Display the monitoring dashboard."""
    orphans = get_orphan_stats(conn)
    decision_stats, recent_decisions = get_decision_stats(conn)
    interaction_stats = get_interaction_stats(conn)
    
    # Calculate totals
    total_decisions = sum(decision_stats.values())
    auto_approved = decision_stats.get('auto_approved', 0)
    pending = decision_stats.get('pending', 0)
    approved = decision_stats.get('approved', 0)
    rejected = decision_stats.get('rejected', 0)
    
    # Header
    print("=" * 70)
    print(f"  WF3005: Hierarchy Consultation Monitor")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Progress bar
    processed = total_decisions
    total = orphans + processed
    if total > 0:
        pct = (processed / total) * 100
        bar_len = 40
        filled = int(bar_len * processed / total)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  Progress: [{bar}] {pct:.1f}%")
        print(f"  {processed} / {total} skills processed")
    print()
    
    # Stats
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  Orphans Remaining:  {orphans:>6}                               │")
    print(f"  │  Total Decisions:    {total_decisions:>6}                               │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Auto-Approved:      {auto_approved:>6}  ✅                            │")
    print(f"  │  Pending Review:     {pending:>6}  ⏳                            │")
    print(f"  │  Human Approved:     {approved:>6}  👍                            │")
    print(f"  │  Rejected:           {rejected:>6}  ❌                            │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()
    
    # Interaction stats per conversation
    print("  Conversations:")
    for name, stats in interaction_stats.items():
        completed = stats.get('completed', 0)
        running = stats.get('running', 0)
        pending_i = stats.get('pending', 0)
        failed = stats.get('failed', 0)
        short_name = name.replace('w3005_', '')
        print(f"    {short_name:<15}  ✓{completed:>3}  ⚡{running:>2}  ⏳{pending_i:>3}  ✗{failed:>2}")
    print()
    
    # Recent decisions
    if recent_decisions:
        print("  Recent Decisions:")
        print("  ─" * 35)
        for skill, parent, conf, status, created in recent_decisions[:5]:
            skill_short = (skill[:25] + '..') if len(skill) > 27 else skill
            parent_short = (parent[:15] + '..') if parent and len(parent) > 17 else (parent or 'N/A')
            status_icon = {'auto_approved': '✅', 'pending': '⏳', 'approved': '👍', 'rejected': '❌'}.get(status, '?')
            print(f"    {skill_short:<28} → {parent_short:<18} {conf:.2f} {status_icon}")
    print()


def main():
    parser = argparse.ArgumentParser(description='WF3005 Hierarchy Consultation Monitor')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=5, help='Refresh interval in seconds')
    args = parser.parse_args()
    
    try:
        if args.once:
            conn = get_db_connection()
            display_dashboard(conn)
            conn.close()
        else:
            while True:
                conn = get_db_connection()
                clear_screen()
                display_dashboard(conn)
                conn.close()
                print(f"  Refreshing in {args.interval}s... (Ctrl+C to exit)")
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n  Monitor stopped.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
