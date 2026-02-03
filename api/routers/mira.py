"""
Mira router — AI companion chat for yogis.

Phase 1.5: Embedding-based FAQ + LLM fallback
- Sage's curated FAQ corpus with BGE-M3 embeddings
- Semantic matching with confidence thresholds
- Du/Sie mirroring from user
- LLM fallback with FAQ context grounding
- "I'll ask" fallback → mira_questions table

Phase 1 additions (2026-02-03):
- Greeting flow: new vs returning yogi detection
- Tour offer for new yogis
- Profile upload prompt
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import json
import re
import random

from api.deps import get_db, require_user
from core.logging_config import get_logger
from lib.mira_faq import get_faq, FAQMatch

logger = get_logger(__name__)

router = APIRouter(prefix="/mira", tags=["mira"])


# ============================================================================
# MODELS
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    uses_du: Optional[bool] = None  # None = unknown, True = du, False = Sie


class GreetingResponse(BaseModel):
    greeting: str
    is_new_yogi: bool
    has_profile: bool
    has_skills: bool
    has_matches: int
    suggested_actions: List[str]
    uses_du: bool  # Server's guess, client can override


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


def detect_formality(message: str) -> Optional[bool]:
    """
    Detect Du vs Sie from user's message.
    
    Returns:
        True = uses du (informal)
        False = uses Sie (formal)
        None = can't determine
    """
    message_lower = message.lower()
    
    # Sie indicators (formal)
    sie_patterns = [
        r'\bsie\b',           # Sie (capitalized intent detected via word boundary)
        r'\bihnen\b',         # Ihnen
        r'\bihr\b',           # Ihr (formal possessive)
        r'\bihre[rsmn]?\b',   # Ihre, Ihres, Ihrem, Ihren
        r'\bkönnen sie\b',
        r'\bhaben sie\b',
        r'\bwürden sie\b',
    ]
    
    # Du indicators (informal)
    du_patterns = [
        r'\bdu\b',
        r'\bdich\b',
        r'\bdir\b',
        r'\bdein[esr]?\b',    # dein, deine, deiner, deines
        r'\bkannst du\b',
        r'\bhast du\b',
        r'\bwürdest du\b',
    ]
    
    # Check for Sie first (more specific)
    for pattern in sie_patterns:
        if re.search(pattern, message_lower):
            return False  # Uses Sie
    
    # Then check for du
    for pattern in du_patterns:
        if re.search(pattern, message_lower):
            return True  # Uses du
    
    return None  # Can't determine


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


# ============================================================================
# GREETING ENDPOINT — New vs Returning Yogi
# ============================================================================

# Greeting templates
GREETINGS_NEW_DU = [
    "Hallo! Ich bin Mira, deine Begleiterin bei talent.yoga. Schön, dass du da bist! 👋",
    "Hey! Willkommen bei talent.yoga! Ich bin Mira und helfe dir bei der Jobsuche. 🌟",
]

GREETINGS_NEW_SIE = [
    "Guten Tag! Ich bin Mira, Ihre Begleiterin bei talent.yoga. Willkommen! 👋",
    "Herzlich willkommen bei talent.yoga! Ich bin Mira und unterstütze Sie bei der Jobsuche.",
]

GREETINGS_RETURNING_DU = [
    "Hey, schön dich wiederzusehen! 👋",
    "Willkommen zurück! Was kann ich heute für dich tun?",
    "Hallo! Gut, dass du wieder da bist.",
]

GREETINGS_RETURNING_SIE = [
    "Guten Tag, schön Sie wiederzusehen! 👋",
    "Willkommen zurück! Wie kann ich Ihnen heute helfen?",
    "Hallo! Gut, dass Sie wieder da sind.",
]

GREETINGS_WITH_MATCHES_DU = [
    "Hey! Du hast {n} neue Matches seit deinem letzten Besuch. 🎯",
    "Willkommen zurück! {n} neue passende Jobs warten auf dich.",
]

GREETINGS_WITH_MATCHES_SIE = [
    "Guten Tag! Sie haben {n} neue Matches seit Ihrem letzten Besuch. 🎯",
    "Willkommen zurück! {n} neue passende Stellen warten auf Sie.",
]


@router.get("/greeting", response_model=GreetingResponse)
async def get_greeting(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get personalized greeting for yogi based on their state.
    
    Detects:
    - New vs returning yogi (first login vs subsequent)
    - Has profile with skills?
    - Has any matches?
    
    Returns appropriate greeting + suggested next actions.
    """
    with conn.cursor() as cur:
        # Get user state
        cur.execute("""
            SELECT u.created_at, u.last_login_at,
                   p.profile_id, p.skill_keywords
            FROM users u
            LEFT JOIN profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Determine state
        created_at = row['created_at']
        last_login = row['last_login_at']
        
        # New yogi: created within last hour OR first login
        is_new = (last_login is None or 
                  (datetime.now() - created_at) < timedelta(hours=1))
        
        has_profile = row['profile_id'] is not None
        skill_keywords = row['skill_keywords']
        has_skills = (skill_keywords is not None and 
                     skill_keywords != '[]' and 
                     len(skill_keywords) > 2)  # Not empty array
        
        # Count recent matches (last 7 days)
        cur.execute("""
            SELECT COUNT(*) as cnt FROM profile_posting_matches m
            JOIN profiles p ON m.profile_id = p.profile_id
            WHERE p.user_id = %s 
              AND m.computed_at > NOW() - INTERVAL '7 days'
        """, (user['user_id'],))
        match_count = cur.fetchone()['cnt']
    
    # Default to du (informal) for German users
    uses_du = True
    
    # Build greeting
    if is_new:
        greeting = random.choice(GREETINGS_NEW_DU if uses_du else GREETINGS_NEW_SIE)
    elif match_count > 0:
        template = random.choice(GREETINGS_WITH_MATCHES_DU if uses_du else GREETINGS_WITH_MATCHES_SIE)
        greeting = template.format(n=match_count)
    else:
        greeting = random.choice(GREETINGS_RETURNING_DU if uses_du else GREETINGS_RETURNING_SIE)
    
    # Build suggested actions
    actions = []
    if is_new:
        actions.append("tour")  # Offer tour
    if not has_profile:
        actions.append("upload_profile")
    elif not has_skills:
        actions.append("add_skills")
    if match_count > 0:
        actions.append("view_matches")
    if not actions:
        actions.append("browse_jobs")
    
    return GreetingResponse(
        greeting=greeting,
        is_new_yogi=is_new,
        has_profile=has_profile,
        has_skills=has_skills,
        has_matches=match_count,
        suggested_actions=actions,
        uses_du=uses_du
    )


# ============================================================================
# TOUR & ONBOARDING
# ============================================================================

class TourStep(BaseModel):
    step_id: str
    title: str
    message: str
    target: Optional[str] = None  # CSS selector or element ID to highlight
    action: Optional[str] = None  # 'click', 'type', 'scroll'


class TourResponse(BaseModel):
    steps: List[TourStep]
    total_steps: int


@router.get("/tour", response_model=TourResponse)
async def get_tour(
    uses_du: bool = True,
    user: dict = Depends(require_user)
):
    """
    Get tour steps for new yogi onboarding.
    
    Tour explains:
    1. What talent.yoga does
    2. How to upload profile
    3. Where matches appear
    4. How to chat with Mira
    """
    if uses_du:
        steps = [
            TourStep(
                step_id="welcome",
                title="Willkommen bei talent.yoga! 🧘",
                message="Ich bin Mira, deine persönliche Begleiterin bei der Jobsuche. Lass mich dir kurz zeigen, wie alles funktioniert.",
                target=None
            ),
            TourStep(
                step_id="profile",
                title="Dein Profil 📋",
                message="Hier kannst du deinen Lebenslauf hochladen oder deine Skills manuell eingeben. Je mehr wir über dich wissen, desto bessere Matches finden wir.",
                target="#profile-section",
                action="click"
            ),
            TourStep(
                step_id="matches",
                title="Deine Matches 🎯",
                message="Hier erscheinen Jobs, die zu deinem Profil passen. Du musst nicht aktiv suchen – wir finden die Jobs für dich!",
                target="#matches-section"
            ),
            TourStep(
                step_id="journey",
                title="Deine Reise 🗺️",
                message="Hier siehst du, wo du bei jeder Bewerbung stehst – von 'entdeckt' bis 'eingestellt'. Wie ein Brettspiel!",
                target="#journey-board"
            ),
            TourStep(
                step_id="chat",
                title="Ich bin immer da 💬",
                message="Du findest mich immer hier unten rechts. Frag mich alles über talent.yoga, deine Matches, oder wenn du nicht weiterkommst.",
                target="#mira-chat-button"
            ),
            TourStep(
                step_id="ready",
                title="Los geht's! 🚀",
                message="Das war's schon! Möchtest du jetzt dein Profil hochladen, oder willst du dich erst mal umschauen?",
                action="choose"
            ),
        ]
    else:
        steps = [
            TourStep(
                step_id="welcome",
                title="Willkommen bei talent.yoga! 🧘",
                message="Ich bin Mira, Ihre persönliche Begleiterin bei der Jobsuche. Lassen Sie mich Ihnen kurz zeigen, wie alles funktioniert.",
                target=None
            ),
            TourStep(
                step_id="profile",
                title="Ihr Profil 📋",
                message="Hier können Sie Ihren Lebenslauf hochladen oder Ihre Skills manuell eingeben. Je mehr wir über Sie wissen, desto bessere Matches finden wir.",
                target="#profile-section",
                action="click"
            ),
            TourStep(
                step_id="matches",
                title="Ihre Matches 🎯",
                message="Hier erscheinen Jobs, die zu Ihrem Profil passen. Sie müssen nicht aktiv suchen – wir finden die Jobs für Sie!",
                target="#matches-section"
            ),
            TourStep(
                step_id="journey",
                title="Ihre Reise 🗺️",
                message="Hier sehen Sie, wo Sie bei jeder Bewerbung stehen – von 'entdeckt' bis 'eingestellt'. Wie ein Brettspiel!",
                target="#journey-board"
            ),
            TourStep(
                step_id="chat",
                title="Ich bin immer da 💬",
                message="Sie finden mich immer hier unten rechts. Fragen Sie mich alles über talent.yoga, Ihre Matches, oder wenn Sie nicht weiterkommen.",
                target="#mira-chat-button"
            ),
            TourStep(
                step_id="ready",
                title="Los geht's! 🚀",
                message="Das war's schon! Möchten Sie jetzt Ihr Profil hochladen, oder wollen Sie sich erst mal umschauen?",
                action="choose"
            ),
        ]
    
    return TourResponse(steps=steps, total_steps=len(steps))


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Handle Mira chat messages with embedding-based FAQ matching."""
    message = request.message.strip()
    
    # Detect formality from message, or use client hint, or default to du
    detected_formality = detect_formality(message)
    if request.uses_du is not None:
        uses_du = request.uses_du  # Client explicitly set
    elif detected_formality is not None:
        uses_du = detected_formality  # Detected from message
    else:
        uses_du = True  # Default to informal
    
    logger.info(f"Mira chat: detected={detected_formality}, request={request.uses_du}, final={uses_du}, message={message[:50]}")
    
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
