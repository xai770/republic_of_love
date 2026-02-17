"""
Company anonymization pipeline — Doug researches, verifier audits.

This module handles the background pipeline for company name anonymization:
1. Doug searches DDG for company info (size, industry, geography)
2. LLM #1 generates anonymized descriptions (EN + DE)
3. LLM #2 (verifier) checks: does it identify the company? Are EN/DE equivalent?
4. Store in company_aliases if verified

The inline anonymizer (cv_anonymizer.py) generates a temp description immediately.
This pipeline upgrades it to a researched, verified, bilingual description.

Usage:
    # Single company:
    python3 core/company_anonymizer.py "Autohaus Kurz"

    # Batch — process all unverified entries:
    python3 core/company_anonymizer.py --batch 20

    # From code:
    from core.company_anonymizer import anonymize_company, lookup_company
    desc = lookup_company(conn, "Deutsche Bank", lang="en")
"""
import argparse
import json
import re
import subprocess
import time
from typing import Optional, Dict, Tuple

import requests

from core.database import get_connection_raw, return_connection
from core.logging_config import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────
from config.settings import OLLAMA_GENERATE_URL as OLLAMA_URL
RESEARCH_MODEL = "qwen2.5:7b"   # Doug's research LLM
VERIFIER_MODEL = "qwen2.5:7b"   # Different prompt, same model for now
TIMEOUT = 60.0

# ─────────────────────────────────────────────────────────
# Lookup — the fast path used by cv_anonymizer
# ─────────────────────────────────────────────────────────

def lookup_company(conn, company_name: str, lang: str = "en") -> Optional[str]:
    """
    Look up a company in the registry.

    Checks both company_aliases.company_pattern and company_alias_variants.variant.
    Returns the anonymized description in the requested language, or None on miss.

    Args:
        conn: DB connection
        company_name: Raw company name from CV (e.g. "Deutsche Bank AG")
        lang: "en" or "de"

    Returns:
        Anonymized description string, or None if not in registry
    """
    if not company_name or not company_name.strip():
        return None

    col = "anonymized_de" if lang == "de" else "anonymized_en"
    pattern = company_name.strip().lower()

    try:
        with conn.cursor() as cur:
            # Check main pattern first
            cur.execute(f"""
                SELECT {col}
                FROM company_aliases
                WHERE LOWER(company_pattern) = %s
                LIMIT 1
            """, (pattern,))
            row = cur.fetchone()
            if row:
                val = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
                return val

            # Check variants
            cur.execute(f"""
                SELECT a.{col}
                FROM company_alias_variants v
                JOIN company_aliases a ON a.alias_id = v.alias_id
                WHERE LOWER(v.variant) = %s
                LIMIT 1
            """, (pattern,))
            row = cur.fetchone()
            if row:
                val = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
                return val

    except Exception as e:
        logger.warning(f"Company lookup failed for '{company_name}': {e}")

    return None


def lookup_or_queue(conn, company_name: str, lang: str = "en") -> str:
    """
    Look up company. If miss, create an unverified inline entry and return it.

    This is the main entry point used by the CV anonymizer.
    A miss triggers:
    1. Immediate: LLM generates temp description (returned instantly)
    2. Background: Doug can later research + verify + upgrade it

    Args:
        conn: DB connection
        company_name: Raw company name
        lang: "en" or "de"

    Returns:
        Anonymized description (may be unverified if newly generated)
    """
    # Fast path: registry hit
    desc = lookup_company(conn, company_name, lang=lang)
    if desc:
        return desc

    # Slow path: generate inline
    result = _generate_inline(company_name)
    if not result:
        # Fallback: generic description
        if lang == "de":
            return "ein Unternehmen"
        return "a company"

    # Sanitize before storing
    result['en'] = _sanitize_description(result.get('en', 'a company'))
    result['de'] = _sanitize_description(result.get('de', 'ein Unternehmen'))

    # Store for future lookups
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO company_aliases
                    (company_pattern, anonymized_en, anonymized_de, industry, source, verified)
                VALUES (LOWER(%s), %s, %s, %s, 'llm_inline', FALSE)
                ON CONFLICT (LOWER(company_pattern)) DO NOTHING
                RETURNING alias_id
            """, (
                company_name.strip(),
                result['en'],
                result['de'],
                result.get('industry'),
            ))
            conn.commit()
            row = cur.fetchone()
            if row:
                logger.info(f"New company alias (inline): '{company_name}' → '{result.get('en')}'")
    except Exception as e:
        logger.warning(f"Failed to store inline alias for '{company_name}': {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    return result['en' if lang == 'en' else 'de']


# ─────────────────────────────────────────────────────────
# Inline generation — fast, uses only the company name
# ─────────────────────────────────────────────────────────

_INLINE_PROMPT = """You are a privacy expert. Given a company name, generate a SHORT anonymized description.

