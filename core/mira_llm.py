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
    actions: Optional[dict] = None  # Structured actions for frontend (e.g. set_filters)


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
- **CRITICAL: NEVER invent job postings, companies, hospitals, or match scores.** You may ONLY mention jobs that appear in "Current User Situation" below. If no matches exist for a search, say "I've set the filters for you — let's see what comes up" instead of making up results.
- NEVER recommend matches below 30% — if no good matches exist, say so honestly
- Don't overwhelm new users with match details — just mention the count
- When the user asks to search for jobs (e.g. "Pflege in Frankfurt"), say you'll set the filters — the system handles the rest. Do NOT list imaginary search results.
- **LISTEN to what the user actually says.** If they tell you something about themselves (e.g. "I'm the developer", "I'm testing", "I work at X"), acknowledge it and respond naturally. Do NOT ignore their message and push onboarding steps.
- If the user already has a profile (shown below), do NOT suggest uploading a CV.

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
- **KRITISCH: Erfinde NIEMALS Stellenangebote, Firmen, Krankenhäuser oder Match-Scores.** Du darfst NUR Jobs nennen, die unter "Aktuelle Situation" aufgelistet sind. Wenn keine Matches für eine Suche existieren, sag "Ich habe die Filter für dich gesetzt — schauen wir was kommt" statt Ergebnisse zu erfinden.
- NIEMALS Matches unter 30% empfehlen — wenn keine guten Matches da sind, sag es ehrlich
- Neue Nutzer nicht mit Match-Details überschütten — nur die Anzahl nennen
- Wenn der Nutzer nach Jobs sucht (z.B. "Pflege in Frankfurt"), sag dass du die Filter setzt — das System erledigt den Rest. Erfinde KEINE Suchergebnisse.
- **HÖRE zu, was der Nutzer wirklich sagt.** Wenn er dir etwas über sich erzählt (z.B. "Ich bin der Entwickler", "Ich teste gerade", "Ich arbeite bei X"), geh darauf ein und antworte natürlich. Ignoriere NICHT seine Nachricht um Onboarding-Schritte zu pushen.
- Wenn der Nutzer bereits ein Profil hat (siehe unten), schlage NICHT vor, einen Lebenslauf hochzuladen.

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
    name = ctx.get('yogi_name') or ctx.get('full_name') or ctx.get('display_name') or None
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
    
    # ── Profile status ──
    if not ctx.get('has_profile'):
        if language == 'en':
            lines.append("(No profile uploaded yet — if relevant, mention they can create one under Profile)")
        else:
            lines.append("(Noch kein Profil hochgeladen — wenn passend, erwähne dass sie eins unter Profil erstellen können)")
    else:
        # User already has a profile — NEVER suggest uploading a CV again
        if language == 'en':
            lines.append("(Profile exists — do NOT suggest uploading a CV. If skills list is empty, you may suggest adding skills under Profile.)")
        else:
            lines.append("(Profil vorhanden — schlage NICHT vor, einen Lebenslauf hochzuladen. Wenn die Skill-Liste leer ist, kannst du vorschlagen, Skills unter Profil hinzuzufügen.)")
    
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
    
    # ── Timeline (recent activity) ──
    timeline = ctx.get('timeline', [])
    if timeline:
        tl_label = 'Recent Activity' if language == 'en' else 'Letzte Aktivität'
        lines.append(f"\n{tl_label}:")
        for entry in timeline[-10:]:  # cap at 10 most recent
            t = entry.get('time')
            time_str = t.strftime('%H:%M') if t else '??:??'
            lines.append(f"  [{time_str}] {entry['text']}")
    
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
        'yogi_name': None,
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
                SELECT display_name, yogi_name, tier, subscription_tier,
                       created_at, last_login_at
                FROM users
                WHERE user_id = %s
            """, (user_id,))
            user_row = cur.fetchone()
            if user_row:
                context['yogi_name'] = user_row['yogi_name']
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

            # ── Interleaved timeline (messages + events) ──
            context['timeline'] = _build_timeline(user_id, conn)

    except Exception as e:
        logger.error(f"Error building yogi context: {e}")
    
    return context


def _build_timeline(user_id: int, conn) -> list:
    """
    Build an interleaved timeline of messages + behavioral events.
    
    Merges yogi_messages (last 10) and yogi_events (last 5) chronologically.
    Returns list of dicts with {time, type, text} — ready for format_yogi_context.
    Budget: ~200-400 tokens (10-15 entries, ~20-30 tokens each).
    """
    timeline = []
    
    try:
        with conn.cursor() as cur:
            # Recent messages (both directions)
            cur.execute("""
                SELECT sender_type, body, created_at
                FROM yogi_messages
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
            for row in cur.fetchall():
                if not row['body']:
                    continue
                sender = row['sender_type']
                body = (row['body'] or '')[:120]
                # Strip markdown for brevity
                body = body.replace('**', '').replace('##', '').strip()
                if body:
                    timeline.append({
                        'time': row['created_at'],
                        'type': 'msg',
                        'text': f"{'Yogi' if sender == 'yogi' else sender.title()}: {body}"
                    })
            
            # Recent behavioral events
            cur.execute("""
                SELECT event_type, event_data, created_at
                FROM yogi_events
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (user_id,))
            for row in cur.fetchall():
                evt = row['event_type']
                data = row['event_data'] or {}
                text = _format_event(evt, data)
                if text:
                    timeline.append({
                        'time': row['created_at'],
                        'type': 'event',
                        'text': text
                    })
    except Exception as e:
        logger.debug(f"Timeline build failed: {e}")
    
    # Sort chronologically (oldest first)
    timeline.sort(key=lambda x: x.get('time') or datetime.min.replace(tzinfo=timezone.utc))
    
    return timeline


def _format_event(event_type: str, data: dict) -> str:
    """Format a single behavioral event as a concise timeline entry."""
    if event_type == 'page_view':
        page = data.get('page', '?')
        return f"Visited {page}"
    elif event_type == 'search_filter':
        parts = []
        if data.get('domains'):
            parts.append(f"domains={data['domains']}")
        if data.get('city'):
            parts.append(f"city={data['city']}")
        if data.get('ql'):
            parts.append(f"QL={data['ql']}")
        if data.get('results') is not None:
            parts.append(f"{data['results']} results")
        return f"Set search filters: {', '.join(parts)}" if parts else None
    elif event_type == 'posting_view':
        title = data.get('title', 'a posting')
        return f"Viewed posting: {title[:80]}"
    elif event_type == 'match_action':
        action = data.get('action', '?')
        return f"Match action: {action}"
    elif event_type == 'login':
        return "Logged in"
    return None


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


# ─────────────────────────────────────────────────────────
# Tier 2: On-demand context tools
# ─────────────────────────────────────────────────────────

def detect_tier2_intent(message: str) -> Optional[str]:
    """
    Detect Tier 2 on-demand intent from user message.
    
    Returns intent key or None. Checked AFTER doug_request (which short-circuits).
    Order matters: first match wins.
    """
    msg = message.lower().strip()
    
    # ── Profile detail ──
    profile_patterns = [
        r'zeig\w*\s+(?:mir\s+)?mein(?:en?)?\s+(?:profil|lebenslauf|cv)',
        r'mein\s+profil\s+(?:zeigen|anzeigen|ansehen|anschauen)',
        r'was\s+steht\s+(?:in|auf)\s+meinem\s+profil',
        r'show\s+(?:me\s+)?my\s+profile',
        r'what(?:\'s| is)\s+(?:in|on)\s+my\s+profile',
        r'my\s+(?:profile|cv|resume)',
    ]
    if any(re.search(p, msg) for p in profile_patterns):
        return 'profile_detail'
    
    # ── Match detail ──
    match_patterns = [
        r'(?:erzähl|sag|zeig)\w*\s+(?:mir\s+)?(?:(?:was|mehr)\s+)?über\s+mein\w*\s+match',
        r'mein\w*\s+(?:besten?|top)\s+match',
        r'(?:was|welche)\s+(?:sind|waren?)\s+mein\w*\s+match',
        r'warum\s+(?:habe? ich|passe? ich)',
        r'match\s+details?',
        r'tell\s+me\s+(?:about|more about)\s+my\s+match',
        r'my\s+(?:best|top)\s+match',
        r'why\s+(?:did|do)\s+i\s+match',
        r'match\s+(?:reasons?|explanation)',
    ]
    if any(re.search(p, msg) for p in match_patterns):
        return 'match_detail'
    
    # ── Doug messages ──
    doug_msg_patterns = [
        r'was\s+hat\s+doug\s+(?:geschrieben|gesagt|berichtet)',
        r'doug(?:s|\'s)?\s+(?:bericht|nachricht|report)',
        r'(?:gibt\s+es|habe?\s+ich)\s+(?:was|etwas)\s+von\s+doug',
        r'what\s+did\s+doug\s+(?:write|say|report|find)',
        r'doug(?:\'s)?\s+(?:report|message|research|findings?)',
        r'anything\s+from\s+doug',
    ]
    if any(re.search(p, msg) for p in doug_msg_patterns):
        return 'doug_messages'
    
    # ── My messages / inbox ──
    inbox_patterns = [
        r'(?:hab(?:e)?\s+ich|gibt\s+es)\s+(?:neue?\s+)?nachricht',
        r'mein\w*\s+(?:nachrichten|posteingang|inbox)',
        r'(?:zeig|check)\w*\s+(?:mir\s+)?(?:meine?\s+)?nachrichten',
        r'(?:any|new|my)\s+messages?',
        r'(?:check|show)\s+(?:my\s+)?(?:inbox|messages)',
        r'(?:anything|something)\s+for\s+me',
    ]
    if any(re.search(p, msg) for p in inbox_patterns):
        return 'my_messages'
    
    return None


def load_tier2_context(intent: str, user_id: int, conn, language: str) -> Optional[str]:
    """
    Load on-demand context for a Tier 2 intent.
    
    Returns a prompt fragment to inject into _extra_prompt, or None.
    Each loader stays under ~500 tokens to respect gemma3:4b's 8K window.
    """
    try:
        if intent == 'profile_detail':
            return _load_profile_detail(user_id, conn, language)
        elif intent == 'match_detail':
            return _load_match_detail(user_id, conn, language)
        elif intent == 'doug_messages':
            return _load_doug_messages(user_id, conn, language)
        elif intent == 'my_messages':
            return _load_my_messages(user_id, conn, language)
    except Exception as e:
        logger.error(f"Tier 2 load failed for {intent}: {e}")
    return None


def _load_profile_detail(user_id: int, conn, language: str) -> Optional[str]:
    """Load full profile text for the yogi."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT profile_raw_text, full_name, current_title, location,
                   experience_level, years_of_experience
            FROM profiles WHERE user_id = %s LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
    
    if not row:
        if language == 'en':
            return "\n\n## Profile Detail\n\nThis yogi has no profile yet. Encourage them to upload a CV or fill in their profile.\n"
        else:
            return "\n\n## Profil-Detail\n\nDieser Yogi hat noch kein Profil. Ermutige zum Erstellen oder CV-Upload.\n"
    
    raw = (row['profile_raw_text'] or '').strip()
    if not raw:
        # Fall back to structured fields
        parts = [f for f in [row['full_name'], row['current_title'], row['location'],
                             f"{row['years_of_experience']}y exp" if row['years_of_experience'] else None,
                             row['experience_level']] if f]
        raw = ' | '.join(parts) if parts else 'Profile exists but no raw text.'
    
    # Truncate to ~500 tokens (~2000 chars)
    raw = raw[:2000] + ('...' if len(raw) > 2000 else '')
    
    if language == 'en':
        return f"\n\n## Yogi's Full Profile\n\nThe yogi asked to see their profile. Summarize the key points in a friendly way.\n\n```\n{raw}\n```\n"
    else:
        return f"\n\n## Vollständiges Profil des Yogis\n\nDer Yogi möchte sein Profil sehen. Fasse die wichtigsten Punkte freundlich zusammen.\n\n```\n{raw}\n```\n"


def _load_match_detail(user_id: int, conn, language: str) -> Optional[str]:
    """Load top matches with go/nogo reasons."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT po.job_title, po.source, po.location_city,
                   m.skill_match_score, m.recommendation,
                   m.go_reasons, m.nogo_reasons
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            JOIN postings po ON m.posting_id = po.posting_id
            WHERE pr.user_id = %s
              AND m.skill_match_score > 0.10
            ORDER BY m.skill_match_score DESC
            LIMIT 5
        """, (user_id,))
        matches = cur.fetchall()
    
    if not matches:
        if language == 'en':
            return "\n\n## Match Details\n\nNo matches found yet. If the yogi has a profile, matching may still be processing.\n"
        else:
            return "\n\n## Match-Details\n\nNoch keine Matches gefunden. Falls ein Profil besteht, läuft das Matching möglicherweise noch.\n"
    
    lines = []
    for m in matches:
        source = (m['source'] or '').replace('_', ' ').title()
        score = float(m['skill_match_score'] or 0)
        city = m['location_city'] or ''
        rec = m['recommendation'] or 'none'
        
        line = f"• {m['job_title']} ({city}) — {source} — {score:.0%} — rec: {rec}"
        
        # Add top 2 go reasons if any
        go = m.get('go_reasons') or []
        if isinstance(go, list) and go:
            for reason in go[:2]:
                line += f"\n  ✓ {reason[:120]}"
        
        # Add top 2 nogo reasons if any
        nogo = m.get('nogo_reasons') or []
        if isinstance(nogo, list) and nogo:
            for reason in nogo[:2]:
                line += f"\n  ✗ {reason[:120]}"
        
        lines.append(line)
    
    details = '\n'.join(lines)
    
    if language == 'en':
        return f"\n\n## Match Details (Top 5)\n\nThe yogi asked about their matches. Explain the strongest matches and why they fit (or don't). Be honest about weak matches.\n\n{details}\n"
    else:
        return f"\n\n## Match-Details (Top 5)\n\nDer Yogi fragt nach seinen Matches. Erkläre die stärksten Matches und warum sie passen (oder nicht). Sei ehrlich bei schwachen Matches.\n\n{details}\n"


