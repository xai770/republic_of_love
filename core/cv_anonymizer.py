"""
CV Anonymizer — Extract and anonymize career data from CV text.

Core principle: "What we don't have, we can't leak."

Flow:
    1. LLM extracts structured data (skills, roles, companies, education)
    2. LLM anonymizes: real name → yogi_name, companies → generalized
    3. PII detector validates: no emails, phones, real names, company names
    4. Only anonymized JSON is returned — raw text never stored

The LLM runs locally (Ollama). Data never leaves our infrastructure.

Usage:
    from core.cv_anonymizer import extract_and_anonymize
    result = await extract_and_anonymize(cv_text, yogi_name="xai")
"""
import json
import os
import re
from typing import Optional

import httpx

from core.logging_config import get_logger
from core.pii_detector import PIIDetector

logger = get_logger(__name__)

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EXTRACTION_MODEL = "qwen2.5:7b"  # Better at structured extraction
TIMEOUT = 90.0  # CV extraction takes longer

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
# The extraction + anonymization prompt (single-pass)
# ─────────────────────────────────────────────────────────

ANONYMIZE_PROMPT = """You are a career data extractor and anonymizer. Your task has TWO parts:

PART 1 — EXTRACT all career information from the CV text.
PART 2 — ANONYMIZE the output by removing all identifying details.

RULES FOR ANONYMIZATION:
- Replace the person's real name with: "{yogi_name}"
- Replace ALL company names with generalized descriptions IN EMPLOYER CONTEXT (see examples below)
- KEEP company names when they appear as technology/product names in skills or certifications
  (e.g., "SAP S/4HANA" stays as "SAP S/4HANA", "SAP Certified" stays as "SAP Certified",
   "AWS Solutions Architect" stays as-is, "Microsoft Azure" stays as-is)
- In work_history employer_description: ALWAYS generalize the company name
- In work_history key_responsibilities: replace company names of CLIENTS/PARTNERS with generalized descriptions
- Replace ALL school/university names with just the degree level and field
- Remove ALL dates — convert to durations where useful (e.g., "4 years")
- Remove ALL contact info (email, phone, address, LinkedIn)
- Remove ALL personal identifiers
- Keep role titles exactly as they are (e.g., "Senior Project Manager" stays)
- Keep: skills, technologies, certifications (by name), languages, role types, industries

{company_examples}

OUTPUT FORMAT — return ONLY valid JSON, no markdown, no explanation:
{{
  "yogi_name": "{yogi_name}",
  "years_experience": <number>,
  "career_level": "<junior|mid|senior|lead|executive>",
  "current_title": "<most recent role title only, e.g. 'Senior Project Manager' — NO company name here>",
  "skills": ["skill1", "skill2", ...],
  "languages": ["language1", "language2", ...],
  "certifications": ["cert1", "cert2", ...],
  "work_history": [
    {{
      "employer_description": "<generalized company description>",
      "role": "<role title only, e.g. 'Senior Project Manager' — NO company name here>",
      "duration_years": <number>,
      "industry": "<industry category>",
      "key_responsibilities": ["resp1", "resp2"]
    }}
  ],
  "education": [
    {{
      "level": "<bachelors|masters|phd|mba|diploma|ausbildung>",
      "field": "<field of study>",
      "duration_years": <number or null>
    }}
  ],
  "profile_summary": "<2-3 sentence professional summary using yogi_name, no company names>"
}}

CRITICAL: If you are unsure whether something is PII, REMOVE IT. Better to lose data than to leak identity.

---
CV TEXT:
{cv_text}
---

Anonymized JSON:"""


