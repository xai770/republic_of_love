"""
Mira router — greeting endpoint.

Phase 1: New vs returning yogi detection with LLM-generated greetings.
"""
import re
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db, require_user
from core.logging_config import get_logger
from api.routers.mira.models import GreetingResponse
from api.routers.mira.context import ask_llm

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# GREETING TEMPLATES
# ============================================================================

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


# ============================================================================
# GREETING ENDPOINT
# ============================================================================

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

        # --- Check if yogi has ignored Mira 3+ consecutive sessions ---
        suppress_greeting = False
        try:
            # Get recent system events + yogi chat messages, ordered by time
            cur.execute("""
                SELECT sender_type, message_type, body
                FROM yogi_messages
                WHERE user_id = %s
                  AND (
                    (sender_type = 'system' AND message_type = 'event' AND body IN ('logon', 'logoff'))
                    OR
                    (sender_type = 'yogi' AND message_type = 'chat')
                  )
                ORDER BY created_at DESC
                LIMIT 30
            """, (user['user_id'],))
            events = cur.fetchall()

            # Walk backwards through events to count consecutive ignored sessions.
            # An ignored session = logon followed by logoff with no yogi chat in between.
            ignored_count = 0
            in_session = False
            had_chat = False
            for ev in events:  # newest first
                if ev['body'] == 'logoff' and ev['sender_type'] == 'system':
                    in_session = True
                    had_chat = False
                elif ev['sender_type'] == 'yogi' and ev['message_type'] == 'chat':
                    had_chat = True
                elif ev['body'] == 'logon' and ev['sender_type'] == 'system':
                    if in_session:
                        if not had_chat:
                            ignored_count += 1
                        else:
                            break  # yogi engaged — stop counting
                    in_session = False

            if ignored_count >= 3 and not is_new:
                suppress_greeting = True
        except Exception as e:
            logger.warning(f"Failed to check greeting suppression: {e}")

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
            # Hard limit: keep only first 2 sentences
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
        uses_du=uses_du,
        suppress_greeting=suppress_greeting
    )
