"""
CV Anonymizer — Two-pass extraction and anonymization of career data.

Core principle: "What we don't have, we can't leak."

Architecture (two-pass):
    Pass 1 — STRUCTURE: LLM splits CV into role blocks with dates, company,
             title, responsibilities. Small focused prompt, no anonymization.
    Pass 2 — ANONYMIZE + SKILLS: For each role, LLM generalizes company name
             and extracts skills/technologies from responsibilities.
    Final  — PII safety check validates the output.

The LLM runs locally (Ollama). Data never leaves our infrastructure.

Usage:
    from core.cv_anonymizer import extract_and_anonymize
    result = await extract_and_anonymize(cv_text, yogi_name="Phoenix")
"""
import asyncio
import datetime
import json
import os
import re
from typing import Optional, List

import httpx

from core.logging_config import get_logger
from core.pii_detector import PIIDetector

logger = get_logger(__name__)

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EXTRACTION_MODEL = "qwen2.5:7b"
FALLBACK_MODEL = "gemma3:4b"
TIMEOUT = 120.0        # per-call timeout — chunks are small so 120 s is generous
CALL_HARD_TIMEOUT = 150.0  # asyncio.wait_for wall-clock limit per LLM call
CHUNK_SIZE = 3500     # chars per CV chunk for Pass 1
PASS2_CONCURRENCY = 5 # max simultaneous Pass-2 LLM calls

# ─────────────────────────────────────────────────────────
# Company generalization templates
# ─────────────────────────────────────────────────────────

COMPANY_GENERALIZATION_EXAMPLES = """
Examples of company name generalization:
- "Deutsche Bank" → "a large German bank"
- "Goldman Sachs" → "a major US investment bank"
- "Novartis" → "one of the top 10 global pharmaceutical companies"
- "SAP" → "a leading enterprise software company"
- "Siemens" → "a large German industrial technology company"
- "Accenture" → "a major global consulting firm"
- "McKinsey" → "a top-tier management consulting firm"
- "BMW" → "a premium German automotive manufacturer"
- "Allianz" → "a leading European insurance group"
- "TCS" / "Infosys" → "a large Indian IT services company"
- "University Hospital Frankfurt" → "a university hospital"
- "INSEAD" → "(MBA)" — just keep the degree level
- "TU München" → "(M.Sc. Computer Science)" — just keep degree + field
- Small unknown companies → "a mid-size company in [industry]"
"""

# ─────────────────────────────────────────────────────────
# Pass 1 — Structure extraction prompt (format-agnostic)
# ─────────────────────────────────────────────────────────

STRUCTURE_PROMPT = """You are a CV parser. Extract the structure of this CV into JSON.

RULES:
- Extract EVERY role/position. Do NOT skip or merge any.
- Keep ALL dates exactly as written (years, months, "today"/"present"/"heute").
- Keep company names exactly as written.
- Keep role titles exactly as written.
- Extract bullet-point responsibilities as a list.
- If dates are missing, use null.
- "today", "present", "heute", "current", "ongoing" → "today" for end_year.

Return ONLY valid JSON, no explanation:
{{
  "person_name": "<full name if visible, or null>",
  "roles": [
    {{
      "company": "<company name exactly as written>",
      "title": "<role/job title exactly as written>",
      "start_year": <year as integer, e.g. 2020, or null>,
      "start_month": <month as integer 1-12, or null>,
      "end_year": <year as integer, or "today", or null>,
      "end_month": <month as integer 1-12, or null>,
      "location": "<city/country if mentioned, or null>",
      "responsibilities": ["bullet 1", "bullet 2", ...]
    }}
  ],
  "education": [
    {{
      "institution": "<school/university name>",
      "degree": "<degree type: bachelors/masters/phd/mba/diploma/ausbildung>",
      "field": "<field of study>",
      "year": <graduation year or null>
    }}
  ],
  "languages": ["language1", "language2"],
  "certifications": ["cert1", "cert2"]
}}

IMPORTANT: Extract ALL roles, even from very long CVs. Every position = one entry.

---
CV TEXT:
{cv_text}
---

JSON:"""

# ─────────────────────────────────────────────────────────
# Pass 2 — Per-role anonymization + skill extraction prompt
# ─────────────────────────────────────────────────────────

