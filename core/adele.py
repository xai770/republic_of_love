"""
Adele — Conversational Profile Builder

Adele is the Interview Coach persona. She builds yogi profiles through
conversation instead of CV upload. She asks focused questions one at a time,
extracts structured data from free-form answers, and anonymizes company names
through the company_aliases registry.

Phases:
    intro → current_role → work_history → skills → education → preferences → summary → complete

Usage:
    from core.adele import adele_chat
    response = await adele_chat(message, user_id, conn, language)
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional
import httpx
from psycopg2.extras import Json

from core.logging_config import get_logger
from core.company_anonymizer import lookup_or_queue

logger = get_logger(__name__)

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
MODEL = "qwen2.5:7b"
FALLBACK_MODEL = "gemma3:4b"
TIMEOUT = 25.0


# ─────────────────────────────────────────────────────────
# Response dataclass
# ─────────────────────────────────────────────────────────

@dataclass
class AdeleResponse:
    """Response from Adele."""
    reply: str
    language: str
    phase: str = 'intro'
    collected: dict = field(default_factory=dict)
    actions: Optional[dict] = None  # For frontend (e.g. save profile)


# ─────────────────────────────────────────────────────────
# Phase definitions + prompts
# ─────────────────────────────────────────────────────────

PHASES = [
    'intro',
    'current_role',
    'work_history',
    'skills',
    'education',
    'preferences',
    'summary',
    'complete',
]


def _extract_prompt(phase: str, message: str, collected: dict) -> str:
    """Build the LLM extraction prompt for a given phase."""

    if phase == 'current_role':
        return f"""Extract the yogi's current or most recent job information from their message.

Message: "{message}"

Return ONLY valid JSON:
{{
    "current_title": "their job title or null",
    "company_name": "company name they mentioned or null",
    "duration_hint": "any duration mentioned (e.g. '3 years', 'since 2020') or null",
    "industry_hint": "any industry mentioned or null",
    "responsibilities": ["key responsibilities mentioned"] 
}}

IMPORTANT RULES:
- Expand common abbreviations in job titles: SW=Software, SME=Subject Matter Expert,
  Mgmt=Management, Eng=Engineering, Dev=Developer, Arch=Architect, Ops=Operations,
  PM=Project Manager, BA=Business Analyst, UX=UX Designer, QA=QA Engineer
- For self-employment, freelance, or founding a startup: set current_title to
  'Freelancer' (or the relevant role) and company_name to null
- If something is not mentioned, use null. Do not invent fields."""

    elif phase == 'work_history':
        return f"""Extract work history information from the yogi's message about a previous job.

Message: "{message}"

Return ONLY valid JSON:
{{
    "role": "their job title or null",
    "company_name": "company name they mentioned or null",
    "duration_hint": "any duration mentioned or null",
    "industry_hint": "industry or null",
    "responsibilities": ["key responsibilities mentioned"],
    "wants_more": true
}}

IMPORTANT RULES:
- Expand common abbreviations in job titles: SW=Software, SME=Subject Matter Expert,
  Mgmt=Management, Eng=Engineering, Dev=Developer, Arch=Architect, PM=Project Manager
- If the yogi describes self-employment, freelancing, running their own business,
  building a startup, or independent projects (no employer), set:
  role = descriptive title (e.g. 'Freelance Developer', 'Gründer', 'Self-employed Consultant')
  company_name = null (they have no employer)
- If something is not mentioned, use null. Do NOT invent a company name.

Set "wants_more" to false if the yogi says they have no more previous jobs,
says "that's all", "no more", "nothing before that", or similar.
Otherwise set "wants_more" to true.

If something is not mentioned, use null. Extract EXACTLY what they said."""

    elif phase == 'skills':
        return f"""Extract ALL technical skills, tools, technologies, programming languages, frameworks, 
and spoken languages from the yogi's message.

Message: "{message}"

Already collected: {json.dumps(collected.get('skills', []))}

Return ONLY valid JSON:
{{
    "technical_skills": ["Python", "Java", "SQL", "Docker"],
    "spoken_languages": ["German", "English"],
    "certifications": ["AWS Solutions Architect"]
}}

IMPORTANT: Put ALL programming languages, tools, frameworks, databases, cloud platforms,
methodologies, and technical competencies into "technical_skills".
Put only human spoken languages into "spoken_languages".
Do NOT repeat items already collected."""

    elif phase == 'education':
        return f"""Extract education information from the yogi's message.

Message: "{message}"

Return ONLY valid JSON:
{{
    "education": [
        {{"level": "masters/bachelors/phd/apprenticeship/etc", "field": "field of study or null"}}
    ]
}}

Extract EXACTLY what they said. Do not invent fields. Use lowercase for level."""

    elif phase == 'preferences':
        return f"""Extract job search preferences from the yogi's message.

Message: "{message}"

Return ONLY valid JSON:
{{
    "desired_roles": ["role1"],
    "desired_locations": ["location1"],
    "salary_min": null,
    "salary_max": null,
    "industries": ["industry1"],
    "remote_preference": null
}}