def _load_doug_messages(user_id: int, conn, language: str) -> Optional[str]:
    """Load recent Doug research reports/messages for the yogi."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT body, message_type, created_at
            FROM yogi_messages
            WHERE user_id = %s AND sender_type = 'doug'
            ORDER BY created_at DESC
            LIMIT 3
        """, (user_id,))
        msgs = cur.fetchall()
    
    if not msgs:
        if language == 'en':
            return "\n\n## Doug's Messages\n\nDoug hasn't sent any research reports to this yogi yet. Explain that Doug researches companies when they ask about a specific posting.\n"
        else:
            return "\n\n## Dougs Nachrichten\n\nDoug hat diesem Yogi noch keine Berichte geschickt. Erkläre, dass Doug Unternehmen recherchiert, wenn man nach einer bestimmten Stelle fragt.\n"
    
    lines = []
    for m in msgs:
        date = m['created_at'].strftime('%d.%m.%Y %H:%M') if m['created_at'] else '?'
        body = (m['body'] or '')[:600] + ('...' if len(m['body'] or '') > 600 else '')
        lines.append(f"[{date}] ({m['message_type']})\n{body}")
    
    details = '\n---\n'.join(lines)
    
    if language == 'en':
        return f"\n\n## Doug's Messages\n\nThe yogi asked about Doug's reports. Summarize the key findings.\n\n{details}\n"
    else:
        return f"\n\n## Dougs Nachrichten\n\nDer Yogi fragt nach Dougs Berichten. Fasse die wichtigsten Erkenntnisse zusammen.\n\n{details}\n"


