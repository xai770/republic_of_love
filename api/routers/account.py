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

        # 6. Reset user state (yogi_name, onboarding, language, formality, notifications)
        cur.execute("""
            UPDATE users
            SET yogi_name = NULL,
                onboarding_completed_at = NULL,
                language = 'de',
                formality = 'du',
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


@router.get("/usage-balance")
def get_usage_balance(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Return the current user's usage balance and trial status.
    Used by the account page and the header usage meter.
    """
    from lib.usage_tracker import get_balance
    return get_balance(conn, user['user_id'])


# ── Transaction history + drill-down ──────────────────────────────────────────


@router.get("/transactions")
def get_transactions(
    month: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Return the user's usage event history with summary previews.

    Each event includes a short human-readable label so the yogi knows
    what the charge was for (e.g. "Mira: Wie finde ich einen Job?",
    "Anschreiben: Deutsche Bank AG — Data Engineer").

    Query params:
        month  — YYYY-MM (default: current month)
        limit  — max rows (default 100)
        offset — pagination offset
    """
    from datetime import date

    if month:
        try:
            year, mon = month.split("-")
            period_start = date(int(year), int(mon), 1)
        except (ValueError, TypeError):
            raise HTTPException(400, "month must be YYYY-MM")
    else:
        today = date.today()
        period_start = today.replace(day=1)

    # Next month start for range query
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)

    user_id = user["user_id"]

    with conn.cursor() as cur:
        # Get events with a LEFT JOIN preview from yogi_messages (for mira/adele chats)
        cur.execute("""
            SELECT
                e.event_id,
                e.event_type,
                e.cost_cents,
                e.context,
                e.created_at,
                e.billed_at
            FROM usage_events e
            WHERE e.user_id = %s
              AND e.created_at >= %s
              AND e.created_at < %s
            ORDER BY e.created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, period_start, period_end, limit, offset))
        events = cur.fetchall()

        # Get total count for pagination
        cur.execute("""
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(cost_cents), 0) AS total_cents
            FROM usage_events
            WHERE user_id = %s
              AND created_at >= %s
              AND created_at < %s
        """, (user_id, period_start, period_end))
        summary = cur.fetchone()

    # Enrich each event with a human-readable label
    enriched = []
    for ev in events:
        ctx = ev["context"] or {}
        label = _build_event_label(ev["event_type"], ctx, conn)
        enriched.append({
            "event_id": ev["event_id"],
            "event_type": ev["event_type"],
            "cost_cents": ev["cost_cents"],
            "label": label,
            "created_at": ev["created_at"].isoformat() if ev["created_at"] else None,
            "billed": ev["billed_at"] is not None,
            "has_detail": ev["event_type"] in (
                "mira_message", "cover_letter", "match_report", "cv_extraction",
            ),
        })

    return {
        "month": period_start.isoformat()[:7],
        "events": enriched,
        "total_events": summary["total"],
        "total_cents": summary["total_cents"],
        "limit": limit,
        "offset": offset,
    }


@router.get("/transactions/{event_id}")
def get_transaction_detail(
    event_id: int,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """
    Drill into a single usage event — show what happened.

    Returns the full content: the chat message, the cover letter text,
    the match analysis, or the CV extraction summary.  Yogi can only
    view their own events.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_id, event_type, cost_cents, context, created_at, billed_at
            FROM usage_events
            WHERE event_id = %s AND user_id = %s
        """, (event_id, user["user_id"]))
        ev = cur.fetchone()

    if not ev:
        raise HTTPException(404, "Event not found")

    ctx = ev["context"] or {}
    detail = _fetch_event_detail(ev["event_type"], ctx, conn)

    return {
        "event_id": ev["event_id"],
        "event_type": ev["event_type"],
        "cost_cents": ev["cost_cents"],
        "created_at": ev["created_at"].isoformat() if ev["created_at"] else None,
        "billed": ev["billed_at"] is not None,
        "context": ctx,
        "detail": detail,
    }


# ── Helpers for transaction labels + drill-down ──────────────────────────────


