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
import os
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

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    message: str
    uses_du: Optional[bool] = None  # None = unknown, True = du, False = Sie
    history: Optional[List[ChatMessage]] = None  # Conversation history


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
    language: Optional[str] = None  # 'de' or 'en' — current response language


# Language switch patterns (T001)
LANGUAGE_SWITCH = {
    "to_english": {
        "patterns": [
            r"english\s*please",
            r"can we (switch|speak|talk|use) (in\s*)?english",
            r"let'?s (switch|speak|talk|use) (in\s*)?english",
            r"in english",
            r"speak english",
            r"auf englisch",
            r"können wir englisch",
            r"lass uns englisch",
        ],
        "response": "Sure! I can speak English. How can I help you today? 🌍"
    },
    "to_german": {
        "patterns": [
            r"deutsch bitte",
            r"auf deutsch",
            r"können wir deutsch",
            r"lass uns deutsch",
            r"switch to german",
            r"speak german",
            r"in german",
            r"let'?s (switch|speak|talk|use) (in\s*)?german",
        ],
        "response_du": "Klar! Ich spreche wieder Deutsch mit dir. Wie kann ich dir helfen? 🇩🇪",
        "response_sie": "Selbstverständlich! Ich spreche wieder Deutsch mit Ihnen. Wie kann ich Ihnen helfen? 🇩🇪"
    }
}


def detect_language_switch(message: str) -> Optional[str]:
    """
    Detect if user is requesting a language switch.
    
    Returns:
        'en' = switch to English
        'de' = switch to German
        None = no language switch request
    """
    message_lower = message.lower()
    
    for pattern in LANGUAGE_SWITCH["to_english"]["patterns"]:
        if re.search(pattern, message_lower):
            return 'en'
    
    for pattern in LANGUAGE_SWITCH["to_german"]["patterns"]:
        if re.search(pattern, message_lower):
            return 'de'
    
    return None


def detect_language_from_message(message: str) -> Optional[str]:
    """
    Detect which language the user is writing in.
    
    Returns:
        'en' = English
        'de' = German
        None = can't determine
    """
    message_lower = message.lower()
    
    # Common English words/phrases (not shared with German)
    english_markers = [
        r'\bthe\b', r'\bwhat\b', r'\bhow\b', r'\bwhy\b', r'\bwhere\b',
        r'\byou\b', r'\byour\b', r'\bplease\b', r'\bthanks?\b',
        r'\bhelp\b', r'\bcan\b', r'\bcould\b', r'\bwould\b',
        r'\bi am\b', r"\bi'm\b", r'\bi have\b', r"\bi've\b",
    ]
    
    # Common German words/phrases (not shared with English)
    german_markers = [
        r'\bich\b', r'\bist\b', r'\bsind\b', r'\bwas\b', r'\bwie\b',
        r'\bwarum\b', r'\bwo\b', r'\bwer\b', r'\bwenn\b', r'\bweil\b',
        r'\bkann\b', r'\bkönnen\b', r'\bmöchte\b', r'\bwürde\b',
        r'\bmit\b', r'\bfür\b', r'\bund\b', r'\baber\b', r'\bauch\b',
        r'\bbitte\b', r'\bdanke\b', r'\bhallo\b', r'\bguten\b',
    ]
    
    en_score = sum(1 for p in english_markers if re.search(p, message_lower))
    de_score = sum(1 for p in german_markers if re.search(p, message_lower))
    
    if en_score > de_score and en_score >= 2:
        return 'en'
    elif de_score > en_score and de_score >= 1:
        return 'de'
    
    return None


