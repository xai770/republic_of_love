"""
Mira LLM-First Module — Clean implementation

This replaces the pattern-matching FAQ approach with pure LLM.
FAQ knowledge is embedded in the system prompt.

Usage:
    from lib.mira_llm import MiraLLM
    
    mira = MiraLLM()
    response = await mira.chat(message, user_id, conn)
"""
import json
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import httpx

from core.logging_config import get_logger

logger = get_logger(__name__)

# Model config
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"
TEMPERATURE = 0.3  # Lower = more consistent
TIMEOUT = 20.0


@dataclass
class MiraResponse:
    """Response from Mira."""
    reply: str
    language: str  # 'de' or 'en'
    fallback: bool = False  # True if LLM failed and we used fallback


# Condensed FAQ knowledge (fits in ~2000 tokens)
FAQ_KNOWLEDGE_DE = """
**Preise:**
- Kostenlos für Jobsuchende
- Standard: €5/Monat (unbegrenzte Matches, Doug-Recherche)
- Sustainer: €10+/Monat (Standard + finanziert andere)
- Alles transparent unter "Finanzen"

**Datenschutz:**
- Nur Skills, Präferenzen, Bewerbungshistorie gespeichert
- KEIN Name, KEINE E-Mail, KEIN CV-Text gespeichert
- Original-Dokumente nach Extraktion gelöscht
- Jederzeit löschbar unter "Mein Konto"
- Keine Datenweitergabe, keine Werbung

**Matching:**
- Semantisches Matching (nicht nur Keywords)
- "Python-Entwickler" matcht "Backend Developer (Python)"
- Prozentzahl = Übereinstimmung Profil ↔ Anforderungen
- Jeder Match erklärt: was passt, was fehlt

**Profil:**
- CV hochladen (PDF/Word) oder Skills manuell
- Nach Extraktion wird Original gelöscht
- Skills jederzeit änderbar unter "Profil"
- Änderungen wirken sofort auf Matches

**Team:**
- Mira (ich) = deine Begleiterin
- Doug = Web-Recherche über Firmen
- Adele = Interview-Coaching

**Fokus:**
- Deutschland (34K+ Stellen von Arbeitsagentur)
- Semantisches Matching mit KI

**Yogis:**
- Jobsuchende heißen hier "Yogis"
- Jobsuche ist eine Praxis, kein einmaliger Vorgang

**Wenn ich nicht helfen kann:**
- Rechtsfragen → Arbeitsagentur oder Anwalt
- Vorhersagen → kann ich nicht machen
- Versprechen → mache ich nicht
"""

FAQ_KNOWLEDGE_EN = """
**Pricing:**
- Free for job seekers
- Standard: €5/month (unlimited matches, Doug research)
- Sustainer: €10+/month (Standard + sponsors others)
- Everything transparent under "Finances"

**Privacy:**
- Only skills, preferences, application history stored
- NO name, NO email, NO CV text stored
- Original documents deleted after extraction
- Deletable anytime under "My Account"
- No data sharing, no ads

**Matching:**
- Semantic matching (not just keywords)
- "Python developer" matches "Backend Developer (Python)"
- Percentage = profile ↔ requirements match
- Each match explained: what fits, what's missing

**Profile:**
- Upload CV (PDF/Word) or enter skills manually
- Original deleted after extraction
- Skills editable anytime under "Profile"
- Changes affect matches immediately

**Team:**
- Mira (me) = your companion
- Doug = web research about companies
- Adele = interview coaching

**Focus:**
- Germany (34K+ jobs from Arbeitsagentur)
- Semantic AI matching

**Yogis:**
- Job seekers are called "yogis" here
- Job searching is a practice, not a one-time event

**When I can't help:**
- Legal questions → employment agency or lawyer
- Predictions → I can't make those
- Promises → I don't make those
"""