def _load_my_messages(user_id: int, conn, language: str) -> Optional[str]:
    """Load recent non-chat messages (system, staff, y2y, arden, etc.)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT sender_type, message_type, body, created_at
            FROM yogi_messages
            WHERE user_id = %s
              AND sender_type NOT IN ('yogi', 'mira')
              AND message_type != 'chat'
            ORDER BY created_at DESC
            LIMIT 5
        """, (user_id,))
        msgs = cur.fetchall()
    
    if not msgs:
        if language == 'en':
            return "\n\n## Your Messages\n\nNo special messages for this yogi. Let them know their inbox is clear.\n"
        else:
            return "\n\n## Deine Nachrichten\n\nKeine besonderen Nachrichten für diesen Yogi. Sag Bescheid, dass der Posteingang leer ist.\n"
    
    lines = []
    for m in msgs:
        date = m['created_at'].strftime('%d.%m.%Y %H:%M') if m['created_at'] else '?'
        sender = m['sender_type']
        mtype = m['message_type']
        body = (m['body'] or '')[:300] + ('...' if len(m['body'] or '') > 300 else '')
        lines.append(f"[{date}] From {sender} ({mtype}):\n{body}")
    
    details = '\n---\n'.join(lines)
    
    if language == 'en':
        return f"\n\n## Messages for You\n\nThe yogi asked about their messages. Summarize what they've received.\n\n{details}\n"
    else:
        return f"\n\n## Nachrichten für dich\n\nDer Yogi fragt nach seinen Nachrichten. Fasse zusammen, was eingegangen ist.\n\n{details}\n"