async def extract_and_anonymize(
    cv_text: str,
    yogi_name: str,
    real_name: Optional[str] = None,
    conn=None
) -> dict:
    """
    Extract career data from CV text and anonymize it.
    
    Args:
        cv_text: Raw text extracted from PDF/DOCX (in memory, never stored)
        yogi_name: The yogi's chosen name (replaces real name)
        real_name: If known, the real name to specifically watch for in PII check
        conn: DB connection for PII detector company corpus
    
    Returns:
        dict with anonymized structured career data
    
    Raises:
        ValueError: If extraction fails or PII is detected after anonymization
    """
    if not cv_text or not cv_text.strip():
        raise ValueError("Empty CV text")
    
    if not yogi_name or not yogi_name.strip():
        raise ValueError("yogi_name is required for anonymization")
    
    # Truncate to reasonable size (LLM context budget)
    cv_text = cv_text[:12000]
    
    prompt = ANONYMIZE_PROMPT.format(
        yogi_name=yogi_name,
        company_examples=COMPANY_GENERALIZATION_EXAMPLES,
        cv_text=cv_text
    )
    
    logger.info(f"CV anonymization: {len(cv_text)} chars, yogi_name={yogi_name}")
    
    # Call LLM
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": EXTRACTION_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": 8192}
                }
            )
            response.raise_for_status()
            result = response.json().get("response", "")
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        raise ValueError(f"LLM extraction failed: {e}")
    
    # Parse JSON from response
    parsed = _extract_json(result)
    if not parsed:
        logger.error(f"Failed to parse JSON from LLM response: {result[:200]}")
        raise ValueError("LLM returned invalid JSON — extraction failed")
    
    # Validate structure
    parsed = _validate_and_normalize(parsed, yogi_name)
    
    # PII safety check
    detector = PIIDetector(conn)
    
    extra_names = []
    if real_name:
        # Split "Firstname Lastname" into parts to catch partial matches too
        extra_names = [n for n in real_name.split() if len(n) > 2]
        extra_names.append(real_name)
    
    # Split PII check: company names are expected in skills/certifications
    # (e.g. "SAP S/4HANA" is a skill, not a PII leak)
    # So we check employer-sensitive fields fully, and skip company check for skills/certs
    skills_certs_text = ' '.join(
        parsed.get('skills', []) +
        parsed.get('certifications', []) +
        parsed.get('languages', [])
    )
    # For skills: only check name/email/phone (not company names)
    skills_violations = detector.check(skills_certs_text, extra_names=extra_names, skip_companies=True)
    
    # For everything else: full PII check including companies
    sensitive_fields = {k: v for k, v in parsed.items() if k not in ('skills', 'certifications', 'languages')}
    sensitive_text = _flatten_to_text(sensitive_fields)
    sensitive_violations = detector.check(sensitive_text, extra_names=extra_names)
    
    violations = skills_violations + sensitive_violations
    
    if violations:
        logger.warning(f"PII detected in anonymized output: {violations}")
        
        # Split violations: company violations only apply to non-skill fields
        company_violations = [v for v in violations if v.startswith('[company]')]
        other_violations = [v for v in violations if not v.startswith('[company]')]
        
        # Scrub non-company violations everywhere
        if other_violations:
            parsed = _scrub_violations(parsed, other_violations)
        
        # Scrub company violations only in sensitive fields (not skills/certs/languages)
        if company_violations:
            protected_keys = ('skills', 'certifications', 'languages')
            protected = {k: parsed[k] for k in protected_keys if k in parsed}
            parsed = _scrub_violations(parsed, company_violations)
            # Restore protected fields
            parsed.update(protected)
        
        # Re-check (light check — just name/email/phone on everything)
        all_text = _flatten_to_text(parsed)
        remaining = detector.check(all_text, extra_names=extra_names, skip_companies=True)
        # Also re-check sensitive fields for companies
        sensitive_fields = {k: v for k, v in parsed.items() if k not in ('skills', 'certifications', 'languages')}
        remaining += detector.check(_flatten_to_text(sensitive_fields), extra_names=extra_names)
        if remaining:
            logger.error(f"PII still present after scrub: {remaining}")
            raise ValueError(f"Anonymization failed safety check: {remaining}")
    
    logger.info(f"CV anonymized: {len(parsed.get('skills', []))} skills, "
                f"{len(parsed.get('work_history', []))} roles")
    
    return parsed


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON object from LLM response text."""
    # Try direct parse first
    text = text.strip()
    if text.startswith('{'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # Find JSON block in response
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    # Try removing markdown code fences
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    return None


def _validate_and_normalize(data: dict, yogi_name: str) -> dict:
    """Ensure the parsed data has the expected structure."""
    result = {
        'yogi_name': yogi_name,
        'years_experience': data.get('years_experience'),
        'career_level': data.get('career_level', 'mid'),
        'current_title': data.get('current_title'),
        'skills': [],
        'languages': [],
        'certifications': [],
        'work_history': [],
        'education': [],
        'profile_summary': data.get('profile_summary', ''),
    }
    
    # Skills
    skills = data.get('skills', [])
    if isinstance(skills, list):
        result['skills'] = [str(s).strip() for s in skills if s][:30]
    
    # Languages
    langs = data.get('languages', [])
    if isinstance(langs, list):
        result['languages'] = [str(l).strip() for l in langs if l][:10]
    
    # Certifications
    certs = data.get('certifications', [])
    if isinstance(certs, list):
        result['certifications'] = [str(c).strip() for c in certs if c][:10]
    
    # Work history
    wh = data.get('work_history', [])
    if isinstance(wh, list):
        for entry in wh[:15]:  # Cap at 15 roles
            if isinstance(entry, dict):
                result['work_history'].append({
                    'employer_description': str(entry.get('employer_description', 'a company')),
                    'role': str(entry.get('role', 'unknown role')),
                    'duration_years': entry.get('duration_years'),
                    'industry': str(entry.get('industry', '')),
                    'key_responsibilities': [str(r) for r in entry.get('key_responsibilities', [])][:5],
                })
    
    # Education
    edu = data.get('education', [])
    if isinstance(edu, list):
        for entry in edu[:5]:
            if isinstance(entry, dict):
                result['education'].append({
                    'level': str(entry.get('level', 'unknown')),
                    'field': str(entry.get('field', '')),
                    'duration_years': entry.get('duration_years'),
                })
    
    # Years experience: sanity check
    yrs = result['years_experience']
    if isinstance(yrs, (int, float)) and 0 <= yrs <= 60:
        result['years_experience'] = int(yrs)
    else:
        result['years_experience'] = None
    
    # Career level: normalize
    valid_levels = {'junior', 'mid', 'senior', 'lead', 'executive', 'entry'}
    if result['career_level'] not in valid_levels:
        result['career_level'] = 'mid'
    
    return result


def _flatten_to_text(data: dict) -> str:
    """Flatten all string values in a dict to a single text for PII checking."""
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
    """
    Attempt to remove detected PII from the anonymized data.
    This is a last-resort cleanup for when the LLM missed something.
    """
    # Extract the actual PII strings from violations
    pii_strings = []
    for v in violations:
        # Violations look like: "[type] actual_text"
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
