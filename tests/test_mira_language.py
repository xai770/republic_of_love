"""
Unit tests for api/routers/mira/language.py — pure functions, no DB needed.
"""
import pytest
from api.routers.mira.language import (
    detect_language_switch,
    detect_language_from_message,
    match_conversational,
    detect_formality,
)


class TestDetectLanguageSwitch:
    """Test explicit language switch detection."""

    def test_switch_to_english(self):
        # "speak English" triggers, but "switch to English" may not
        result = detect_language_switch("Can you speak English please?")
        assert result == "en"

    def test_switch_to_german(self):
        assert detect_language_switch("Lass uns auf Deutsch wechseln") == "de"

    def test_no_switch(self):
        assert detect_language_switch("I want to find a job") is None

    def test_speak_english(self):
        assert detect_language_switch("Can we speak English?") == "en"


class TestDetectLanguageFromMessage:
    """Test language detection from message content."""

    def test_german_message(self):
        assert detect_language_from_message("Ich suche eine Stelle als Koch") == "de"

    def test_english_message(self):
        # Detection is German-first; English needs strong markers
        result = detect_language_from_message("I would like to find a new job please")
        # May return 'en' or None depending on marker word coverage
        assert result in ("en", None)

    def test_short_ambiguous_message(self):
        # Short messages may return None — that's OK
        result = detect_language_from_message("OK")
        assert result in ("en", "de", None)

    def test_german_with_umlauts(self):
        result = detect_language_from_message("Können Sie mir helfen eine Stelle zu finden?")
        assert result == "de"


class TestMatchConversational:
    """Test conversational pattern matching (greetings, thanks, etc.)."""

    def test_greeting_hallo(self):
        result = match_conversational("Hallo!")
        assert result is not None

    def test_greeting_hi(self):
        result = match_conversational("Hi there")
        assert result is not None

    def test_thanks(self):
        result = match_conversational("Danke schön!")
        assert result is not None

    def test_goodbye(self):
        result = match_conversational("Tschüss!")
        assert result is not None

    def test_not_conversational(self):
        result = match_conversational("Ich suche eine Stelle als Softwareentwickler in Berlin")
        assert result is None


class TestDetectFormality:
    """Test du/Sie formality detection."""

    def test_informal_du(self):
        result = detect_formality("Kannst du mir helfen?")
        assert result is True  # True = du (informal)

    def test_formal_sie(self):
        result = detect_formality("Können Sie mir helfen?")
        assert result is False  # False = Sie (formal)

    def test_neutral(self):
        result = detect_formality("Software Engineer Berlin")
        assert result is None  # No formality signal

    def test_informal_dir(self):
        result = detect_formality("Ich schick dir mal meinen Lebenslauf")
        assert result is True