# ─────────────────────────────────────────────────────────
# Search intent extraction → filter actions
# ─────────────────────────────────────────────────────────

# Keyword → KLDB domain codes mapping (mirrors KLDB_DOMAINS in search.py)
DOMAIN_KEYWORDS = {
    # German keywords
    'pflege': ['81', '82'], 'gesundheit': ['81', '82'], 'medizin': ['81', '82'],
    'klinik': ['81', '82'], 'krankenhaus': ['81', '82'], 'arzt': ['81', '82'],
    'krankenpflege': ['81', '82'], 'altenpflege': ['81', '82'],
    'it': ['43'], 'software': ['43'], 'entwickler': ['43'], 'programmier': ['43'],
    'technologie': ['43'], 'informatik': ['43'], 'daten': ['43'],
    'finanzen': ['72'], 'bank': ['72'], 'buchhaltung': ['72'], 'controlling': ['72'],
    'handel': ['61', '62'], 'vertrieb': ['61', '62'], 'verkauf': ['61', '62'],
    'bildung': ['83', '84'], 'sozial': ['83', '84'], 'erzieh': ['83', '84'],
    'lehrer': ['83', '84'], 'pädagog': ['83', '84'],
    'bau': ['31', '32', '33', '34', '54'], 'handwerk': ['31', '32', '33', '34', '54'],
    'elektro': ['25', '26'], 'maschinen': ['25', '26'],
    'logistik': ['51', '52'], 'transport': ['51', '52'], 'lager': ['51', '52'],
    'fertigung': ['21', '22', '23', '24', '27', '28'], 'produktion': ['21', '22', '23', '24', '27', '28'],
    'wirtschaft': ['71'], 'management': ['71'], 'beratung': ['71'],
    'verwaltung': ['73'], 'recht': ['73'], 'jura': ['73'],
    'gastro': ['29'], 'küche': ['29'], 'koch': ['29'], 'restaurant': ['29'],
    'tourismus': ['63'], 'hotel': ['63'],
    'kultur': ['91', '92', '93', '94'], 'medien': ['91', '92', '93', '94'],
    'wissenschaft': ['41', '42'], 'forschung': ['41', '42'],
    'sicherheit': ['01', '02', '03', '53'],
    'landwirtschaft': ['11', '12', '13', '14'],
    # English keywords
    'healthcare': ['81', '82'], 'nursing': ['81', '82'], 'care': ['81', '82'],
    'medical': ['81', '82'], 'hospital': ['81', '82'],
    'technology': ['43'], 'developer': ['43'], 'programming': ['43'], 'data': ['43'],
    'finance': ['72'], 'banking': ['72'], 'accounting': ['72'],
    'sales': ['61', '62'], 'retail': ['61', '62'], 'trade': ['61', '62'],
    'education': ['83', '84'], 'social': ['83', '84'], 'teaching': ['83', '84'],
    'construction': ['31', '32', '33', '34', '54'],
    'engineering': ['25', '26'],
    'logistics': ['51', '52'],
    'manufacturing': ['21', '22', '23', '24', '27', '28'],
    'business': ['71'], 'consulting': ['71'],
    'administration': ['73'], 'legal': ['73'], 'law': ['73'],
    'hospitality': ['29'], 'catering': ['29'],
    'tourism': ['63'],
    'science': ['41', '42'], 'research': ['41', '42'],
    'security': ['01', '02', '03', '53'],
    'agriculture': ['11', '12', '13', '14'],
}

# Major German cities → coordinates
CITY_COORDS = {
    'berlin': (52.52, 13.41), 'hamburg': (53.55, 9.99), 'münchen': (48.14, 11.58),
    'munich': (48.14, 11.58), 'köln': (50.94, 6.96), 'cologne': (50.94, 6.96),
    'frankfurt': (50.11, 8.68), 'stuttgart': (48.78, 9.18), 'düsseldorf': (51.23, 6.78),
    'dortmund': (51.51, 7.47), 'essen': (51.46, 7.01), 'leipzig': (51.34, 12.37),
    'bremen': (53.08, 8.80), 'dresden': (51.05, 13.74), 'hannover': (52.37, 9.74),
    'nürnberg': (49.45, 11.08), 'nuremberg': (49.45, 11.08), 'duisburg': (51.43, 6.76),
    'bochum': (51.48, 7.22), 'wuppertal': (51.26, 7.17), 'bielefeld': (52.02, 8.53),
    'bonn': (50.74, 7.10), 'münster': (51.96, 7.63), 'karlsruhe': (49.01, 8.40),
    'mannheim': (49.49, 8.47), 'augsburg': (48.37, 10.90), 'wiesbaden': (50.08, 8.24),
    'mainz': (50.00, 8.27), 'freiburg': (47.99, 7.85), 'basel': (47.56, 7.59),
    'aachen': (50.78, 6.08), 'kiel': (54.32, 10.14), 'rostock': (54.09, 12.10),
    'potsdam': (52.40, 13.07), 'darmstadt': (49.87, 8.65), 'heidelberg': (49.40, 8.69),
    'kassel': (51.31, 9.50), 'regensburg': (49.01, 12.10), 'wolfsburg': (52.42, 10.79),
    'ulm': (48.40, 9.99), 'lübeck': (53.87, 10.69), 'erlangen': (49.60, 11.00),
}