def _build_event_label(event_type: str, ctx: dict, conn) -> str:
    """
    Build a short human-readable label for a usage event.
    Examples:
        "Mira: Wie finde ich einen Job in Berlin?"
        "Anschreiben: Deutsche Bank AG — Data Engineer"
        "Match-Bericht: Siemens AG — Software Developer"
        "Lebenslauf-Analyse"
        "Profil-Update"
    """
    try:
        if event_type == "mira_message":
            msg_id = ctx.get("user_message_id")
            if msg_id:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT LEFT(body, 60) AS preview FROM yogi_messages WHERE message_id = %s",
                        (msg_id,),
                    )
                    row = cur.fetchone()
                if row and row["preview"]:
                    preview = row["preview"]
                    if len(preview) >= 60:
                        preview = preview[:57] + "..."
                    return f"Mira: {preview}"
            return "Mira-Gespräch"

        if event_type in ("cover_letter", "match_report"):
            match_id = ctx.get("match_id")
            posting_id = ctx.get("posting_id")
            if match_id or posting_id:
                with conn.cursor() as cur:
                    if match_id:
                        cur.execute("""
                            SELECT p.company, p.title
                            FROM profile_posting_matches m
                            JOIN postings p ON p.posting_id = m.posting_id
                            WHERE m.match_id = %s
                        """, (match_id,))
                    else:
                        cur.execute(
                            "SELECT company, title FROM postings WHERE posting_id = %s",
                            (posting_id,),
                        )
                    row = cur.fetchone()
                if row:
                    company = row.get("company") or "?"
                    title = row.get("title") or "?"
                    prefix = "Anschreiben" if event_type == "cover_letter" else "Match-Bericht"
                    return f"{prefix}: {company} — {title}"
            return "Anschreiben" if event_type == "cover_letter" else "Match-Bericht"

        if event_type == "cv_extraction":
            return "Lebenslauf-Analyse"

        if event_type == "profile_embed":
            return "Profil-Update"

    except Exception:
        pass  # Fall through to generic label

    return event_type.replace("_", " ").title()


def _fetch_event_detail(event_type: str, ctx: dict, conn) -> dict:
    """
    Fetch the full content behind a usage event for drill-down view.
    Returns a dict with event-type-specific fields.
    """
    detail: dict = {"type": event_type}

    try:
        if event_type == "mira_message":
            user_msg_id = ctx.get("user_message_id")
            mira_msg_id = ctx.get("mira_message_id")
            msgs = []
            with conn.cursor() as cur:
                if user_msg_id:
                    cur.execute(
                        "SELECT body, created_at FROM yogi_messages WHERE message_id = %s",
                        (user_msg_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        msgs.append({"role": "user", "content": row["body"],
                                     "at": row["created_at"].isoformat() if row["created_at"] else None})
                if mira_msg_id:
                    cur.execute(
                        "SELECT body, created_at FROM yogi_messages WHERE message_id = %s",
                        (mira_msg_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        msgs.append({"role": "mira", "content": row["body"],
                                     "at": row["created_at"].isoformat() if row["created_at"] else None})
            detail["messages"] = msgs

        elif event_type in ("cover_letter", "match_report"):
            match_id = ctx.get("match_id")
            if match_id:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT m.match_rate, m.recommendation, m.confidence,
                               m.go_reasons, m.nogo_reasons,
                               m.cover_letter, m.nogo_narrative,
                               p.company, p.title, p.external_url
                        FROM profile_posting_matches m
                        JOIN postings p ON p.posting_id = m.posting_id
                        WHERE m.match_id = %s
                    """, (match_id,))
                    row = cur.fetchone()
                if row:
                    detail["company"] = row.get("company")
                    detail["title"] = row.get("title")
                    detail["external_url"] = row.get("external_url")
                    detail["match_rate"] = row.get("match_rate")
                    detail["recommendation"] = row.get("recommendation")
                    detail["confidence"] = float(row["confidence"]) if row.get("confidence") else None
                    if event_type == "cover_letter":
                        detail["cover_letter"] = row.get("cover_letter")
                    else:
                        detail["go_reasons"] = row.get("go_reasons")
                        detail["nogo_reasons"] = row.get("nogo_reasons")
                        detail["nogo_narrative"] = row.get("nogo_narrative")

        elif event_type == "cv_extraction":
            session_id = ctx.get("session_id")
            if session_id:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT phase, work_history_count, turn_count,
                               started_at, completed_at
                        FROM adele_sessions WHERE session_id = %s
                    """, (session_id,))
                    row = cur.fetchone()
                if row:
                    detail["phase"] = row["phase"]
                    detail["work_history_count"] = row["work_history_count"]
                    detail["turn_count"] = row["turn_count"]
                    detail["started_at"] = row["started_at"].isoformat() if row["started_at"] else None
                    detail["completed_at"] = row["completed_at"].isoformat() if row["completed_at"] else None

        elif event_type == "profile_embed":
            detail["info"] = "Profile embedding was refreshed after a profile edit."

    except Exception as e:
        log.warning(f"Failed to fetch detail for event {event_type}: {e}")
        detail["error"] = "Detail unavailable"

    return detail
