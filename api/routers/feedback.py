"""
Feedback router — in-app issue reporting ("Fehler melden").

POST /api/feedback         — yogi submits a report (with optional screenshot)
GET  /admin/feedback       — admin views all reports
POST /admin/feedback/resolve — admin marks a report resolved
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from api.deps import get_db, require_user, get_current_user
from api.i18n import get_language_from_request, create_translator, SUPPORTED_LANGUAGES

router = APIRouter(tags=["feedback"])


# ---------- schemas ----------

class FeedbackSubmit(BaseModel):
    url: str
    description: str
    category: str = "bug"
    screenshot: Optional[str] = None          # base64 data URI
    annotation: Optional[dict] = None         # {x, y, width, height}
    viewport: Optional[dict] = None           # {width, height, dpr}


class FeedbackResolve(BaseModel):
    feedback_id: int
    admin_notes: str = ""


# ---------- user endpoint ----------

@router.post("/feedback")
def submit_feedback(
    body: FeedbackSubmit,
    request: Request,
    user: dict = Depends(require_user),
    conn=Depends(get_db),
):
    """Yogi submits an issue report."""
    ua = request.headers.get("user-agent", "")

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO feedback (user_id, url, description, category,
                                  screenshot, annotation, viewport, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING feedback_id
        """, (
            user["user_id"],
            body.url,
            body.description,
            body.category,
            body.screenshot,
            None if body.annotation is None else __import__("json").dumps(body.annotation),
            None if body.viewport is None else __import__("json").dumps(body.viewport),
            ua,
        ))
        fid = cur.fetchone()["feedback_id"]
    conn.commit()

    return {"ok": True, "feedback_id": fid}


# ---------- admin endpoints ----------

def _require_admin(user):
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/feedback", response_class=HTMLResponse)
def admin_feedback_list(
    request: Request,
    status_filter: str = "open",
    conn=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Admin feedback dashboard."""
    from fastapi.templating import Jinja2Templates
    from pathlib import Path

    _require_admin(user)

    templates = Jinja2Templates(
        directory=Path(__file__).parent.parent.parent / "frontend" / "templates"
    )
    lang = get_language_from_request(request)

    with conn.cursor() as cur:
        if status_filter == "all":
            cur.execute("""
                SELECT f.*, u.display_name, u.email, u.yogi_name
                FROM feedback f
                LEFT JOIN users u ON u.user_id = f.user_id
                ORDER BY f.created_at DESC
                LIMIT 200
            """)
        else:
            cur.execute("""
                SELECT f.*, u.display_name, u.email, u.yogi_name
                FROM feedback f
                LEFT JOIN users u ON u.user_id = f.user_id
                WHERE f.status = %s
                ORDER BY f.created_at DESC
                LIMIT 200
            """, (status_filter,))
        rows = [dict(r) for r in cur.fetchall()]

    # Count by status
    with conn.cursor() as cur:
        cur.execute("""
            SELECT status, COUNT(*) AS n
            FROM feedback GROUP BY status
        """)
        counts = {r["status"]: r["n"] for r in cur.fetchall()}

    return templates.TemplateResponse("admin/feedback.html", {
        "request": request,
        "user": user,
        "reports": rows,
        "status_filter": status_filter,
        "counts": counts,
        "t": create_translator(lang),
        "lang": lang,
        "languages": SUPPORTED_LANGUAGES,
    })


@router.post("/feedback/resolve")
def resolve_feedback(
    body: FeedbackResolve,
    user: dict = Depends(get_current_user),
    conn=Depends(get_db),
):
    """Admin resolves a feedback report."""
    _require_admin(user)

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE feedback
            SET status = 'resolved', admin_notes = %s, resolved_at = NOW()
            WHERE feedback_id = %s
            RETURNING feedback_id
        """, (body.admin_notes, body.feedback_id))
        row = cur.fetchone()
    conn.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return {"ok": True}
