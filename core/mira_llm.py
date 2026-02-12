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
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import httpx

from core.logging_config import get_logger

logger = get_logger(__name__)

# Model config
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/chat'
MODEL = "gemma3:4b"  # Swapped from qwen2.5:7b — better German, fewer hallucinations, lighter (3.3GB vs 4.7GB)
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
        prompt = f"""You are Mira, a companion at talent.yoga. Not a chatbot — a companion.

Think of yourself as sitting next to the yogi at a coffee shop, helping them navigate their job search in Germany. You're steady, knowledgeable, and warm. You care about their journey.

## Your Voice

- Brief (2-4 sentences), chat style
- Helpful but not pushy
- Honest when you don't know: "I'm not sure. Let me check."
- Follow language switches

## What You KNOW

{FAQ_KNOWLEDGE_EN}

## What You CANNOT Do

- Legal advice → "That's a legal question — I'd suggest the employment agency or a lawyer."
- Predict outcomes → "I can't predict, but here's what I see..."
- Promise anything → "Based on the data..."
- Make up answers → "I don't know" is always valid
- NEVER recommend matches below 30% — if no good matches exist, say so honestly
- Don't overwhelm new users with match details — just mention the count

## Examples of How You Sound

**Greeting:**
User: Hi!
Mira: Hey! I'm Mira. I help people find jobs in Germany. Want a quick tour, or ready to dive in?

**When you don't know:**
User: What's the best salary to ask for?
Mira: Good question! I don't have salary data for your specific field. The Arbeitsagentur has regional salary info — want me to explain how matching works instead?

**Clarification (don't guess):**
User: I need something in care.
Mira: Do you mean healthcare/nursing (Pflege)? Or software maintenance? Just want to search the right thing.

**Boundary (legal/predictions):**
User: Can my employer fire me during probation?
Mira: That's a legal question — I'm not the right one for that. The Arbeitsagentur or an employment lawyer would know. Can I help with something else?
"""
    else:
        formal = "Sie" if not uses_du else "du"
        poss = "Ihre" if not uses_du else "deine"
        poss_cap = "Ihre" if not uses_du else "Deine"
        verb_haben = "haben Sie" if not uses_du else "hast du"
        
        prompt = f"""Du bist Mira, eine Begleiterin bei talent.yoga. Kein Chatbot — eine Begleiterin.

Stell dir vor, du sitzt neben dem Yogi im Café und hilfst bei der Jobsuche in Deutschland. Du bist ruhig, kompetent und warmherzig. Dir liegt die Reise am Herzen.

## Deine Stimme

- Kurz (2-4 Sätze), Chat-Stil
- Hilfsbereit, aber nicht aufdringlich
- Ehrlich wenn du nicht weißt: "Das weiß ich nicht sicher. Ich frage nach."
- Du sprichst den Nutzer mit "{formal}" an
- Bei Sprachwechsel: folge dem Nutzer

## Was du WEISST

{FAQ_KNOWLEDGE_DE}

## Was du NICHT kannst

- Rechtsberatung → "Das ist eine rechtliche Frage — da bin ich nicht die Richtige. Die Arbeitsagentur oder ein Anwalt wäre besser."
- Vorhersagen → "Ob {formal} den Job bekomm{('en' if not uses_du else 'st')}, kann ich nicht sagen, aber..."
- Versprechen → "Basierend auf den Daten..."
- Antworten erfinden → "Das weiß ich nicht" ist immer gültig
- NIEMALS Matches unter 30% empfehlen — wenn keine guten Matches da sind, sag es ehrlich
- Neue Nutzer nicht mit Match-Details überschütten — nur die Anzahl nennen

## So klingst du (Beispiele)

**Begrüßung:**
Yogi: Hallo!
Mira: Hallo! Ich bin Mira, {poss} Begleiterin hier. Möchtest du erst schauen, wie das funktioniert? Oder direkt loslegen?

**Wenn du nicht weißt:**
Yogi: Was ist ein gutes Gehalt für meinen Job?
Mira: Gute Frage! Gehaltsdaten für {poss} Bereich habe ich nicht. Die Arbeitsagentur hat regionale Infos. Soll ich dir erklären, wie das Matching funktioniert?

**Nachfragen (nicht raten):**
Yogi: Ich suche was im Bereich Pflege.
Mira: Meinst du Pflege im Gesundheitsbereich? Oder Software-Wartung (Pflege)? Sag kurz Bescheid, dann suche ich richtig.

**Grenze (Recht/Vorhersagen):**
Yogi: Kann mein Chef mich in der Probezeit kündigen?
Mira: Das ist eine rechtliche Frage — da bin ich nicht die Richtige für. Die Arbeitsagentur oder ein Fachanwalt wäre besser. Kann ich dir bei etwas anderem helfen?
"""

    # Add yogi context if available
    if yogi_context:
        context_str = format_yogi_context(yogi_context, uses_du, language)
        if context_str:
            if language == 'en':
                prompt += f"\n## Current User Situation\n\n{context_str}\n"
            else:
                prompt += f"\n## Aktuelle Situation des Nutzers\n\n{context_str}\n"
        
        # Inject extra context (e.g., newsletter for "what's new" queries)
        if yogi_context.get('_extra_prompt'):
            prompt += yogi_context['_extra_prompt']
    
    return prompt