RULES:
1. The description must NOT identify the specific company
2. At least 3 real companies should plausibly match your description
3. Write ONE SHORT PHRASE (5-10 words), not a sentence or paragraph
4. Include: size (large/mid-size/small), geography if known, industry
5. Do NOT use the company's actual name or any unique identifiers
6. Generate in BOTH English and German (same meaning)

EXAMPLES:
- "Deutsche Bank" → EN: "a large German bank" / DE: "eine große deutsche Bank"
- "Autohaus Kurz" → EN: "a mid-size car dealership" / DE: "ein mittelständisches Autohaus"
- "SAP" → EN: "a leading enterprise software company" / DE: "ein führendes Unternehmen für Unternehmenssoftware"
- "Bäckerei Schmidt" → EN: "a local bakery" / DE: "eine lokale Bäckerei"
- "Müller GmbH" → EN: "a mid-size German company" / DE: "ein mittelständisches deutsches Unternehmen"

Company name: {company_name}

Return ONLY valid JSON:
{{"en": "short phrase", "de": "kurze Beschreibung", "industry": "..."}}"""


def _generate_inline(company_name: str) -> Optional[dict]:
    """Generate a quick anonymized description using just the company name."""
    prompt = _INLINE_PROMPT.format(company_name=company_name)

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                'model': RESEARCH_MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3, 'num_predict': 200}
            },
            timeout=TIMEOUT
        )
        if resp.status_code != 200:
            logger.error(f"Inline LLM error: {resp.status_code}")
            return None

        text = resp.json().get('response', '')
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        return _parse_json(text)

    except Exception as e:
        logger.error(f"Inline generation failed for '{company_name}': {e}")
        return None


# ─────────────────────────────────────────────────────────
# Doug's research — the thorough path
# ─────────────────────────────────────────────────────────

def _search_ddg(query: str) -> str:
    """Search DuckDuckGo via ddgr."""
    try:
        result = subprocess.run(
            ['ddgr', '--json', '--num', '5', query],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout:
            items = json.loads(result.stdout)
            lines = []
            for item in items[:5]:
                title = item.get('title', '')
                abstract = item.get('abstract', '')
                lines.append(f"- {title}: {abstract}")
            return '\n'.join(lines)
    except Exception as e:
        logger.warning(f"DDG search failed: {e}")
    return ""


_RESEARCH_PROMPT = """You are Doug, a company research assistant.
Given a company name and web search results, create a SHORT anonymized description.

RESEARCH CONTEXT:
{search_results}

RULES:
1. The description must NOT identify the specific company
2. At least 3 real companies should plausibly match your description
3. The description must be ONE SHORT PHRASE (5-10 words max), like these examples:
   - "a large German bank"
   - "a mid-size car dealership in southern Germany"
   - "a leading enterprise software company"
   - "a local bakery"
   - "a mid-size logistics company"
   - "a regional healthcare provider"
4. Generate BOTH English and German (same meaning, short phrase)
5. Do NOT write sentences or paragraphs. Just a short descriptor.

Company: {company_name}

Return ONLY valid JSON:
{{
  "en": "short anonymized phrase in English (5-10 words)",
  "de": "kurze anonymisierte Beschreibung auf Deutsch (5-10 Wörter)",
  "industry": "industry sector",
  "size_hint": "large|mid-size|small|startup",
  "country": "ISO 2-letter country code",
  "research_notes": "brief summary of what you found about this company (2-3 sentences)"
}}"""


def research_company(company_name: str) -> Optional[dict]:
    """
    Doug researches a company via DDG and generates an anonymized description.

    Returns dict with: en, de, industry, size_hint, country, research_notes
    """
    logger.info(f"Doug researching company: '{company_name}'")

    # Search 1: General company info
    search1 = _search_ddg(f"{company_name} company industry employees")
    time.sleep(1)

    # Search 2: Company size and location
    search2 = _search_ddg(f"{company_name} headquarter revenue size")
    time.sleep(1)

    combined = f"Search 1 (general):\n{search1}\n\nSearch 2 (size/location):\n{search2}"

    if not search1 and not search2:
        logger.warning(f"No search results for '{company_name}' — using inline generation")
        return _generate_inline(company_name)

    prompt = _RESEARCH_PROMPT.format(
        company_name=company_name,
        search_results=combined
    )

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                'model': RESEARCH_MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3, 'num_predict': 400}
            },
            timeout=TIMEOUT
        )
        if resp.status_code != 200:
            logger.error(f"Research LLM error: {resp.status_code}")
            return None

        text = resp.json().get('response', '')
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        return _parse_json(text)

    except Exception as e:
        logger.error(f"Research generation failed for '{company_name}': {e}")
        return None


# ─────────────────────────────────────────────────────────
# Verifier — different prompt, acts as privacy auditor
# ─────────────────────────────────────────────────────────

_VERIFIER_PROMPT = """You are a strict privacy auditor for a job platform.
Your job: check whether an anonymized company description is safe to use.

