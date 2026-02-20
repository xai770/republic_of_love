"""
Messages router — unified inbox for yogi communications.

All actors (Doug, Sage, Sandy, Mysti, Mira) plus system and Y2Y
messages flow through this single API.

Sender types:
- doug: Research reports
- sage: Skill assessments, learning recommendations
- sandy: Market insights, job alerts
- mysti: Encouragement, motivational messages
- mira: Conversation follow-ups, FAQ answers
- adele: Application support messages
- system: Transactional notifications
- yogi: User-to-user messages (Y2Y)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])


# ============================================================
# Models
# ============================================================

SenderType = Literal["doug", "sage", "sandy", "mysti", "mira", "adele", "arden", "system", "yogi"]

class Message(BaseModel):
    message_id: int
    sender_type: str
    sender_user_id: Optional[int]
    posting_id: Optional[int]
    message_type: Optional[str]
    subject: Optional[str]
    body: str
    attachment_json: Optional[dict]
    is_read: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageSummary(BaseModel):
    message_id: int
    sender_type: str
    recipient_type: Optional[str] = None  # Set when message is TO an actor
    direction: str = "incoming"  # 'incoming' (from actor/user) or 'outgoing' (to actor)
    subject: Optional[str]
    body: str  # Full message body
    preview: str  # First ~100 chars of body (for sidebar)
    posting_id: Optional[int]
    is_read: bool
    created_at: datetime


class MessageList(BaseModel):
    messages: List[MessageSummary]
    total: int
    unread_count: int


class UnreadCounts(BaseModel):
    total: int
    by_sender: dict  # {"doug": 2, "sage": 1, ...}


class SendMessageRequest(BaseModel):
    recipient_user_id: Optional[int] = None  # For Y2Y messages
    recipient_type: Optional[SenderType] = None  # For messages to actors (doug, mira, etc.)
    subject: Optional[str] = None
    body: str
    posting_id: Optional[int] = None  # If discussing a specific posting


class MarkReadRequest(BaseModel):
    message_ids: List[int]


# ============================================================
# Endpoints
# ============================================================

@router.get("/", response_model=MessageList)
def list_messages(
    sender_type: Optional[SenderType] = None,
    posting_id: Optional[int] = None,
    unread_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    List messages for the current user.
    
    Filters:
    - sender_type: Filter by sender (doug, sage, etc.)
    - posting_id: Filter messages about a specific posting
    - unread_only: Only show unread messages
    """
    cur = conn.cursor()
    user_id = user["user_id"]
    
    # Build query with filters
    where_clauses = ["user_id = %s"]
    params = [user_id]
    
    if sender_type:
        where_clauses.append("sender_type = %s")
        params.append(sender_type)
    
    if posting_id:
        where_clauses.append("posting_id = %s")
        params.append(posting_id)
    
    if unread_only:
        where_clauses.append("read_at IS NULL")
    
    where_sql = " AND ".join(where_clauses)
    
    # Get total count
    cur.execute(f"""
        SELECT COUNT(*) as cnt FROM yogi_messages WHERE {where_sql}
    """, params)
    total = cur.fetchone()["cnt"]
    
    # Get unread count (for this filter set)
    cur.execute(f"""
        SELECT COUNT(*) as cnt FROM yogi_messages 
        WHERE {where_sql} AND read_at IS NULL
    """, params)
    unread_count = cur.fetchone()["cnt"]
    
    # Get messages
    cur.execute(f"""
        SELECT 
            message_id, sender_type, recipient_type, subject, body, posting_id,
            read_at IS NOT NULL as is_read, created_at
        FROM yogi_messages
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    
    messages = []
    for row in cur.fetchall():
        preview = row["body"][:100] + "..." if len(row["body"]) > 100 else row["body"]
        # Strip markdown for preview
        preview = preview.replace("#", "").replace("*", "").strip()
        
        # Determine direction: outgoing if recipient_type is set (message TO actor)
        direction = "outgoing" if row["recipient_type"] else "incoming"
        
        messages.append(MessageSummary(
            message_id=row["message_id"],
            sender_type=row["recipient_type"] or row["sender_type"],  # Show actor name for grouping
            recipient_type=row["recipient_type"],
            direction=direction,
            subject=row["subject"],
            body=row["body"],
            preview=preview,
            posting_id=row["posting_id"],
            is_read=row["is_read"],
            created_at=row["created_at"]
        ))
    
    return MessageList(
        messages=messages,
        total=total,
        unread_count=unread_count
    )


@router.get("/unread-counts", response_model=UnreadCounts)
def get_unread_counts(
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Get unread message counts, grouped by sender type.
    Useful for showing badges in UI.
    """
    cur = conn.cursor()
    user_id = user["user_id"]
    
    cur.execute("""
        SELECT sender_type, COUNT(*) as cnt
        FROM yogi_messages
        WHERE user_id = %s AND read_at IS NULL
        GROUP BY sender_type
    """, (user_id,))
    
    by_sender = {}
    total = 0
    for row in cur.fetchall():
        by_sender[row["sender_type"]] = row["cnt"]
        total += row["cnt"]
    
    return UnreadCounts(total=total, by_sender=by_sender)


@router.get("/{message_id}", response_model=Message)
def get_message(
    message_id: int,
    mark_read: bool = True,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Get a single message by ID.
    Automatically marks as read unless mark_read=false.
    """
    cur = conn.cursor()
    user_id = user["user_id"]
    
    cur.execute("""
        SELECT * FROM yogi_messages
        WHERE message_id = %s AND user_id = %s
    """, (message_id, user_id))
    
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Auto mark as read
    if mark_read and row["read_at"] is None:
        cur.execute("""
            UPDATE yogi_messages
            SET read_at = NOW()
            WHERE message_id = %s
        """, (message_id,))
        conn.commit()
    
    return Message(
        message_id=row["message_id"],
        sender_type=row["sender_type"],
        sender_user_id=row["sender_user_id"],
        posting_id=row["posting_id"],
        message_type=row["message_type"],
        subject=row["subject"],
        body=row["body"],
        attachment_json=row["attachment_json"],
        is_read=True if mark_read else row["read_at"] is not None,
        created_at=row["created_at"]
    )


@router.post("/mark-read")
def mark_messages_read(
    request: MarkReadRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Mark multiple messages as read."""
    cur = conn.cursor()
    user_id = user["user_id"]
    
    cur.execute("""
        UPDATE yogi_messages
        SET read_at = NOW()
        WHERE message_id = ANY(%s) AND user_id = %s AND read_at IS NULL
        RETURNING message_id
    """, (request.message_ids, user_id))
    
    updated = [row["message_id"] for row in cur.fetchall()]
    conn.commit()
    
    return {"marked_read": updated, "count": len(updated)}


@router.post("/mark-all-read")
def mark_all_read(
    sender_type: Optional[SenderType] = None,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Mark all messages as read.
    Optionally filter by sender_type (e.g., mark all Doug messages read).
    """
    cur = conn.cursor()
    user_id = user["user_id"]
    
    if sender_type:
        cur.execute("""
            UPDATE yogi_messages
            SET read_at = NOW()
            WHERE user_id = %s AND sender_type = %s AND read_at IS NULL
        """, (user_id, sender_type))
    else:
        cur.execute("""
            UPDATE yogi_messages
            SET read_at = NOW()
            WHERE user_id = %s AND read_at IS NULL
        """, (user_id,))
    
    count = cur.rowcount
    conn.commit()
    
    return {"marked_read": count}


@router.post("/send")
def send_message(
    request: SendMessageRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Send a message to another yogi OR to an actor.
    
    - recipient_user_id: Send to another human user (Y2Y)
    - recipient_type: Send to an actor (doug, mira, etc.)
    
    Everyone is a citizen - humans and AIs alike can exchange messages.
    """
    cur = conn.cursor()
    sender_id = user["user_id"]
    
    # Must specify either recipient_user_id OR recipient_type
    if not request.recipient_user_id and not request.recipient_type:
        raise HTTPException(status_code=400, detail="Must specify recipient_user_id or recipient_type")
    
    if request.recipient_type:
        # Message TO an actor (doug, mira, etc.)
        # Store in sender's inbox with recipient_type set
        cur.execute("""
            INSERT INTO yogi_messages (
                user_id, sender_type, sender_user_id, posting_id,
                message_type, subject, body, recipient_type
            ) VALUES (%s, 'yogi', %s, %s, 'to_actor', %s, %s, %s)
            RETURNING message_id
        """, (
            sender_id,  # Stored in sender's inbox
            sender_id,
            request.posting_id,
            request.subject,
            request.body,
            request.recipient_type
        ))
        
        message_id = cur.fetchone()["message_id"]
        conn.commit()
        
        logger.info(f"Message to actor: user {sender_id} → {request.recipient_type}, message_id={message_id}")
        return {"message_id": message_id, "sent": True, "recipient_type": request.recipient_type}
    
    else:
        # Y2Y message to another user
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (request.recipient_user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        if request.recipient_user_id == sender_id:
            raise HTTPException(status_code=400, detail="Cannot send message to yourself")
        
        cur.execute("""
            INSERT INTO yogi_messages (
                user_id, sender_type, sender_user_id, posting_id,
                message_type, subject, body
            ) VALUES (%s, 'yogi', %s, %s, 'y2y', %s, %s)
            RETURNING message_id
        """, (
            request.recipient_user_id,
            sender_id,
            request.posting_id,
            request.subject,
            request.body
        ))
        
        message_id = cur.fetchone()["message_id"]
        conn.commit()
        
        logger.info(f"Y2Y message sent: {sender_id} → {request.recipient_user_id}, message_id={message_id}")
        return {"message_id": message_id, "sent": True}


@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Delete a message (soft delete would be better, but KISS for now).
    """
    cur = conn.cursor()
    user_id = user["user_id"]
    
    cur.execute("""
        DELETE FROM yogi_messages
        WHERE message_id = %s AND user_id = %s
        RETURNING message_id
    """, (message_id, user_id))
    
    deleted = cur.fetchone()
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    
    conn.commit()
    return {"deleted": message_id}


# ============================================================
# Actor-specific endpoints (for posting-context messages)
# ============================================================

@router.get("/posting/{posting_id}")
def get_messages_for_posting(
    posting_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Get all messages related to a specific posting.
    Useful for showing Doug's research, Sage's skill analysis, etc.
    in the posting detail view.
    """
    cur = conn.cursor()
    user_id = user["user_id"]
    
    cur.execute("""
        SELECT 
            message_id, sender_type, message_type, subject, body,
            read_at IS NOT NULL as is_read, created_at
        FROM yogi_messages
        WHERE user_id = %s AND posting_id = %s
        ORDER BY created_at DESC
    """, (user_id, posting_id))
    
    messages = []
    for row in cur.fetchall():
        messages.append({
            "message_id": row["message_id"],
            "sender_type": row["sender_type"],
            "message_type": row["message_type"],
            "subject": row["subject"],
            "body": row["body"],
            "is_read": row["is_read"],
            "created_at": row["created_at"].isoformat()
        })
    
    return {"posting_id": posting_id, "messages": messages}
