#!/usr/bin/env python3
"""
Y2Y Connection Detector Actor

Finds pairs of yogis interested in the same posting
and creates connection invitations.

Usage:
    python3 actors/y2y__match_detector_C.py          # Scan all postings
    python3 actors/y2y__match_detector_C.py 12345   # Scan specific posting
    python3 actors/y2y__match_detector_C.py --batch 50  # Process up to 50 pairs

This is a C (Create) actor - it creates yogi_connections records.
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection_raw
from core.logging_config import get_logger

logger = get_logger(__name__)


def find_unconnected_pairs(conn, posting_id: int = None, limit: int = 50):
    """Find yogi pairs interested in same posting who aren't connected yet."""
    cur = conn.cursor()
    
    params = []
    where_clause = "WHERE i.is_interested = TRUE"
    
    if posting_id:
        where_clause += " AND i.posting_id = %s"
        params.append(posting_id)
    
    cur.execute(f"""
        WITH interested AS (
            SELECT posting_id, user_id
            FROM user_posting_interactions i
            {where_clause}
        ),
        pairs AS (
            SELECT 
                a.posting_id,
                LEAST(a.user_id, b.user_id) as yogi_a_id,
                GREATEST(a.user_id, b.user_id) as yogi_b_id
            FROM interested a
            JOIN interested b ON a.posting_id = b.posting_id AND a.user_id < b.user_id
        )
        SELECT p.*, pos.job_title
        FROM pairs p
        JOIN postings pos ON p.posting_id = pos.posting_id
        LEFT JOIN yogi_connections c 
            ON p.posting_id = c.posting_id 
            AND p.yogi_a_id = c.yogi_a_id 
            AND p.yogi_b_id = c.yogi_b_id
        WHERE c.connection_id IS NULL
        LIMIT %s
    """, params + [limit])
    
    return cur.fetchall()


def send_invite_message(cur, user_id: int, posting_id: int, job_title: str):
    """Send Y2Y connection invite to a user."""
    
    cur.execute("""
        INSERT INTO yogi_messages (
            user_id, sender_type, posting_id, message_type, subject, body
        ) VALUES (%s, 'system', %s, 'y2y_invite', %s, %s)
        RETURNING message_id
    """, (
        user_id,
        posting_id,
        "🤝 Another yogi is interested in the same job!",
        f"Another yogi is also interested in **{job_title}**.\n\n"
        f"Would you like to connect anonymously? You can:\n"
        f"- Share tips and insights about the company\n"
        f"- Prep for interviews together\n"  
        f"- Or just know you're not alone in this\n\n"
        f"Go to **Messages → Y2Y Connections** to respond.\n\n"
        f"*Your identity stays hidden until you choose to reveal it.*"
    ))
    return cur.fetchone()['message_id']


def create_connection(conn, pair: dict) -> dict:
    """Create a Y2Y connection and send invites to both yogis."""
    cur = conn.cursor()
    
    # Create connection record
    cur.execute("""
        INSERT INTO yogi_connections (posting_id, yogi_a_id, yogi_b_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (posting_id, yogi_a_id, yogi_b_id) DO NOTHING
        RETURNING connection_id
    """, (pair['posting_id'], pair['yogi_a_id'], pair['yogi_b_id']))
    
    result = cur.fetchone()
    if not result:
        return None  # Already exists
    
    connection_id = result['connection_id']
    
    # Send invites
    job_title = pair['job_title'] or 'a position'
    
    msg_a = send_invite_message(cur, pair['yogi_a_id'], pair['posting_id'], job_title)
    msg_b = send_invite_message(cur, pair['yogi_b_id'], pair['posting_id'], job_title)
    
    conn.commit()
    
    return {
        'connection_id': connection_id,
        'posting_id': pair['posting_id'],
        'yogi_a_id': pair['yogi_a_id'],
        'yogi_b_id': pair['yogi_b_id'],
        'message_ids': [msg_a, msg_b]
    }


def main():
    parser = argparse.ArgumentParser(description="Y2Y Connection Detector")
    parser.add_argument('posting_id', nargs='?', type=int, help="Specific posting to check")
    parser.add_argument('--batch', '-b', type=int, default=50, help="Max pairs to process")
    args = parser.parse_args()
    
    conn = get_connection_raw()
    
    # Find pairs
    pairs = find_unconnected_pairs(conn, args.posting_id, args.batch)
    
    if not pairs:
        print("No new Y2Y matches found")
        return
    
    print(f"Found {len(pairs)} potential Y2Y connections")
    
    # Create connections
    created = 0
    for pair in pairs:
        result = create_connection(conn, pair)
        if result:
            created += 1
            print(f"✅ Connection {result['connection_id']}: "
                  f"Posting {result['posting_id']} ({pair['job_title'][:30]}...) - "
                  f"Users {result['yogi_a_id']} ↔ {result['yogi_b_id']}")
    
    print(f"\nCreated {created} new Y2Y connections")


if __name__ == '__main__':
    main()