For salary, extract numbers in EUR annual. Use null for unmentioned fields.
For remote_preference, use "remote", "hybrid", "onsite", or null."""

    return "{}"


def _conversation_prompt(phase: str, message: str, collected: dict, lang: str) -> str:
    """Build the LLM prompt for generating Adele's conversational reply."""
    lang_instruction = "Respond in German." if lang == 'de' else "Respond in English."

    if phase == 'intro':
        return f"""You are Adele, a warm and friendly interview coach at talent.yoga.
You are meeting a new user for the first time. They just sent you their first message.

User's message: "{message}"

Respond naturally to what they said. Introduce yourself briefly as Adele, their
interview coach. Explain that you help build their professional profile through
conversation — no CV upload needed. Mention that company names are automatically
anonymized for privacy. Then gently ask about their current or most recent job
title and company.

Keep your response warm, conversational, and SHORT (3-5 sentences max).
Use one emoji maximum. Do NOT use bullet points or lists.
{lang_instruction}"""

    return None


# ─────────────────────────────────────────────────────────
# LLM call
# ─────────────────────────────────────────────────────────

async def _ask_llm(prompt: str, temperature: float = 0.1, model: str = MODEL) -> Optional[str]:
    """Call Ollama for extraction or conversation."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(OLLAMA_URL, json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature}
            })
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
    except Exception as e:
        logger.error(f"Adele LLM call failed ({model}): {e}")
        return None


async def _ask_llm_cascade(prompt: str, temperature: float = 0.1) -> Optional[str]:
    """Try primary model, fall back to secondary model."""
    result = await _ask_llm(prompt, temperature=temperature, model=MODEL)
    if result:
        return result
    logger.warning(f"Primary model {MODEL} failed, trying fallback {FALLBACK_MODEL}")
    return await _ask_llm(prompt, temperature=temperature, model=FALLBACK_MODEL)


def _parse_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
    if not text:
        return None
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find JSON object in text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


# ─────────────────────────────────────────────────────────
# Session management
# ─────────────────────────────────────────────────────────

def get_session(user_id: int, conn) -> Optional[dict]:
    """Get or create Adele session for this user."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT session_id, phase, collected, work_history_count, turn_count
            FROM adele_sessions
            WHERE user_id = %s AND completed_at IS NULL
        """, (user_id,))
        row = cur.fetchone()
        if row:
            collected = row['collected']
            if isinstance(collected, str):
                collected = json.loads(collected)
            return {
                'session_id': row['session_id'],
                'phase': row['phase'],
                'collected': collected,
                'work_history_count': row['work_history_count'],
                'turn_count': row['turn_count'],
            }
        # Create new session
        cur.execute("""
            INSERT INTO adele_sessions (user_id, phase, collected)
            VALUES (%s, 'intro', '{}'::jsonb)
            RETURNING session_id
        """, (user_id,))
        conn.commit()
        return {
            'session_id': cur.fetchone()['session_id'],
            'phase': 'intro',
            'collected': {},
            'work_history_count': 0,
            'turn_count': 0,
        }


def _update_session(conn, session_id: int, phase: str, collected: dict,
                     work_history_count: int = None, turn_count: int = None):
    """Update session state."""
    with conn.cursor() as cur:
        parts = ["phase = %s", "collected = %s::jsonb", "updated_at = NOW()"]
        vals = [phase, json.dumps(collected, ensure_ascii=False)]
        if work_history_count is not None:
            parts.append("work_history_count = %s")
            vals.append(work_history_count)
        if turn_count is not None:
            parts.append("turn_count = %s")
            vals.append(turn_count)
        vals.append(session_id)
        cur.execute(
            f"UPDATE adele_sessions SET {', '.join(parts)} WHERE session_id = %s",
            vals
        )
        conn.commit()


def _complete_session(conn, session_id: int):
    """Mark session as completed."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE adele_sessions SET completed_at = NOW(), phase = 'complete'
            WHERE session_id = %s
        """, (session_id,))
        conn.commit()


def _reset_session(conn, user_id: int):
    """Delete existing session so a new one can start."""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM adele_sessions WHERE user_id = %s
        """, (user_id,))
        conn.commit()


# ─────────────────────────────────────────────────────────
# Duration parsing
# ─────────────────────────────────────────────────────────

def _parse_duration(hint: str) -> Optional[float]:
    """Parse a duration hint like '3 years', '18 months', 'since 2020'."""
    if not hint:
        return None
    hint_lower = hint.lower().strip()

    # "X years"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|jahre?)', hint_lower)
    if m:
        return float(m.group(1))

    # "X months"
    m = re.search(r'(\d+)\s*(?:months?|monate?)', hint_lower)
    if m:
        return round(int(m.group(1)) / 12, 1)

    # "since YYYY"
    m = re.search(r'(?:since|seit)\s*(\d{4})', hint_lower)
    if m:
        from datetime import datetime
        years = datetime.now().year - int(m.group(1))
        return max(0.5, float(years))

    return None


# ─────────────────────────────────────────────────────────
# Conversation replies (bilingual)
# ─────────────────────────────────────────────────────────

def _reply(lang: str, en: str, de: str) -> str:
    return de if lang == 'de' else en


