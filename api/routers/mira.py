"""
Mira router — AI companion chat for yogis.

Phase 1.5: Embedding-based FAQ + LLM fallback
- Sage's curated FAQ corpus with BGE-M3 embeddings
- Semantic matching with confidence thresholds
- Du/Sie mirroring from user
- LLM fallback with FAQ context grounding
- "I'll ask" fallback → mira_questions table
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import httpx
import json
import re

from api.deps import get_db, require_user
from core.logging_config import get_logger
from lib.mira_faq import get_faq, FAQMatch

logger = get_logger(__name__)

router = APIRouter(prefix="/mira", tags=["mira"])


class ChatRequest(BaseModel):
    message: str
    uses_du: Optional[bool] = None  # None = unknown, True = du, False = Sie


class ChatResponse(BaseModel):
    reply: str
    fallback: bool = False  # True if we couldn't answer and logged to mira_questions
    confidence: Optional[str] = None  # 'high', 'medium', 'low' for debugging
    faq_id: Optional[str] = None  # Which FAQ was matched


# Conversational responses for greetings/thanks/bye (not in FAQ)
CONVERSATIONAL = {
    "greeting": {
        "patterns": [r"^hallo", r"^hi\b", r"^hey", r"^guten (morgen|tag|abend)", r"^servus", r"^moin"],
        "responses_du": ["Hallo! Wie kann ich dir helfen?", "Hey! Was kann ich für dich tun?"],
        "responses_sie": ["Guten Tag! Wie kann ich Ihnen helfen?", "Hallo! Was kann ich für Sie tun?"]
    },
    "thanks": {
        "patterns": [r"dank", r"danke", r"super", r"toll", r"klasse", r"prima"],
        "responses_du": ["Gern geschehen! Wenn du noch Fragen hast, bin ich da.", "Freut mich, dass ich helfen konnte!"],
        "responses_sie": ["Gern geschehen! Wenn Sie noch Fragen haben, bin ich da.", "Freut mich, dass ich helfen konnte!"]
    },
    "bye": {
        "patterns": [r"tschüss", r"bye", r"auf wiedersehen", r"bis (bald|dann|später)", r"ciao"],
        "responses_du": ["Bis bald! Du findest mich immer hier unten rechts.", "Tschüss! Melde dich, wenn du mich brauchst."],
        "responses_sie": ["Auf Wiedersehen! Sie finden mich immer hier unten rechts.", "Bis bald! Melden Sie sich, wenn Sie mich brauchen."]
    }
}


def match_conversational(message: str) -> Optional[str]:
    """Check if message is a simple conversational pattern (greeting/thanks/bye)."""
    message_lower = message.lower()
    
    for category, data in CONVERSATIONAL.items():
        for pattern in data["patterns"]:
            if re.search(pattern, message_lower):
                return category
    
    return None


def get_conversational_response(category: str, uses_du: bool) -> str:
    """Get response for conversational patterns."""
    import random
    data = CONVERSATIONAL[category]
    responses = data["responses_du"] if uses_du else data["responses_sie"]
    return random.choice(responses)


async def ask_llm(message: str, uses_du: bool, context: Optional[str] = None) -> Optional[str]:
    """Fallback to LLM for unmatched questions, optionally with FAQ context."""
    try:
        formal = "Sie" if not uses_du else "du"
        
        # Base system prompt
        system_prompt = f"""Du bist Mira, die freundliche KI-Begleiterin bei talent.yoga, einer Plattform die Talente mit passenden Jobs verbindet.

Deine Eigenschaften:
- Warm, hilfsbereit, aber nicht überschwänglich
- Du sprichst den Nutzer mit "{formal}" an
- Du antwortest auf Deutsch, kurz und präzise (2-3 Sätze)
- Du bist ehrlich: wenn du etwas nicht weißt, sagst du es