# Conversational responses for greetings/thanks/bye (not in FAQ)
CONVERSATIONAL = {
    "greeting": {
        "patterns": [r"^hallo", r"^hi\b", r"^hey", r"^guten (morgen|tag|abend)", r"^servus", r"^moin", r"^hello", r"^good (morning|afternoon|evening)"],
        "responses_du": ["Hallo! Wie kann ich dir helfen?", "Hey! Was kann ich für dich tun?"],
        "responses_sie": ["Guten Tag! Wie kann ich Ihnen helfen?", "Hallo! Was kann ich für Sie tun?"],
        "responses_en": ["Hi! How can I help you today?", "Hello! What can I do for you?"]
    },
    "thanks": {
        "patterns": [r"dank", r"danke", r"super", r"toll", r"klasse", r"prima", r"thanks?", r"thank you", r"great", r"awesome"],
        "responses_du": ["Gern geschehen! Wenn du noch Fragen hast, bin ich da.", "Freut mich, dass ich helfen konnte!"],
        "responses_sie": ["Gern geschehen! Wenn Sie noch Fragen haben, bin ich da.", "Freut mich, dass ich helfen konnte!"],
        "responses_en": ["You're welcome! Let me know if you have more questions.", "Happy to help!"]
    },
    "bye": {
        "patterns": [r"tschüss", r"bye", r"auf wiedersehen", r"bis (bald|dann|später)", r"ciao", r"goodbye", r"see you"],
        "responses_du": ["Bis bald! Du findest mich immer hier unten rechts.", "Tschüss! Melde dich, wenn du mich brauchst."],
        "responses_sie": ["Auf Wiedersehen! Sie finden mich immer hier unten rechts.", "Bis bald! Melden Sie sich, wenn Sie mich brauchen."],
        "responses_en": ["See you! You can find me in the bottom right corner anytime.", "Bye! Let me know if you need anything."]
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


def get_conversational_response(category: str, uses_du: bool, language: str = 'de') -> str:
    """Get response for conversational patterns."""
    import random
    data = CONVERSATIONAL[category]
    
    if language == 'en':
        responses = data.get("responses_en", data["responses_du"])  # Fallback to du
    elif uses_du:
        responses = data["responses_du"]
    else:
        responses = data["responses_sie"]
    
    return random.choice(responses)


def build_yogi_context(user_id: int, conn) -> dict:
    """
    Build context about the yogi for Mira's responses.
    
    Returns dict with:
    - profile_summary: skills, preferences
    - recent_matches: top 3 match titles
    - journey_summary: active applications, states
    - last_activity: what yogi did recently
    """
    context = {
        'has_profile': False,
        'skills': [],
        'recent_matches': [],
        'journey_states': {},
        'match_count': 0,
    }
    
    with conn.cursor() as cur:
        # Get profile info
        cur.execute("""
            SELECT p.skill_keywords
            FROM profiles p
            WHERE p.user_id = %s
        """, (user_id,))
        profile = cur.fetchone()
        
        if profile:
            context['has_profile'] = True
            try:
                import json
                skills = json.loads(profile['skill_keywords'] or '[]')
                context['skills'] = skills[:10]  # Limit to 10
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        
        # Get best matches (score > 30%, ordered by quality, not recency)
        cur.execute("""
            SELECT p.job_title, p.posting_name as company, m.skill_match_score as score
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            JOIN postings p ON m.posting_id = p.posting_id
            WHERE pr.user_id = %s
              AND m.skill_match_score > 30
            ORDER BY m.skill_match_score DESC
            LIMIT 3
        """, (user_id,))
        
        context['recent_matches'] = [
            {'title': r['job_title'], 'company': r['company'], 'score': float(r['score'] or 0) / 100}
            for r in cur.fetchall()
        ]
        
        # Get journey state counts
        cur.execute("""
            SELECT state, COUNT(*) as cnt
            FROM user_posting_interactions
            WHERE user_id = %s
            GROUP BY state
        """, (user_id,))
        context['journey_states'] = {r['state']: r['cnt'] for r in cur.fetchall()}
        
        # Total match count
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM profile_posting_matches m
            JOIN profiles p ON m.profile_id = p.profile_id
            WHERE p.user_id = %s
        """, (user_id,))
        context['match_count'] = cur.fetchone()['cnt']
    
    return context


def format_yogi_context_for_prompt(ctx: dict, uses_du: bool) -> str:
    """Format yogi context as text for system prompt."""
    parts = []
    
    formal = "Sie" if not uses_du else "du"
    poss = "Ihre" if not uses_du else "deine"
    
    if ctx['has_profile']:
        if ctx['skills']:
            skills_str = ', '.join(ctx['skills'])
            parts.append(f"""TATSÄCHLICHE SKILLS (aus dem Profil — NUR diese verwenden, niemals andere erfinden):
[{skills_str}]""")
    else:
        if uses_du:
            parts.append("(Noch kein Profil hochgeladen)")
        else:
            parts.append("(Noch kein Profil hochgeladen)")
    
    if ctx['match_count'] > 0:
        parts.append(f"Matches: {ctx['match_count']} gefunden")
        if ctx['recent_matches']:
            recent = ctx['recent_matches'][0]
            parts.append(f"Neuester Match: {recent['title']} bei {recent['company']} ({recent['score']:.0%})")
    
    if ctx['journey_states']:
        applied = ctx['journey_states'].get('applied', 0)
        interested = ctx['journey_states'].get('interested', 0)
        if applied > 0:
            parts.append(f"Bewerbungen: {applied}")
        if interested > 0:
            parts.append(f"Interessiert an: {interested} Jobs")
    
    return '\n'.join(parts) if parts else ''


async def ask_llm(message: str, uses_du: bool, context: Optional[str] = None, yogi_context: Optional[dict] = None, language: str = 'de') -> Optional[str]:
    """Fallback to LLM for unmatched questions, optionally with FAQ and yogi context."""
    try:
        if language == 'en':
            # English system prompt
            system_prompt = """You are Mira, a friendly AI companion at talent.yoga, a platform that connects talent with matching jobs.

Your traits:
- Warm, helpful, but not overly enthusiastic
- You respond in English, brief and precise (2-3 sentences)
- You're honest: if you don't know something, you say so

About talent.yoga:
- Free for job seekers (Standard €5, Sustainer €10+ optional)
- AI-based matching between profile and jobs
- Privacy is priority, no names/emails stored
- Doug does research, Adele does interview coaching
- Matches are found automatically, no active searching needed

If the question is unrelated to talent.yoga, politely say that as Mira you can only help with talent.yoga related questions."""
        else:
            formal = "Sie" if not uses_du else "du"
            
            # German system prompt
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

        # Add yogi context if available
        if yogi_context:
            yogi_text = format_yogi_context_for_prompt(yogi_context, uses_du)
            if yogi_text:
                system_prompt += f"""

Aktueller Stand {"des Nutzers" if not uses_du else "des Yogis"}:
{yogi_text}

Nutze diese Information wenn relevant, aber erwähne sie nicht ungefragt."""

        # Add FAQ context for medium-confidence matches
        if context:
            system_prompt += f"""

Ich habe einen ähnlichen FAQ-Eintrag gefunden, der helfen könnte:
{context}

Nutze diese Information als Grundlage, aber passe die Antwort an die konkrete Frage an."""

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/chat',
                json={
                    "model": "gemma3:4b",
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
    "Hey! {n} neue Matches seit deinem letzten Besuch — eine davon sieht vielversprechend aus! 🎯",
    "Willkommen zurück! {n} neue passende Jobs warten auf dich.",
    "Schön dich zu sehen! {n} neue Stellen seit gestern. Soll ich sie dir zeigen?",
]

GREETINGS_WITH_MATCHES_SIE = [
    "Guten Tag! {n} neue Matches seit Ihrem letzten Besuch. 🎯",
    "Willkommen zurück! {n} neue passende Stellen warten auf Sie.",
    "Schön Sie zu sehen! {n} neue Stellen seit Ihrem letzten Besuch.",
]


@router.get("/greeting", response_model=GreetingResponse)
async def get_greeting(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get personalized, LLM-generated greeting for the Home page.
    
    Mira remembers the yogi: loads recent conversation history from 
    yogi_messages and profile state, then asks the LLM to generate a 
    warm, personal greeting. Falls back to templates if LLM is unavailable.
    """
    with conn.cursor() as cur:
        # Get user state
        cur.execute("""
            SELECT u.created_at, u.last_login_at, u.display_name,
                   p.profile_id, p.skill_keywords, p.full_name,
                   p.experience_level, p.location
            FROM users u
            LEFT JOIN profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Extract state
        created_at = row['created_at']
        last_login = row['last_login_at']
        display_name = row['display_name'] or row['full_name'] or ''
        first_name = display_name.split()[0] if display_name else ''
        
        is_new = (last_login is None or 
                  (datetime.now() - created_at) < timedelta(hours=1))
        
        has_profile = row['profile_id'] is not None
        skill_keywords = row['skill_keywords']
        has_skills = (skill_keywords is not None and 
                     skill_keywords != '[]' and 
                     len(skill_keywords) > 2)
        
        # Count matches
        if last_login:
            cur.execute("""
                SELECT COUNT(*) as cnt FROM profile_posting_matches m
                JOIN profiles p ON m.profile_id = p.profile_id
                WHERE p.user_id = %s AND m.computed_at > %s
            """, (user['user_id'], last_login))
        else:
            cur.execute("""
                SELECT COUNT(*) as cnt FROM profile_posting_matches m
                JOIN profiles p ON m.profile_id = p.profile_id
                WHERE p.user_id = %s
            """, (user['user_id'],))
        match_count = cur.fetchone()['cnt']
        
        # --- MEMORY: Load last few messages from yogi_messages ---
        recent_messages = []
        try:
            cur.execute("""
                SELECT sender_type, body, created_at
                FROM yogi_messages
                WHERE user_id = %s AND sender_type IN ('yogi', 'mira')
                ORDER BY created_at DESC
                LIMIT 6
            """, (user['user_id'],))
            rows = cur.fetchall()
            for r in reversed(rows):
                speaker = 'Yogi' if r['sender_type'] == 'yogi' else 'Mira'
                recent_messages.append(f"{speaker}: {r['body']}")
        except Exception as e:
            logger.warning(f"Failed to load greeting memory: {e}")
    
    uses_du = True
    
    # --- LLM-GENERATED GREETING ---
    llm_greeting = None
    try:
        hour = datetime.now().hour
        if hour < 12:
            time_ctx = "Morgen"
        elif hour < 18:
            time_ctx = "Nachmittag"
        else:
            time_ctx = "Abend"
        
        # Build memory context — extract just topics, not raw messages
        memory_block = ""
        if recent_messages:
            # Summarize recent topics instead of dumping raw history
            # This prevents the LLM from garbling message content
            yogi_topics = [m.split(': ', 1)[1][:60] for m in recent_messages if m.startswith('Yogi:')]
            if yogi_topics:
                memory_block = f"\n\nLETZTE THEMEN: {', '.join(yogi_topics[-3:])}"
        
        # Build yogi state
        state_parts = []
        if first_name:
            state_parts.append(f"Name: {first_name}")
        if is_new:
            state_parts.append("Status: Ganz neu bei talent.yoga")
        else:
            state_parts.append("Status: Kehrt zurück")
        if has_profile and has_skills:
            state_parts.append("Profil: Vorhanden mit Skills")
        elif has_profile:
            state_parts.append("Profil: Vorhanden, braucht noch Skills")
        else:
            state_parts.append("Profil: Noch nicht hochgeladen")
        if match_count > 0:
            state_parts.append(f"Neue Matches: {match_count}")
        state_block = "\n".join(state_parts)
        
        greeting_prompt = f"""Du bist Mira bei talent.yoga. Schreibe eine KURZE Begrüßung.

STRENGE REGELN:
- GENAU 1-2 Sätze. NIEMALS mehr. Maximal 120 Zeichen.
- Duze den Yogi
- Erwähne den Namen wenn bekannt
- Wenn neue Matches: nenne die Anzahl
- Wenn du Themen siehst: ein kurzer Bezug zeigt Erinnerung
- Kein Emoji, keine Ausrufezeichen-Flut
- Ende mit EINER kurzen Einladung (nicht mehrere Optionen auflisten!)
- VERBOTEN: Fragen stapeln, Optionen auflisten, mehr als 2 Sätze

KONTEXT:
{state_block}{memory_block}

Begrüßung (max 120 Zeichen):"""

        response = await ask_llm(greeting_prompt, uses_du=True, language='de')
        if response and len(response.strip()) > 10:
            cleaned = response.strip().strip('"').strip()
            # Hard limit: if LLM ignores the rules, keep only first 2 sentences
            # Split on sentence boundaries (". " or "! " or end-of-string), NOT on every period
            # This preserves "talent.yoga" and similar dotted names
            import re
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]
            if len(sentences) > 2:
                cleaned = ' '.join(sentences[:2])
                if not cleaned.endswith(('.', '!', '?')):
                    cleaned += '.'
            llm_greeting = cleaned
    except Exception as e:
        logger.warning(f"LLM greeting failed, falling back to template: {e}")
    
    # --- FALLBACK: Template-based greeting ---
    if llm_greeting:
        greeting = llm_greeting
    elif is_new:
        greeting = random.choice(GREETINGS_NEW_DU)
    elif match_count > 0:
        template = random.choice(GREETINGS_WITH_MATCHES_DU)
        greeting = template.format(n=match_count)
    else:
        greeting = random.choice(GREETINGS_RETURNING_DU)
    
    # Build suggested actions
    actions = []
    if is_new:
        actions.append("tour")
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


# ============================================================================
# CONTEXT & PROACTIVE MESSAGES
# ============================================================================

class YogiContext(BaseModel):
    has_profile: bool
    skills: List[str]
    match_count: int
    recent_matches: List[dict]
    journey_states: dict


@router.get("/context", response_model=YogiContext)
async def get_yogi_context(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get yogi's context for display or debugging.
    
    This is the same context Mira uses to personalize responses.
    """
    ctx = build_yogi_context(user['user_id'], conn)
    return YogiContext(**ctx)


class ProactiveMessage(BaseModel):
    message_type: str  # new_matches, saved_job_open, application_viewed
    message: str
    data: Optional[dict] = None


class ProactiveResponse(BaseModel):
    messages: List[ProactiveMessage]


@router.get("/proactive", response_model=ProactiveResponse)
async def get_proactive_messages(
    uses_du: bool = True,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Get proactive messages Mira should display.
    
    Checks for:
    - New matches since last visit
    - Saved jobs still open
    - Application status changes (if trackable)
    """
    messages = []
    
    with conn.cursor() as cur:
        # Get last login
        cur.execute("""
            SELECT last_login_at FROM users WHERE user_id = %s
        """, (user['user_id'],))
        last_login = cur.fetchone()
        last_login_at = last_login['last_login_at'] if last_login else None
        
        # Count new matches since last login
        if last_login_at:
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM profile_posting_matches m
                JOIN profiles p ON m.profile_id = p.profile_id
                WHERE p.user_id = %s AND m.computed_at > %s
            """, (user['user_id'], last_login_at))
            new_matches = cur.fetchone()['cnt']
            
            if new_matches > 0:
                if uses_du:
                    msg = f"🎯 {new_matches} neue Matches seit deinem letzten Besuch!"
                else:
                    msg = f"🎯 {new_matches} neue Matches seit Ihrem letzten Besuch!"
                messages.append(ProactiveMessage(
                    message_type="new_matches",
                    message=msg,
                    data={"count": new_matches}
                ))
        
        # Check favorited jobs still available
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM user_posting_interactions i
            JOIN postings p ON i.posting_id = p.posting_id
            WHERE i.user_id = %s 
              AND i.is_favorited = TRUE
              AND p.posting_status = 'active'
        """, (user['user_id'],))
        saved_open = cur.fetchone()['cnt']
        
        if saved_open > 0 and not last_login_at:  # Only for returning users who haven't seen this
            if uses_du:
                msg = f"⭐ {saved_open} deiner gemerkten Jobs sind noch offen!"
            else:
                msg = f"⭐ {saved_open} Ihrer gemerkten Jobs sind noch offen!"
            messages.append(ProactiveMessage(
                message_type="saved_job_open",
                message=msg,
                data={"count": saved_open}
            ))
        
        # Check for pending applications (ghosting detection)
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM user_posting_interactions
            WHERE user_id = %s 
              AND state = 'outcome_pending'
              AND state_changed_at < NOW() - INTERVAL '14 days'
        """, (user['user_id'],))
        waiting_long = cur.fetchone()['cnt']
        
        if waiting_long > 0:
            if uses_du:
                msg = f"⏳ {waiting_long} Bewerbungen warten schon länger auf Antwort. Soll ich nachfragen helfen?"
            else:
                msg = f"⏳ {waiting_long} Bewerbungen warten schon länger auf Antwort. Soll ich beim Nachfragen helfen?"
            messages.append(ProactiveMessage(
                message_type="long_wait",
                message=msg,
                data={"count": waiting_long}
            ))
    
    return ProactiveResponse(messages=messages)


# ============================================================================
# CONSENT PROMPT — Notification Opt-in
# ============================================================================

class ConsentPromptResponse(BaseModel):
    should_prompt: bool
    message: Optional[str] = None
    consent_given: bool = False


@router.get("/consent-prompt", response_model=ConsentPromptResponse)
async def get_consent_prompt(
    uses_du: bool = True,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Check if user should be prompted for notification consent.
    
    Should prompt when:
    - User has a profile with skills
    - User has NOT yet given consent (notification_consent_at is NULL)
    - We have matches to notify about
    
    Returns a personalized Mira prompt message.
    """
    with conn.cursor() as cur:
        # Check user's consent status
        cur.execute("""
            SELECT u.notification_email, u.notification_consent_at,
                   p.profile_id, p.skill_keywords
            FROM users u
            LEFT JOIN profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        
        if not row:
            return ConsentPromptResponse(should_prompt=False)
        
        # Already has consent
        if row['notification_consent_at']:
            return ConsentPromptResponse(
                should_prompt=False, 
                consent_given=True
            )
        
        # No profile yet - don't prompt
        if not row['profile_id']:
            return ConsentPromptResponse(should_prompt=False)
        
        # Check if has skills
        skill_keywords = row['skill_keywords']
        has_skills = (skill_keywords is not None and 
                     skill_keywords != '[]' and 
                     len(skill_keywords) > 2)
        
        if not has_skills:
            return ConsentPromptResponse(should_prompt=False)
        
        # User has profile with skills but no consent - prompt!
        if uses_du:
            message = (
                "Soll ich dir Bescheid sagen, wenn es neue passende Stellen gibt? 📬 "
                "Dafür bräuchte ich deine E-Mail-Adresse. "
                "Du kannst das jederzeit in den Einstellungen ändern."
            )
        else:
            message = (
                "Soll ich Ihnen Bescheid sagen, wenn es neue passende Stellen gibt? 📬 "
                "Dafür bräuchte ich Ihre E-Mail-Adresse. "
                "Sie können das jederzeit in den Einstellungen ändern."
            )
        
        return ConsentPromptResponse(
            should_prompt=True,
            message=message,
            consent_given=False
        )


class ConsentSubmission(BaseModel):
    email: str
    grant_consent: bool = True


@router.post("/consent-submit")
async def submit_consent(
    data: ConsentSubmission,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Submit notification consent via Mira chat.
    
    This is a convenience endpoint that wraps the notifications/consent API.
    """
    import re
    
    # Validate email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, data.email):
        raise HTTPException(status_code=400, detail="Ungültige E-Mail-Adresse")
    
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE users
            SET notification_email = %s,
                notification_consent_at = CASE WHEN %s THEN NOW() ELSE NULL END
            WHERE user_id = %s
            RETURNING notification_consent_at
        """, (data.email, data.grant_consent, user['user_id']))
        
        row = cur.fetchone()
        conn.commit()
        
        return {
            "status": "ok",
            "consent_given": row['notification_consent_at'] is not None
        }


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
    # Session history from frontend may overlap with DB, so we use DB as base
    # and only append session messages not already in DB
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
        # Find last user message and its Mira response
        for i in range(len(history_list) - 1, 0, -1):
            if history_list[i]['role'] == 'assistant' and history_list[i-1]['role'] == 'user':
                previous_exchange = (history_list[i-1]['content'], history_list[i]['content'])
                break
    
    # Use the new LLM-first module
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
    try:
        with conn.cursor() as cur:
            # Save user message
            cur.execute("""
                INSERT INTO yogi_messages (user_id, sender_type, message_type, body, recipient_type)
                VALUES (%s, 'yogi', 'chat', %s, 'mira')
            """, (user['user_id'], message))
            # Save Mira's reply
            cur.execute("""
                INSERT INTO yogi_messages (user_id, sender_type, message_type, body)
                VALUES (%s, 'mira', 'chat', %s)
            """, (user['user_id'], response.reply))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to persist chat messages: {e}")
    
    logger.info(f"Mira LLM response: lang={response.language}, fallback={response.fallback}, db_history={len(db_history)}, session_history={len(request.history) if request.history else 0}")
    
    return ChatResponse(
        reply=response.reply,
        confidence='llm' if not response.fallback else 'none',
        language=response.language,
        fallback=response.fallback
    )