def build_system_prompt(language: str, uses_du: bool, yogi_context: Optional[dict] = None) -> str:
    """Build the complete system prompt for Mira."""
    
    if language == 'en':
        prompt = f"""You are Mira, the personal companion at talent.yoga — a platform connecting job seekers with matching positions in Germany.

## Your Personality

You are calm, knowledgeable, and warm — like a friend who knows job searching and sits beside you.

- You respond briefly (2-4 sentences), in chat style
- You are helpful but never pushy
- If you don't know something, say so: "I'm not sure about that. Let me check."
- If the user switches language, follow them

## What you KNOW

{FAQ_KNOWLEDGE_EN}

## What you CANNOT do

- Give legal advice → suggest "employment agency or lawyer"
- Predict outcomes → "I can't predict, but here's what I see..."
- Make promises → "Based on the data..."
- Criticize employers harshly
- Make up answers → "I don't know" is always valid

## Instructions

1. Answer based on your knowledge above
2. Keep it SHORT — 2-4 sentences max
3. Be honest when you don't know
4. Match the user's language and formality
"""
    else:
        formal = "Sie" if not uses_du else "du"
        poss = "Ihre" if not uses_du else "deine"
        verb_end = "en Sie" if not uses_du else "st du"
        
        prompt = f"""Du bist Mira, die persönliche Begleiterin bei talent.yoga — einer Plattform, die Jobsuchende mit passenden Stellen in Deutschland verbindet.

## Deine Persönlichkeit

Du bist ruhig, kompetent und warmherzig — wie eine Freundin, die Jobsuche kennt und neben dir sitzt.

- Du antwortest kurz (2-4 Sätze), im Chat-Stil
- Du sprichst den Nutzer mit "{formal}" an
- Du bist hilfsbereit, aber nicht aufdringlich
- Wenn du etwas nicht weißt, sag es: "Das weiß ich nicht sicher. Ich frage nach."
- Wenn der Nutzer die Sprache wechseln möchte, folge ihm

## Was du WEISST

{FAQ_KNOWLEDGE_DE}

## Was du NICHT kannst

- Rechtsberatung → verweise auf "Arbeitsagentur oder Anwalt"
- Vorhersagen → "Ob du den Job bekommst, kann ich nicht sagen, aber..."
- Versprechen → "Basierend auf den Daten..."
- Arbeitgeber hart kritisieren
- Antworten erfinden → "Das weiß ich nicht" ist immer gültig

## Anweisungen

1. Antworte basierend auf deinem Wissen oben
2. Halte dich KURZ — maximal 2-4 Sätze
3. Sei ehrlich wenn du etwas nicht weißt
4. Spiegele die Sprache und Formalität des Nutzers
"""

    # Add yogi context if available
    if yogi_context:
        context_str = format_yogi_context(yogi_context, uses_du, language)
        if context_str:
            if language == 'en':
                prompt += f"\n## Current User Situation\n\n{context_str}\n"
            else:
                prompt += f"\n## Aktuelle Situation des Nutzers\n\n{context_str}\n"
    
    return prompt


def format_yogi_context(ctx: dict, uses_du: bool, language: str) -> str:
    """Format yogi context for the system prompt."""
    parts = []
    
    if language == 'en':
        if ctx.get('has_profile'):
            if ctx.get('skills'):
                skills_str = ', '.join(ctx['skills'][:5])
                parts.append(f"Skills: {skills_str}")
        else:
            parts.append("(No profile uploaded yet)")
        
        if ctx.get('match_count', 0) > 0:
            parts.append(f"Matches: {ctx['match_count']} found")
            if ctx.get('recent_matches'):
                recent = ctx['recent_matches'][0]
                parts.append(f"Latest: {recent['title']} at {recent['company']} ({recent['score']:.0%})")
    else:
        if ctx.get('has_profile'):
            if ctx.get('skills'):
                skills_str = ', '.join(ctx['skills'][:5])
                parts.append(f"Skills: {skills_str}")
        else:
            parts.append("(Noch kein Profil hochgeladen)")
        
        if ctx.get('match_count', 0) > 0:
            parts.append(f"Matches: {ctx['match_count']} gefunden")
            if ctx.get('recent_matches'):
                recent = ctx['recent_matches'][0]
                parts.append(f"Neuester: {recent['title']} bei {recent['company']} ({recent['score']:.0%})")
    
    return '\n'.join(parts) if parts else ''


def detect_language(message: str) -> str:
    """
    Detect message language and language switch requests.
    
    Returns 'en' or 'de'.
    """
    message_lower = message.lower()
    
    # Explicit language switch requests
    english_switch = [
        r'english\s*please', r'in english', r'speak english',
        r'can we (switch|speak|talk|use).*english',
        r"let'?s.*english", r'auf englisch',
    ]
    german_switch = [
        r'deutsch\s*bitte', r'auf deutsch', r'in german',
        r'können wir deutsch', r'lass uns deutsch',
        r'speak german', r'switch to german',
    ]
    
    for pattern in english_switch:
        if re.search(pattern, message_lower):
            return 'en'
    
    for pattern in german_switch:
        if re.search(pattern, message_lower):
            return 'de'
    
    # Detect from content
    english_markers = [
        r'\bthe\b', r'\bwhat\b', r'\bhow\b', r'\bwhy\b', r'\bwhere\b',
        r'\byou\b', r'\byour\b', r'\bplease\b', r'\bthanks?\b',
        r'\bi am\b', r"\bi'm\b", r'\bcan\b', r'\bcould\b',
    ]
    german_markers = [
        r'\bich\b', r'\bist\b', r'\bsind\b', r'\bwas\b', r'\bwie\b',
        r'\bwarum\b', r'\bwo\b', r'\bkann\b', r'\bkönnen\b',
        r'\bbitte\b', r'\bdanke\b', r'\bhallo\b', r'\bguten\b',
        r'\bmit\b', r'\bfür\b', r'\bund\b', r'\baber\b',
    ]
    
    en_score = sum(1 for p in english_markers if re.search(p, message_lower))
    de_score = sum(1 for p in german_markers if re.search(p, message_lower))
    
    # Default to German for this German-focused platform
    if en_score > de_score and en_score >= 2:
        return 'en'
    return 'de'


