"""
Mira router — yogi context building and LLM helpers.
"""
import os
import json
import httpx
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)


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

    if ctx['has_profile']:
        if ctx['skills']:
            skills_str = ', '.join(ctx['skills'])
            parts.append(f"""TATSÄCHLICHE SKILLS (aus dem Profil — NUR diese verwenden, niemals andere erfinden):
[{skills_str}]""")
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