def _nominative_to_dative_de(phrase: str) -> str:
    """Convert a German nominative 'ein(e) [adj*] noun' phrase to dative form.

    Used when the phrase follows a preposition like 'bei' which governs dative.
    Examples:
        "eine große deutsche Bank"  → "einer großen deutschen Bank"
        "ein mittelständisches Autohaus" → "einem mittelständischen Autohaus"
        "ein führendes Unternehmen" → "einem führenden Unternehmen"
    Only alters phrases that start with 'ein'/'eine'. Others returned unchanged.
    """
    # Swap indefinite article
    result, swapped = re.subn(r'^eine\b', 'einer', phrase)
    if not swapped:
        result, swapped = re.subn(r'^ein\b', 'einem', phrase)
    if not swapped:
        return phrase  # doesn't start with ein/eine — return as-is

    # Convert adjective endings to dative weak inflection (-en for all genders)
    # Only process words between the article (index 0) and the last word (the noun)
    words = result.split(' ')
    for i in range(1, len(words) - 1):
        w = words[i]
        if w.endswith('es') or w.endswith('er'):
            words[i] = w[:-2] + 'en'
        elif (w.endswith('e')
              and not w.endswith('ie')
              and not w.endswith('ee')
              and not w.endswith('ue')):
            words[i] = w[:-1] + 'en'
    return ' '.join(words)


def _detect_redirect(message: str) -> bool:
    """Detect if the user is asking a question or offering to elaborate rather than
    providing the requested structured information (title/company)."""
    msg = message.strip()
    # Ends with a question mark
    if msg.endswith('?'):
        return True
    # Common redirect phrases in German and English
    redirect_patterns = re.compile(
        r'\b(?:'
        r'warte?\s*mal|soll\s*ich|kann\s*ich|darf\s*ich|'
        r'lass\s*mich|let\s*me|should\s*i|can\s*i|'
        r'wollte?\s*(?:nur|gerne?)|ich\s*meine|gemeint|'
        r'eigentlich|genauer\s*gesagt|erzähl(?:en)?\s*dir'
        r')\b',
        re.IGNORECASE
    )
    return bool(redirect_patterns.search(msg))


# ─────────────────────────────────────────────────────────
# Profile save
# ─────────────────────────────────────────────────────────