def detect_formality(message: str) -> bool:
    """
    Detect Du vs Sie from user's message.
    
    Returns True for du (informal), False for Sie (formal).
    Default: True (du)
    """
    message_lower = message.lower()
    
    # Sie indicators
    sie_patterns = [r'\bsie\b', r'\bihnen\b', r'\bihr\b', r'\bihre[rsmn]?\b']
    # Du indicators
    du_patterns = [r'\bdu\b', r'\bdich\b', r'\bdir\b', r'\bdein[esr]?\b']
    
    for pattern in sie_patterns:
        if re.search(pattern, message_lower):
            return False
    
    for pattern in du_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return True  # Default to informal


async def ask_llm(message: str, system_prompt: str) -> Optional[str]:
    """Send message to Ollama and get response."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "stream": False,
                    "options": {"temperature": TEMPERATURE}
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "").strip()
    
    except httpx.TimeoutException:
        logger.warning("Mira LLM timeout")
    except Exception as e:
        logger.error(f"Mira LLM error: {e}")
    
    return None


def build_yogi_context(user_id: int, conn) -> dict:
    """
    Build context about the yogi from database.
    """
    context = {
        'has_profile': False,
        'skills': [],
        'recent_matches': [],
        'match_count': 0,
    }
    
    try:
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
                    context['skills'] = skills[:10]
                except:
                    pass
            
            # Get match count
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM profile_posting_matches m
                JOIN profiles p ON m.profile_id = p.profile_id
                WHERE p.user_id = %s
            """, (user_id,))
            context['match_count'] = cur.fetchone()['cnt']
            
            # Get recent matches
            if context['match_count'] > 0:
                cur.execute("""
                    SELECT p.job_title, p.posting_name as company, m.skill_match_score as score
                    FROM profile_posting_matches m
                    JOIN profiles pr ON m.profile_id = pr.profile_id
                    JOIN postings p ON m.posting_id = p.posting_id
                    WHERE pr.user_id = %s
                    ORDER BY m.computed_at DESC
                    LIMIT 3
                """, (user_id,))
                
                context['recent_matches'] = [
                    {'title': r['job_title'], 'company': r['company'], 'score': float(r['score'] or 0) / 100}
                    for r in cur.fetchall()
                ]
    except Exception as e:
        logger.error(f"Error building yogi context: {e}")
    
    return context


async def chat(message: str, user_id: int, conn) -> MiraResponse:
    """
    Main chat function — LLM-first, no pattern matching.
    
    Args:
        message: User's message
        user_id: User ID for context
        conn: Database connection
    
    Returns:
        MiraResponse with reply and metadata
    """
    if not message or not message.strip():
        return MiraResponse(
            reply="I didn't catch that. Could you say that again?",
            language='en',
            fallback=True
        )
    
    message = message.strip()
    
    # Detect language and formality
    language = detect_language(message)
    uses_du = detect_formality(message)
    
    logger.info(f"Mira LLM chat: lang={language}, uses_du={uses_du}, message={message[:50]}")
    
    # Build yogi context
    yogi_context = build_yogi_context(user_id, conn)
    
    # Build system prompt
    system_prompt = build_system_prompt(language, uses_du, yogi_context)
    
    # Ask LLM
    reply = await ask_llm(message, system_prompt)
    
    if reply:
        return MiraResponse(reply=reply, language=language, fallback=False)
    
    # Fallback if LLM fails
    if language == 'en':
        fallback = "I'm having trouble responding right now. Could you try again in a moment?"
    else:
        fallback = "Ich habe gerade Probleme zu antworten. Kannst du es gleich nochmal versuchen?" if uses_du else \
                   "Ich habe gerade Probleme zu antworten. Können Sie es gleich nochmal versuchen?"
    
    return MiraResponse(reply=fallback, language=language, fallback=True)


# Singleton instance
_mira_instance = None

def get_mira():
    """Get or create Mira instance."""
    global _mira_instance
    if _mira_instance is None:
        _mira_instance = True  # Just a flag, the functions above are stateless
    return True
