"""
Event tracking router — lightweight behavioral events for Mira context.

NOT chat messages — those stay in yogi_messages.
Events: login, page_view, search_filter, posting_view, match_action

Fire-and-forget from frontend: POST /api/events/track
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

VALID_EVENT_TYPES = {'login', 'page_view', 'search_filter', 'posting_view', 'match_action'}


class TrackEventRequest(BaseModel):
    event_type: str
    event_data: Optional[dict] = Field(default_factory=dict)


def _insert_event(user_id: int, event_type: str, event_data: dict, conn):
    """Insert event in background — no blocking the response."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO yogi_events (user_id, event_type, event_data) VALUES (%s, %s, %s)",
                (user_id, event_type, _sanitize_json(event_data))
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Event insert failed: {e}")


def _sanitize_json(data: dict) -> str:
    """Sanitize and serialize event data — strip PII, cap size."""
    import json
    # Remove any sensitive fields
    safe = {k: v for k, v in (data or {}).items()
            if k not in ('password', 'token', 'cookie', 'session')
            and isinstance(v, (str, int, float, bool, list, type(None)))}
    # Cap string values to 500 chars
    for k, v in safe.items():
        if isinstance(v, str) and len(v) > 500:
            safe[k] = v[:500]
    return json.dumps(safe)


@router.post("/track", status_code=204)
def track_event(
    request: TrackEventRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Track a behavioral event. Fire-and-forget from frontend.
    Returns 204 No Content immediately.
    """
    if request.event_type not in VALID_EVENT_TYPES:
        # Silently ignore unknown events — don't break the frontend
        return

    _insert_event(user['user_id'], request.event_type, request.event_data or {}, conn)
