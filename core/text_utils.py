#!/usr/bin/env python3
"""
Text Utilities - Single Source of Truth for Text Processing
============================================================

All text cleaning, encoding fixes, and normalization should use these functions.
Do NOT duplicate this logic elsewhere.

Functions:
- fix_encoding() - Fix mojibake from external sources
- clean_whitespace() - Normalize whitespace
- sanitize_for_storage() - Full pipeline for DB storage
- normalize_extraction() - Normalize LLM outputs for comparison
- normalize_for_match() - Prepare text for substring matching
- detect_language() - Detect language (ISO 639-1)
- verify_quote_in_source() - Check if quote exists in source
- clean_json_from_llm() - Extract JSON from LLM response

Author: Arden & xai
Date: December 10, 2025 (enhanced January 18, 2026)
"""

import unicodedata
import re
from typing import Optional


def fix_encoding(text: str) -> str:
    """
    Fix common UTF-8 encoding issues (mojibake).
    
    USE THIS FUNCTION whenever text comes from external sources
    (APIs, web scraping, file imports) before storing in the database.
    
    Fixes double-encoded UTF-8 patterns like:
        Ã¼ → ü (German umlaut)
        â€" → – (en-dash)
        â€™ → ' (apostrophe)
        &amp; → & (HTML entities)
    
    Args:
        text: Input text that may have encoding issues
        
    Returns:
        Cleaned text with proper Unicode characters
        
    Example:
        >>> fix_encoding("Ãœber den Bereich")
        'Über den Bereich'
    """
    if not text:
        return text
    
    # Common mojibake patterns (double-encoded UTF-8)
    # These occur when UTF-8 bytes are misinterpreted as Latin-1/Windows-1252
    replacements = {
        # German characters
        'Ã¼': 'ü', 'Ã¤': 'ä', 'Ã¶': 'ö',
        'Ãœ': 'Ü', 'Ã„': 'Ä', 'Ã–': 'Ö',
        'ÃŸ': 'ß',
        # French/other European
        'Ã©': 'é', 'Ã¨': 'è', 'Ã ': 'à', 
        'Ã¢': 'â', 'Ã®': 'î', 'Ã´': 'ô',
        'Ã§': 'ç', 'Ã±': 'ñ',
        # Punctuation (smart quotes, dashes)
        'â€"': '–',  # en-dash
        'â€"': '—',  # em-dash
        'â€™': "'",  # right single quote
        'â€˜': "'",  # left single quote
        'â€œ': '"',  # left double quote
        'â€': '"',   # right double quote
        'â€¦': '…',  # ellipsis
        # Partial mojibake (incomplete sequences)
        'Ã\u009c': 'Ü',
        'â\u0080\u0093': '–',
        'â\u0080\u0099': "'",
        'â\u0080\u009c': '"',
        'â\u0080\u009d': '"',
    }
    
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    
    # HTML entities
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&apos;': "'",
        '&nbsp;': ' ',
    }
    
    for entity, char in html_entities.items():
        text = text.replace(entity, char)
    
    # Normalize unicode (NFC form - composed characters)
    text = unicodedata.normalize('NFC', text)
    
    return text


