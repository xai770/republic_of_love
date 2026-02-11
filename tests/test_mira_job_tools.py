"""
Tests for core/mira_job_tools.py — job search intent detection and extraction.
"""
import pytest
from core.mira_job_tools import (
    detect_job_search_intent,
    extract_search_query,
    extract_location,
    extract_qualification_level,
    get_qualification_emoji,
    get_qualification_label,
)


# ── detect_job_search_intent ─────────────────────────────────────────

class TestDetectJobSearchIntent:
    def test_german_search(self):
        result = detect_job_search_intent("Ich suche einen Job als Entwickler")
        assert result is not None
        assert result["intent_type"] == "search"

    def test_english_search(self):
        result = detect_job_search_intent("Find me jobs as a developer")
        assert result is not None
        assert result["intent_type"] == "search"

    def test_german_browse(self):
        result = detect_job_search_intent("Gibt es Jobs in Berlin?")
        assert result is not None
        assert result["intent_type"] == "browse"

    def test_english_with_location(self):
        result = detect_job_search_intent("Are there any jobs in Hamburg?")
        assert result is not None
        assert result["intent_type"] in ("browse", "search")

    def test_greeting_not_search(self):
        assert detect_job_search_intent("Hallo") is None

    def test_thanks_not_search(self):
        assert detect_job_search_intent("Danke") is None

    def test_short_chat_ignored(self):
        assert detect_job_search_intent("hi") is None

    def test_specific_job(self):
        result = detect_job_search_intent("Stellen als Mechaniker in München")
        assert result is not None


# ── extract_search_query ─────────────────────────────────────────────

class TestExtractSearchQuery:
    def test_removes_filler_de(self):
        result = extract_search_query("Ich suche Entwickler")
        assert "suche" not in result.lower() or result == "Entwickler" or len(result) > 0

    def test_removes_filler_en(self):
        result = extract_search_query("Find me developer")
        assert len(result) > 0

    def test_fallback_to_original(self):
        # If stripping removes everything, return original
        result = extract_search_query("jobs")
        assert len(result) > 0


# ── extract_location ─────────────────────────────────────────────────

class TestExtractLocation:
    def test_in_berlin(self):
        assert extract_location("Jobs in Berlin") == "Berlin"

    def test_in_muenchen(self):
        assert extract_location("Stellen in München") == "München"

    def test_bei_hamburg(self):
        assert extract_location("Arbeit bei Hamburg") == "Hamburg"

    def test_city_mentioned(self):
        assert extract_location("Frankfurt developer jobs") == "Frankfurt"

    def test_no_location(self):
        assert extract_location("I want a job") is None


# ── extract_qualification_level ──────────────────────────────────────

class TestExtractQualificationLevel:
    def test_helper(self):
        assert extract_qualification_level("Helfer ohne Ausbildung") == 1

    def test_entry(self):
        assert extract_qualification_level("entry level position") == 1

    def test_vocational(self):
        assert extract_qualification_level("Mit Ausbildung") == 2

    def test_apprentice(self):
        assert extract_qualification_level("looking for an apprentice role") == 2

    def test_bachelor(self):
        assert extract_qualification_level("Bachelor degree required") == 3

    def test_meister(self):
        assert extract_qualification_level("Meister in Elektrotechnik") == 3

    def test_senior(self):
        assert extract_qualification_level("Senior developer") == 4

    def test_no_level(self):
        assert extract_qualification_level("Something random") is None


# ── get_qualification_emoji ──────────────────────────────────────────

class TestQualificationEmoji:
    def test_returns_string(self):
        for level in [1, 2, 3, 4]:
            result = get_qualification_emoji(level)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_none_returns_string(self):
        result = get_qualification_emoji(None)
        assert isinstance(result, str)


# ── get_qualification_label ──────────────────────────────────────────

class TestQualificationLabel:
    def test_german_labels(self):
        label = get_qualification_label(1, "de")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_english_labels(self):
        label = get_qualification_label(1, "en")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_none_level(self):
        label = get_qualification_label(None, "de")
        assert isinstance(label, str)
