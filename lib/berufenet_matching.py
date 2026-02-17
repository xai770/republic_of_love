"""
Berufenet Matching Utilities

Matches job titles to Germany's official Berufenet taxonomy.
Provides KLDB codes and qualification levels (1-4).

V5 POC Results (100 titles, clean semantic matching):
- ≥ 0.85: Auto-accept (9% of titles)
- 0.70-0.85: LLM verification (37%)
- < 0.70: NULL - don't guess (54%)

Philosophy: No artificial similarity boosts (/in suffixes etc).
Let the semantic meaning drive the match.
"""

import os
import re
from typing import Optional, Tuple

import requests

BERUFENET_MODEL = os.getenv('BERUFENET_MODEL', 'qwen2.5:7b')
OLLAMA_GENERATE_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'

# Thresholds derived from 100-title POC with V5 clean matching (no artificial /in)
THRESHOLD_AUTO_ACCEPT = 0.85  # 9% - very reliable
THRESHOLD_LLM_VERIFY = 0.70   # 37% - needs confirmation  
# Below 0.70 → NULL (54% - unreliable, don't guess)


def clean_job_title(title: str) -> str:
    """
    Normalize job title - strip all noise, no artificial suffixes.
    
    Strategy:
    1. Remove ALL gender markers (m/w/d), /in, -in, *in etc
    2. Remove location patterns
    3. Strip salary, hours, employment type, codes
    4. Clean marketing fluff
    
    Examples:
        "Koch in Baierbrunn (m/w/d)" → "Koch"
        "Verkäuferin (m/w/d) in Teilzeit!" → "Verkäuferin"
        "Staplerfahrer/in (m/w/d)" → "Staplerfahrer"
    """
    # 1. Remove location patterns FIRST
    title = re.sub(r'\s+in\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*(?:\s*$|\s*\()', r' (', title)
    title = re.sub(r'\s+-\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\s*$', '', title)

    # 2. Remove ALL gender markers — no artificial similarity
    title = re.sub(r'\s*\([mwdxfMWDXF/\-,|]+\)', '', title)  # (m/w/d), (m,w,d), (m|w|d)
    title = re.sub(r'\s*-\s*[mwMW]\s*/\s*[wdWD]\s*/?\s*[dxfDXF]?\s*$', '', title)  # - m/w/d (no parens)
    title = re.sub(r'\*in\b', '', title)                     # *in gender suffix
    title = re.sub(r'\*r\b', '', title)                      # *r gender suffix (Mitarbeiter*r)
    title = re.sub(r'/in\b', '', title)                      # /in suffix
    title = re.sub(r':in\b', '', title)                      # :in suffix
    title = re.sub(r'-in\b(?!\s*[A-Z])', '', title)          # -in suffix (not -Industrie)

    # 3. Company names
    title = re.sub(r'\s+bei\s+[A-ZÄÖÜ][A-Za-zäöüß\s&]+$', '', title)
    title = re.sub(r'\s+für\s+[A-ZÄÖÜ][A-Za-zäöüß\s&]+$', '', title)

    # 4. Salary/hours/price info (€ anywhere, price ranges)
    title = re.sub(r'\s+[\d,\.]+\s*[-–—]\s*[\d,\.]+\s*€.*$', '', title)  # 20,30 - 29,12€/h
    title = re.sub(r'\s+[\d,\.]+\s*€.*$', '', title)                     # 23,23€ Std. brutto
    title = re.sub(r'\s+ab\s+[\d,\.]+\s*€.*$', '', title, flags=re.I)
    title = re.sub(r'\s+bis\s+zu\s+[\d,\.]+.*$', '', title, flags=re.I)
    title = re.sub(r'\s+\d+\s*(?:Std|Wochenstunden|h/Woche).*$', '', title, flags=re.I)

    # 5. Employment type
    title = re.sub(r'\s+in\s+(Teilzeit|Vollzeit|Minijob).*$', '', title, flags=re.I)
    title = re.sub(r'\s+(Teilzeit|Vollzeit|Minijob).*$', '', title, flags=re.I)

    # 6. Job codes/IDs
    title = re.sub(r'\s+-\s*\d{3,}[-\d]*\s*$', '', title)
    title = re.sub(r'\s+\(\d+\)\s*$', '', title)

    # 7. Marketing fluff / temporal
    title = re.sub(r'\s+ab\s+(sofort|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\b.*$', '', title, flags=re.I)
    title = re.sub(r'\s+gesucht!*\s*$', '', title, flags=re.I)
    title = re.sub(r'\s+dringend!*\s*$', '', title, flags=re.I)

    # 8. Pipe-separated sections (keep first section only)
    title = re.sub(r'\s*\|.*$', '', title)

    # 9. Clean up
    title = re.sub(r'\(\s*\)', '', title)            # empty parens ()
    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'^[-–—]\s*', '', title)
    title = re.sub(r'\s*[-–—]$', '', title)

    return title