# Qualification level keywords
QL_KEYWORDS = {
    'helfer': [1], 'helper': [1], 'ungelernt': [1], 'unskilled': [1],
    'fachkraft': [2], 'skilled': [2], 'facharbeiter': [2],
    'spezialist': [3], 'specialist': [3],
    'experte': [4], 'expert': [4], 'führungskraft': [4], 'senior': [4], 'manager': [4],
}


# Human-readable domain names for composing search replies
_KLDB_DOMAIN_NAMES = {
    '01': 'Sicherheit & Verteidigung', '02': 'Sicherheit & Verteidigung',
    '03': 'Sicherheit & Verteidigung', '53': 'Sicherheit & Verteidigung',
    '11': 'Land- & Forstwirtschaft', '12': 'Land- & Forstwirtschaft',
    '13': 'Land- & Forstwirtschaft', '14': 'Land- & Forstwirtschaft',
    '21': 'Fertigung & Technik', '22': 'Fertigung & Technik',
    '23': 'Fertigung & Technik', '24': 'Fertigung & Technik',
    '27': 'Fertigung & Technik', '28': 'Fertigung & Technik',
    '25': 'Maschinen & Elektro', '26': 'Maschinen & Elektro',
    '29': 'Gastgewerbe & Lebensmittel',
    '31': 'Bau & Handwerk', '32': 'Bau & Handwerk',
    '33': 'Bau & Handwerk', '34': 'Bau & Handwerk', '54': 'Bau & Handwerk',
    '41': 'Wissenschaft & Forschung', '42': 'Wissenschaft & Forschung',
    '43': 'IT & Technologie',
    '51': 'Transport & Logistik', '52': 'Transport & Logistik',
    '61': 'Handel & Vertrieb', '62': 'Handel & Vertrieb',
    '63': 'Gastgewerbe & Tourismus',
    '71': 'Wirtschaft & Management',
    '72': 'Finanzen & Banken',
    '73': 'Verwaltung & Recht',
    '81': 'Gesundheit & Medizin', '82': 'Gesundheit & Medizin',
    '83': 'Bildung & Soziales', '84': 'Bildung & Soziales',
    '91': 'Kultur & Medien', '92': 'Kultur & Medien',
    '93': 'Kultur & Medien', '94': 'Kultur & Medien',
}


def _compose_search_reply(actions: dict, language: str, uses_du: bool) -> str:
    """
    Compose a deterministic reply for search intent — no LLM involved.
    Prevents hallucination by skipping the model entirely.
    """
    filters = actions.get('set_filters', {})
    
    # Collect readable filter descriptions
    parts_de = []
    parts_en = []
    
    # Domain names (deduplicated)
    if 'domains' in filters:
        domain_names = list(dict.fromkeys(
            _KLDB_DOMAIN_NAMES.get(c, c) for c in filters['domains']
        ))
        parts_de.append(', '.join(domain_names))
        parts_en.append(', '.join(domain_names))
    
    # City
    city = filters.get('city', '')
    if city:
        parts_de.append(f'in {city}')
        parts_en.append(f'in {city}')
    
    # Radius
    radius = filters.get('radius_km')
    if radius:
        parts_de.append(f'im Umkreis von {radius} km')
        parts_en.append(f'within {radius} km')
    
    filter_desc_de = ' '.join(parts_de) if parts_de else 'deine Suchkriterien'
    filter_desc_en = ' '.join(parts_en) if parts_en else 'your search criteria'
    
    if language == 'de':
        if uses_du:
            return (
                f"Alles klar! Ich setze die Filter auf **{filter_desc_de}**. "
                f"Die Ergebnisse erscheinen gleich auf der Suchseite — schau mal! 🔍"
            )
        else:
            return (
                f"Sehr gerne! Ich setze die Filter auf **{filter_desc_de}**. "
                f"Die Ergebnisse erscheinen gleich auf der Suchseite. 🔍"
            )
    else:
        return (
            f"Got it! I'm setting the filters to **{filter_desc_en}**. "
            f"The results will appear on the search page — take a look! 🔍"
        )


