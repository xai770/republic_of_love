"""
Mira router — main chat endpoint.

LLM-first approach with persistent memory via yogi_messages.
"""
from fastapi import APIRouter, Depends

from api.deps import get_db, require_user
from core.logging_config import get_logger
from api.routers.mira.models import ChatRequest, ChatResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Handle Mira chat messages — LLM-first approach.

    Memory: loads last 5 messages from yogi_messages (persistent DB history)
    and prepends them before the current session history. This gives Mira
    memory across browser refreshes / sessions.

    Everyone is a citizen: both user messages and Mira's replies are stored
    in yogi_messages for future recall.

    FAQ candidate detection: Flags interesting exchanges for human review.
    """
    from core.mira_llm import chat as mira_chat
    from lib.faq_candidate_detector import maybe_flag_exchange

    message = request.message.strip()

    if not message:
        return ChatResponse(
            reply="I didn't catch that. Could you say that again?",
            confidence='low',
            language='en'
        )

    # --- MEMORY: Load persistent chat history from yogi_messages ---
    db_history = []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sender_type, body, created_at
                FROM yogi_messages
                WHERE user_id = %s
                  AND sender_type IN ('yogi', 'mira')
                ORDER BY created_at DESC
                LIMIT 10
            """, (user['user_id'],))
            rows = cur.fetchall()
            # Reverse to chronological order
            for row in reversed(rows):
                role = 'user' if row['sender_type'] == 'yogi' else 'assistant'
                db_history.append({"role": role, "content": row['body']})
    except Exception as e:
        logger.warning(f"Failed to load chat history: {e}")

    # --- Merge: DB history (older) + session history (current) ---
    history_list = db_history.copy()
    if request.history:
        session_msgs = [{"role": m.role, "content": m.content} for m in request.history]
        # Append only messages not already in db_history (by content match)
        db_contents = {h['content'] for h in db_history}
        for msg in session_msgs:
            if msg['content'] not in db_contents:
                history_list.append(msg)

    # Extract previous exchange for feedback detection
    previous_exchange = None
    if len(history_list) >= 2:
        for i in range(len(history_list) - 1, 0, -1):
            if history_list[i]['role'] == 'assistant' and history_list[i-1]['role'] == 'user':
                previous_exchange = (history_list[i-1]['content'], history_list[i]['content'])
                break

    # Use the LLM-first module
    response = await mira_chat(message, user['user_id'], conn, history=history_list)

    # --- FAQ CANDIDATE DETECTION ---
    try:
        maybe_flag_exchange(
            conn=conn,
            user_id=user['user_id'],
            user_message=message,
            mira_response=response.reply,
            was_fallback=response.fallback,
            previous_exchange=previous_exchange
        )
    except Exception as e:
        logger.warning(f"FAQ candidate detection failed: {e}")

    # --- PERSIST: Save both user message and Mira's reply to yogi_messages ---
    user_message_id = None
    mira_message_id = None
    try:
        with conn.cursor() as cur:
            # Save user message
            cur.execute("""
                INSERT INTO yogi_messages (user_id, sender_type, message_type, body, recipient_type)
                VALUES (%s, 'yogi', 'chat', %s, 'mira')
                RETURNING message_id
            """, (user['user_id'], message))
            user_message_id = cur.fetchone()['message_id']
            # Save Mira's reply
            cur.execute("""
                INSERT INTO yogi_messages (user_id, sender_type, message_type, body)
                VALUES (%s, 'mira', 'chat', %s)
                RETURNING message_id
            """, (user['user_id'], response.reply))
            mira_message_id = cur.fetchone()['message_id']
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to persist chat messages: {e}")

    # --- USAGE: Log billable event (with message_ids for drill-down) ---
    try:
        from lib.usage_tracker import log_event
        log_event(conn, user['user_id'], 'mira_message',
                  context={
                      'user_message_id': user_message_id,
                      'mira_message_id': mira_message_id,
                      'message_len': len(message),
                      'fallback': response.fallback,
                  })
    except Exception as e:
        logger.warning(f"Usage tracking failed: {e}")

    logger.info(f"Mira LLM response: lang={response.language}, fallback={response.fallback}, db_history={len(db_history)}, session_history={len(request.history) if request.history else 0}")

    return ChatResponse(
        reply=response.reply,
        confidence='llm' if not response.fallback else 'none',
        language=response.language,
        fallback=response.fallback,
        actions=response.actions
    )
