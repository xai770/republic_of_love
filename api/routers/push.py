"""
Push notifications router — Web Push for talent.yoga.

Uses VAPID (Voluntary Application Server Identification) for web push.
Works without storing email addresses - privacy friendly.

Events:
- New matches found
- Mira has an answer
- Application status changes (if trackable)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import json

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/push", tags=["push"])


# ============================================================================
# CONFIGURATION
# ============================================================================

# VAPID keys from environment
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
VAPID_SUBJECT = os.getenv('VAPID_SUBJECT', 'mailto:hello@talent.yoga')

PUSH_ENABLED = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)


# ============================================================================
# MODELS
# ============================================================================

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict  # p256dh, auth


class SubscriptionResponse(BaseModel):
    subscribed: bool
    vapid_public_key: Optional[str]


class NotificationPayload(BaseModel):
    title: str
    body: str
    icon: Optional[str] = "/icons/mira-192.png"
    badge: Optional[str] = "/icons/badge-72.png"
    tag: Optional[str] = None  # Group notifications
    url: Optional[str] = None  # Click action URL
    data: Optional[dict] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/vapid-key")
def get_vapid_key():
    """
    Get VAPID public key for push subscription.
    
    Frontend uses this to subscribe to push notifications.
    """
    return {
        "vapid_public_key": VAPID_PUBLIC_KEY,
        "push_enabled": PUSH_ENABLED
    }


@router.post("/subscribe", response_model=SubscriptionResponse)
def subscribe_to_push(
    subscription: PushSubscription,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Store push subscription for user.
    
    Called when user grants notification permission in browser.
    """
    if not PUSH_ENABLED:
        return SubscriptionResponse(
            subscribed=False,
            vapid_public_key=None
        )
    
    with conn.cursor() as cur:
        # Store or update subscription
        cur.execute("""
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, endpoint) DO UPDATE
            SET p256dh = EXCLUDED.p256dh,
                auth = EXCLUDED.auth,
                last_used_at = NOW()
            RETURNING subscription_id
        """, (
            user['user_id'],
            subscription.endpoint,
            subscription.keys.get('p256dh'),
            subscription.keys.get('auth')
        ))
        
        conn.commit()
        logger.info(f"Push subscription stored for user {user['user_id']}")
    
    return SubscriptionResponse(
        subscribed=True,
        vapid_public_key=VAPID_PUBLIC_KEY
    )


@router.delete("/unsubscribe")
def unsubscribe_from_push(
    endpoint: str,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Remove push subscription.
    
    Called when user revokes notification permission.
    """
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM push_subscriptions
            WHERE user_id = %s AND endpoint = %s
        """, (user['user_id'], endpoint))
        
        deleted = cur.rowcount
        conn.commit()
        
        logger.info(f"Push subscription removed for user {user['user_id']}: {deleted} rows")
    
    return {"status": "ok", "deleted": deleted > 0}


@router.get("/subscriptions")
def get_subscriptions(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Get user's push subscriptions (for debugging/management)."""
    with conn.cursor() as cur:
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'push_subscriptions'
            ) as exists
        """)
        if not cur.fetchone()['exists']:
            return {"subscriptions": [], "count": 0}
        
        cur.execute("""
            SELECT subscription_id, endpoint, created_at, last_used_at
            FROM push_subscriptions
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user['user_id'],))
        
        subs = [
            {
                "id": r['subscription_id'],
                "endpoint_preview": r['endpoint'][:50] + "...",
                "created_at": r['created_at'].isoformat() if r['created_at'] else None,
                "last_used_at": r['last_used_at'].isoformat() if r['last_used_at'] else None
            }
            for r in cur.fetchall()
        ]
    
    return {"subscriptions": subs, "count": len(subs)}


# ============================================================================
# PUSH SENDING (internal functions)
# ============================================================================

def send_push_notification(user_id: int, notification: NotificationPayload, conn) -> int:
    """
    Send push notification to all user's subscribed devices.
    
    Returns number of notifications sent successfully.
    """
    if not PUSH_ENABLED:
        logger.warning("Push not enabled, skipping notification")
        return 0
    
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error("pywebpush not installed")
        return 0
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT subscription_id, endpoint, p256dh, auth
            FROM push_subscriptions
            WHERE user_id = %s
        """, (user_id,))
        
        subscriptions = cur.fetchall()
        
        if not subscriptions:
            return 0
        
        sent = 0
        failed_ids = []
        
        payload = json.dumps({
            "title": notification.title,
            "body": notification.body,
            "icon": notification.icon,
            "badge": notification.badge,
            "tag": notification.tag,
            "data": {
                "url": notification.url,
                **(notification.data or {})
            }
        })
        
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub['endpoint'],
                        "keys": {
                            "p256dh": sub['p256dh'],
                            "auth": sub['auth']
                        }
                    },
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": VAPID_SUBJECT}
                )
                sent += 1
                
                # Update last_used_at
                cur.execute("""
                    UPDATE push_subscriptions
                    SET last_used_at = NOW()
                    WHERE subscription_id = %s
                """, (sub['subscription_id'],))
                
            except WebPushException as e:
                logger.warning(f"Push failed for subscription {sub['subscription_id']}: {e}")
                
                # If subscription is gone (410 Gone), remove it
                if e.response and e.response.status_code == 410:
                    failed_ids.append(sub['subscription_id'])
            except Exception as e:
                logger.error(f"Push error: {e}")
        
        # Clean up failed subscriptions
        if failed_ids:
            cur.execute("""
                DELETE FROM push_subscriptions
                WHERE subscription_id = ANY(%s)
            """, (failed_ids,))
            logger.info(f"Removed {len(failed_ids)} expired push subscriptions")
        
        conn.commit()
        
        logger.info(f"Sent {sent}/{len(subscriptions)} push notifications to user {user_id}")
        return sent


# ============================================================================
# NOTIFICATION TRIGGERS (called by other parts of the system)
# ============================================================================

def notify_new_matches(user_id: int, match_count: int, conn):
    """Send push notification for new matches."""
    notification = NotificationPayload(
        title="Neue Matches! 🎯",
        body=f"{match_count} neue passende Jobs gefunden",
        tag="new-matches",
        url="/matches"
    )
    return send_push_notification(user_id, notification, conn)


def notify_mira_answer(user_id: int, question_preview: str, conn):
    """Send push notification when Mira has an answer to a logged question."""
    notification = NotificationPayload(
        title="Mira hat geantwortet 💬",
        body=f"Antwort auf: {question_preview[:50]}...",
        tag="mira-answer",
        url="/chat"
    )
    return send_push_notification(user_id, notification, conn)


def notify_application_update(user_id: int, job_title: str, status: str, conn):
    """Send push notification for application status change."""
    status_messages = {
        'viewed': '👀 wurde angesehen',
        'shortlisted': '⭐ auf der Shortlist',
        'interview': '🎤 Interview-Einladung!',
        'offer': '🎉 Angebot erhalten!',
        'rejected': '❌ leider abgesagt'
    }
    
    msg = status_messages.get(status, f'Status: {status}')
    
    notification = NotificationPayload(
        title=f"Bewerbung: {job_title[:30]}",
        body=msg,
        tag=f"application-{status}",
        url="/journey"
    )
    return send_push_notification(user_id, notification, conn)