def format_yogi_context(ctx: dict, uses_du: bool, language: str) -> str:
    """
    Format yogi context as a structured card for the system prompt.
    
    This is what Mira "sees" about the yogi. ~150-300 tokens.
    Language-aware: German labels for DE, English for EN.
    """
    lines = []
    
    # ── Name & identity ──
    name = ctx.get('full_name') or ctx.get('display_name') or None
    if name:
        identity = f"Name: {name}"
        if ctx.get('member_since'):
            identity += f" | Member since: {ctx['member_since']}" if language == 'en' else f" | Mitglied seit: {ctx['member_since']}"
        if ctx.get('tier') and ctx['tier'] != 'free':
            identity += f" | Tier: {ctx['tier'].title()}"
        if ctx.get('last_seen'):
            seen_label = 'Last seen' if language == 'en' else 'Zuletzt gesehen'
            identity += f" | {seen_label}: {ctx['last_seen']}"
        lines.append(identity)
    
    # ── Current role ──
    if ctx.get('current_title'):
        title_line = ctx['current_title']
        if ctx.get('years_of_experience'):
            yrs = ctx['years_of_experience']
            title_line += f" | {yrs} {'years' if language == 'en' else 'Jahre'} {'experience' if language == 'en' else 'Erfahrung'}"
        if ctx.get('experience_level'):
            title_line += f" | Level: {ctx['experience_level'].title()}"
        lines.append(title_line)
    
    # ── What they're looking for ──
    looking = []
    if ctx.get('desired_roles'):
        roles_label = 'Looking for' if language == 'en' else 'Sucht'
        looking.append(f"{roles_label}: {', '.join(ctx['desired_roles'])}")
    if ctx.get('desired_locations'):
        loc_label = 'Locations' if language == 'en' else 'Orte'
        looking.append(f"{loc_label}: {', '.join(ctx['desired_locations'])}")
    elif ctx.get('location'):
        loc_label = 'Location' if language == 'en' else 'Ort'
        looking.append(f"{loc_label}: {ctx['location']}")
    if looking:
        lines.append(' | '.join(looking))
    
    # ── Salary ──
    if ctx.get('salary_min') or ctx.get('salary_max'):
        sal_label = 'Salary' if language == 'en' else 'Gehalt'
        sal_min = f"€{ctx['salary_min']:,.0f}" if ctx.get('salary_min') else '?'
        sal_max = f"€{ctx['salary_max']:,.0f}" if ctx.get('salary_max') else '?'
        lines.append(f"{sal_label}: {sal_min}–{sal_max}")
    
    # ── Skills ──
    if ctx.get('skills'):
        skills_str = ', '.join(ctx['skills'])
        if language == 'en':
            lines.append(f"Skills (from profile — ONLY use these, never invent): [{skills_str}]")
        else:
            lines.append(f"Skills (aus dem Profil — NUR diese verwenden, nie erfinden): [{skills_str}]")
    
    # ── Profile summary ──
    if ctx.get('profile_summary'):
        summary_label = 'Summary' if language == 'en' else 'Zusammenfassung'
        lines.append(f"{summary_label}: {ctx['profile_summary']}")
    
    # ── No profile yet ──
    if not ctx.get('has_profile'):
        if language == 'en':
            lines.append("(No profile uploaded yet — encourage them to create one)")
        else:
            lines.append("(Noch kein Profil hochgeladen — ermutige zum Erstellen)")
    
    # ── Matches ──
    if ctx.get('match_count', 0) > 0:
        match_label = 'Matches' if language == 'en' else 'Matches'
        lines.append(f"{match_label}: {ctx['match_count']}")
        for m in ctx.get('recent_matches', [])[:3]:
            where = f" ({m['city']})" if m.get('city') else ''
            lines.append(f"  • {m['title']}{where} — {m['source']} ({m['score']:.0%})")
    elif ctx.get('has_profile'):
        if language == 'en':
            lines.append("Matches: 0 (profile exists but no matches yet)")
        else:
            lines.append("Matches: 0 (Profil vorhanden, aber noch keine Matches)")
    
    # ── Current time ──
    if ctx.get('now'):
        lines.insert(0, f"Current time: {ctx['now']}")
    
    return '\n'.join(lines) if lines else ''


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