def clean_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    
    - Replaces multiple spaces/tabs with single space
    - Strips leading/trailing whitespace
    - Normalizes line endings to \\n
    """
    if not text:
        return text
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Replace multiple whitespace (except newlines) with single space
    text = re.sub(r'[^\S\n]+', ' ', text)
    
    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def sanitize_for_storage(text: str) -> str:
    """
    Full sanitization pipeline for text before database storage.
    
    Combines:
    1. Encoding fix (mojibake)
    2. Whitespace normalization
    
    USE THIS for any external text before INSERT/UPDATE.
    """
    if not text:
        return text
    
    text = fix_encoding(text)
    text = clean_whitespace(text)
    
    return text


def normalize_extraction(response: str) -> str:
    """
    Normalize LLM extraction output for consistent comparison and storage.
    
    Created after RAQ analysis showed 5% variance in WF3007 c2_extract outputs
    was largely due to formatting differences, not semantic differences.
    
    Handles:
    - Case: NONE/none/None → NONE
    - Separators: budget_management / budget-management → budget management
    - Delimiters: java, python / java\\npython → java, python  
    - Order: sorts items alphabetically for deterministic comparison
    - Mixed NONE: filters out NONE items from lists (e.g., "competency\\nNONE" → "competency")
    
    Args:
        response: Raw LLM extraction output
        
    Returns:
        Normalized string, or "NONE" if empty/null
        
    Examples:
        >>> normalize_extraction("budget_management")
        'budget management'
        >>> normalize_extraction("java\\npython")
        'java, python'
        >>> normalize_extraction("NONE")
        'NONE'
        >>> normalize_extraction("team_player\\nNONE")
        'team player'
        >>> normalize_extraction("communication\\nwritten\\nverbal")
        'communication, verbal, written'
    """
    if not response:
        return "NONE"
    
    s = response.strip().lower()
    
    # Pure NONE check
    if s in ('none', 'null', ''):
        return "NONE"
    
    # Split on newlines and commas
    items = re.split(r'[\n,]+', s)
    
    normalized = []
    for item in items:
        item = item.strip()
        
        # Skip empty or none items
        if not item or item in ('none', 'null'):
            continue
        
        # Replace _ and - with space
        item = item.replace('_', ' ').replace('-', ' ')
        
        # Collapse multiple spaces
        item = ' '.join(item.split())
        
        if item:
            normalized.append(item)
    
    if not normalized:
        return "NONE"
    
    # Sort for order-independence
    normalized.sort()
    
    # Join with consistent delimiter
    return ', '.join(normalized)


# ============================================================================
# MATCHING & VERIFICATION
# ============================================================================

# Double-encoded UTF-8 patterns (scraped data artifacts)
# These occur when UTF-8 bytes are stored in a Latin-1 column
DOUBLE_ENCODED_MATCH_MAP = {
    'â\x80\x98': "'",   # Left single quote
    'â\x80\x99': "'",   # Right single quote  
    'â\x80\x9c': '"',   # Left double quote
    'â\x80\x9d': '"',   # Right double quote
    'â\x80\x93': '-',   # En dash
    'â\x80\x94': '-',   # Em dash
    'â\x80¦': '...',    # Ellipsis
    'Ã\x9f': 'ss',      # German eszett (ß)
    'Ã¶': 'o',          # German o-umlaut (ö)
    'Ã¼': 'u',          # German u-umlaut (ü)
    'Ã¤': 'a',          # German a-umlaut (ä)
    'Ã\x96': 'O',       # German O-umlaut (Ö)
    'Ã\x9c': 'U',       # German U-umlaut (Ü)
    'Ã\x84': 'A',       # German A-umlaut (Ä)
}


def normalize_for_match(text: str) -> str:
    """
    Normalize text for fuzzy/substring matching.
    
    Unlike sanitize_for_storage(), this aggressively normalizes for comparison:
    - Fixes double-encoded UTF-8
    - Lowercases
    - Collapses all whitespace to single space
    - Removes ALL punctuation
    
    Use this for quote verification, duplicate detection, etc.
    
    Example:
        >>> normalize_for_match("Hello, World!")
        'hello world'
        >>> normalize_for_match("24 daysâ\\x80\\x99 holiday")
        '24 days holiday'
    """
    if not text:
        return ''
    
    # Fix double-encoded UTF-8
    for pattern, replacement in DOUBLE_ENCODED_MATCH_MAP.items():
        text = text.replace(pattern, replacement)
    
    # Normalize unicode (NFKC = compatibility decomposition)
    text = unicodedata.normalize('NFKC', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    
    # Replace common unicode punctuation
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace('–', '-').replace('—', '-').replace('…', '...')
    
    # Remove all punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    return text.strip()


def detect_language(text: str) -> str:
    """
    Detect language with belt-and-suspenders approach.
    
    Returns ISO 639-1 code: 'en', 'de', 'fr', etc.
    Defaults to 'en' if detection fails.
    
    Example:
        >>> detect_language("This is English text")
        'en'
        >>> detect_language("Das ist deutscher Text")
        'de'
    """
    if not text:
        return 'en'
    
    # Quick heuristic for German (catches 90% of cases)
    german_chars = set('äöüßÄÖÜ')
    if any(c in text for c in german_chars):
        return 'de'
    
    # Use langdetect for everything else
    try:
        from langdetect import detect
        return detect(text[:2000])
    except Exception:
        return 'en'


def verify_quote_in_source(quote: str, source: str, min_length: int = 10) -> bool:
    """
    Verify a quote exists in source text using normalized matching.
    
    Handles:
    - Unicode differences
    - Whitespace differences
    - Truncated quotes (first 50 chars)
    
    Returns True if quote is found, False otherwise.
    """
    if not quote or len(quote) < min_length:
        return False
    
    quote_norm = normalize_for_match(quote)
    source_norm = normalize_for_match(source)
    
    # Exact match
    if quote_norm in source_norm:
        return True
    
    # Truncation tolerance: first 50 chars
    if len(quote_norm) > 50 and quote_norm[:50] in source_norm:
        return True
    
    return False


def verify_quotes_batch(requirements: list, source: str) -> tuple:
    """
    Verify multiple quotes against source text.
    
    Args:
        requirements: List of dicts with 'quote' key
        source: Source text to verify against
        
    Returns:
        (verified_list, unverified_list)
    """
    verified = []
    unverified = []
    
    for req in requirements:
        if not isinstance(req, dict) or 'quote' not in req:
            continue
        
        quote = req.get('quote', '')
        if verify_quote_in_source(quote, source):
            verified.append(req)
        else:
            unverified.append(req)
    
    return verified, unverified


def clean_json_from_llm(text: str) -> Optional[str]:
    """
    Extract JSON from LLM response, handling markdown formatting.
    
    LLMs often wrap JSON in ```json blocks or add explanatory text.
    This extracts just the JSON part.
    
    Returns the JSON string or None if not found.
    """
    if not text:
        return None
        
    text = text.strip()
    
    # Remove markdown code blocks
    if text.startswith('```'):
        lines = text.split('\n')
        lines = lines[1:]  # Remove first line (```json or ```)
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines)
    
    # Find JSON array or object
    array_match = re.search(r'\[.*\]', text, re.DOTALL)
    object_match = re.search(r'\{.*\}', text, re.DOTALL)
    
    if array_match:
        return array_match.group()
    if object_match:
        return object_match.group()
    
    return None


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """Truncate text to max_length, adding suffix if truncated."""
    if not text or len(text) <= max_length:
        return text or ''
    return text[:max_length - len(suffix)] + suffix


# ============================================================================
# TESTS
# ============================================================================
if __name__ == '__main__':
    # Test normalize_for_match
    assert normalize_for_match('Hello  World!') == 'hello world'
    assert normalize_for_match('Hello, World!') == 'hello world'
    
    # Test detect_language
    assert detect_language('This is English text') == 'en'
    assert detect_language('Das ist deutscher Text mit Ümlauten') == 'de'
    
    # Test verify_quote_in_source
    assert verify_quote_in_source('Hello World', 'Say Hello World today') == True
    assert verify_quote_in_source('Goodbye', 'Hello World') == False
    
    # Test clean_json_from_llm
    assert clean_json_from_llm('```json\n[1,2,3]\n```') == '[1,2,3]'
    assert clean_json_from_llm('Here is the result: {"a": 1}') == '{"a": 1}'
    
    print('✅ All text_utils tests passed')