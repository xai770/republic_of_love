"""
PII Safety Net — Post-anonymization validator.

Catches any PII that the LLM anonymizer might have missed.
Runs AFTER LLM processing as a paranoia check.

Usage:
    from core.pii_detector import PIIDetector
    detector = PIIDetector(conn)   # loads company corpus from DB
    violations = detector.check(text)
    if violations:
        raise PIILeakageError(f"PII detected: {violations}")
"""
import re
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)


# Patterns that should NEVER appear in anonymized output
_PII_PATTERNS = [
    # Email addresses
    (r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b', 'email'),
    # German phone: +49 xxx, 0xxx, etc.
    (r'(?:\+49|0049|0)[\s\-/\.]*\d[\d\s\-/\.]{5,14}\d', 'phone_de'),
    # International phone: +xx followed by digits/spaces
    (r'\+\d{1,3}[\s\-\.]?[\d\s\-\.]{6,15}\d', 'phone_intl'),
    # Dates: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD
    (r'\b\d{1,2}[./\-]\d{1,2}[./\-]\d{4}\b', 'date'),
    (r'\b\d{4}[./\-]\d{1,2}[./\-]\d{1,2}\b', 'date_iso'),
    # Years (1950-2029) — in anonymized text we shouldn't have specific years
    (r'\b(19[5-9]\d|20[0-2]\d)\b', 'year'),
    # LinkedIn URLs
    (r'linkedin\.com/in/\w+', 'linkedin'),
    # XING URLs
    (r'xing\.com/profile/\w+', 'xing'),
    # German postal codes (5 digits, specific ranges)
    (r'\b[0-9]{5}\b', 'postal_code'),
    # Street addresses (German pattern: Streetname Nr.)
    (r'\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.|weg|allee|platz|gasse|ring)\s+\d+', 'street_address'),
]

# Compile once
_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), label) for p, label in _PII_PATTERNS]

# Well-known companies/universities that should NEVER appear
# (loaded from DB at runtime, this is the fallback for offline use)
_KNOWN_ENTITIES = {
    # Top employers
    'deutsche bank', 'commerzbank', 'dresdner bank', 'goldman sachs',
    'jp morgan', 'morgan stanley', 'credit suisse', 'ubs',
    'mckinsey', 'bcg', 'bain', 'deloitte', 'kpmg', 'pwc', 'ey',
    'accenture', 'capgemini', 'infosys', 'tcs', 'wipro',
    'siemens', 'bosch', 'sap', 'basf', 'bayer', 'henkel',
    'daimler', 'mercedes', 'bmw', 'volkswagen', 'audi', 'porsche',
    'novartis', 'roche', 'pfizer', 'merck', 'sanofi', 'astrazeneca',
    'allianz', 'munich re', 'zurich insurance',
    'amazon', 'google', 'microsoft', 'apple', 'meta', 'facebook',
    'tesla', 'netflix', 'uber', 'airbnb', 'spotify',
    # Universities
    'harvard', 'stanford', 'mit', 'oxford', 'cambridge',
    'insead', 'lbs', 'london business school', 'wharton',
    'eth zürich', 'eth zurich', 'tu münchen', 'tu munich',
    'rwth aachen', 'fu berlin', 'hu berlin', 'lmu münchen',
    'uni frankfurt', 'goethe-universität', 'goethe universität',
    'uni heidelberg', 'uni köln', 'uni hamburg',
    'kit karlsruhe', 'tu berlin', 'tu darmstadt',
    'mannheim business school', 'WHU',
}


class PIIDetector:
    """
    Post-anonymization PII checker.
    
    Loads company names from the postings table to build a comprehensive
    entity corpus. Falls back to hardcoded list if DB unavailable.
    """
    
    def __init__(self, conn=None):
        self._company_names: set = set(_KNOWN_ENTITIES)
        if conn:
            self._load_company_corpus(conn)
    
    def _load_company_corpus(self, conn):
        """Load unique company names from postings table."""
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT LOWER(posting_name) 
                    FROM postings 
                    WHERE posting_name IS NOT NULL 
                      AND posting_name != ''
                      AND LENGTH(posting_name) > 3
                """)
                for row in cur:
                    name = row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
                    if name:
                        self._company_names.add(name.strip())
            logger.info(f"PII detector loaded {len(self._company_names)} company names")
        except Exception as e:
            logger.warning(f"Could not load company corpus: {e}")
    
    def check(self, text: str, extra_names: Optional[list] = None, skip_companies: bool = False) -> list:
        """
        Check text for PII violations.
        
        Args:
            text: The anonymized text to validate.
            extra_names: Additional names to check for (e.g., yogi's real name from CV).
            skip_companies: If True, skip company name checks (useful for skills/certs fields
                           where company names like "SAP" are expected as skill references).
        
        Returns:
            List of violation strings. Empty = clean.
        """
        if not text:
            return []
        
        violations = []
        text_lower = text.lower()
        
        # Pattern checks
        for pattern, label in _COMPILED_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                # Allow "years" as duration context (e.g., "4 years")
                if label == 'year':
                    # Filter: only flag if the year appears NOT after "years" or "Jahre"
                    for m in matches:
                        year_str = m if isinstance(m, str) else m[0] if m else ''
                        # Check surrounding context
                        idx = text_lower.find(year_str.lower())
                        if idx > 0:
                            before = text_lower[max(0, idx-15):idx]
                            if 'year' in before or 'jahr' in before or 'dauer' in before:
                                continue  # This is "X years of experience", not a date
                        violations.append(f"[{label}] {year_str}")
                elif label == 'postal_code':
                    # Skip 5-digit numbers that are clearly not postal codes
                    for m in matches:
                        num = int(m) if isinstance(m, str) else 0
                        if 1000 <= num <= 99999:
                            # Check context: is this near "PLZ", address, or city?
                            idx = text_lower.find(str(num))
                            if idx > 0:
                                context = text_lower[max(0, idx-30):idx+30]
                                if any(w in context for w in ['plz', 'straß', 'str.', 'stadt', 'ort', 'adress']):
                                    violations.append(f"[{label}] {num}")
                else:
                    for m in matches[:3]:  # Cap at 3 per pattern
                        violations.append(f"[{label}] {m}")
        
        # Company name checks
        if not skip_companies:
            for company in self._company_names:
                if len(company) >= 3 and company in text_lower:
                    # Avoid false positives for very short names embedded in words
                    # Check word boundaries
                    pattern = r'\b' + re.escape(company) + r'\b'
                    if re.search(pattern, text_lower):
                        violations.append(f"[company] {company}")
        
        # Extra names (e.g., the yogi's real name)
        if extra_names:
            # Split compound names into parts ("Gershon Pollatschek" → check each part)
            all_names = []
            for name in extra_names:
                if name:
                    all_names.append(name)
                    for part in name.split():
                        if part not in all_names:
                            all_names.append(part)
            for name in all_names:
                if name and len(name) > 2 and name.lower() in text_lower:
                    violations.append(f"[real_name] {name}")
        
        return violations
    
    @property
    def corpus_size(self) -> int:
        """Number of known company/entity names."""
        return len(self._company_names)