REAL COMPANY NAME: {company_name}
PROPOSED ENGLISH: {desc_en}
PROPOSED GERMAN: {desc_de}
RESEARCH NOTES: {research_notes}

RULES FOR DESCRIPTIONS:
- Must be a SHORT PHRASE (5-10 words), not a sentence
- Must NOT contain specific numbers (employees, revenue, ranking)
- Must NOT contain city names, founding years, or unique facts
- At least 3 real companies must plausibly match the description
- Examples of GOOD: "a large German discount retailer", "a mid-size IT consultancy"
- Examples of BAD: "global chain with 375,000 employees in 30 countries" (too specific)

Check these criteria:
1. IDENTIFICATION: Could a reader identify the SPECIFIC company from the description alone?
   (If only 1-2 companies worldwide match → REJECT)
2. LENGTH: Is it a short phrase (5-10 words)? If it's a full sentence → REJECT
3. NUMBERS: Does it contain specific numbers? → REJECT
4. EQUIVALENCE: Are the EN and DE descriptions semantically equivalent?
5. SPECIFICITY: Is it specific enough to be useful? ("a company" is too vague)

Return ONLY valid JSON:
{{
  "approved": true or false,
  "identification_risk": "none|low|medium|high",
  "length_ok": true or false,
  "numbers_ok": true or false,
  "equivalence_ok": true or false,
  "specificity_ok": true or false,
  "reason": "brief explanation",
  "suggestion_en": "improved SHORT EN phrase if not approved, otherwise null",
  "suggestion_de": "improved SHORT DE phrase if not approved, otherwise null"
}}"""


def verify_description(
    company_name: str,
    desc_en: str,
    desc_de: str,
    research_notes: str = ""
) -> dict:
    """
    Privacy auditor checks if a description is safe to use.

    Returns dict with: approved, identification_risk, reason, suggestions
    """
    prompt = _VERIFIER_PROMPT.format(
        company_name=company_name,
        desc_en=desc_en,
        desc_de=desc_de,
        research_notes=research_notes or "No research available"
    )

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                'model': VERIFIER_MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.1, 'num_predict': 300}
            },
            timeout=TIMEOUT
        )
        if resp.status_code != 200:
            logger.error(f"Verifier LLM error: {resp.status_code}")
            return {'approved': False, 'reason': f'LLM error: {resp.status_code}'}

        text = resp.json().get('response', '')
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        result = _parse_json(text)

        if result:
            return result

        return {'approved': False, 'reason': 'Failed to parse verifier response'}

    except Exception as e:
        logger.error(f"Verification failed for '{company_name}': {e}")
        return {'approved': False, 'reason': str(e)}


# ─────────────────────────────────────────────────────────
# Full pipeline: research + verify + store
# ─────────────────────────────────────────────────────────

def anonymize_company(conn, company_name: str) -> Tuple[str, str]:
    """
    Full pipeline: Doug researches, verifier audits, store if approved.

    Returns: (desc_en, desc_de)
    """
    # Check registry first
    existing_en = lookup_company(conn, company_name, lang="en")
    existing_de = lookup_company(conn, company_name, lang="de")
    if existing_en and existing_de:
        return existing_en, existing_de

    # Doug researches
    research = research_company(company_name)
    if not research:
        return "a company", "ein Unternehmen"

    desc_en = _sanitize_description(research.get('en', 'a company'))
    desc_de = _sanitize_description(research.get('de', 'ein Unternehmen'))
    industry = research.get('industry')
    size_hint = research.get('size_hint')
    country = research.get('country')
    research_notes = research.get('research_notes', '')

    # Verifier checks
    verification = verify_description(company_name, desc_en, desc_de, research_notes)

    approved = verification.get('approved', False)

    if not approved:
        # Use verifier's suggestions if available
        if verification.get('suggestion_en'):
            desc_en = _sanitize_description(verification['suggestion_en'])
        if verification.get('suggestion_de'):
            desc_de = _sanitize_description(verification['suggestion_de'])

        # Re-verify with suggestions
        if verification.get('suggestion_en') or verification.get('suggestion_de'):
            re_check = verify_description(company_name, desc_en, desc_de, research_notes)
            approved = re_check.get('approved', False)

        if not approved:
            logger.warning(
                f"Company '{company_name}' not verified: {verification.get('reason')}. "
                f"Storing as unverified."
            )

    # Store
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO company_aliases
                    (company_pattern, anonymized_en, anonymized_de, industry,
                     size_hint, country, verified, verified_at, source, research_notes)
                VALUES (LOWER(%s), %s, %s, %s, %s, %s, %s, CASE WHEN %s THEN NOW() ELSE NULL END, 'doug', %s)
                ON CONFLICT (LOWER(company_pattern))
                DO UPDATE SET
                    anonymized_en = EXCLUDED.anonymized_en,
                    anonymized_de = EXCLUDED.anonymized_de,
                    industry = COALESCE(EXCLUDED.industry, company_aliases.industry),
                    size_hint = COALESCE(EXCLUDED.size_hint, company_aliases.size_hint),
                    country = COALESCE(EXCLUDED.country, company_aliases.country),
                    verified = EXCLUDED.verified,
                    verified_at = CASE WHEN EXCLUDED.verified THEN NOW() ELSE company_aliases.verified_at END,
                    source = 'doug',
                    research_notes = EXCLUDED.research_notes,
                    updated_at = NOW()
            """, (
                company_name.strip(),
                desc_en, desc_de, industry,
                size_hint, country,
                approved, approved,
                research_notes
            ))
            conn.commit()
            status = "verified" if approved else "unverified"
            logger.info(f"Stored ({status}): '{company_name}' → EN: '{desc_en}' / DE: '{desc_de}'")
    except Exception as e:
        logger.error(f"Failed to store alias for '{company_name}': {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    return desc_en, desc_de


def process_unverified_batch(conn, limit: int = 20) -> dict:
    """
    Process unverified company_aliases entries: re-research and verify.

    Returns stats dict.
    """
    stats = {'processed': 0, 'verified': 0, 'failed': 0}

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alias_id, company_pattern, anonymized_en, anonymized_de
                FROM company_aliases
                WHERE verified = FALSE
                ORDER BY created_at ASC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()

        for row in rows:
            if isinstance(row, dict):
                alias_id = row['alias_id']
                pattern = row['company_pattern']
            else:
                alias_id, pattern = row[0], row[1]

            stats['processed'] += 1
            en, de = anonymize_company(conn, pattern)

            # Check if it got verified
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT verified FROM company_aliases WHERE alias_id = %s",
                    (alias_id,)
                )
                check = cur.fetchone()
                if check:
                    v = check[0] if isinstance(check, (list, tuple)) else check.get('verified', False)
                    if v:
                        stats['verified'] += 1
                    else:
                        stats['failed'] += 1

            time.sleep(2)  # Rate limit

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")

    return stats


