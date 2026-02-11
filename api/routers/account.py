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

from api.deps import get_db, require_user

router = APIRouter(prefix="/account", tags=["account"])


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
async def update_display_name(
    data: DisplayNameUpdate,
    user: dict = Depends(require_user),
    db=Depends(get_db)
):
    """Update user's display name."""
    display_name = data.display_name.strip()[:30]  # Max 30 chars
    if not display_name:
        raise HTTPException(400, "Display name cannot be empty")
    
    await db.execute(
        "UPDATE users SET display_name = $1 WHERE user_id = $2",
        display_name, user["user_id"]
    )
    return {"ok": True, "display_name": display_name}


@router.post("/avatar")
async def update_avatar(
    data: AvatarUpdate,
    user: dict = Depends(require_user),
    db=Depends(get_db)
):
    """Update user's avatar (emoji only)."""
    # Only allow single emoji characters (basic validation)
    avatar = data.avatar.strip()
    if len(avatar) > 8:  # Emoji can be multi-byte
        raise HTTPException(400, "Invalid avatar")
    
    await db.execute(
        "UPDATE users SET avatar_url = $1 WHERE user_id = $2",
        avatar, user["user_id"]
    )
    return {"ok": True, "avatar": avatar}


@router.post("/email-consent")
async def update_email_consent(
    data: EmailConsentUpdate,
    user: dict = Depends(require_user),
    db=Depends(get_db)
):
    """
    Update email notification consent.
    Privacy-by-design: when consent is given, we store their email.
    When consent is revoked, we clear it.
    """
    if data.consent:
        # User consents — copy email from auth to notification_email
        await db.execute("""
            UPDATE users 
            SET notification_email = email,
                notification_consent_at = NOW()
            WHERE user_id = $1
        """, user["user_id"])
        return {"ok": True, "consented": True, "message": "Dream job notifications enabled"}
    else:
        # User revokes — clear notification email
        await db.execute("""
            UPDATE users 
            SET notification_email = NULL,
                notification_consent_at = NULL
            WHERE user_id = $1
        """, user["user_id"])
        return {"ok": True, "consented": False, "message": "Notifications disabled"}


@router.post("/mira-preferences")
async def update_mira_preferences(
    data: MiraPreferencesUpdate,
    user: dict = Depends(require_user),
    db=Depends(get_db)
):
    """Update Mira's communication preferences."""
    # Get existing preferences
    row = await db.fetchrow(
        "SELECT notification_preferences FROM users WHERE user_id = $1",
        user["user_id"]
    )
    prefs = row["notification_preferences"] or {} if row else {}
    
    # Update only provided fields
    if data.language:
        prefs["language"] = data.language
    if data.formality:
        prefs["formality"] = data.formality
    if data.tone:
        prefs["tone"] = data.tone
    
    await db.execute(
        "UPDATE users SET notification_preferences = $1 WHERE user_id = $2",
        json.dumps(prefs), user["user_id"]
    )
    return {"ok": True, "preferences": prefs}


@router.get("/export")
async def export_user_data(
    user: dict = Depends(require_user),
    db=Depends(get_db)
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
    
    # User info
    user_row = await db.fetchrow(
        "SELECT user_id, email, display_name, created_at FROM users WHERE user_id = $1",
        user_id
    )
    if user_row:
        export_data["user"] = dict(user_row)
        export_data["user"]["created_at"] = export_data["user"]["created_at"].isoformat() if export_data["user"]["created_at"] else None
    
    # Profiles
    profiles = await db.fetch(
        "SELECT * FROM profiles WHERE user_id = $1", user_id
    )
    for p in profiles:
        profile_dict = dict(p)
        # Convert dates to ISO strings
        for k, v in profile_dict.items():
            if hasattr(v, 'isoformat'):
                profile_dict[k] = v.isoformat()
        export_data["profiles"].append(profile_dict)
    
    # Get profile IDs for related queries
    profile_ids = [p["profile_id"] for p in profiles]
    
    if profile_ids:
        # Skills
        skills = await db.fetch(
            "SELECT * FROM profile_skills WHERE profile_id = ANY($1)",
            profile_ids
        )
        export_data["skills"] = [dict(s) for s in skills]
        
        # Work history
        work_history = await db.fetch(
            "SELECT * FROM work_history WHERE profile_id = ANY($1)",
            profile_ids
        )
        for wh in work_history:
            wh_dict = dict(wh)
            for k, v in wh_dict.items():
                if hasattr(v, 'isoformat'):
                    wh_dict[k] = v.isoformat()
            export_data["work_history"].append(wh_dict)
        
        # Preferences
        prefs = await db.fetch(
            "SELECT * FROM profile_preferences WHERE profile_id = ANY($1)",
            profile_ids
        )
        export_data["preferences"] = [dict(p) for p in prefs]
    
    # Documents
    docs = await db.fetch(
        "SELECT document_id, filename, doc_type, created_at FROM documents WHERE user_id = $1",
        user_id
    )
    for d in docs:
        d_dict = dict(d)
        d_dict["created_at"] = d_dict["created_at"].isoformat() if d_dict["created_at"] else None
        export_data["documents"].append(d_dict)
    
    # Messages
    msgs = await db.fetch(
        "SELECT sender_type, content, created_at FROM messages WHERE user_id = $1 ORDER BY created_at",
        user_id
    )
    for m in msgs:
        m_dict = dict(m)
        m_dict["created_at"] = m_dict["created_at"].isoformat() if m_dict["created_at"] else None
        export_data["messages"].append(m_dict)
    
    # Interactions
    interactions = await db.fetch(
        "SELECT * FROM user_interactions WHERE user_id = $1",
        user_id
    )
    for i in interactions:
        i_dict = dict(i)
        for k, v in i_dict.items():
            if hasattr(v, 'isoformat'):
                i_dict[k] = v.isoformat()
        export_data["interactions"].append(i_dict)
    
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
async def request_account_deletion(
    user: dict = Depends(require_user),
    db=Depends(get_db)
):
    """
    GDPR: Request account deletion.
    For safety, this creates a deletion request rather than immediate deletion.
    Data will be deleted within 30 days per GDPR requirements.
    """
    user_id = user["user_id"]
    
    # Mark user for deletion
    await db.execute("""
        UPDATE users 
        SET deletion_requested_at = NOW(),
            notification_preferences = notification_preferences || '{"deletion_requested": true}'::jsonb
        WHERE user_id = $1
    """, user_id)
    
    return {
        "ok": True,
        "message": "Account deletion requested. Your data will be permanently deleted within 30 days."
    }