def save_profile(user_id: int, collected: dict, conn):
    """
    Save collected data to the profiles + profile_work_history tables.
    Uses the same import path as the CV import endpoint.
    """
    from psycopg2.extras import Json

    with conn.cursor() as cur:
        # Ensure profile exists
        cur.execute("SELECT profile_id FROM profiles WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            profile_id = row['profile_id']
        else:
            cur.execute("""
                SELECT yogi_name FROM users WHERE user_id = %s
            """, (user_id,))
            u = cur.fetchone()
            yogi_name = u['yogi_name'] if u else 'New Yogi'
            cur.execute("""
                INSERT INTO profiles (full_name, user_id, profile_source)
                VALUES (%s, %s, 'adele_interview')
                RETURNING profile_id
            """, (yogi_name, user_id))
            profile_id = cur.fetchone()['profile_id']

        # Merge skills + languages + certifications into skill_keywords
        all_keywords = list(dict.fromkeys(
            collected.get('skills', []) +
            collected.get('languages', []) +
            collected.get('certifications', [])
        ))

        # Years experience estimate
        years_exp = None
        wh = collected.get('work_history', [])
        if wh:
            total = sum(e.get('duration_years') or 0 for e in wh)
            if total > 0:
                years_exp = int(total)

        # Preferences
        prefs = collected.get('preferences', {})

        # implied_skills: only write if Pass 3 produced results and column is empty
        implied = collected.get('implied_skills') or []
        implied_json = Json(implied) if implied else None

        # Update profile
        cur.execute("""
            UPDATE profiles SET
                current_title = COALESCE(%s, current_title),
                experience_level = COALESCE(%s, experience_level),
                years_of_experience = COALESCE(%s, years_of_experience),
                skill_keywords = %s,
                implied_skills = CASE
                    WHEN %s IS NOT NULL THEN %s
                    ELSE implied_skills
                END,
                profile_summary = COALESCE(%s, profile_summary),
                desired_roles = COALESCE(%s, desired_roles),
                desired_locations = COALESCE(%s, desired_locations),
                expected_salary_min = COALESCE(%s, expected_salary_min),
                expected_salary_max = COALESCE(%s, expected_salary_max),
                profile_source = 'adele_interview',
                skills_extraction_status = 'imported',
                updated_at = NOW()
            WHERE profile_id = %s
        """, (
            collected.get('current_title'),
            collected.get('career_level'),
            years_exp,
            Json(all_keywords),
            implied_json, implied_json,  # CASE condition + value
            collected.get('profile_summary'),
            prefs.get('desired_roles') if prefs else None,
            prefs.get('desired_locations') if prefs else None,
            prefs.get('salary_min') if prefs else None,
            prefs.get('salary_max') if prefs else None,
            profile_id,
        ))

        # Remove previous adele-imported work history
        cur.execute("""
            DELETE FROM profile_work_history
            WHERE profile_id = %s AND extraction_status = 'adele_interview'
        """, (profile_id,))

        # Insert work history
        for entry in wh:
            duration_months = None
            dy = entry.get('duration_years')
            if dy:
                duration_months = int(float(dy) * 12)
            desc = '; '.join(r for r in entry.get('key_responsibilities', []) if r)
            cur.execute("""
                INSERT INTO profile_work_history
                    (profile_id, company_name, job_title, duration_months,
                     job_description, extraction_status)
                VALUES (%s, %s, %s, %s, %s, 'adele_interview')
            """, (
                profile_id,
                entry.get('employer_description') or 'a company',
                entry.get('role') or 'unknown role',
                duration_months,
                desc or None,
            ))

        conn.commit()
        logger.info(f"Adele saved profile for user {user_id}: "
                    f"{len(all_keywords)} skills, {len(wh)} work entries")
        return profile_id


# ─────────────────────────────────────────────────────────
# Format profile summary for display
# ─────────────────────────────────────────────────────────

def _format_summary(collected: dict, lang: str) -> str:
    """Format collected data as a readable profile summary."""
    parts = []

    # Title
    title = collected.get('current_title')
    if title:
        parts.append(f"**{title}**")

    # Work history
    wh = collected.get('work_history', [])
    if wh:
        h = _reply(lang, "Work History", "Berufserfahrung")
        parts.append(f"\n🏢 **{h}:**")
        for entry in wh:
            role = entry.get('role', '?')
            emp = entry.get('employer_description', 'a company')
            dur = entry.get('duration_years')
            dur_str = f" ({dur}y)" if dur else ""
            parts.append(f"- {role} — {emp}{dur_str}")

    # Skills
    skills = collected.get('skills', [])
    if skills:
        h = _reply(lang, "Skills", "Fähigkeiten")
        parts.append(f"\n🛠 **{h}:** {', '.join(skills)}")

    # Languages
    langs = collected.get('languages', [])
    if langs:
        h = _reply(lang, "Languages", "Sprachen")
        parts.append(f"\n🌐 **{h}:** {', '.join(langs)}")

    # Certifications
    certs = collected.get('certifications', [])
    if certs:
        h = _reply(lang, "Certifications", "Zertifizierungen")
        parts.append(f"\n📜 **{h}:** {', '.join(certs)}")

    # Education
    edu = collected.get('education', [])
    if edu:
        h = _reply(lang, "Education", "Ausbildung")
        parts.append(f"\n📚 **{h}:**")
        for e in edu:
            level = (e.get('level') or '').title()
            fld = e.get('field') or ''
            parts.append(f"- {level} {fld}".strip())

    # Preferences
    prefs = collected.get('preferences', {})
    if prefs:
        h = _reply(lang, "Looking For", "Sucht")
        parts.append(f"\n🎯 **{h}:**")
        if prefs.get('desired_roles'):
            parts.append(f"- {_reply(lang, 'Roles', 'Rollen')}: {', '.join(prefs['desired_roles'])}")
        if prefs.get('desired_locations'):
            parts.append(f"- {_reply(lang, 'Locations', 'Standorte')}: {', '.join(prefs['desired_locations'])}")
        sal_min = prefs.get('salary_min')
        sal_max = prefs.get('salary_max')
        if sal_min or sal_max:
            sal_str = f"€{sal_min:,}–{sal_max:,}" if sal_min and sal_max else \
                      f"€{sal_min:,}+" if sal_min else f"bis €{sal_max:,}"
            parts.append(f"- {_reply(lang, 'Salary', 'Gehalt')}: {sal_str}")

    return '\n'.join(parts)


# ─────────────────────────────────────────────────────────
# Incremental save helper
# ─────────────────────────────────────────────────────────

def _try_save(user_id: int, collected: dict, conn):
    """Save profile to DB so the right-pane preview stays current after each turn."""
    if not collected.get('current_title') and not collected.get('work_history'):
        return
    try:
        save_profile(user_id, collected, conn)
    except Exception as e:
        logger.warning(f"Incremental profile save failed: {e}")


# ─────────────────────────────────────────────────────────
# Main chat function
# ─────────────────────────────────────────────────────────

async def adele_chat(message: str, user_id: int, conn,
                     language: str = 'de') -> AdeleResponse:
    """
    Main entry point for Adele conversation.

    Works as a state machine: each call reads the current phase,
    processes the yogi's message, extracts data, advances the phase,
    and returns the next question.
    """
    if not message or not message.strip():
        return AdeleResponse(
            reply=_reply(language, "I didn't catch that — could you try again?",
                         "Das habe ich nicht verstanden — kannst du es nochmal versuchen?"),
            language=language
        )

    message = message.strip()

    # Check for restart intent
    if re.match(r'^(?:restart|reset|start over|von vorne|nochmal|neu starten)\s*$',
                message, re.IGNORECASE):
        _reset_session(conn, user_id)
        session = get_session(user_id, conn)
        return AdeleResponse(
            reply=_reply(language, _INTRO_EN, _INTRO_DE),
            language=language,
            phase='intro',
            actions={'adele': 'restart'}
        )

    # Get or create session
    session = get_session(user_id, conn)
    phase = session['phase']
    collected = session['collected']
    turn = session['turn_count'] + 1

    # ── INTRO phase ──
    if phase == 'intro':
        # Use LLM to respond naturally to the user's first message
        conv_prompt = _conversation_prompt('intro', message, collected, language)
        llm_reply = await _ask_llm_cascade(conv_prompt, temperature=0.7)

        if not llm_reply:
            # Last resort: canned intro (both LLMs failed)
            llm_reply = _reply(language, _INTRO_EN, _INTRO_DE)

        _update_session(conn, session['session_id'], 'current_role', collected,
                        turn_count=turn)
        return AdeleResponse(
            reply=llm_reply,
            language=language,
            phase='current_role',
            actions={'adele': 'started'}
        )

    # ── CURRENT_ROLE phase ──
    if phase == 'current_role':
        extracted = await _extract(phase, message, collected)

        # ── Responsibilities follow-up: user is elaborating on an already-captured role
        if collected.get('current_title') and collected.get('work_history') and extracted:
            resps = extracted.get('responsibilities', [])
            if resps:
                collected['work_history'][0].setdefault('key_responsibilities', []).extend(resps)
                _update_session(conn, session['session_id'], 'work_history', collected,
                                work_history_count=1, turn_count=turn)
                _try_save(user_id, collected, conn)
                return AdeleResponse(
                    reply=_reply(language,
                        "Got it — responsibilities noted.\n\n"
                        "What was your previous role before that? "
                        "If this was your first job, just say so.",
                        "Verstanden — Aufgaben notiert.\n\n"
                        "Was war deine vorherige Position davor? "
                        "Wenn das dein erster Job war, sag einfach Bescheid."),
                    language=language,
                    phase='work_history',
                    collected=collected,
                )

        if extracted and (extracted.get('current_title') or extracted.get('company_name')):
            # Store current title
            if extracted.get('current_title'):
                collected['current_title'] = extracted['current_title']
            # Build work entry (replace first entry to avoid duplicates on re-entry)
            company = extracted.get('company_name')
            entry = _build_work_entry(
                role=extracted.get('current_title'),
                company_name=company,
                duration_hint=extracted.get('duration_hint'),
                industry_hint=extracted.get('industry_hint'),
                responsibilities=extracted.get('responsibilities', []),
                conn=conn,
                lang=language,
            )
            if collected.get('work_history'):
                collected['work_history'][0] = entry
            else:
                collected['work_history'] = [entry]
            wh_count = 1

            # Say what we got + ask about responsibilities if thin
            emp_raw = entry.get('employer_description')
            emp_de = _nominative_to_dative_de(emp_raw) if emp_raw else None
            emp_en = emp_raw or 'your company'
            emp_de = emp_de or 'deinem Unternehmen'
            role_label = entry.get('role')
            dur = entry.get('duration_years')
            dur_str = f" ({dur} {'years' if language == 'en' else 'Jahre'})" if dur else ""

            if role_label and entry.get('key_responsibilities'):
                # Good enough — move to previous jobs
                _update_session(conn, session['session_id'], 'work_history', collected,
                                work_history_count=wh_count, turn_count=turn)
                _try_save(user_id, collected, conn)
                return AdeleResponse(
                    reply=_reply(language,
                        f"Got it — **{role_label}** at {emp_en}{dur_str}.\n\n"
                        f"What was your previous role before that? "
                        f"If this was your first job, just say so.",
                        f"Verstanden — **{role_label}** bei {emp_de}{dur_str}.\n\n"
                        f"Was war deine vorherige Position davor? "
                        f"Wenn das dein erster Job war, sag einfach Bescheid."),
                    language=language,
                    phase='work_history',
                    collected=collected,
                )
            elif role_label:
                # Stay in current_role to collect responsibilities
                _update_session(conn, session['session_id'], 'current_role', collected,
                                work_history_count=wh_count, turn_count=turn)
                _try_save(user_id, collected, conn)
                return AdeleResponse(
                    reply=_reply(language,
                        f"Got it — **{role_label}** at {emp_en}{dur_str}.\n\n"
                        f"What are your main responsibilities there? What do you actually do day-to-day?",
                        f"Verstanden — **{role_label}** bei {emp_de}{dur_str}.\n\n"
                        f"Was sind deine Hauptaufgaben dort? Was machst du so im Tagesgeschäft?"),
                    language=language,
                    phase='current_role',  # stay here for responsibilities
                    collected=collected,
                )
            else:
                # Got a company but no title — ask for the title specifically
                _update_session(conn, session['session_id'], 'current_role', collected,
                                turn_count=turn)
                return AdeleResponse(
                    reply=_reply(language,
                        f"I see you're at {emp_en} — what's your job title there?",
                        f"Ich sehe, du bist bei {emp_de} — wie lautet dein Jobtitel dort?"),
                    language=language,
                    phase='current_role',
                    collected=collected,
                )
        else:
            # Couldn't extract — check if user is asking a question or offering to elaborate
            if _detect_redirect(message):
                return AdeleResponse(
                    reply=_reply(language,
                        "Of course! Please go ahead — tell me more.",
                        "Natürlich! Nur zu — erzähl mir gerne mehr."),
                    language=language,
                    phase='current_role',
                )
            # Otherwise ask more specifically
            return AdeleResponse(
                reply=_reply(language,
                    "Could you tell me your current or most recent job title and company?",
                    "Kannst du mir deinen aktuellen oder letzten Jobtitel und die Firma nennen?"),
                language=language,
                phase='current_role',
            )

    # ── WORK_HISTORY phase (loop) ──
    if phase == 'work_history':
        extracted = await _extract(phase, message, collected)

        # Check if yogi says "no more jobs"
        no_more = _detect_no_more(message) or \
                  (extracted and not extracted.get('wants_more', True))

        if no_more:
            # Move to skills
            _update_session(conn, session['session_id'], 'skills', collected,
                            turn_count=turn)
            return AdeleResponse(
                reply=_reply(language,
                    "Great, thanks for walking me through your experience!\n\n"
                    "Now — what **technologies, tools, and skills** do you work with? "
                    "Programming languages, frameworks, methodologies — anything that comes to mind.",
                    "Super, danke für den Überblick über deine Erfahrung!\n\n"
                    "Jetzt — welche **Technologien, Tools und Fähigkeiten** nutzt du? "
                    "Programmiersprachen, Frameworks, Methoden — alles was dir einfällt."),
                language=language,
                phase='skills',
                collected=collected,
            )

        if extracted and (extracted.get('role') or extracted.get('company_name')):
            entry = _build_work_entry(
                role=extracted.get('role'),
                company_name=extracted.get('company_name'),
                duration_hint=extracted.get('duration_hint'),
                industry_hint=extracted.get('industry_hint'),
                responsibilities=extracted.get('responsibilities', []),
                conn=conn,
                lang=language,
            )
            collected.setdefault('work_history', []).append(entry)
            wh_count = len(collected['work_history'])
            _update_session(conn, session['session_id'], 'work_history', collected,
                            work_history_count=wh_count, turn_count=turn)
            _try_save(user_id, collected, conn)

            emp_raw = entry.get('employer_description')
            emp_de = _nominative_to_dative_de(emp_raw) if emp_raw else None
            emp_en = emp_raw or 'a company'
            emp_de = emp_de or 'einem Unternehmen'
            role_label = entry.get('role')

            if not role_label:
                # Got a company but no title — ask for clarification before noting
                return AdeleResponse(
                    reply=_reply(language,
                        f"I see you were at {emp_en} — what was your job title there?",
                        f"Du warst bei {emp_de} — wie war dein Jobtitel dort?"),
                    language=language,
                    phase='work_history',
                    collected=collected,
                )

            # Self-employed / no company case
            if not emp_raw:
                return AdeleResponse(
                    reply=_reply(language,
                        f"**{role_label}** — noted.\n\n"
                        f"And before that? Any earlier roles, or was that the start?",
                        f"**{role_label}** — notiert.\n\n"
                        f"Und davor? Gab es noch frühere Positionen, oder war das der Anfang?"),
                    language=language,
                    phase='work_history',
                    collected=collected,
                )

            return AdeleResponse(
                reply=_reply(language,
                    f"**{role_label}** at {emp_en} — noted.\n\n"
                    f"And before that? Any earlier roles, or was that the start?",
                    f"**{role_label}** bei {emp_de} — notiert.\n\n"
                    f"Und davor? Gab es noch frühere Positionen, oder war das der Anfang?"),
                language=language,
                phase='work_history',
                collected=collected,
            )

        # If they mentioned responsibilities for the LAST entry, append them
        if extracted and extracted.get('responsibilities'):
            wh = collected.get('work_history', [])
            if wh:
                wh[-1].setdefault('key_responsibilities', []).extend(
                    extracted['responsibilities']
                )
                _update_session(conn, session['session_id'], 'work_history', collected,
                                turn_count=turn)
                _try_save(user_id, collected, conn)
                return AdeleResponse(
                    reply=_reply(language,
                        "Got it — noted those details.\n\n"
                        "What was your previous role before that? "
                        "If this was your first job, just say so.",
                        "Gut, notiert!\n\n"
                        "Was war deine vorherige Position davor? "
                        "Wenn das dein erster Job war, sag einfach Bescheid."),
                    language=language,
                    phase='work_history',
                    collected=collected,
                )

        # If user is asking a question or offering to elaborate, respond conversationally
        if _detect_redirect(message):
            return AdeleResponse(
                reply=_reply(language,
                    "Of course! Go ahead — tell me about it.",
                    "Natürlich! Erzähl mir gerne davon."),
                language=language,
                phase='work_history',
            )
        return AdeleResponse(
            reply=_reply(language,
                "Could you tell me the job title and company for your previous role?",
                "Kannst du mir den Jobtitel und die Firma deiner vorherigen Stelle nennen?"),
            language=language,
            phase='work_history',
        )

    # ── SKILLS phase ──
    if phase == 'skills':
        extracted = await _extract(phase, message, collected)
        if extracted:
            # Merge all skill-like keys into 'skills'
            new_skills = set()
            for key in ('technical_skills', 'skills', 'tools', 'frameworks',
                        'methodologies', 'soft_skills', 'programming_languages'):
                vals = extracted.get(key)
                if vals and isinstance(vals, list):
                    new_skills.update(vals)
            existing_skills = set(collected.get('skills', []))
            collected.setdefault('skills', []).extend(
                sorted(new_skills - existing_skills)
            )

            # Spoken languages
            new_langs = set()
            for key in ('spoken_languages', 'languages'):
                vals = extracted.get(key)
                if vals and isinstance(vals, list):
                    new_langs.update(vals)
            existing_langs = set(collected.get('languages', []))
            collected.setdefault('languages', []).extend(
                sorted(new_langs - existing_langs)
            )

            # Certifications
            certs = extracted.get('certifications')
            if certs and isinstance(certs, list):
                existing_certs = set(collected.get('certifications', []))
                collected.setdefault('certifications', []).extend(
                    [c for c in certs if c not in existing_certs]
                )

        _update_session(conn, session['session_id'], 'education', collected,
                        turn_count=turn)
        _try_save(user_id, collected, conn)

        skills_str = ', '.join(collected.get('skills', [])) or 'none yet'
        return AdeleResponse(
            reply=_reply(language,
                f"Skills noted: **{skills_str}**\n\n"
                f"What about your **education**? Degree(s), field of study?",
                f"Skills notiert: **{skills_str}**\n\n"
                f"Wie sieht es mit deiner **Ausbildung** aus? Abschluss, Studienrichtung?"),
            language=language,
            phase='education',
            collected=collected,
        )

    # ── EDUCATION phase ──
    if phase == 'education':
        extracted = await _extract(phase, message, collected)
        if extracted and extracted.get('education'):
            collected['education'] = extracted['education']

        _update_session(conn, session['session_id'], 'preferences', collected,
                        turn_count=turn)
        _try_save(user_id, collected, conn)

        return AdeleResponse(
            reply=_reply(language,
                "Good. Last section — **what are you looking for?**\n\n"
                "Tell me about the kind of role, location, salary range, "
                "or industry you're interested in.",
                "Gut. Letzter Abschnitt — **was suchst du?**\n\n"
                "Erzähl mir von der Art von Rolle, Standort, Gehaltsvorstellung "
                "oder Branche, die dich interessiert."),
            language=language,
            phase='preferences',
            collected=collected,
        )

    # ── PREFERENCES phase ──
    if phase == 'preferences':
        extracted = await _extract(phase, message, collected)
        if extracted:
            prefs = {}
            for key in ('desired_roles', 'desired_locations', 'salary_min',
                        'salary_max', 'industries', 'remote_preference'):
                val = extracted.get(key)
                if val:
                    prefs[key] = val
            if prefs:
                collected['preferences'] = prefs

        # Generate summary
        summary_text = _format_summary(collected, language)

        # Build a short profile_summary string
        title = collected.get('current_title', '')
        skills = collected.get('skills', [])
        wh_count = len(collected.get('work_history', []))
        collected['profile_summary'] = (
            f"{title}. {wh_count} roles. Skills: {', '.join(skills[:10])}"
        ) if title else None

        _update_session(conn, session['session_id'], 'summary', collected,
                        turn_count=turn)

        return AdeleResponse(
            reply=_reply(language,
                f"Here's your profile:\n\n{summary_text}\n\n"
                f"Does this look right? Say **yes** to save, or tell me what to change.",
                f"Hier ist dein Profil:\n\n{summary_text}\n\n"
                f"Sieht das richtig aus? Sag **ja** um zu speichern, oder sag mir was ich ändern soll."),
            language=language,
            phase='summary',
            collected=collected,
        )

    # ── SUMMARY phase (confirm or edit) ──
    if phase == 'summary':
        if _detect_confirm(message):
            # Save to DB
            profile_id = save_profile(user_id, collected, conn)
            _complete_session(conn, session['session_id'])

            return AdeleResponse(
                reply=_reply(language,
                    "Profile saved! 🎉\n\n"
                    "Mira will start matching you with jobs right away. "
                    "You can always update your profile by coming back to chat with me.",
                    "Profil gespeichert! 🎉\n\n"
                    "Mira wird sofort anfangen, passende Stellen für dich zu finden. "
                    "Du kannst dein Profil jederzeit aktualisieren, indem du wieder mit mir sprichst."),
                language=language,
                phase='complete',
                collected=collected,
                actions={'adele': 'profile_saved', 'profile_id': profile_id}
            )
        else:
            # They want changes — let them describe, then re-show
            # For now, acknowledge and re-display
            return AdeleResponse(
                reply=_reply(language,
                    "What would you like to change? Tell me and I'll update it.\n\n"
                    "(You can also say **restart** to start over.)",
                    "Was möchtest du ändern? Sag es mir und ich aktualisiere es.\n\n"
                    "(Du kannst auch **nochmal** sagen, um von vorne zu beginnen.)"),
                language=language,
                phase='summary',
                collected=collected,
            )

    # ── COMPLETE phase — start new session ──
    if phase == 'complete':
        _reset_session(conn, user_id)
        session = get_session(user_id, conn)
        _update_session(conn, session['session_id'], 'current_role', {}, turn_count=1)
        return AdeleResponse(
            reply=_reply(language, _INTRO_EN, _INTRO_DE),
            language=language,
            phase='current_role',
            actions={'adele': 'new_session'}
        )

    # Fallback
    return AdeleResponse(
        reply=_reply(language,
            "I got a bit lost. Let's continue — what's your current job?",
            "Ich bin etwas durcheinander gekommen. Weiter — was ist dein aktueller Job?"),
        language=language,
        phase=phase,
    )


# ─────────────────────────────────────────────────────────
# Helper: extract data from message via LLM
# ─────────────────────────────────────────────────────────

async def _extract(phase: str, message: str, collected: dict) -> Optional[dict]:
    """Run LLM extraction for a phase."""
    prompt = _extract_prompt(phase, message, collected)
    if not prompt or prompt == "{}":
        return None
    raw = await _ask_llm_cascade(prompt)
    return _parse_json(raw)


# ─────────────────────────────────────────────────────────
# Helper: build work entry with company anonymization
# ─────────────────────────────────────────────────────────

def _build_work_entry(role: str, company_name: str, duration_hint: str,
                      industry_hint: str, responsibilities: list,
                      conn, lang: str) -> dict:
    """Build a work history entry, anonymizing the company name."""
    entry = {
        'role': role or None,  # None = not yet known; never display 'unknown role'
        'key_responsibilities': responsibilities or [],
    }

    # Anonymize company
    if company_name:
        desc = lookup_or_queue(conn, company_name, lang=lang)
        entry['employer_description'] = desc
    else:
        entry['employer_description'] = None  # self-employed / no employer

    # Duration
    duration = _parse_duration(duration_hint)
    if duration:
        entry['duration_years'] = duration

    # Industry
    if industry_hint:
        entry['industry'] = industry_hint

    return entry


# ─────────────────────────────────────────────────────────
# Helper: detect "no more jobs" signals
# ─────────────────────────────────────────────────────────

_NO_MORE_PATTERNS = re.compile(
    r'\b(?:'
    r'that\'?s\s*(?:all|it|everything)|no\s*more|nothing\s*(?:else|before)|'
    r'first\s*job|keine\s*(?:weiteren?|mehr)|das\s*war(?:\'?s|\s*alles)|'
    r'mein\s*erster|nichts\s*(?:davor|weiter)|nein|fertig|done|nope'
    r')\b',
    re.IGNORECASE
)

def _detect_no_more(message: str) -> bool:
    return bool(_NO_MORE_PATTERNS.search(message))


# ─────────────────────────────────────────────────────────
# Helper: detect confirmation
# ─────────────────────────────────────────────────────────

_CONFIRM_PATTERNS = re.compile(
    r'^(?:yes|ja|jap?|yep|yup|sure|ok|okay|passt|stimmt|richtig|correct|'
    r'looks?\s*good|sieht\s*gut\s*aus|save|speichern|genau|perfect|perfekt|'
    r'alles\s*richtig|that\'?s\s*(?:right|correct)|y|ja\s*passt|ja,?\s*passt|'
    r'passt\s*so|sieht\s*richtig\s*aus|looks?\s*correct|save\s*it|'
    r'ja,?\s*sieht\s*gut\s*aus|yes,?\s*save|ja,?\s*speichern|'
    r'yes,?\s*save\s*it|ja,?\s*save|yes,?\s*(?:please|bitte)|'
    r'(?:yes|ja|yep|sure),?\s*(?:looks?\s*good|passt|save\s*it|perfect|perfekt))\s*[.!]*$',
    re.IGNORECASE
)

def _detect_confirm(message: str) -> bool:
    return bool(_CONFIRM_PATTERNS.match(message.strip()))


# ─────────────────────────────────────────────────────────
# Intro messages
# ─────────────────────────────────────────────────────────

_INTRO_EN = (
    "Hi! I'm Adele, your interview coach. 🎯\n\n"
    "I'd like to help you build your professional profile through a quick conversation — "
    "no CV upload needed. I'll ask a few questions about your experience, skills, "
    "and what you're looking for. Company names will be automatically anonymized "
    "for your privacy.\n\n"
    "Let's start: **What's your current (or most recent) job title and company?**"
)

_INTRO_DE = (
    "Hi! Ich bin Adele, dein Interview-Coach. 🎯\n\n"
    "Ich würde gerne dein berufliches Profil durch ein kurzes Gespräch aufbauen — "
    "kein Lebenslauf-Upload nötig. Ich stelle dir ein paar Fragen zu deiner Erfahrung, "
    "deinen Fähigkeiten und was du suchst. Firmennamen werden automatisch anonymisiert "
    "für deinen Datenschutz.\n\n"
    "Fangen wir an: **Was ist dein aktueller (oder letzter) Jobtitel und bei welcher Firma?**"
)
