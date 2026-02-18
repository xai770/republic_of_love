"""
Account endpoints — user settings, preferences, consent, GDPR data export/deletion.
Privacy-by-design: emails only stored with explicit consent.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import io
import logging

from api.deps import get_db, require_user

router = APIRouter(prefix="/account", tags=["account"])
log = logging.getLogger(__name__)


class DisplayNameUpdate(BaseModel):
    display_name: str


class AvatarUpdate(BaseModel):
    avatar: str


class EmailConsentUpdate(BaseModel):
    consent: bool


class MiraPreferencesUpdate(BaseModel):
    language: Optional[str] = None  # 'de' or 'en'
    formality: Optional[str] = None  # 'du' or 'sie'
    tone: Optional[str] = None  # 'friendly', 'concise', 'professional'


@router.post("/display-name")
def update_display_name(
    data: DisplayNameUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Update user's display name."""
    display_name = data.display_name.strip()[:30]  # Max 30 chars
    if not display_name:
        raise HTTPException(400, "Display name cannot be empty")

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET display_name = %s WHERE user_id = %s",
            (display_name, user["user_id"])
        )
    conn.commit()
    return {"ok": True, "display_name": display_name}


@router.post("/avatar")
def update_avatar(
    data: AvatarUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Update user's avatar (emoji only)."""
    # Only allow single emoji characters (basic validation)
    avatar = data.avatar.strip()
    if len(avatar) > 8:  # Emoji can be multi-byte
        raise HTTPException(400, "Invalid avatar")

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET avatar_url = %s WHERE user_id = %s",
            (avatar, user["user_id"])
        )
    conn.commit()
    return {"ok": True, "avatar": avatar}


