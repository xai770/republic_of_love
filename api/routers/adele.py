"""
Adele router — conversational profile builder.

Endpoint: POST /api/adele/chat
Like Mira's chat but with interview-state tracking.
Messages are persisted in yogi_messages for continuity.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional, List

from api.deps import get_db, require_user
from api.i18n import get_language_from_request
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/adele", tags=["adele"])


class AdeleChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class AdeleChatRequest(BaseModel):
    message: str
    history: Optional[List[AdeleChatMessage]] = None


class AdeleChatResponse(BaseModel):
    reply: str
    language: str = 'de'
    phase: str = 'intro'
    actions: Optional[dict] = None


@router.post("/chat", response_model=AdeleChatResponse)
async def chat(
    req: Request,
    request: AdeleChatRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Handle Adele interview chat messages.

    State is tracked in adele_sessions table (phase + collected data).
    Messages are persisted in yogi_messages for continuity.
    """
    from core.adele import adele_chat
    from core.mira_llm import detect_language

    message = request.message.strip()

    if not message:
        return AdeleChatResponse(
            reply="I didn't catch that. Could you say that again?",
            language='en',
            phase='intro'
        )

    # Use cookie language as primary source; fall back to message-based detection
    # (message detection fails for short words like 'weiter', 'ja', etc.)
    language = get_language_from_request(req)
    if not language:
        language = detect_language(message)

    # Call Adele's chat logic
    response = await adele_chat(message, user['user_id'], conn, language=language)

    # Persist messages in yogi_messages
    try:
        with conn.cursor() as cur:
            # Save user message
            cur.execute("""
                INSERT INTO yogi_messages (user_id, sender_type, message_type, body, recipient_type)
                VALUES (%s, 'yogi', 'chat', %s, 'adele')
            """, (user['user_id'], message))
            # Save Adele's reply
            cur.execute("""
                INSERT INTO yogi_messages (user_id, sender_type, message_type, body)
                VALUES (%s, 'adele', 'chat', %s)
            """, (user['user_id'], response.reply))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to persist Adele chat messages: {e}")

    logger.info(f"Adele chat: phase={response.phase}, lang={response.language}")

    return AdeleChatResponse(
        reply=response.reply,
        language=response.language,
        phase=response.phase,
        actions=response.actions,
    )


@router.get("/greet")
async def greet(
    req: Request,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Return Adele's opening greeting for a new session and advance phase to
    current_role so the next user message is processed correctly.
    Idempotent — returns null if the session is already past intro.
    """
    from core.adele import get_session, _update_session, _INTRO_EN, _INTRO_DE
    lang = get_language_from_request(req)

    session = get_session(user['user_id'], conn)
    if session['phase'] != 'intro':
        return {"reply": None, "phase": session['phase']}

    greeting = _INTRO_DE if lang == 'de' else _INTRO_EN
    _update_session(conn, session['session_id'], 'current_role',
                    session['collected'], turn_count=0)

    # Persist as Adele message so it appears on reload
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO yogi_messages
                    (user_id, sender_type, message_type, body)
                VALUES (%s, 'adele', 'chat', %s)
            """, (user['user_id'], greeting))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to persist greet: {e}")

    return {"reply": greeting, "phase": "current_role"}


@router.get("/session")
def get_session_status(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Get current Adele session state (for frontend to show progress)."""
    from core.adele import get_session

    session = get_session(user['user_id'], conn)
    phases = ['intro', 'current_role', 'work_history', 'skills',
              'education', 'preferences', 'summary', 'complete']
    current_idx = phases.index(session['phase']) if session['phase'] in phases else 0
    progress = int((current_idx / (len(phases) - 1)) * 100)

    return {
        "phase": session['phase'],
        "turn_count": session['turn_count'],
        "work_history_count": session['work_history_count'],
        "progress": progress,
        "has_data": bool(session.get('collected')),
    }
