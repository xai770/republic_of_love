"""
Mira router — language detection, formality, conversational patterns.
"""
import re
import random
from typing import Optional


# Language switch patterns (T001)
LANGUAGE_SWITCH = {
    "to_english": {
        "patterns": [
            r"english\s*please",
            r"can we (switch|speak|talk|use) (in\s*)?english",
            r"let'?s (switch|speak|talk|use) (in\s*)?english",
            r"in english",
            r"speak english",
            r"auf englisch",
            r"können wir englisch",
            r"lass uns englisch",
        ],
        "response": "Sure! I can speak English. How can I help you today? 🌍"
    },
    "to_german": {
        "patterns": [
            r"deutsch bitte",
            r"auf deutsch",
            r"können wir deutsch",
            r"lass uns deutsch",
            r"switch to german",
            r"speak german",
            r"in german",
            r"let'?s (switch|speak|talk|use) (in\s*)?german",
        ],
        "response_du": "Klar! Ich spreche wieder Deutsch mit dir. Wie kann ich dir helfen? 🇩🇪",
        "response_sie": "Selbstverständlich! Ich spreche wieder Deutsch mit Ihnen. Wie kann ich Ihnen helfen? 🇩🇪"
    }
}


# Conversational responses for greetings/thanks/bye (not in FAQ)
CONVERSATIONAL = {
    "greeting": {
        "patterns": [r"^hallo", r"^hi\b", r"^hey", r"^guten (morgen|tag|abend)", r"^servus", r"^moin", r"^hello", r"^good (morning|afternoon|evening)"],
        "responses_du": ["Hallo! Wie kann ich dir helfen?", "Hey! Was kann ich für dich tun?"],
        "responses_sie": ["Guten Tag! Wie kann ich Ihnen helfen?", "Hallo! Was kann ich für Sie tun?"],
        "responses_en": ["Hi! How can I help you today?", "Hello! What can I do for you?"]
    },
    "thanks": {
        "patterns": [r"dank", r"danke", r"super", r"toll", r"klasse", r"prima", r"thanks?", r"thank you", r"great", r"awesome"],
        "responses_du": ["Gern geschehen! Wenn du noch Fragen hast, bin ich da.", "Freut mich, dass ich helfen konnte!"],
        "responses_sie": ["Gern geschehen! Wenn Sie noch Fragen haben, bin ich da.", "Freut mich, dass ich helfen konnte!"],
        "responses_en": ["You're welcome! Let me know if you have more questions.", "Happy to help!"]
    },
    "bye": {
        "patterns": [r"tschüss", r"bye", r"auf wiedersehen", r"bis (bald|dann|später)", r"ciao", r"goodbye", r"see you"],
        "responses_du": ["Bis bald! Du findest mich immer hier unten rechts.", "Tschüss! Melde dich, wenn du mich brauchst."],
        "responses_sie": ["Auf Wiedersehen! Sie finden mich immer hier unten rechts.", "Bis bald! Melden Sie sich, wenn Sie mich brauchen."],
        "responses_en": ["See you! You can find me in the bottom right corner anytime.", "Bye! Let me know if you need anything."]
    }
}


def detect_language_switch(message: str) -> Optional[str]:
    """
    Detect if user is requesting a language switch.

    Returns:
        'en' = switch to English
        'de' = switch to German
        None = no language switch request
    """
    message_lower = message.lower()

    for pattern in LANGUAGE_SWITCH["to_english"]["patterns"]:
        if re.search(pattern, message_lower):
            return 'en'

    for pattern in LANGUAGE_SWITCH["to_german"]["patterns"]:
        if re.search(pattern, message_lower):
            return 'de'

    return None


def detect_language_from_message(message: str) -> Optional[str]:
    """
    Detect which language the user is writing in.

    Returns:
        'en' = English
        'de' = German
        None = can't determine
    """
    message_lower = message.lower()

    # Common English words/phrases (not shared with German)
    english_markers = [
        r'\bthe\b', r'\bwhat\b', r'\bhow\b', r'\bwhy\b', r'\bwhere\b',
        r'\byou\b', r'\byour\b', r'\bplease\b', r'\bthanks?\b',
        r'\bhelp\b', r'\bcan\b', r'\bcould\b', r'\bwould\b',
        r'\bi am\b', r"\bi'm\b", r'\bi have\b', r"\bi've\b",
    ]

    # Common German words/phrases (not shared with English)
    german_markers = [
        r'\bich\b', r'\bist\b', r'\bsind\b', r'\bwas\b', r'\bwie\b',
        r'\bwarum\b', r'\bwo\b', r'\bwer\b', r'\bwenn\b', r'\bweil\b',
        r'\bkann\b', r'\bkönnen\b', r'\bmöchte\b', r'\bwürde\b',
        r'\bmit\b', r'\bfür\b', r'\bund\b', r'\baber\b', r'\bauch\b',
        r'\bbitte\b', r'\bdanke\b', r'\bhallo\b', r'\bguten\b',
    ]

    en_score = sum(1 for p in english_markers if re.search(p, message_lower))
    de_score = sum(1 for p in german_markers if re.search(p, message_lower))

    if en_score > de_score and en_score >= 2:
        return 'en'
    elif de_score > en_score and de_score >= 1:
        return 'de'

    return None


def match_conversational(message: str) -> Optional[str]:
    """Check if message is a simple conversational pattern (greeting/thanks/bye)."""
    message_lower = message.lower()

    for category, data in CONVERSATIONAL.items():
        for pattern in data["patterns"]:
            if re.search(pattern, message_lower):
                return category

    return None


def detect_formality(message: str) -> Optional[bool]:
    """
    Detect Du vs Sie from user's message.

    Returns:
        True = uses du (informal)
        False = uses Sie (formal)
        None = can't determine
    """
    message_lower = message.lower()

    # Sie indicators (formal)
    sie_patterns = [
        r'\bsie\b',
        r'\bihnen\b',
        r'\bihr\b',
        r'\bihre[rsmn]?\b',
        r'\bkönnen sie\b',
        r'\bhaben sie\b',
        r'\bwürden sie\b',
    ]

    # Du indicators (informal)
    du_patterns = [
        r'\bdu\b',
        r'\bdich\b',
        r'\bdir\b',
        r'\bdein[esr]?\b',
        r'\bkannst du\b',
        r'\bhast du\b',
        r'\bwürdest du\b',
    ]

    # Check for Sie first (more specific)
    for pattern in sie_patterns:
        if re.search(pattern, message_lower):
            return False  # Uses Sie

    # Then check for du
    for pattern in du_patterns:
        if re.search(pattern, message_lower):
            return True  # Uses du

    return None  # Can't determine


def get_conversational_response(category: str, uses_du: bool, language: str = 'de') -> str:
    """Get response for conversational patterns."""
    data = CONVERSATIONAL[category]

    if language == 'en':
        responses = data.get("responses_en", data["responses_du"])  # Fallback to du
    elif uses_du:
        responses = data["responses_du"]
    else:
        responses = data["responses_sie"]

    return random.choice(responses)