ROLE_ANONYMIZE_PROMPT = """Anonymize this role and extract skills from the responsibilities.

ROLE:
Company: {company}
Title: {title}
Responsibilities:
{responsibilities}

RULES:
1. Generalize the company name into a description (see examples below).
2. Extract specific skills, tools, technologies, methodologies from the responsibilities.
   Include: software tools, frameworks, standards, methodologies, platforms.
   Do NOT include generic verbs like "management" or "coordination" unless they are
   specific methodologies (e.g. "PRINCE2", "Scrum").
3. Do NOT include the company name itself as a skill. "SAP S/4HANA", "ServiceNow" etc. ARE skills.
4. Keep the role title exactly as-is.
5. Determine the industry category (e.g. "Banking", "Automotive", "IT Services", "Healthcare").

{company_examples}

Return ONLY valid JSON:
{{
  "employer_description": "<generalized company description>",
  "skills": ["skill1", "skill2", ...],
  "industry": "<industry category>"
}}

JSON:"""


# ─────────────────────────────────────────────────────────
# LLM call helpers
# ─────────────────────────────────────────────────────────

async def _call_llm(prompt: str, temperature: float = 0.1,
                    num_ctx: int = 16384) -> Optional[str]:
    """Try primary model, fall back to secondary.

    Uses asyncio.wait_for as a hard wall-clock guard so a slow Ollama
    response (which trickles bytes and resets the httpx read-timer) cannot
    hold up the background job indefinitely.
    """
    for model in [EXTRACTION_MODEL, FALLBACK_MODEL]:
        try:
            async def _do_call():
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    response = await client.post(
                        f"{OLLAMA_URL}/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": temperature, "num_ctx": num_ctx}
                        }
                    )
                    response.raise_for_status()
                    return response.json().get("response", "").strip()

            result = await asyncio.wait_for(_do_call(), timeout=CALL_HARD_TIMEOUT)
            if result:
                logger.info(f"LLM call succeeded with {model}")
                return result
        except asyncio.TimeoutError:
            logger.warning(f"LLM call timed out (>{CALL_HARD_TIMEOUT}s) with {model}")
            continue
        except Exception as e:
            logger.warning(f"LLM call failed with {model}: {e}")
            continue
    return None


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON object from LLM response text."""
    text = text.strip()
    if text.startswith('{'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _clean_cv_text(cv_text: str) -> str:
    """Clean HTML noise, MD formatting, table pipes from CV text."""
    cv_text = re.sub(r'<br\s*/?>', '\n', cv_text)
    cv_text = re.sub(r'<[^>]+>', '', cv_text)
    cv_text = re.sub(r'\|+', ' ', cv_text)
    cv_text = re.sub(r'#{2,}\s*', '', cv_text)
    cv_text = re.sub(r'[ \t]{2,}', ' ', cv_text)
    cv_text = re.sub(r'\n[ \t]+\n', '\n', cv_text)
    cv_text = re.sub(r'\n{3,}', '\n\n', cv_text)
    return cv_text.strip()


def _chunk_cv_text(cv_text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Split CV text into overlapping chunks at paragraph boundaries.

    Each chunk is at most *chunk_size* characters.  We always split at a blank
    line so we never cut a role entry in half.  A small overlap (the last two
    lines of the previous chunk) is prepended to each new chunk so that roles
    that span a boundary are still captured.
    """
    if len(cv_text) <= chunk_size:
        return [cv_text]

    paragraphs = re.split(r'\n{2,}', cv_text)
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    overlap_lines: List[str] = []  # last paragraph of previous chunk

    for para in paragraphs:
        para_len = len(para) + 2  # +2 for the \n\n separator
        if current_len + para_len > chunk_size and current:
            chunk_text = '\n\n'.join(current)
            chunks.append(chunk_text)
            # carry last paragraph as overlap into next chunk
            overlap_lines = current[-1:]
            current = overlap_lines[:]
            current_len = sum(len(p) + 2 for p in current)
        current.append(para)
        current_len += para_len

    if current:
        chunks.append('\n\n'.join(current))

    logger.info(f"CV chunked: {len(cv_text)} chars → {len(chunks)} chunks "
                f"(~{len(cv_text)//len(chunks)} chars each)")
    return chunks


# ─────────────────────────────────────────────────────────
# Date parsing helpers
# ─────────────────────────────────────────────────────────

def _parse_year(val) -> Optional[int]:
    """Parse a year value from LLM output."""
    if val is None:
        return None
    if isinstance(val, int) and 1950 <= val <= 2030:
        return val
    if isinstance(val, (str, float)):
        match = re.search(r'(19|20)\d{2}', str(val))
        if match:
            return int(match.group())
    return None


def _parse_month(val) -> Optional[int]:
    """Parse a month value from LLM output."""
    if val is None:
        return None
    try:
        m = int(val)
        return m if 1 <= m <= 12 else None
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────

async def extract_and_anonymize(
    cv_text: str,
    yogi_name: str,
    real_name: Optional[str] = None,
    conn=None
) -> dict:
    """
    Two-pass CV extraction and anonymization.

    Pass 1: Extract structure (roles, dates, companies, responsibilities)
    Pass 2: Per-role anonymization (generalize companies, extract skills)
    Final:  PII safety check

    Returns dict with anonymized career data including dates.
    """
    if not cv_text or not cv_text.strip():
        raise ValueError("Empty CV text")

    if not yogi_name or not yogi_name.strip():
        raise ValueError("yogi_name is required for anonymization")

    cv_text = _clean_cv_text(cv_text)
    cv_text = cv_text[:24000]  # hard cap — chunker handles the splitting

    logger.info(f"CV extraction: {len(cv_text)} chars, yogi_name={yogi_name}")

    # ── Pass 1: Chunked structure extraction ──────────────
    # Split the CV into small chunks so each LLM call is fast and reliable.
    # Results from all chunks are merged (de-duplicated by role title+company).
    chunks = _chunk_cv_text(cv_text)

    all_roles: List[dict] = []
    all_education: List[dict] = []
    all_languages: List[str] = []
    all_certs: List[str] = []
    detected_name: Optional[str] = None

    for chunk_idx, chunk in enumerate(chunks):
        prompt_1 = STRUCTURE_PROMPT.format(cv_text=chunk)
        raw_1 = await _call_llm(prompt_1, temperature=0.1)
        if not raw_1:
            logger.warning(f"Pass 1 chunk {chunk_idx+1}/{len(chunks)} failed — skipping")
            continue

        structure = _extract_json(raw_1)
        if not structure:
            logger.warning(f"Pass 1 chunk {chunk_idx+1} JSON parse failed — skipping")
            continue

        chunk_roles = structure.get('roles', []) or []
        all_roles.extend(r for r in chunk_roles if isinstance(r, dict))
        all_education.extend(e for e in (structure.get('education') or []) if isinstance(e, dict))
        all_languages.extend(structure.get('languages') or [])
        all_certs.extend(structure.get('certifications') or [])
        if not detected_name:
            detected_name = structure.get('person_name')

        logger.info(f"Pass 1 chunk {chunk_idx+1}/{len(chunks)}: "
                    f"+{len(chunk_roles)} roles (total so far: {len(all_roles)})")

    if not all_roles:
        raise ValueError("Pass 1 (structure extraction) failed with all models")

    # De-duplicate roles: same title+company = same role appearing in overlap
    seen_keys: set = set()
    roles: List[dict] = []
    for r in all_roles:
        key = (str(r.get('title', '')).strip().lower(),
               str(r.get('company', '')).strip().lower())
        if key not in seen_keys:
            seen_keys.add(key)
            roles.append(r)

    # De-dup education/languages/certs
    all_education = list({str(e.get('institution',''))+str(e.get('field','')): e
                          for e in all_education}.values())
    all_languages = sorted(set(str(l).strip() for l in all_languages if l))[:10]
    all_certs = sorted(set(str(c).strip() for c in all_certs if c))[:10]

    logger.info(f"Pass 1 total: {len(roles)} roles, "
                f"{len(all_education)} education, "
                f"{len(all_languages)} languages (from {len(chunks)} chunks)")

    # ── Pass 2: Per-role anonymization + skill extraction ─
    # Run all roles concurrently (capped at PASS2_CONCURRENCY in-flight at once)
    # to avoid sequential 6 s × N_roles delays.

    async def _process_role(i: int, role: dict):
        """Anonymize one role; returns (index, anonymized_dict)."""
        if not isinstance(role, dict):
            return i, None

        company = str(role.get('company', 'unknown'))
        title = str(role.get('title', 'unknown role'))
        resps = role.get('responsibilities', [])
        if not isinstance(resps, list):
            resps = [str(resps)] if resps else []

        employer_desc: Optional[str] = None
        industry: Optional[str] = None
        role_skills: List[str] = []

        # Company registry lookup (sync, but fast)
        if conn:
            try:
                from core.company_anonymizer import lookup_or_queue
                registry_desc = lookup_or_queue(conn, company, lang='en')
                if registry_desc:
                    employer_desc = registry_desc
            except Exception as e:
                logger.debug(f"Registry lookup failed for '{company}': {e}")

        resp_text = '\n'.join(f"- {r}" for r in resps[:8])
        role_prompt = ROLE_ANONYMIZE_PROMPT.format(
            company=company,
            title=title,
            responsibilities=resp_text or "(none listed)",
            company_examples=COMPANY_GENERALIZATION_EXAMPLES
        )

        role_result = await _call_llm(role_prompt, temperature=0.1, num_ctx=4096)
        if role_result:
            role_parsed = _extract_json(role_result)
            if role_parsed:
                if not employer_desc:
                    employer_desc = role_parsed.get('employer_description', 'a company')
                role_skills = role_parsed.get('skills', []) or []
                if not isinstance(role_skills, list):
                    role_skills = []
                industry = role_parsed.get('industry', '') or ''

        if not employer_desc:
            employer_desc = 'a company'

        # Date parsing
        start_year = _parse_year(role.get('start_year'))
        end_year_raw = role.get('end_year')
        is_current = False
        if isinstance(end_year_raw, str) and end_year_raw.lower() in (
            'today', 'present', 'heute', 'current', 'ongoing'
        ):
            is_current = True
            end_year = None
        else:
            end_year = _parse_year(end_year_raw)

        start_month = _parse_month(role.get('start_month'))
        end_month = _parse_month(role.get('end_month'))

        duration_years = None
        if start_year:
            end_y = end_year or datetime.date.today().year
            duration_years = max(1, end_y - start_year)

        logger.info(f"  Role {i+1}/{len(roles[:20])}: {title} → {employer_desc} "
                    f"({start_year or '?'}-{end_year or ('today' if is_current else '?')}) "
                    f"[{len(role_skills)} skills]")

        return i, {
            'employer_description': employer_desc,
            'role': title,
            'start_year': start_year,
            'start_month': start_month,
            'end_year': end_year,
            'end_month': end_month,
            'is_current': is_current,
            'duration_years': duration_years,
            'industry': industry or '',
            'key_responsibilities': [str(r) for r in resps[:5]],
            'technologies_used': [str(s) for s in role_skills][:10],
            '_skills': role_skills,  # kept for skill aggregation, removed later
        }

    # Semaphore limits concurrent Ollama calls so the GPU isn't overwhelmed
    sem = asyncio.Semaphore(PASS2_CONCURRENCY)

    async def _process_with_sem(i: int, role: dict):
        async with sem:
            return await _process_role(i, role)

    tasks = [_process_with_sem(i, role) for i, role in enumerate(roles[:20])]
    results_raw = await asyncio.gather(*tasks)

    # Reassemble in original order, collect skills
    all_skills: List[str] = []
    anonymized_roles: List[dict] = []
    for _i, anon in sorted(results_raw, key=lambda x: x[0]):
        if anon is None:
            continue
        role_skills = anon.pop('_skills', [])
        all_skills.extend(str(s).strip() for s in role_skills if s)
        anonymized_roles.append(anon)

    # Dedupe and sort skills
    all_skills = sorted(set(s for s in all_skills if s and len(s) > 1))

    # Languages and certifications merged from all chunks in Pass 1
    languages = all_languages
    certifications = all_certs

    # Calculate total years from date range
    years_experience = None
    if anonymized_roles:
        years_with_dates = [r for r in anonymized_roles if r.get('start_year')]
        if years_with_dates:
            earliest = min(r['start_year'] for r in years_with_dates)
            years_experience = datetime.date.today().year - earliest

    # Career level heuristic
    career_level = 'mid'
    if years_experience:
        if years_experience >= 20:
            career_level = 'executive'
        elif years_experience >= 12:
            career_level = 'lead'
        elif years_experience >= 6:
            career_level = 'senior'
        elif years_experience >= 2:
            career_level = 'mid'
        else:
            career_level = 'junior'

    # Current title = most recent role
    current_title = anonymized_roles[0].get('role') if anonymized_roles else None

    # Generate summary (rule-based, no LLM needed)
    summary = _build_summary(yogi_name, current_title, years_experience,
                             career_level, all_skills[:8], anonymized_roles)

    # Education merged from all chunks in Pass 1
    education = []
    for edu in all_education[:5]:
        if isinstance(edu, dict):
            education.append({
                'level': str(edu.get('degree', edu.get('level', 'unknown'))),
                'field': str(edu.get('field', '')),
                'duration_years': None,
            })

    # Assemble result
    result = {
        'yogi_name': yogi_name,
        'years_experience': years_experience,
        'career_level': career_level,
        'current_title': current_title,
        'skills': all_skills[:50],
        'languages': languages,
        'certifications': certifications,
        'work_history': anonymized_roles,
        'education': education,
        'profile_summary': summary,
    }

    # ── PII safety check ─────────────────────────────────
    result = _run_pii_check(result, yogi_name, detected_name or real_name, conn)

    logger.info(f"CV anonymized: {len(result['skills'])} skills, "
                f"{len(result['work_history'])} roles, "
                f"dates={'yes' if any(r.get('start_year') for r in result['work_history']) else 'no'}")

    return result