# OWL Synonyms: Colloquial → Formal Berufenet names
# Map common job titles to their official Berufenet equivalents.
# Use base forms without gender suffixes.
OWL_SYNONYMS = {
    # Logistics / Warehouse
    "Staplerfahrer": "Fachkraft Lagerlogistik",
    "Gabelstaplerfahrer": "Fachkraft Lagerlogistik", 
    "Flurförderzeugführer": "Fachkraft Lagerlogistik",
    "Lagerist": "Fachkraft Lagerlogistik",
    "Kommissionierer": "Fachkraft Lagerlogistik",
    "Verpacker": "Verpackungsmittelmechaniker",
    "Warenverräumer": "Verkäufer",
    
    # Healthcare - many common terms NOT in Berufenet
    "Krankenschwester": "Pflegefachmann",
    "Krankenpfleger": "Pflegefachmann",
    "Altenpfleger": "Pflegefachmann",
    "Pfleger": "Pflegefachmann",
    "Pflegefachkraft": "Pflegefachmann",  # Very common, not in Berufenet
    "Gesundheits- und Krankenpfleger": "Pflegefachmann",
    
    # Trades
    "Elektriker": "Elektroniker",
    "Schlosser": "Metallbauer",
    "Klempner": "Anlagenmechaniker Sanitär Heizung Klima",
    "Installateur": "Anlagenmechaniker Sanitär Heizung Klima",
    "CNC-Programmierer": "CNC-Fachkraft",  # Not in Berufenet
    "CNC Programmierer": "CNC-Fachkraft",
    
    # Office
    "Sekretärin": "Kaufmann Büromanagement",
    "Sachbearbeiter": "Kaufmann Büromanagement",
    "Bürokraft": "Kaufmann Büromanagement",
    "Office Manager": "Kaufmann Büromanagement",  # English term
    
    # Cleaning / Low-skill - not in Berufenet as-is
    "Reinigungskraft": "Helfer Reinigung",
    "Raumpfleger": "Helfer Reinigung",
    "Spülkraft": "Helfer Küche",
    "Küchenhilfe": "Helfer Küche",
    
    # IT - English terms common in Germany
    "Netzwerkadministrator": "Fachinformatiker Systemintegration",
    "Systemadministrator": "Fachinformatiker Systemintegration",
    "HR Generalist": "Personalreferent",
    "HR Manager": "Personalreferent",
    
    # Food service
    "Kellner": "Restaurantfachmann",
    "Servicekraft": "Restaurantfachmann",
    
    # IT (English → German)
    "Developer": "Softwareentwickler",
    "Frontend Developer": "Softwareentwickler",
    "Backend Developer": "Softwareentwickler",
    "Software Engineer": "Softwareentwickler",
    "DevOps Engineer": "DevOps Engineer",
    "IT Support": "Fachinformatiker Systemintegration",
    "Sysadmin": "Fachinformatiker Systemintegration",
}


def apply_owl_synonyms(title: str) -> str:
    """
    Replace colloquial terms with formal Berufenet equivalents.
    
    Example:
        "Staplerfahrer gesucht" → "Fachkraft Lagerlogistik gesucht"
    """
    for colloquial, formal in OWL_SYNONYMS.items():
        # Match the colloquial term (case-insensitive)
        pattern = re.compile(re.escape(colloquial), re.IGNORECASE)
        title = pattern.sub(formal, title)
    return title


def get_qualification_level_name(level: int) -> str:
    """Convert KLDB qualification level digit to human-readable name."""
    names = {
        1: "Helfer (unqualified)",
        2: "Fachkraft (vocational training)", 
        3: "Spezialist (advanced vocational)",
        4: "Experte (university degree)",
    }
    return names.get(level, f"Unknown ({level})")


def classify_match_confidence(score: float) -> Tuple[str, str]:
    """
    Classify embedding match score into action buckets.
    
    Returns:
        (bucket_name, action_description)
    """
    if score >= THRESHOLD_AUTO_ACCEPT:
        return ("high", "Auto-accept: embedding match reliable")
    elif score >= THRESHOLD_LLM_VERIFY:
        return ("medium", "LLM-verify: needs confirmation")
    else:
        return ("low", "NULL: unreliable, skip matching")


# =============================================================================
# LLM Triage — pick best match(es) from candidates
# =============================================================================

