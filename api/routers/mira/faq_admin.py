"""
FAQ Pipeline Admin — review candidates, promote to quick actions.

Endpoints:
  GET  /faq/candidates      — list pending FAQ candidates
  POST /faq/candidates/{id}/review — approve/reject/skip a candidate
  GET  /faq/promoted        — list promoted FAQ entries
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _require_admin(user: dict = Depends(require_user)) -> dict:
    if not user.get('is_admin'):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Models ──────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    decision: str  # 'approve', 'reject', 'skip'
    notes: Optional[str] = None
    # For approve: optional quick-action config
    quick_action_label_en: Optional[str] = None
    quick_action_label_de: Optional[str] = None
    quick_action_page: Optional[str] = None  # e.g. '/search:power', '/account'


# ── Endpoints ───────────────────────────────────────────────────

@router.get("/faq/candidates")
def list_faq_candidates(
    status: str = Query(default="pending", pattern="^(pending|approved|rejected|all)$"),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(_require_admin),
    conn=Depends(get_db),
):
    """List FAQ candidates for review."""
    with conn.cursor() as cur:
        if status == "all":
            cur.execute("""
                SELECT id, user_id, user_message, mira_response, flagged_reason,
                       user_feedback, review_decision, review_notes,
                       promoted_faq_id, created_at, reviewed_at
                FROM mira_faq_candidates
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
        elif status == "pending":
            cur.execute("""
                SELECT id, user_id, user_message, mira_response, flagged_reason,
                       user_feedback, review_decision, review_notes,
                       promoted_faq_id, created_at, reviewed_at
                FROM mira_faq_candidates
                WHERE review_decision IS NULL
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
        else:
            cur.execute("""
                SELECT id, user_id, user_message, mira_response, flagged_reason,
                       user_feedback, review_decision, review_notes,
                       promoted_faq_id, created_at, reviewed_at
                FROM mira_faq_candidates
                WHERE review_decision = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (status, limit))

        rows = cur.fetchall()

    return {
        "candidates": [
            {
                "id": r['id'],
                "user_message": r['user_message'],
                "mira_response": r['mira_response'],
                "flagged_reason": r['flagged_reason'],
                "user_feedback": r['user_feedback'],
                "review_decision": r['review_decision'],
                "review_notes": r['review_notes'],
                "promoted_faq_id": r['promoted_faq_id'],
                "created_at": r['created_at'].isoformat() if r['created_at'] else None,
                "reviewed_at": r['reviewed_at'].isoformat() if r['reviewed_at'] else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.post("/faq/candidates/{candidate_id}/review")
def review_faq_candidate(
    candidate_id: int,
    req: ReviewRequest,
    user: dict = Depends(_require_admin),
    conn=Depends(get_db),
):
    """Review a FAQ candidate: approve, reject, or skip."""
    if req.decision not in ('approve', 'reject', 'skip'):
        raise HTTPException(status_code=400, detail="Decision must be approve, reject, or skip")

    with conn.cursor() as cur:
        # Verify candidate exists
        cur.execute("SELECT id, user_message, mira_response FROM mira_faq_candidates WHERE id = %s", (candidate_id,))
        candidate = cur.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Update review
        cur.execute("""
            UPDATE mira_faq_candidates
            SET review_decision = %s,
                review_notes = %s,
                reviewed_at = NOW(),
                reviewed_by = %s
            WHERE id = %s
        """, (req.decision, req.notes, user['user_id'], candidate_id))

        promoted_id = None

        # If approved with quick-action config, promote to mira_contexts
        if req.decision == 'approve' and req.quick_action_label_en and req.quick_action_page:
            promoted_id = f"faq_promoted_{candidate_id}"

            # Store promoted entry in DB for persistence
            cur.execute("""
                INSERT INTO mira_faq_promoted (
                    candidate_id, faq_id, page_key,
                    label_en, label_de, message_text
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (faq_id) DO NOTHING
            """, (
                candidate_id, promoted_id, req.quick_action_page,
                req.quick_action_label_en,
                req.quick_action_label_de or req.quick_action_label_en,
                candidate['mira_response'],
            ))

            cur.execute("""
                UPDATE mira_faq_candidates
                SET promoted_at = NOW(), promoted_faq_id = %s
                WHERE id = %s
            """, (promoted_id, candidate_id))

        conn.commit()

    action = "promoted as quick action" if promoted_id else req.decision
    logger.info(f"FAQ candidate #{candidate_id} → {action} by user {user['user_id']}")

    return {"status": "ok", "decision": req.decision, "promoted_faq_id": promoted_id}


@router.get("/faq/promoted")
def list_promoted_faqs(
    user: dict = Depends(_require_admin),
    conn=Depends(get_db),
):
    """List all promoted FAQ entries (quick actions added from pipeline)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.faq_id, p.page_key, p.label_en, p.label_de,
                   p.message_text, p.created_at, c.user_message
            FROM mira_faq_promoted p
            LEFT JOIN mira_faq_candidates c ON c.id = p.candidate_id
            ORDER BY p.created_at DESC
        """)
        rows = cur.fetchall()

    return {
        "promoted": [
            {
                "faq_id": r['faq_id'],
                "page_key": r['page_key'],
                "label_en": r['label_en'],
                "label_de": r['label_de'],
                "original_question": r['user_message'],
                "message_text": r['message_text'],
                "created_at": r['created_at'].isoformat() if r['created_at'] else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }
