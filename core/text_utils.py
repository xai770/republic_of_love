#!/usr/bin/env python3
"""
Text Utilities - Single Source of Truth for Text Processing
============================================================

All text cleaning, encoding fixes, and normalization should use these functions.
Do NOT duplicate this logic elsewhere.

Author: Arden & xai
Date: December 10, 2025
"""

import unicodedata
import re


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
