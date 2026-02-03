"""
Y2Y (Yogi-to-Yogi) connection router.

When two yogis are interested in the same posting, they can connect
anonymously to share insights, prep together, or just commiserate.

Flow:
1. System detects overlap (actor or trigger)
2. Both yogis get "Someone else is interested - connect?" message
3. Both accept → connection established
4. They chat through yogi_messages with anonymous aliases
5. Can reveal real names if they choose
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/y2y", tags=["yogi-to-yogi"])


# ============================================================
# Models
# ============================================================

class ConnectionRequest(BaseModel):
    posting_id: int


class ConnectionResponse(BaseModel):
    action: Literal["accept", "decline"]


class Connection(BaseModel):
    connection_id: int
    posting_id: int
    job_title: Optional[str]
    posting_name: Optional[str]  # Company/source name
    my_status: str
    their_status: str
    my_alias: str
    their_alias: str
    their_revealed_name: Optional[str]  # Only if they revealed
    is_active: bool
    created_at: datetime
    connected_at: Optional[datetime]


class ChatMessage(BaseModel):
    body: str


# ============================================================
# Helper Functions
# ============================================================

def get_my_role(conn, connection_id: int, user_id: int) -> Optional[str]:
    """Determine if user is yogi_a or yogi_b in this connection."""
    cur = conn.cursor()
    cur.execute("""
        SELECT yogi_a_id, yogi_b_id FROM yogi_connections WHERE connection_id = %s
    """, (connection_id,))
    row = cur.fetchone()
    if not row:
        return None
    if row['yogi_a_id'] == user_id:
        return 'a'
    if row['yogi_b_id'] == user_id:
        return 'b'
    return None


def send_system_message(cur, user_id: int, posting_id: int, subject: str, body: str):
    """Send a system message to a user about a posting."""
    cur.execute("""
        INSERT INTO yogi_messages (user_id, sender_type, posting_id, message_type, subject, body)
        VALUES (%s, 'system', %s, 'y2y_invite', %s, %s)
        RETURNING message_id
    """, (user_id, posting_id, subject, body))
    return cur.fetchone()['message_id']


# ============================================================
# Endpoints
# ============================================================

@router.get("/connections")
def list_connections(
    status: Optional[str] = None,  # pending, active, all
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """List all Y2Y connections for the current user."""
    cur = conn.cursor()
    user_id = user['user_id']
    
    # Build query to find connections where user is either yogi_a or yogi_b
    cur.execute("""
        SELECT 
            c.*,
            p.job_title,
            p.posting_name,
            CASE WHEN c.yogi_a_id = %s THEN 'a' ELSE 'b' END as my_role
        FROM yogi_connections c
        JOIN postings p ON c.posting_id = p.posting_id
        WHERE (c.yogi_a_id = %s OR c.yogi_b_id = %s)
          AND c.expires_at > NOW()
        ORDER BY c.created_at DESC
    """, (user_id, user_id, user_id))
    
    connections = []
    for row in cur.fetchall():
        my_role = row['my_role']
        
        # Determine statuses and aliases based on role
        if my_role == 'a':
            my_status = row['yogi_a_status']
            their_status = row['yogi_b_status']
            my_alias = row['yogi_a_alias']
            their_alias = row['yogi_b_alias']
            their_revealed = row['yogi_b_revealed']
            their_id = row['yogi_b_id']
        else:
            my_status = row['yogi_b_status']
            their_status = row['yogi_a_status']
            my_alias = row['yogi_b_alias']
            their_alias = row['yogi_a_alias']
            their_revealed = row['yogi_a_revealed']
            their_id = row['yogi_a_id']
        
        # Filter by status if requested
        is_active = my_status == 'accepted' and their_status == 'accepted'
        is_pending = my_status == 'pending' or their_status == 'pending'
        
        if status == 'pending' and not is_pending:
            continue
        if status == 'active' and not is_active:
            continue
        
        # Get their revealed name if applicable
        their_revealed_name = None
        if their_revealed:
            cur.execute("SELECT display_name FROM users WHERE user_id = %s", (their_id,))
            name_row = cur.fetchone()
            if name_row:
                their_revealed_name = name_row['display_name']
        
        connections.append(Connection(
            connection_id=row['connection_id'],
            posting_id=row['posting_id'],
            job_title=row['job_title'],
            posting_name=row['posting_name'],
            my_status=my_status,
            their_status=their_status,
            my_alias=my_alias,
            their_alias=their_alias,
            their_revealed_name=their_revealed_name,
            is_active=is_active,
            created_at=row['created_at'],
            connected_at=row['connected_at']
        ))
    
    return {"connections": connections}


@router.post("/connections/{connection_id}/respond")
def respond_to_connection(
    connection_id: int,
    response: ConnectionResponse,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Accept or decline a connection request."""
    cur = conn.cursor()
    user_id = user['user_id']
    
    # Find user's role in this connection
    role = get_my_role(conn, connection_id, user_id)
    if not role:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    status_col = f'yogi_{role}_status'
    new_status = response.action + 'ed'  # accept → accepted, decline → declined
    
    # Update status
    cur.execute(f"""
        UPDATE yogi_connections
        SET {status_col} = %s
        WHERE connection_id = %s
        RETURNING yogi_a_status, yogi_b_status, yogi_a_id, yogi_b_id, posting_id
    """, (new_status, connection_id))
    
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Check if both accepted → mark as connected
    if row['yogi_a_status'] == 'accepted' and row['yogi_b_status'] == 'accepted':
        cur.execute("""
            UPDATE yogi_connections SET connected_at = NOW() WHERE connection_id = %s
        """, (connection_id,))
        
        # Notify both that connection is active
        other_id = row['yogi_b_id'] if role == 'a' else row['yogi_a_id']
        
        # Get posting info for message
        cur.execute("SELECT job_title FROM postings WHERE posting_id = %s", (row['posting_id'],))
        posting = cur.fetchone()
        job_title = posting['job_title'] if posting else 'a position'
        
        # Message to the other yogi
        send_system_message(
            cur, other_id, row['posting_id'],
            f"🤝 Connection established!",
            f"Great news! Your connection request for **{job_title}** was accepted.\n\n"
            f"You can now chat anonymously. Go to Y2Y Connections to start the conversation.\n\n"
            f"*Remember: You're both in this together. Be kind, be helpful.*"
        )
        
        logger.info(f"Y2Y connection {connection_id} established between users {row['yogi_a_id']} and {row['yogi_b_id']}")
    
    conn.commit()
    
    return {
        "status": "ok",
        "connection_id": connection_id,
        "my_status": new_status,
        "connected": row['yogi_a_status'] == 'accepted' and row['yogi_b_status'] == 'accepted'
    }


