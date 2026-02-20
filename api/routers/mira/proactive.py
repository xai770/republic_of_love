"""
Mira router — yogi context, proactive messages, and consent endpoints.
"""
import re

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db, require_user
from api.routers.mira.models import (
    YogiContext, ProactiveMessage, ProactiveResponse,
    ConsentPromptResponse, ConsentSubmission,
)
from api.routers.mira.context import build_yogi_context

router = APIRouter()


@router.get("/context", response_model=YogiContext)
async def get_yogi_context(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get yogi's context for display or debugging.

    This is the same context Mira uses to personalize responses.
    """
    ctx = build_yogi_context(user['user_id'], conn)
    return YogiContext(**ctx)


@router.get("/proactive", response_model=ProactiveResponse)
async def get_proactive_messages(
    uses_du: bool = True,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get proactive messages Mira should display.

    Checks for:
    - New matches since last visit
    - Saved jobs still open
    - Application status changes (if trackable)
    """
    messages = []

    with conn.cursor() as cur:
        # Get last login + skills guard
        cur.execute("""
            SELECT u.last_login_at, p.skill_keywords, p.created_at AS profile_created_at
            FROM users u
            LEFT JOIN profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user['user_id'],))
        urow = cur.fetchone()
        last_login_at = urow['last_login_at'] if urow else None
        _sk = urow['skill_keywords'] if urow else None
        has_skills = bool(_sk and str(_sk) not in ('[]', '', 'None') and len(str(_sk)) > 2)
        profile_created_at = urow['profile_created_at'] if urow else None

        # Count new matches — only if profile has skills, and only since profile creation
        # (prevents stale matches from previous profiles surfacing as "new")
        if last_login_at and has_skills and profile_created_at:
            since = max(last_login_at, profile_created_at)
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM profile_posting_matches m
                JOIN profiles p ON m.profile_id = p.profile_id
                WHERE p.user_id = %s AND m.computed_at > %s
            """, (user['user_id'], since))
            new_matches = cur.fetchone()['cnt']

            if new_matches > 0:
                if uses_du:
                    msg = f"🎯 {new_matches} neue Matches seit deinem letzten Besuch!"
                else:
                    msg = f"🎯 {new_matches} neue Matches seit Ihrem letzten Besuch!"
                messages.append(ProactiveMessage(
                    message_type="new_matches",
                    message=msg,
                    data={"count": new_matches}
                ))

        # Check favorited jobs still available
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM user_posting_interactions i
            JOIN postings p ON i.posting_id = p.posting_id
            WHERE i.user_id = %s
              AND i.is_favorited = TRUE
              AND p.enabled = TRUE
              AND p.invalidated = FALSE
        """, (user['user_id'],))
        saved_open = cur.fetchone()['cnt']

        if saved_open > 0 and not last_login_at:
            if uses_du:
                msg = f"⭐ {saved_open} deiner gemerkten Jobs sind noch offen!"
            else:
                msg = f"⭐ {saved_open} Ihrer gemerkten Jobs sind noch offen!"
            messages.append(ProactiveMessage(
                message_type="saved_job_open",
                message=msg,
                data={"count": saved_open}
            ))

        # Check for pending applications (ghosting detection)
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM user_posting_interactions
            WHERE user_id = %s
              AND state = 'outcome_pending'
              AND state_changed_at < NOW() - INTERVAL '14 days'
        """, (user['user_id'],))
        waiting_long = cur.fetchone()['cnt']

        if waiting_long > 0:
            if uses_du:
                msg = f"⏳ {waiting_long} Bewerbungen warten schon länger auf Antwort. Soll ich nachfragen helfen?"
            else:
                msg = f"⏳ {waiting_long} Bewerbungen warten schon länger auf Antwort. Soll ich beim Nachfragen helfen?"
            messages.append(ProactiveMessage(
                message_type="long_wait",
                message=msg,
                data={"count": waiting_long}
            ))

    return ProactiveResponse(messages=messages)


@router.get("/consent-prompt", response_model=ConsentPromptResponse)
async def get_consent_prompt(
    uses_du: bool = True,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Check if user should be prompted for notification consent.

    Should prompt when:
    - User has a profile with skills
    - User has NOT yet given consent (notification_consent_at is NULL)
    - We have matches to notify about
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT u.notification_email, u.notification_consent_at,
                   p.profile_id, p.skill_keywords
            FROM users u
            LEFT JOIN profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()

        if not row:
            return ConsentPromptResponse(should_prompt=False)

        # Already has consent
        if row['notification_consent_at']:
            return ConsentPromptResponse(
                should_prompt=False,
                consent_given=True
            )

        # No profile yet - don't prompt
        if not row['profile_id']:
            return ConsentPromptResponse(should_prompt=False)

        # Check if has skills
        skill_keywords = row['skill_keywords']
        has_skills = (skill_keywords is not None and
                     skill_keywords != '[]' and
                     len(skill_keywords) > 2)

        if not has_skills:
            return ConsentPromptResponse(should_prompt=False)

        # User has profile with skills but no consent - prompt!
        if uses_du:
            message = (
                "Soll ich dir Bescheid sagen, wenn es neue passende Stellen gibt? 📬 "
                "Dafür bräuchte ich deine E-Mail-Adresse. "
                "Du kannst das jederzeit in den Einstellungen ändern."
            )
        else:
            message = (
                "Soll ich Ihnen Bescheid sagen, wenn es neue passende Stellen gibt? 📬 "
                "Dafür bräuchte ich Ihre E-Mail-Adresse. "
                "Sie können das jederzeit in den Einstellungen ändern."
            )

        return ConsentPromptResponse(
            should_prompt=True,
            message=message,
            consent_given=False
        )


@router.post("/consent-submit")
async def submit_consent(
    data: ConsentSubmission,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Submit notification consent via Mira chat.
    """
    # Validate email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, data.email):
        raise HTTPException(status_code=400, detail="Ungültige E-Mail-Adresse")

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE users
            SET notification_email = %s,
                notification_consent_at = CASE WHEN %s THEN NOW() ELSE NULL END
            WHERE user_id = %s
            RETURNING notification_consent_at
        """, (data.email, data.grant_consent, user['user_id']))

        row = cur.fetchone()
        conn.commit()

        return {
            "status": "ok",
            "consent_given": row['notification_consent_at'] is not None
        }