def extract_search_intent(message: str) -> Optional[dict]:
    """
    Extract structured search intent from a user message.
    
    Returns dict with optional keys:
    - domains: list of KLDB 2-digit codes
    - city: str (city name for display)
    - lat, lon: float (coordinates)
    - radius_km: int
    - ql: list of ints [1-4]
    
    Returns None if no search intent detected.
    """
    msg = message.lower().strip()
    
    # Must look like a job search request
    search_triggers_de = [
        r'such\w*', r'find\w*', r'job', r'stell\w*', r'arbeit',
        r'berufs?\b', r'hilf\w*\s+mir', r'zeig\w*\s+mir',
    ]
    search_triggers_en = [
        r'search', r'find', r'look\w*\s+for', r'job', r'position',
        r'show me', r'help me',
    ]
    
    has_trigger = any(re.search(p, msg) for p in search_triggers_de + search_triggers_en)
    if not has_trigger:
        return None
    
    result = {}
    
    # ── Extract domain ──
    found_codes = set()
    for keyword, codes in DOMAIN_KEYWORDS.items():
        if re.search(r'\b' + re.escape(keyword), msg):
            found_codes.update(codes)
    if found_codes:
        result['domains'] = sorted(found_codes)
    
    # ── Extract city ──
    for city_name, (lat, lon) in CITY_COORDS.items():
        if re.search(r'\b' + re.escape(city_name) + r'\b', msg):
            result['city'] = city_name.title()
            result['lat'] = lat
            result['lon'] = lon
            result['radius_km'] = 50  # sensible default
            break
    
    # ── Extract qualification level ──
    found_ql = set()
    for keyword, levels in QL_KEYWORDS.items():
        if re.search(r'\b' + re.escape(keyword), msg):
            found_ql.update(levels)
    if found_ql:
        result['ql'] = sorted(found_ql)
    
    # Only return if we found at least one meaningful filter
    if result:
        return {'set_filters': result}
    
    return None


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
    
    # ── Onboarding check: yogi_name + notification email ──
    onboarding_state = get_onboarding_state(user_id, conn)
    if onboarding_state['needs_yogi_name'] or onboarding_state.get('asking_notification_email'):
        onboarding_response = await handle_onboarding(message, user_id, conn, language, uses_du, onboarding_state)
        if onboarding_response:
            return onboarding_response
    
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
    
    # Tier 2: On-demand context injection
    tier2_intent = detect_tier2_intent(message)
    if tier2_intent:
        tier2_context = load_tier2_context(tier2_intent, user_id, conn, language)
        if tier2_context:
            existing = yogi_context.get('_extra_prompt', '')
            yogi_context['_extra_prompt'] = existing + tier2_context
            logger.info(f"Tier 2 context injected: {tier2_intent}")
    
    # Extract search intent (domains, city, ql) before LLM call
    search_actions = extract_search_intent(message)
    if search_actions:
        logger.info(f"Search intent detected: {search_actions}")
        # Short-circuit: don't call LLM at all for search intents.
        # gemma3:4b hallucinates fake job postings no matter what prompt says.
        # The reply is deterministic anyway — just confirm filter changes.
        reply = _compose_search_reply(search_actions, language, uses_du)
        return MiraResponse(reply=reply, language=language, fallback=False, actions=search_actions)
    
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


# ─────────────────────────────────────────────────────────
# Onboarding: yogi_name + notification email
# ─────────────────────────────────────────────────────────

def get_onboarding_state(user_id: int, conn) -> dict:
    """
    Check onboarding progress for a yogi.
    
    Returns dict with:
        needs_yogi_name: bool
        needs_profile: bool
        needs_notification_email: bool
        asking_notification_email: bool  (name set, email not yet answered, onboarding not completed)
        yogi_name: str or None
        onboarding_completed: bool
    """
    state = {
        'needs_yogi_name': True,
        'needs_profile': True,
        'needs_notification_email': True,
        'asking_notification_email': False,
        'yogi_name': None,
        'onboarding_completed': False,
    }
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT yogi_name, onboarding_completed_at, notification_email
                FROM users WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
            if row:
                state['yogi_name'] = row['yogi_name']
                state['needs_yogi_name'] = not row['yogi_name']
                state['needs_notification_email'] = not row['notification_email']
                state['onboarding_completed'] = row['onboarding_completed_at'] is not None
                # We ask for email right after name is set, before onboarding is marked complete
                state['asking_notification_email'] = (
                    bool(row['yogi_name'])
                    and not row['notification_email']
                    and not row['onboarding_completed_at']
                )
            
            cur.execute("SELECT profile_id FROM profiles WHERE user_id = %s LIMIT 1", (user_id,))
            state['needs_profile'] = cur.fetchone() is None
    except Exception as e:
        logger.warning(f"Onboarding state check failed: {e}")
    
    return state


_YOGI_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9äöüÄÖÜß][a-zA-Z0-9äöüÄÖÜß._\- ]{0,18}[a-zA-Z0-9äöüÄÖÜß]$')

