"""
Notifications router — in-app message system.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from api.deps import get_db, require_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class Notification(BaseModel):
    notification_id: int
    type: str
    title: str
    message: Optional[str]
    link: Optional[str]
    read_at: Optional[datetime]
    created_at: datetime


class NotificationCount(BaseModel):
    unread: int
    total: int


@router.get("/", response_model=List[Notification])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, le=100),
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Get user's notifications."""
    with conn.cursor() as cur:
        if unread_only:
            cur.execute("""
                SELECT notification_id, type, title, message, link, read_at, created_at
                FROM notifications
                WHERE user_id = %s AND read_at IS NULL
                ORDER BY created_at DESC
                LIMIT %s
            """, (user['user_id'], limit))
        else:
            cur.execute("""
                SELECT notification_id, type, title, message, link, read_at, created_at
                FROM notifications
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user['user_id'], limit))
        
        return [Notification(**row) for row in cur.fetchall()]


@router.get("/count", response_model=NotificationCount)
def get_notification_count(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Get count of unread notifications (for badge)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE read_at IS NULL) as unread,
                COUNT(*) as total
            FROM notifications
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        return NotificationCount(unread=row['unread'], total=row['total'])


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Mark a notification as read."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE notifications
            SET read_at = NOW()
            WHERE notification_id = %s AND user_id = %s AND read_at IS NULL
            RETURNING notification_id
        """, (notification_id, user['user_id']))
        
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Notification not found or already read")
        
        conn.commit()
        return {"status": "ok"}


@router.post("/read-all")
def mark_all_read(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Mark all notifications as read."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE notifications
            SET read_at = NOW()
            WHERE user_id = %s AND read_at IS NULL
        """, (user['user_id'],))
        count = cur.rowcount
        conn.commit()
        return {"status": "ok", "marked": count}


# --- Notification Creation (internal use) ---

def create_notification(
    conn,
    user_id: int,
    type: str,
    title: str,
    message: str = None,
    link: str = None
) -> int:
    """Create a notification for a user. Returns notification_id."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO notifications (user_id, type, title, message, link)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING notification_id
        """, (user_id, type, title, message, link))
        notification_id = cur.fetchone()['notification_id']
        conn.commit()
        return notification_id


def notify_new_matches(conn, user_id: int, match_count: int, top_match: dict = None):
    """
    Create notification for new matches.
    Called by daily_match.py after computing matches.
    """
    if match_count == 0:
        return
    
    if match_count == 1 and top_match:
        title = f"New match: {top_match['title']}"
        message = f"{top_match['score']:.0%} match at {top_match['company']}"
        link = f"/report/{top_match['match_id']}"
    else:
        title = f"🎯 {match_count} new matches"
        message = "Check your dashboard for new job opportunities"
        link = "/matches"
    
    create_notification(conn, user_id, "match_new", title, message, link)


def notify_high_match(conn, user_id: int, match: dict):
    """
    Create notification for a high-quality match (≥85%).
    Called immediately when a great match is found.
    """
    title = f"✨ Great match: {match['title']}"
    message = f"{match['score']:.0%} match at {match['company']} — {match['recommendation']}"
    link = f"/report/{match['match_id']}"
    
    create_notification(conn, user_id, "match_high", title, message, link)


# --- P0.8: Notification Consent Management ---

class NotificationConsentUpdate(BaseModel):
    notification_email: Optional[str] = None
    grant_consent: Optional[bool] = None
    preferences: Optional[dict] = None


class NotificationConsentResponse(BaseModel):
    notification_email: Optional[str]
    notification_consent_at: Optional[datetime]
    notification_preferences: dict


@router.get("/consent", response_model=NotificationConsentResponse)
def get_notification_consent(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Get current notification consent settings."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT notification_email, notification_consent_at, notification_preferences
            FROM users
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        
        return NotificationConsentResponse(
            notification_email=row['notification_email'],
            notification_consent_at=row['notification_consent_at'],
            notification_preferences=row['notification_preferences'] or {}
        )


@router.put("/consent")
def update_notification_consent(
    data: NotificationConsentUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Update notification consent settings.
    
    - Set grant_consent=True with an email to grant consent
    - Set preferences to update notification preferences
    - Set notification_email to update email address
    """
    with conn.cursor() as cur:
        updates = []
        params = []
        
        if data.notification_email is not None:
            updates.append("notification_email = %s")
            params.append(data.notification_email)
        
        if data.grant_consent:
            # Granting consent - set timestamp
            updates.append("notification_consent_at = NOW()")
        
        if data.preferences is not None:
            updates.append("notification_preferences = %s")
            params.append(json.dumps(data.preferences))
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        params.append(user['user_id'])
        
        cur.execute(f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE user_id = %s
            RETURNING notification_email, notification_consent_at, notification_preferences
        """, params)
        
        row = cur.fetchone()
        conn.commit()
        
        return {
            "status": "ok",
            "notification_email": row['notification_email'],
            "notification_consent_at": row['notification_consent_at'].isoformat() if row['notification_consent_at'] else None,
            "notification_preferences": row['notification_preferences'] or {}
        }


@router.delete("/consent")
def revoke_notification_consent(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Revoke notification consent (GDPR Art. 7(3)).
    Sets consent timestamp to NULL but keeps preferences for potential re-consent.
    """
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE users
            SET notification_consent_at = NULL
            WHERE user_id = %s
        """, (user['user_id'],))
        
        conn.commit()
        
        return {"status": "ok", "message": "Consent revoked"}