# ─────────────────────────────────────────────────────────
# Summary builder
# ─────────────────────────────────────────────────────────

def _build_summary(yogi_name: str, current_title: Optional[str],
                   years_exp: Optional[int], career_level: str,
                   top_skills: List[str], roles: List[dict]) -> str:
    """Build a professional summary from extracted data (no LLM needed)."""
    parts = [f"{yogi_name} is"]

    if career_level in ('executive', 'lead'):
        parts.append("a highly experienced")
    elif career_level == 'senior':
        parts.append("an experienced")
    else:
        parts.append("a")

    if current_title:
        parts.append(f"professional, most recently serving as {current_title}.")
    else:
        parts.append("professional.")

    if years_exp:
        parts.append(f"With {years_exp}+ years of experience")
    else:
        parts.append("With extensive experience")

    # Industries from roles
    industries = sorted(set(r.get('industry', '') for r in roles if r.get('industry')))
    if industries:
        parts.append(f"spanning {', '.join(industries[:3])},")
    else:
        parts[-1] += ','

    if top_skills:
        parts.append(f"core competencies include {', '.join(top_skills[:6])}.")
    else:
        parts.append("bringing broad domain expertise.")

    return ' '.join(parts)


# ─────────────────────────────────────────────────────────
# PII safety check
# ─────────────────────────────────────────────────────────