def validate_yogi_name(name: str) -> tuple:
    """
    Validate a proposed yogi name.
    
    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not name or not name.strip():
        return False, "Name cannot be empty"
    
    name = name.strip()
    
    if len(name) < 2:
        return False, "Name must be at least 2 characters"
    if len(name) > 20:
        return False, "Name must be 20 characters or fewer"
    
    if not _YOGI_NAME_PATTERN.match(name):
        return False, "Name can only contain letters, numbers, dots, hyphens, and spaces"
    
    # Block obvious bad names
    blocked = {'admin', 'mira', 'doug', 'adele', 'system', 'bot', 'test', 'null', 'undefined'}
    if name.lower() in blocked:
        return False, "That name is reserved"
    
    return True, None


def save_yogi_name(user_id: int, name: str, conn) -> bool:
    """
    Store yogi_name. Returns False if name is taken (case-insensitive).
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET yogi_name = %s
                WHERE user_id = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM users 
                      WHERE LOWER(yogi_name) = LOWER(%s) AND user_id != %s
                  )
            """, (name, user_id, name, user_id))
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to save yogi_name: {e}")
        conn.rollback()
        return False


def extract_yogi_name_from_message(message: str) -> Optional[str]:
    """
    Try to extract a yogi name from a conversational response.
    
    Handles:
    - "Nenn mich xai" → "xai"
    - "I'm Luna" → "Luna"
    - "xai" → "xai" (plain name)
    - "Ich heiße Max" → "Max"
    - "Call me Stellar" → "Stellar"
    
    Returns None for greetings, questions, and non-name responses.
    """
    message = message.strip()
    
    # Filter out greetings and non-name messages
    _GREETINGS = {
        'hallo', 'hello', 'hi', 'hey', 'moin', 'servus', 'grüß gott',
        'guten tag', 'guten morgen', 'guten abend', 'good morning',
        'good evening', 'howdy', 'yo', 'sup', 'ciao', 'tschüss',
        'danke', 'thanks', 'ja', 'nein', 'yes', 'no', 'ok', 'okay',
        'hi there', 'hey there', 'hello there', 'hi mira', 'hey mira',
        'hello mira', 'hallo mira', 'na', 'na du', 'hey ho',
        'was geht', 'wie geht es', 'how are you', "what's up",
        'good day', 'guten tag mira', 'hallo zusammen',
    }
    cleaned = message.lower().rstrip('!?., ')
    if cleaned in _GREETINGS:
        return None
    
    # Also filter if first word is a greeting and rest is filler
    _GREETING_STARTERS = {'hi', 'hey', 'hello', 'hallo', 'moin'}
    _FILLER_WORDS = {'there', 'mira', 'du', 'ihr', 'alle', 'zusammen', 'folks', 'everyone', 'all'}
    words_lower = cleaned.split()
    if words_lower and words_lower[0] in _GREETING_STARTERS:
        rest = set(words_lower[1:])
        if rest and rest.issubset(_FILLER_WORDS):
            return None
    
    # Filter out questions
    if message.rstrip().endswith('?'):
        return None
    
    # Pattern-based extraction
    patterns = [
        r'(?:nenn|ruf)\s+mich\s+(.+)',
        r"(?:call|name)\s+me\s+(.+)",
        r"(?:ich heiße|ich bin|i'?m|i am|mein name ist|my name is)\s+(.+)",
        r"(?:du kannst mich|you can call me)\s+(.+)\s+nennen",
        r"(?:du kannst mich|you can call me)\s+(.+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            name = match.group(1).strip().rstrip('.!?')
            # Take first word if response is conversational
            if ' ' in name and len(name) > 20:
                name = name.split()[0]
            return name
    
    # If it's a short plain response (just the name), use it directly
    words = message.strip().rstrip('.!?').split()
    if 1 <= len(words) <= 3 and len(message) <= 30:
        return ' '.join(words)
    
    return None


async def handle_onboarding(message: str, user_id: int, conn, language: str, uses_du: bool, onboarding_state: dict) -> Optional[MiraResponse]:
    """
    Handle onboarding conversation.
    
    Returns MiraResponse if onboarding handled the message, None to fall through.
    """
    # Step 1: yogi_name not set yet
    if onboarding_state['needs_yogi_name']:
        # Try to extract a name from the message
        proposed_name = extract_yogi_name_from_message(message)
        
        if proposed_name:
            valid, error = validate_yogi_name(proposed_name)
            if valid:
                saved = save_yogi_name(user_id, proposed_name, conn)
                if saved:
                    # Name saved — now ask about notification email
                    if language == 'en':
                        reply = (f"Nice to meet you, {proposed_name}! 🧘\n\n"
                                 f"One quick thing — if we find your dream job, should we let you know? "
                                 f"You can give me any email address you like for notifications. "
                                 f"No pressure — you can also just say no and check in whenever you want.")
                    else:
                        if uses_du:
                            reply = (f"Schön dich kennenzulernen, {proposed_name}! 🧘\n\n"
                                     f"Eine kurze Frage — wenn wir deinen Traumjob finden, sollen wir dich benachrichtigen? "
                                     f"Du kannst mir eine beliebige E-Mail-Adresse dafür geben. "
                                     f"Kein Druck — du kannst auch einfach nein sagen und dich einloggen, wann immer du magst.")
                        else:
                            reply = (f"Schön Sie kennenzulernen, {proposed_name}! 🧘\n\n"
                                     f"Eine kurze Frage — wenn wir Ihren Traumjob finden, sollen wir Sie benachrichtigen? "
                                     f"Sie können mir eine beliebige E-Mail-Adresse dafür geben. "
                                     f"Kein Druck — Sie können auch einfach nein sagen und sich einloggen, wann immer Sie möchten.")
                    return MiraResponse(reply=reply, language=language, actions={'onboarding': 'name_set', 'yogi_name': proposed_name})
                else:
                    # Name taken
                    if language == 'en':
                        reply = f"Hmm, '{proposed_name}' is already taken. Could you choose a different name?"
                    else:
                        reply = f"Hmm, '{proposed_name}' ist leider schon vergeben. Magst du einen anderen Namen wählen?"
                    return MiraResponse(reply=reply, language=language)
            else:
                # Invalid name
                if language == 'en':
                    reply = f"That name doesn't quite work — {error}. Try something between 2 and 20 characters?"
                else:
                    reply = f"Der Name passt leider nicht — {error}. Versuch etwas zwischen 2 und 20 Zeichen?"
                return MiraResponse(reply=reply, language=language)
        else:
            # First message or couldn't extract name — ask for it
            if language == 'en':
                reply = ("Welcome to talent.yoga! 🧘 I'm Mira, your career companion.\n\n"
                         "Before we start — what should I call you? "
                         "Choose any name you like. It doesn't have to be your real one — "
                         "your privacy matters here.")
            else:
                if uses_du:
                    reply = ("Willkommen bei talent.yoga! 🧘 Ich bin Mira, deine Begleiterin bei der Jobsuche.\n\n"
                             "Bevor wir loslegen — wie soll ich dich nennen? "
                             "Such dir einen Namen aus, der dir gefällt. Muss nicht dein richtiger sein — "
                             "deine Privatsphäre ist uns wichtig.")
                else:
                    reply = ("Willkommen bei talent.yoga! 🧘 Ich bin Mira, Ihre Begleiterin bei der Jobsuche.\n\n"
                             "Bevor wir beginnen — wie soll ich Sie ansprechen? "
                             "Wählen Sie einen Namen, der Ihnen gefällt. Er muss nicht Ihr richtiger sein — "
                             "Ihre Privatsphäre ist uns wichtig.")
            return MiraResponse(reply=reply, language=language, actions={'onboarding': 'ask_name'})
    
    # Step 2: yogi_name set, but notification email not yet answered
    if onboarding_state.get('asking_notification_email'):
        email_response = detect_notification_email_response(message)
        yogi_name = onboarding_state.get('yogi_name', 'yogi')
        
        if email_response == 'decline':
            # Yogi declined — that's fine, complete onboarding
            complete_onboarding(user_id, conn)
            if language == 'en':
                reply = (f"No problem, {yogi_name}! You can always check your matches when you log in.\n\n"
                         f"Want to upload your CV? I'll extract your skills and start finding matches for you. "
                         f"Your data stays private — I only keep the skills, never the original document.")
            else:
                if uses_du:
                    reply = (f"Kein Problem, {yogi_name}! Du siehst deine Matches immer, wenn du dich einloggst.\n\n"
                             f"Möchtest du deinen Lebenslauf hochladen? Ich extrahiere deine Skills "
                             f"und fange an, passende Stellen für dich zu finden. "
                             f"Deine Daten bleiben privat — ich speichere nur die Skills, nie das Original.")
                else:
                    reply = (f"Kein Problem, {yogi_name}! Sie sehen Ihre Matches immer, wenn Sie sich einloggen.\n\n"
                             f"Möchten Sie Ihren Lebenslauf hochladen? Ich extrahiere Ihre Skills "
                             f"und fange an, passende Stellen für Sie zu finden. "
                             f"Ihre Daten bleiben privat — ich speichere nur die Skills, nie das Original.")
            return MiraResponse(reply=reply, language=language, actions={'onboarding': 'email_declined'})
        
        elif email_response and email_response != 'decline':
            # Got an email — save it and complete onboarding
            saved = save_notification_email(user_id, email_response, conn)
            complete_onboarding(user_id, conn)
            if saved:
                if language == 'en':
                    reply = (f"Got it, {yogi_name}! I'll notify you at {email_response} when we find great matches. "
                             f"You can unsubscribe anytime.\n\n"
                             f"Now — want to upload your CV? I'll extract your skills and start matching right away.")
                else:
                    if uses_du:
                        reply = (f"Perfekt, {yogi_name}! Ich benachrichtige dich unter {email_response}, wenn wir tolle Matches finden. "
                                 f"Du kannst dich jederzeit abmelden.\n\n"
                                 f"Und jetzt — möchtest du deinen Lebenslauf hochladen? Ich extrahiere deine Skills "
                                 f"und fange sofort an zu matchen.")
                    else:
                        reply = (f"Perfekt, {yogi_name}! Ich benachrichtige Sie unter {email_response}, wenn wir tolle Matches finden. "
                                 f"Sie können sich jederzeit abmelden.\n\n"
                                 f"Und jetzt — möchten Sie Ihren Lebenslauf hochladen?")
                return MiraResponse(reply=reply, language=language, actions={'onboarding': 'email_set', 'notification_email': email_response})
            else:
                if language == 'en':
                    reply = "Something went wrong saving that email — could you try again?"
                else:
                    reply = "Da ist etwas schiefgegangen — kannst du es nochmal versuchen?"
                return MiraResponse(reply=reply, language=language)
        
        else:
            # Didn't understand — it's a normal message, let it fall through.
            # But first, complete onboarding so we don't keep asking
            complete_onboarding(user_id, conn)
            return None  # Fall through to normal chat


def save_notification_email(user_id: int, email: str, conn) -> bool:
    """Save notification email and record consent timestamp."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET notification_email = %s,
                    notification_consent_at = NOW()
                WHERE user_id = %s
            """, (email, user_id))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save notification email: {e}")
        return False


def complete_onboarding(user_id: int, conn) -> bool:
    """Mark onboarding as completed."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET onboarding_completed_at = NOW()
                WHERE user_id = %s AND onboarding_completed_at IS NULL
            """, (user_id,))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to complete onboarding: {e}")
        return False


def detect_notification_email_response(message: str) -> Optional[str]:
    """
    Detect if user is providing an email for notifications,
    or declining notification.
    
    Returns:
        email string if provided, 'decline' if explicitly declined, None if not relevant.
    """
    message_lower = message.lower().strip()
    
    # Decline patterns
    decline_patterns = [
        r'\b(?:nein|no|nope|nicht|kein|keine|lieber nicht|rather not|no thanks|nein danke)\b',
    ]
    for p in decline_patterns:
        if re.search(p, message_lower):
            return 'decline'
    
    # Extract email
    email_match = re.search(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b', message)
    if email_match:
        return email_match.group()
    
    return None


# Singleton instance
_mira_instance = None

def get_mira():
    """Get or create Mira instance."""
    global _mira_instance
    if _mira_instance is None:
        _mira_instance = True  # Just a flag, the functions above are stateless
    return True
