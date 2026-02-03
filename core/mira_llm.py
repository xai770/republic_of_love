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
                # Queue for research
                cur.execute("""
                    UPDATE user_posting_interactions
                    SET state = 'researching', state_changed_at = NOW(), updated_at = NOW()
                    WHERE interaction_id = %s
                """, (interaction_id,))
                conn.commit()
                
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