async def ask_llm(message: str, system_prompt: str, history: list = None) -> Optional[str]:
    """Send message to Ollama and get response.
    
    Args:
        message: Current user message
        system_prompt: System prompt for Mira
        history: Optional list of prior messages [{"role": "user"|"assistant", "content": str}]
    """
    try:
        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if history:
            messages.extend(history)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": messages,
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
    Build rich context about the yogi from database.
    
    This is Mira's "eyes" — everything she knows about who she's talking to.
    Loads: identity, profile summary, skills, matches, recent activity, newsletter.
    Budget: ~150-400 tokens. gemma3:4b has 8K context, we can afford this.
    """
    context = {
        # Identity
        'display_name': None,
        'full_name': None,
        'tier': None,
        'member_since': None,
        'last_seen': None,
        # Profile
        'has_profile': False,
        'current_title': None,
        'desired_roles': [],
        'desired_locations': [],
        'experience_level': None,
        'years_of_experience': None,
        'salary_min': None,
        'salary_max': None,
        'location': None,
        'profile_summary': None,
        'skills': [],
        # Matches
        'recent_matches': [],
        'match_count': 0,
        # Meta
        'now': datetime.now(timezone.utc).strftime('%A, %d %B %Y, %H:%M UTC'),
        'newsletter_snippet': None,
    }
    
    try:
        with conn.cursor() as cur:
            # ── Identity from users table ──
            cur.execute("""
                SELECT display_name, tier, subscription_tier,
                       created_at, last_login_at
                FROM users
                WHERE user_id = %s
            """, (user_id,))
            user_row = cur.fetchone()
            if user_row:
                context['display_name'] = user_row['display_name']
                context['tier'] = user_row['subscription_tier'] or user_row['tier'] or 'free'
                if user_row['created_at']:
                    context['member_since'] = user_row['created_at'].strftime('%B %Y')
                if user_row['last_login_at']:
                    delta = datetime.now(timezone.utc) - user_row['last_login_at'].replace(tzinfo=timezone.utc)
                    if delta.total_seconds() < 300:
                        context['last_seen'] = 'online now'
                    elif delta.total_seconds() < 3600:
                        context['last_seen'] = f'{int(delta.total_seconds() // 60)} min ago'
                    elif delta.total_seconds() < 86400:
                        context['last_seen'] = f'{int(delta.total_seconds() // 3600)} hours ago'
                    else:
                        context['last_seen'] = f'{int(delta.days)} days ago'

            # ── Profile data ──
            cur.execute("""
                SELECT full_name, current_title, desired_roles, desired_locations,
                       experience_level, years_of_experience,
                       expected_salary_min, expected_salary_max,
                       location, profile_summary, skill_keywords
                FROM profiles
                WHERE user_id = %s
                LIMIT 1
            """, (user_id,))
            profile = cur.fetchone()
            
            if profile:
                context['has_profile'] = True
                context['full_name'] = profile['full_name']
                context['current_title'] = profile['current_title']
                context['experience_level'] = profile['experience_level']
                context['years_of_experience'] = profile['years_of_experience']
                context['salary_min'] = profile['expected_salary_min']
                context['salary_max'] = profile['expected_salary_max']
                context['location'] = profile['location']
                
                # Profile summary — truncate to save tokens
                if profile['profile_summary']:
                    summary = profile['profile_summary'].strip()
                    context['profile_summary'] = summary[:300] + ('...' if len(summary) > 300 else '')
                
                # Desired roles/locations (text[] arrays)
                if profile['desired_roles']:
                    context['desired_roles'] = list(profile['desired_roles'])[:5]
                if profile['desired_locations']:
                    context['desired_locations'] = list(profile['desired_locations'])[:5]
                
                # Skills
                try:
                    skills = profile['skill_keywords'] or []
                    if isinstance(skills, str):
                        skills = json.loads(skills)
                    context['skills'] = list(skills)[:12]
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # ── Match count + top matches ──
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM profile_posting_matches m
                JOIN profiles p ON m.profile_id = p.profile_id
                WHERE p.user_id = %s
            """, (user_id,))
            context['match_count'] = cur.fetchone()['cnt']
            
            if context['match_count'] > 0:
                cur.execute("""
                    SELECT po.job_title, po.source, po.location_city, m.skill_match_score as score
                    FROM profile_posting_matches m
                    JOIN profiles pr ON m.profile_id = pr.profile_id
                    JOIN postings po ON m.posting_id = po.posting_id
                    WHERE pr.user_id = %s
                      AND m.skill_match_score > 0.10
                    ORDER BY m.skill_match_score DESC
                    LIMIT 3
                """, (user_id,))
                context['recent_matches'] = [
                    {
                        'title': r['job_title'],
                        'source': (r['source'] or '').replace('_', ' ').title(),
                        'city': r['location_city'] or '',
                        'score': float(r['score'] or 0),
                    }
                    for r in cur.fetchall()
                ]

            # ── Latest newsletter from Doug ──
            try:
                from actors.doug__newsletter_C import get_latest_newsletter_content
                newsletter = get_latest_newsletter_content(language='de')
                if newsletter and newsletter.get('content'):
                    content = newsletter['content']
                    context['newsletter_snippet'] = content[:300] + ('...' if len(content) > 300 else '')
                    context['newsletter_date'] = str(newsletter.get('newsletter_date', ''))
            except Exception as e:
                logger.debug(f"Newsletter not available: {e}")
    except Exception as e:
        logger.error(f"Error building yogi context: {e}")
    
    return context