@router.post("/email-consent")
def update_email_consent(
    data: EmailConsentUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Update email notification consent.
    Privacy-by-design: when consent is given, we store their email.
    When consent is revoked, we clear it.
    """
    with conn.cursor() as cur:
        if data.consent:
            # User consents — copy email from auth to notification_email
            cur.execute("""
                UPDATE users
                SET notification_email = email,
                    notification_consent_at = NOW()
                WHERE user_id = %s
            """, (user["user_id"],))
            conn.commit()
            return {"ok": True, "consented": True, "message": "Dream job notifications enabled"}
        else:
            # User revokes — clear notification email
            cur.execute("""
                UPDATE users
                SET notification_email = NULL,
                    notification_consent_at = NULL
                WHERE user_id = %s
            """, (user["user_id"],))
            conn.commit()
            return {"ok": True, "consented": False, "message": "Notifications disabled"}


@router.post("/mira-preferences")
def update_mira_preferences(
    data: MiraPreferencesUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Update Mira's communication preferences."""
    with conn.cursor() as cur:
        # Get existing preferences
        cur.execute(
            "SELECT notification_preferences FROM users WHERE user_id = %s",
            (user["user_id"],)
        )
        row = cur.fetchone()
        prefs = (row["notification_preferences"] or {}) if row else {}

        # Update only provided fields
        if data.language:
            prefs["language"] = data.language
        if data.formality:
            prefs["formality"] = data.formality
        if data.tone:
            prefs["tone"] = data.tone

        cur.execute(
            "UPDATE users SET notification_preferences = %s WHERE user_id = %s",
            (json.dumps(prefs), user["user_id"])
        )
    conn.commit()
    return {"ok": True, "preferences": prefs}


@router.get("/export")
def export_user_data(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    GDPR: Export all user data as JSON.
    Returns a downloadable JSON file with all user-related data.
    """
    user_id = user["user_id"]

    # Collect all user data
    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "user": {},
        "profiles": [],
        "skills": [],
        "work_history": [],
        "preferences": {},
        "documents": [],
        "messages": [],
        "interactions": [],
    }

    # Helper: query table that may not exist yet (uses savepoint to avoid poisoning transaction)
    def safe_query(query, params):
        try:
            with conn.cursor() as c:
                c.execute("SAVEPOINT export_sp")
                c.execute(query, params)
                result = [dict(r) for r in c.fetchall()]
                c.execute("RELEASE SAVEPOINT export_sp")
                return result
        except Exception:
            with conn.cursor() as c:
                c.execute("ROLLBACK TO SAVEPOINT export_sp")
            return []

    with conn.cursor() as cur:
        # User info
        cur.execute(
            "SELECT user_id, email, display_name, created_at FROM users WHERE user_id = %s",
            (user_id,)
        )
        user_row = cur.fetchone()
        if user_row:
            export_data["user"] = dict(user_row)

        # Profiles
        cur.execute("SELECT * FROM profiles WHERE user_id = %s", (user_id,))
        profiles = cur.fetchall()
        export_data["profiles"] = [dict(p) for p in profiles]

        # Get profile IDs for related queries
        profile_ids = [p["profile_id"] for p in profiles]

        if profile_ids:
            export_data["skills"] = safe_query(
                "SELECT * FROM profile_skills WHERE profile_id = ANY(%s)", (profile_ids,))
            export_data["work_history"] = safe_query(
                "SELECT * FROM work_history WHERE profile_id = ANY(%s)", (profile_ids,))
            export_data["preferences"] = safe_query(
                "SELECT * FROM profile_preferences WHERE profile_id = ANY(%s)", (profile_ids,))

        export_data["documents"] = safe_query(
            "SELECT document_id, filename, doc_type, created_at FROM documents WHERE user_id = %s", (user_id,))

        # Messages (yogi_messages always exists)
        cur.execute(
            "SELECT sender_type, body as content, created_at FROM yogi_messages WHERE user_id = %s ORDER BY created_at",
            (user_id,)
        )
        export_data["messages"] = [dict(m) for m in cur.fetchall()]

        export_data["interactions"] = safe_query(
            "SELECT * FROM user_interactions WHERE user_id = %s", (user_id,))

    # Convert to JSON and return as downloadable file
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)

    return StreamingResponse(
        io.BytesIO(json_str.encode('utf-8')),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=talentyoga_data_{user_id}_{datetime.utcnow().strftime('%Y%m%d')}.json"
        }
    )


@router.post("/delete-request")
def request_account_deletion(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    GDPR: Request account deletion.
    For safety, this creates a deletion request rather than immediate deletion.
    Data will be deleted within 30 days per GDPR requirements.
    """
    user_id = user["user_id"]

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE users
            SET deletion_requested_at = NOW(),
                notification_preferences = COALESCE(notification_preferences, '{}'::jsonb) || '{"deletion_requested": true}'::jsonb
            WHERE user_id = %s
        """, (user_id,))
    conn.commit()

    return {
        "ok": True,
        "message": "Account deletion requested. Your data will be permanently deleted within 30 days."
    }


@router.post("/reset-onboarding")
def reset_onboarding(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Reset all user data for re-testing the onboarding flow.
    Admin-only: clears profile, matches, messages, Adele session, and user state.
    After reset, the user will see the onboarding tour again.
    """
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    user_id = user["user_id"]
    deleted = {}

    with conn.cursor() as cur:
        # 1. Delete matches (depends on profiles via profile_id)
        cur.execute("""
            DELETE FROM profile_posting_matches
            WHERE profile_id IN (SELECT profile_id FROM profiles WHERE user_id = %s)
        """, (user_id,))
        deleted["matches"] = cur.rowcount

        # 2. Delete work history (depends on profiles)
        cur.execute("""
            DELETE FROM profile_work_history
            WHERE profile_id IN (SELECT profile_id FROM profiles WHERE user_id = %s)
        """, (user_id,))
        deleted["work_history"] = cur.rowcount

        # 3. Delete profile
        cur.execute("DELETE FROM profiles WHERE user_id = %s", (user_id,))
        deleted["profiles"] = cur.rowcount

        # 4. Delete Adele sessions
        cur.execute("DELETE FROM adele_sessions WHERE user_id = %s", (user_id,))
        deleted["adele_sessions"] = cur.rowcount

        # 5. Delete all messages (Mira, Adele, system, etc.)
        cur.execute("DELETE FROM yogi_messages WHERE user_id = %s", (user_id,))
        deleted["messages"] = cur.rowcount

        # 6. Reset user state (yogi_name, onboarding, notifications)
        cur.execute("""
            UPDATE users
            SET yogi_name = NULL,
                onboarding_completed_at = NULL,
                notification_email = NULL,
                notification_consent_at = NULL
            WHERE user_id = %s
        """, (user_id,))

    conn.commit()

    log.info(f"Reset onboarding for user {user_id} ({user.get('display_name')}): {deleted}")

    total = sum(deleted.values())
    return {
        "ok": True,
        "message": f"Onboarding reset complete. Cleared {total} records.",
        "deleted": deleted
    }