Über talent.yoga:
- Kostenlos für Jobsuchende (Standard €5, Sustainer €10+ optional)
- KI-basiertes Matching zwischen Profil und Jobs
- Datenschutz hat Priorität, keine Namen/E-Mails gespeichert
- Doug macht Recherche, Adele macht Interview-Coaching
- Matches werden automatisch gefunden, kein aktives Suchen nötig

Wenn die Frage nichts mit talent.yoga zu tun hat, antworte freundlich dass du als Mira nur bei Fragen rund um talent.yoga helfen kannst."""

        # Add FAQ context for medium-confidence matches
        if context:
            system_prompt += f"""

Ich habe einen ähnlichen FAQ-Eintrag gefunden, der helfen könnte:
{context}

Nutze diese Information als Grundlage, aber passe die Antwort an die konkrete Frage an."""

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.7}
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "").strip()
                
    except Exception as e:
        logger.error(f"Mira LLM error: {e}")
    
    return None


async def log_unanswered(user_id: int, message: str, conn) -> None:
    """Log unanswered question to mira_questions for later review."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO mira_questions (user_id, question, created_at)
                VALUES (%s, %s, NOW())
            """, (user_id, message[:1000]))
        conn.commit()
        logger.info(f"Logged unanswered Mira question from user {user_id}")
    except Exception as e:
        logger.error(f"Failed to log Mira question: {e}")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Handle Mira chat messages with embedding-based FAQ matching."""
    message = request.message.strip()
    uses_du = request.uses_du if request.uses_du is not None else True  # Default to du
    
    logger.info(f"Mira chat: uses_du={request.uses_du} → {uses_du}, message={message[:50]}")
    
    if not message:
        return ChatResponse(
            reply="Ich hab dich nicht verstanden. Kannst du das nochmal sagen?" if uses_du 
                  else "Ich habe Sie nicht verstanden. Können Sie das bitte wiederholen?",
            confidence='low'
        )
    
    # 1. Check for simple conversational patterns (greeting/thanks/bye)
    conv_category = match_conversational(message)
    if conv_category:
        reply = get_conversational_response(conv_category, uses_du)
        return ChatResponse(reply=reply, confidence='high')
    
    # 2. Try embedding-based FAQ matching
    try:
        faq = get_faq()
        match = faq.find_answer(message, uses_du=uses_du, language='de')
        
        logger.info(f"FAQ match: confidence={match.confidence}, score={match.score:.3f}, "
                   f"faq_id={match.faq_entry.faq_id if match.faq_entry else 'none'}")
        
        # High confidence: return curated answer directly
        if match.confidence == 'high' and match.answer:
            return ChatResponse(
                reply=match.answer,
                confidence='high',
                faq_id=match.faq_entry.faq_id if match.faq_entry else None
            )
        
        # Medium confidence: use LLM with FAQ context for grounding
        if match.confidence == 'medium' and match.context:
            llm_reply = await ask_llm(message, uses_du, context=match.context)
            if llm_reply:
                return ChatResponse(
                    reply=llm_reply,
                    confidence='medium',
                    faq_id=match.faq_entry.faq_id if match.faq_entry else None
                )
    
    except Exception as e:
        logger.error(f"FAQ matching error: {e}")
    
    # 3. Low confidence: freeform LLM
    llm_reply = await ask_llm(message, uses_du)
    
    if llm_reply:
        return ChatResponse(reply=llm_reply, confidence='low')
    
    # 4. Ultimate fallback - log and acknowledge
    await log_unanswered(user['user_id'], message, conn)
    
    fallback_msg = ("Das ist eine gute Frage! Ich muss kurz nachfragen und melde mich. "
                   "Du kannst auch direkt an hello@talent.yoga schreiben." if uses_du else
                   "Das ist eine gute Frage! Ich muss kurz nachfragen und melde mich. "
                   "Sie können auch direkt an hello@talent.yoga schreiben.")
    
    return ChatResponse(reply=fallback_msg, fallback=True, confidence='none')