def detect_whats_new(message: str) -> bool:
    """Detect if user is asking 'what's new' / 'was gibts neues'."""
    patterns = [
        r"what'?s new", r"anything new", r"what happened",
        r"was gibt'?s? neues", r"was ist neu", r"neuigkeiten",
        r"was hab ich verpasst", r"was ist passiert",
        r"what did i miss", r"any updates", r"any news",
    ]
    msg = message.lower().strip()
    return any(re.search(p, msg) for p in patterns)


async def chat(message: str, user_id: int, conn, history: list = None) -> MiraResponse:
    """
    Main chat function — LLM-first, no pattern matching.
    
    Args:
        message: User's message
        user_id: User ID for context
        conn: Database connection
        history: Optional conversation history [{"role": "user"|"assistant", "content": str}]
    
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
    
    # Check for Doug research request
    doug_request = detect_doug_request(message)
    if doug_request:
        doug_response = await handle_doug_request(doug_request, user_id, conn, language, uses_du)
        if doug_response:
            return doug_response
    
    # Build yogi context
    yogi_context = build_yogi_context(user_id, conn)
    
    # If asking "what's new", inject newsletter into conversation context
    if detect_whats_new(message) and yogi_context.get('newsletter_snippet'):
        if language == 'en':
            newsletter_context = f"\n\n## Doug's Latest Newsletter ({yogi_context.get('newsletter_date', 'today')})\n{yogi_context['newsletter_snippet']}\n\nSummarize Doug's newsletter highlights briefly. Reply in English."
        else:
            newsletter_context = f"\n\n## Dougs neuester Newsletter ({yogi_context.get('newsletter_date', 'heute')})\n{yogi_context['newsletter_snippet']}\n\nFasse Dougs Newsletter-Highlights kurz zusammen. Antworte auf Deutsch."
        yogi_context['_extra_prompt'] = newsletter_context
    
    # Build system prompt
    system_prompt = build_system_prompt(language, uses_du, yogi_context)
    
    # Ask LLM with history
    reply = await ask_llm(message, system_prompt, history)
    
    if reply:
        return MiraResponse(reply=reply, language=language, fallback=False)
    
    # Fallback if LLM fails
    if language == 'en':
        fallback = "I'm having trouble responding right now. Could you try again in a moment?"
    else:
        fallback = "Ich habe gerade Probleme zu antworten. Kannst du es gleich nochmal versuchen?" if uses_du else \
                   "Ich habe gerade Probleme zu antworten. Können Sie es gleich nochmal versuchen?"
    
    return MiraResponse(reply=fallback, language=language, fallback=True)


def detect_doug_request(message: str) -> Optional[dict]:
    """
    Detect if user is asking for company research.
    
    Patterns:
    - "Was weißt du über [Company]?"
    - "Tell me about [Company]"
    - "Research [Company] for me"
    - "Can Doug look into [Company]?"
    
    Returns dict with 'company' key if detected, None otherwise.
    """
    message_lower = message.lower()
    
    # German patterns
    de_patterns = [
        r'was weißt du über\s+(.+?)(?:\?|$)',
        r'was wisst ihr über\s+(.+?)(?:\?|$)',
        r'recherchier(?:e|st)?\s+(?:mal\s+)?(.+?)(?:\s+für mich)?(?:\?|$)',
        r'kannst du (?:mir\s+)?(?:was|etwas) über\s+(.+?)\s+(?:sagen|erzählen|herausfinden)',
        r'(?:mehr\s+)?(?:infos?|informationen)\s+(?:über|zu)\s+(.+?)(?:\?|$)',
        r'doug.*?(?:über|zu)\s+(.+?)(?:\?|$)',
    ]
    
    # English patterns  
    en_patterns = [
        r'what do you know about\s+(.+)',
        r'tell me (?:more\s+)?about\s+(.+)',
        r'research\s+(.+)',
        r'can (?:you|doug) look into\s+(.+)',
        r'(?:more\s+)?info(?:rmation)?\s+(?:about|on)\s+(.+)',
        r'doug.*?about\s+(.+)',
    ]
    
    all_patterns = de_patterns + en_patterns
    
    for pattern in all_patterns:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            # Clean up common suffixes (order matters - longer first)
            company = re.sub(r'\s+for me please$', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+for me$', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+für mich$', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+please$', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+bitte$', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+mal$', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+doch$', '', company, flags=re.IGNORECASE)
            # Remove trailing punctuation
            company = company.rstrip('?.!').strip()
            if company and len(company) > 1:
                return {'company': company, 'raw_match': match.group(0)}
    
    return None


async def handle_doug_request(
    request: dict, 
    user_id: int, 
    conn, 
    language: str, 
    uses_du: bool
) -> Optional[MiraResponse]:
    """
    Handle a Doug research request.
    
    1. Find if user has any matches/interactions with this company
    2. If yes → queue Doug research on that posting
    3. If no → offer to search generally
    """
    company = request['company']
    
    with conn.cursor() as cur:
        # Check if user has any interactions with postings from this company
        cur.execute("""
            SELECT upi.interaction_id, upi.posting_id, upi.state,
                   p.job_title, p.extracted_summary
            FROM user_posting_interactions upi
            JOIN postings p ON upi.posting_id = p.posting_id
            WHERE upi.user_id = %s
              AND (
                  LOWER(p.job_title) LIKE %s
                  OR LOWER(p.extracted_summary) LIKE %s
              )
            ORDER BY upi.updated_at DESC
            LIMIT 1
        """, (user_id, f'%{company.lower()}%', f'%{company.lower()}%'))
        
        interaction = cur.fetchone()
        
        if interaction:
            # User has interacted with a posting from this company
            interaction_id = interaction['interaction_id']
            job_title = interaction['job_title']
            current_state = interaction['state']
            
            # Check if already researched
            if current_state == 'informed':
                # Already researched — check for existing report
                cur.execute("""
                    SELECT body FROM yogi_messages
                    WHERE user_id = %s AND posting_id = %s 
                      AND sender_type = 'doug' AND message_type = 'research_report'
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id, interaction['posting_id']))
                report = cur.fetchone()
                
                if report:
                    if language == 'en':
                        reply = f"Doug already researched {company}! Check your messages for his report on '{job_title}'."
                    else:
                        if uses_du:
                            reply = f"Doug hat {company} schon recherchiert! Schau in deine Nachrichten — dort findest du seinen Bericht zu '{job_title}'."
                        else:
                            reply = f"Doug hat {company} bereits recherchiert! Schauen Sie in Ihre Nachrichten — dort finden Sie seinen Bericht zu '{job_title}'."
                    return MiraResponse(reply=reply, language=language)
            
            elif current_state == 'researching':
                # Already in queue
                if language == 'en':
                    reply = f"Doug is already working on researching {company}. I'll let you know when he's done!"
                else:
                    if uses_du:
                        reply = f"Doug recherchiert gerade schon zu {company}. Ich sag dir Bescheid, wenn er fertig ist!"
                    else:
                        reply = f"Doug recherchiert gerade bereits zu {company}. Ich sage Ihnen Bescheid, wenn er fertig ist!"
                return MiraResponse(reply=reply, language=language)
            
            else:
                # Queue for research AND fire Doug immediately
                cur.execute("""
                    UPDATE user_posting_interactions
                    SET state = 'researching', state_changed_at = NOW(), updated_at = NOW()
                    WHERE interaction_id = %s
                """, (interaction_id,))
                conn.commit()
                
                # Fire Doug async — don't block Mira's response
                try:
                    from actors.doug__research_C import research_fire_and_forget
                    research_fire_and_forget(interaction_id)
                except Exception as e:
                    logger.warning(f"Failed to fire Doug async: {e}")
                
                if language == 'en':
                    reply = f"I've asked Doug to research {company} for the '{job_title}' position. He'll dig into company culture, reviews, and anything useful. This takes a few minutes — I'll notify you when it's ready!"
                else:
                    if uses_du:
                        reply = f"Ich hab Doug gebeten, {company} zu recherchieren — speziell für die Stelle '{job_title}'. Er schaut sich Firmenkultur, Bewertungen und alles Nützliche an. Das dauert ein paar Minuten — ich sag dir Bescheid!"
                    else:
                        reply = f"Ich habe Doug gebeten, {company} zu recherchieren — speziell für die Stelle '{job_title}'. Er schaut sich Firmenkultur, Bewertungen und alles Nützliche an. Das dauert ein paar Minuten — ich sage Ihnen Bescheid!"
                return MiraResponse(reply=reply, language=language)
        
        else:
            # No interaction with this company yet
            # Check if we have any postings from this company at all
            cur.execute("""
                SELECT posting_id, job_title FROM postings
                WHERE LOWER(job_title) LIKE %s OR LOWER(extracted_summary) LIKE %s
                LIMIT 3
            """, (f'%{company.lower()}%', f'%{company.lower()}%'))
            postings = cur.fetchall()
            
            if postings:
                # We have postings but user hasn't interacted
                if language == 'en':
                    reply = f"I found some jobs that mention {company}, but you haven't viewed them yet. Want me to show you those matches first? Then Doug can research the ones you're interested in."
                else:
                    if uses_du:
                        reply = f"Ich habe Stellen gefunden, die {company} erwähnen, aber du hast sie noch nicht angeschaut. Soll ich dir die Matches zuerst zeigen? Dann kann Doug die recherchieren, die dich interessieren."
                    else:
                        reply = f"Ich habe Stellen gefunden, die {company} erwähnen, aber Sie haben sie noch nicht angesehen. Soll ich Ihnen die Matches zuerst zeigen? Dann kann Doug die recherchieren, die Sie interessieren."
            else:
                # Company not in our database
                if language == 'en':
                    reply = f"I don't have any job postings from {company} right now. We focus on jobs in Germany from Arbeitsagentur and Deutsche Bank. Is there something else I can help with?"
                else:
                    if uses_du:
                        reply = f"Ich habe gerade keine Stellenangebote von {company}. Wir konzentrieren uns auf Jobs in Deutschland von der Arbeitsagentur und Deutsche Bank. Kann ich dir bei etwas anderem helfen?"
                    else:
                        reply = f"Ich habe derzeit keine Stellenangebote von {company}. Wir konzentrieren uns auf Jobs in Deutschland von der Arbeitsagentur und Deutsche Bank. Kann ich Ihnen bei etwas anderem helfen?"
            
            return MiraResponse(reply=reply, language=language)
    
    return None  # Fall through to normal LLM response


# Singleton instance
_mira_instance = None

def get_mira():
    """Get or create Mira instance."""
    global _mira_instance
    if _mira_instance is None:
        _mira_instance = True  # Just a flag, the functions above are stateless
    return True
