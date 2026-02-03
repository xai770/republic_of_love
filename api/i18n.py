"""
i18n — Internationalization support for talent.yoga

Usage in templates:
    {{ t('nav.start') }}
    {{ t('dashboard.welcome', name=user.display_name) }}

Supported languages:
    - de (German) — default
    - en (English)
"""
import json
from pathlib import Path
from typing import Optional
from functools import lru_cache

# Available languages (first is default)
SUPPORTED_LANGUAGES = ['de', 'en']
DEFAULT_LANGUAGE = 'de'

# Path to translation files
I18N_DIR = Path(__file__).parent.parent / 'frontend' / 'static' / 'i18n'


@lru_cache(maxsize=10)
def load_translations(lang: str) -> dict:
    """Load translation file for a language. Cached for performance."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    file_path = I18N_DIR / f'{lang}.json'
    if not file_path.exists():
        file_path = I18N_DIR / f'{DEFAULT_LANGUAGE}.json'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return {}


def get_nested(data: dict, key: str, default: str = '') -> str:
    """Get nested dictionary value using dot notation (e.g., 'nav.start')."""
    keys = key.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
        if value is None:
            return default
    return value if isinstance(value, str) else default


def translate(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Translate a key to the given language.
    
    Args:
        key: Dot-notation key like 'nav.start' or 'dashboard.welcome'
        lang: Language code ('de', 'en')
        **kwargs: Substitution values for placeholders like {name}
    
    Returns:
        Translated string, or key if not found
    """
    translations = load_translations(lang)
    text = get_nested(translations, key, key)
    
    # Handle {placeholder} substitutions
    if kwargs and '{' in text:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # Leave unmatched placeholders as-is
    
    return text


def create_translator(lang: str):
    """
    Create a translator function bound to a specific language.
    Use this in templates: t = create_translator('de')
    """
    def t(key: str, **kwargs) -> str:
        return translate(key, lang, **kwargs)
    return t


def get_language_from_request(request) -> str:
    """
    Detect language from request in order of priority:
    1. ?lang= query parameter
    2. lang cookie
    3. Accept-Language header
    4. Default language
    """
    # 1. Query parameter
    lang = request.query_params.get('lang')
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang
    
    # 2. Cookie
    lang = request.cookies.get('lang')
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang
    
    # 3. Accept-Language header
    accept = request.headers.get('accept-language', '')
    for part in accept.split(','):
        code = part.split(';')[0].strip().lower()[:2]
        if code in SUPPORTED_LANGUAGES:
            return code
    
    # 4. Default
    return DEFAULT_LANGUAGE


def get_all_translations(lang: str) -> dict:
    """Get all translations for a language (for client-side use)."""
    return load_translations(lang)