@router.post("/connections/{connection_id}/chat")
def send_chat_message(
    connection_id: int,
    message: ChatMessage,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Send a message in a Y2Y chat."""
    cur = conn.cursor()
    user_id = user['user_id']
    
    # Verify user is part of this connection and it's active
    role = get_my_role(conn, connection_id, user_id)
    if not role:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    cur.execute("""
        SELECT * FROM yogi_connections WHERE connection_id = %s
    """, (connection_id,))
    row = cur.fetchone()
    
    if row['yogi_a_status'] != 'accepted' or row['yogi_b_status'] != 'accepted':
        raise HTTPException(status_code=400, detail="Connection not yet established")
    
    # Determine recipient and alias
    if role == 'a':
        recipient_id = row['yogi_b_id']
        sender_alias = row['yogi_a_alias']
    else:
        recipient_id = row['yogi_a_id']
        sender_alias = row['yogi_b_alias']
    
    # Send message as Y2Y type
    cur.execute("""
        INSERT INTO yogi_messages (
            user_id, sender_type, sender_user_id, posting_id,
            message_type, subject, body, attachment_json
        ) VALUES (%s, 'yogi', %s, %s, 'y2y_chat', %s, %s, %s)
        RETURNING message_id
    """, (
        recipient_id,
        user_id,
        row['posting_id'],
        f"Message from {sender_alias}",
        message.body,
        json.dumps({"connection_id": connection_id, "sender_alias": sender_alias})
    ))
    
    message_id = cur.fetchone()['message_id']
    conn.commit()
    
    logger.info(f"Y2Y message sent in connection {connection_id}: {user_id} → {recipient_id}")
    
    return {"status": "ok", "message_id": message_id}


@router.get("/connections/{connection_id}/chat")
def get_chat_history(
    connection_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get chat history for a Y2Y connection."""
    cur = conn.cursor()
    user_id = user['user_id']
    
    # Verify user is part of this connection
    role = get_my_role(conn, connection_id, user_id)
    if not role:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    cur.execute("""
        SELECT * FROM yogi_connections WHERE connection_id = %s
    """, (connection_id,))
    connection = cur.fetchone()
    
    # Get all messages between these two users for this posting
    yogi_a_id = connection['yogi_a_id']
    yogi_b_id = connection['yogi_b_id']
    posting_id = connection['posting_id']
    
    cur.execute("""
        SELECT 
            message_id, sender_user_id, body, attachment_json, created_at
        FROM yogi_messages
        WHERE message_type = 'y2y_chat'
          AND posting_id = %s
          AND (
              (user_id = %s AND sender_user_id = %s) OR
              (user_id = %s AND sender_user_id = %s)
          )
        ORDER BY created_at ASC
    """, (posting_id, yogi_a_id, yogi_b_id, yogi_b_id, yogi_a_id))
    
    messages = []
    for row in cur.fetchall():
        is_mine = row['sender_user_id'] == user_id
        attachment = row['attachment_json'] or {}
        
        messages.append({
            "message_id": row['message_id'],
            "is_mine": is_mine,
            "sender_alias": attachment.get('sender_alias', 'Unknown'),
            "body": row['body'],
            "created_at": row['created_at'].isoformat()
        })
    
    return {
        "connection_id": connection_id,
        "my_alias": connection['yogi_a_alias'] if role == 'a' else connection['yogi_b_alias'],
        "their_alias": connection['yogi_b_alias'] if role == 'a' else connection['yogi_a_alias'],
        "messages": messages
    }


@router.post("/connections/{connection_id}/reveal")
def reveal_identity(
    connection_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Reveal your real name to the other yogi."""
    cur = conn.cursor()
    user_id = user['user_id']
    
    role = get_my_role(conn, connection_id, user_id)
    if not role:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    revealed_col = f'yogi_{role}_revealed'
    
    cur.execute(f"""
        UPDATE yogi_connections
        SET {revealed_col} = TRUE
        WHERE connection_id = %s
        RETURNING *
    """, (connection_id,))
    
    row = cur.fetchone()
    
    # Get user's display name
    cur.execute("SELECT display_name FROM users WHERE user_id = %s", (user_id,))
    user_row = cur.fetchone()
    display_name = user_row['display_name'] if user_row else 'A fellow yogi'
    
    # Notify the other yogi
    other_id = row['yogi_b_id'] if role == 'a' else row['yogi_a_id']
    my_alias = row['yogi_a_alias'] if role == 'a' else row['yogi_b_alias']
    
    send_system_message(
        cur, other_id, row['posting_id'],
        f"🎭 {my_alias} revealed their identity!",
        f"**{my_alias}** has chosen to reveal their real name to you.\n\n"
        f"They are: **{display_name}**\n\n"
        f"*You can reveal your identity too, or continue anonymously. Your choice.*"
    )
    
    conn.commit()
    
    logger.info(f"User {user_id} revealed identity in connection {connection_id}")
    
    return {"status": "ok", "revealed": True, "display_name": display_name}


# ============================================================
# Detection: Find potential connections (called by actor/trigger)
# ============================================================

@router.post("/detect-matches")
def detect_connection_matches(
    posting_id: Optional[int] = None,
    user: dict = Depends(require_user),  # Requires auth, but could be system
    conn = Depends(get_db)
):
    """
    Find yogis interested in the same posting who haven't been connected yet.
    Creates connection records and sends invites.
    
    Can be called by an actor or triggered when someone expresses interest.
    """
    cur = conn.cursor()
    
    # Find postings with 2+ interested yogis who aren't already connected
    where_clause = "WHERE i.is_interested = TRUE"
    params = []
    
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
        SELECT p.*
        FROM pairs p
        LEFT JOIN yogi_connections c 
            ON p.posting_id = c.posting_id 
            AND p.yogi_a_id = c.yogi_a_id 
            AND p.yogi_b_id = c.yogi_b_id
        WHERE c.connection_id IS NULL
        LIMIT 50
    """, params)
    
    new_pairs = cur.fetchall()
    created = []
    
    for pair in new_pairs:
        # Create connection record
        cur.execute("""
            INSERT INTO yogi_connections (posting_id, yogi_a_id, yogi_b_id)
            VALUES (%s, %s, %s)
            RETURNING connection_id
        """, (pair['posting_id'], pair['yogi_a_id'], pair['yogi_b_id']))
        
        conn_id = cur.fetchone()['connection_id']
        
        # Get posting info
        cur.execute("SELECT job_title, posting_name FROM postings WHERE posting_id = %s", (pair['posting_id'],))
        posting = cur.fetchone()
        job_title = posting['job_title'] if posting else 'a position'
        posting_name = posting['posting_name'] if posting else ''
        
        # Send invites to both yogis
        invite_body = (
            f"Another yogi is also interested in **{job_title}**"
            + (f" at {posting_name}" if posting_name else "") + ".\n\n"
            f"Would you like to connect anonymously? You can:\n"
            f"- Share tips and insights\n"
            f"- Prep for interviews together\n"
            f"- Or just know you're not alone\n\n"
            f"*Your identity stays hidden until you choose to reveal it.*"
        )
        
        send_system_message(
            cur, pair['yogi_a_id'], pair['posting_id'],
            "🤝 Another yogi is interested in the same job!",
            invite_body
        )
        
        send_system_message(
            cur, pair['yogi_b_id'], pair['posting_id'],
            "🤝 Another yogi is interested in the same job!",
            invite_body
        )
        
        created.append({
            "connection_id": conn_id,
            "posting_id": pair['posting_id'],
            "yogi_a_id": pair['yogi_a_id'],
            "yogi_b_id": pair['yogi_b_id']
        })
        
        logger.info(f"Created Y2Y connection {conn_id} for posting {pair['posting_id']}")
    
    conn.commit()
    
    return {"created": len(created), "connections": created}
