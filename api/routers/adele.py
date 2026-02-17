"""
Adele router — conversational profile builder.

Endpoint: POST /api/adele/chat
Like Mira's chat but with interview-state tracking.
Messages are persisted in yogi_messages for continuity.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List

from api.deps import get_db, require_user
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

    # Detect language from the message
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