# ─────────────────────────────────────────────────────────
# Utils
# ─────────────────────────────────────────────────────────

def _sanitize_description(desc: str) -> str:
    """Strip specific numbers, trim to short phrase."""
    if not desc:
        return desc
    # Remove specific numbers (e.g., "375,000 employees", "in 30 countries")
    desc = re.sub(r'\b\d[\d,\.]*\s*(?:employees|Mitarbeiter|countries|Länder|locations|Standorte|stores|Filialen|branches|years?|Jahre?)\b', '', desc, flags=re.IGNORECASE)
    # Remove dangling "with over" / "mit über" / "operating in more than"
    desc = re.sub(r'\s+(?:with|mit)\s+(?:over|über|more than|mehr als)\s*$', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+(?:operating|tätig)\s+in\s*$', '', desc, flags=re.IGNORECASE)
    # Clean up double spaces
    desc = re.sub(r'\s+', ' ', desc).strip().rstrip(',')
    return desc


def _parse_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
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


# ─────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Company anonymization pipeline (Doug + verifier)")
    parser.add_argument('company', nargs='?', help='Company name to anonymize')
    parser.add_argument('--batch', '-b', type=int, default=0, help='Process N unverified entries')
    parser.add_argument('--lookup', '-l', help='Just look up a company (no research)')
    args = parser.parse_args()

    conn = get_connection_raw()

    try:
        if args.lookup:
            en = lookup_company(conn, args.lookup, lang="en")
            de = lookup_company(conn, args.lookup, lang="de")
            if en:
                print(f"EN: {en}")
                print(f"DE: {de}")
            else:
                print(f"Not in registry: '{args.lookup}'")

        elif args.batch > 0:
            stats = process_unverified_batch(conn, limit=args.batch)
            print(f"Processed: {stats['processed']}, Verified: {stats['verified']}, Failed: {stats['failed']}")

        elif args.company:
            en, de = anonymize_company(conn, args.company)
            print(f"EN: {en}")
            print(f"DE: {de}")

        else:
            parser.print_help()

    finally:
        return_connection(conn)


if __name__ == '__main__':
    main()