def _run_pii_check(result: dict, yogi_name: str,
                   real_name: Optional[str], conn) -> dict:
    """Run PII safety check and scrub violations."""
    detector = PIIDetector(conn)

    extra_names = []
    if real_name:
        extra_names = [n for n in real_name.split() if len(n) > 2]
        extra_names.append(real_name)

    # Skills/certs: only check name/email/phone (SAP etc. are valid skill names)
    skills_text = ' '.join(
        result.get('skills', []) +
        result.get('certifications', []) +
        result.get('languages', [])
    )
    skills_violations = detector.check(skills_text, extra_names=extra_names, skip_companies=True)

    # Everything else: full PII check
    sensitive = {k: v for k, v in result.items() if k not in ('skills', 'certifications', 'languages')}
    sensitive_text = _flatten_to_text(sensitive)
    sensitive_violations = detector.check(sensitive_text, extra_names=extra_names)

    violations = skills_violations + sensitive_violations

    if violations:
        logger.warning(f"PII detected in anonymized output: {violations}")

        company_violations = [v for v in violations if v.startswith('[company]')]
        other_violations = [v for v in violations if not v.startswith('[company]')]

        if other_violations:
            result = _scrub_violations(result, other_violations)

        if company_violations:
            protected = {k: result[k] for k in ('skills', 'certifications', 'languages') if k in result}
            result = _scrub_violations(result, company_violations)
            result.update(protected)

        # Re-check
        all_text = _flatten_to_text(result)
        remaining = detector.check(all_text, extra_names=extra_names, skip_companies=True)
        sensitive = {k: v for k, v in result.items() if k not in ('skills', 'certifications', 'languages')}
        remaining += detector.check(_flatten_to_text(sensitive), extra_names=extra_names)
        if remaining:
            logger.error(f"PII still present after scrub: {remaining}")
            raise ValueError(f"Anonymization failed safety check: {remaining}")

    return result


def _flatten_to_text(data: dict) -> str:
    """Flatten all string values to a single text for PII checking."""
    parts = []

    def _recurse(obj):
        if isinstance(obj, str):
            parts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _recurse(v)
        elif isinstance(obj, list):
            for item in obj:
                _recurse(item)

    _recurse(data)
    return ' '.join(parts)


def _scrub_violations(data: dict, violations: list) -> dict:
    """Remove detected PII from anonymized data (last-resort cleanup)."""
    pii_strings = []
    for v in violations:
        match = re.match(r'\[.+?\]\s*(.+)', v)
        if match:
            pii_strings.append(match.group(1).strip())
    if not pii_strings:
        return data

    def _clean(obj):
        if isinstance(obj, str):
            result = obj
            for pii in pii_strings:
                if pii.lower() in result.lower():
                    result = re.sub(re.escape(pii), '[REDACTED]', result, flags=re.IGNORECASE)
            return result
        elif isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_clean(item) for item in obj]
        return obj

    return _clean(data)
