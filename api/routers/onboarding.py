"""
Onboarding API — completes the first-login wizard.

POST /api/onboarding/complete
    Body: { language, formality, yogi_name }
    Sets language, formality, yogi_name, onboarding_completed_at on the users row.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from api.deps import get_db

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _require_user(request: Request, conn=Depends(get_db)):
    """Lightweight auth check — returns user dict or 401."""
    from api.deps import get_current_user
    user = get_current_user(request, conn)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/complete")
async def complete_onboarding(
    request: Request,
    user: dict = Depends(_require_user),
    conn=Depends(get_db),
):
    """
    Finish the onboarding wizard.

    Saves language, formality, yogi_name and stamps onboarding_completed_at.
    Validates the yogi name through Taro before accepting.
    """
    body = await request.json()
    language = body.get("language", "de")
    formality = body.get("formality", "du")
    yogi_name = (body.get("yogi_name") or "").strip()

    # ── Validate inputs ──────────────────────────────
    if language not in ("de", "en"):
        language = "de"
    if formality not in ("du", "sie"):
        formality = "du"
    if not yogi_name or len(yogi_name) < 3:
        return {"ok": False, "error": "Yogi name must be at least 3 characters."}

    # ── Validate name via Taro ───────────────────────
    from core.taro import validate_yogi_name

    display_name = user.get("display_name") or ""
    email = user.get("email") or ""

    # Get profile full_name (transient, for comparison only)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT full_name FROM profiles WHERE user_id = %s",
            (user["user_id"],)
        )
        row = cur.fetchone()
        profile_name = ""
        if row and row.get("full_name") and row["full_name"] not in ("New Yogi",):
            profile_name = row["full_name"]

    real_name = display_name or profile_name or None

    ok, msg, severity = validate_yogi_name(
        yogi_name,
        real_name=real_name,
        email=email,
        conn=conn,
        current_user_id=user["user_id"]
    )

    if severity == "error":
        error_messages = {
            "contains_email": "Name may not contain an email address.",
            "contains_phone": "Name may not contain a phone number.",
            "contains_address": "Name may not contain an address.",
            "reserved": "This name is reserved.",
            "matches_real_name": "Your yogi name may not be your real name.",
            "contains_real_name": "Your yogi name contains your real name.",
            "subset_of_real_name": "Your yogi name is too similar to your real name.",
            "already_taken": "This yogi name is already taken.",
        }
        return {"ok": False, "error": error_messages.get(msg, msg)}

    # Warnings during onboarding are accepted (user already chose)

    # ── Save everything ──────────────────────────────
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE users
            SET yogi_name = %s,
                language = %s,
                formality = %s,
                onboarding_completed_at = NOW()
            WHERE user_id = %s
        """, (yogi_name, language, formality, user["user_id"]))
        conn.commit()

    return {"ok": True}