LLM_TRIAGE_PROMPT = """You are a German job classification expert. Given a job posting title, pick which Berufenet professions it matches.

RULES:
- Pick ALL candidates that genuinely match the job title (can be 1, 2, or all 3)
- A match means: same profession, or the job title is commonly filled by this profession
- Qualification level matters: Helfer ≠ Fachkraft ≠ Spezialist ≠ Experte
- If NONE match, say NONE
- Answer with ONLY the numbers (e.g. "1" or "1,3" or "NONE")

Job title: "{job_title}"

Candidates:
{candidates_text}

Answer (numbers only):"""


def llm_triage_pick(job_title: str, candidates: list[dict], model: str = None) -> list[int]:
    """
    Ask LLM to pick the best match(es) from a list of candidates.
    Returns list of 0-based indices of matching candidates, or empty list.
    """
    model = model or BERUFENET_MODEL

    cands_text = "\n".join(
        f"  {i+1}. {c.get('name', '?')} (score: {c.get('score', 0):.3f})"
        for i, c in enumerate(candidates)
    )

    prompt = LLM_TRIAGE_PROMPT.format(
        job_title=job_title,
        candidates_text=cands_text
    )

    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={'model': model, 'prompt': prompt, 'stream': False},
            timeout=60
        )
        answer = resp.json().get('response', '').strip().upper()

        if 'NONE' in answer:
            return []

        # Parse comma-separated numbers
        picked = []
        for token in answer.replace(',', ' ').split():
            token = token.strip('.')
            if token.isdigit():
                idx = int(token) - 1  # 1-based → 0-based
                if 0 <= idx < len(candidates):
                    picked.append(idx)
        return picked
    except Exception:
        return []


# LLM Verification prompt - tested with qwen2.5:7b
# Results: 65% confirmed, 15% rejected (caught real errors), 20% uncertain
LLM_VERIFY_PROMPT = """You are a German job classification expert. Verify if a job title matches a Berufenet profession.

DECISION RULES:
- YES = Same profession, or the job title is commonly filled by this Berufenet profession
- NO = Fundamentally different profession (different field, skill set, or qualification level)
- UNCERTAIN = Not enough information, or could go either way

QUALIFICATION LEVELS MATTER:
- Level 1 (Helfer) = unskilled labor
- Level 2 (Fachkraft) = vocational training required
- Level 3 (Spezialist) = advanced vocational/Meister
- Level 4 (Experte) = university degree

A Staplerfahrer (forklift, Level 2) is NOT a Reinigungskraft (cleaning, Level 1).
A Sozialarbeiter (social worker, Level 4) is NOT a Sozialassistent (Level 2).

Answer ONLY: YES, NO, or UNCERTAIN

Job: "{job_title}"
Match: "{berufenet_match}"
Answer:"""


def llm_verify_match(job_title: str, berufenet_match: str, model: str = None) -> str:
    """
    Use LLM to verify if job title matches Berufenet profession.
    Uses Ollama HTTP API (not subprocess) for speed.

    Args:
        job_title: Cleaned job title from posting
        berufenet_match: Best Berufenet match from embedding
        model: Ollama model to use (default: BERUFENET_MODEL env var)

    Returns:
        "YES", "NO", or "UNCERTAIN"
    """
    model = model or BERUFENET_MODEL

    prompt = LLM_VERIFY_PROMPT.format(
        job_title=job_title,
        berufenet_match=berufenet_match
    )

    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={'model': model, 'prompt': prompt, 'stream': False},
            timeout=60
        )
        answer = resp.json().get('response', '').strip().upper()

        if 'YES' in answer:
            return 'YES'
        elif 'NO' in answer:
            return 'NO'
        else:
            return 'UNCERTAIN'
    except Exception as e:
        return 'ERROR'


if __name__ == "__main__":
    # Test cleaning
    test_cases = [
        ("Koch in Baierbrunn (m/w/d)", "Koch"),
        ("Verkäuferin (m/w/d) in Teilzeit!", "Verkäuferin"),
        ("Staplerfahrer/in (m/w/d)", "Staplerfahrer"),
        ("IT Support (m/w/d)", "IT Support"),
        ("Sozialarbeiter (m/w/d) Vollzeit", "Sozialarbeiter"),
        ("Optiker/in (m/w/d)", "Optiker"),
        ("Elektriker:in gesucht", "Elektriker"),
    ]
    
    print("Job Title Cleaning Tests:")
    for original, expected in test_cases:
        result = clean_job_title(original)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{original}' → '{result}'")
        if result != expected:
            print(f"       Expected: '{expected}'")
