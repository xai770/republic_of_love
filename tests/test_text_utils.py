"""
Tests for core/text_utils.py — encoding fixes, normalization, extraction, matching.
"""
import pytest
from core.text_utils import (
    fix_encoding,
    clean_whitespace,
    sanitize_for_storage,
    normalize_extraction,
    normalize_for_match,
    detect_language,
    verify_quote_in_source,
    verify_quotes_batch,
    clean_json_from_llm,
    truncate_text,
)


# ── fix_encoding ──────────────────────────────────────────────────────

class TestFixEncoding:
    def test_german_umlauts(self):
        assert fix_encoding("Ã¼ber") == "über"
        assert fix_encoding("Ã¤rztlich") == "ärztlich"
        assert fix_encoding("Ã¶ffnen") == "öffnen"

    def test_uppercase_umlauts(self):
        assert fix_encoding("Ãœbung") == "Übung"

    def test_html_entities(self):
        assert fix_encoding("Tom &amp; Jerry") == "Tom & Jerry"
        assert fix_encoding("&lt;b&gt;bold&lt;/b&gt;") == "<b>bold</b>"
        assert fix_encoding("&quot;quoted&quot;") == '"quoted"'

    def test_clean_text_unchanged(self):
        assert fix_encoding("Normal text") == "Normal text"

    def test_empty_and_none(self):
        assert fix_encoding("") == ""
        assert fix_encoding(None) is None

    def test_smart_quotes(self):
        result = fix_encoding("â€™")
        assert "â" not in result  # Should be replaced


# ── clean_whitespace ──────────────────────────────────────────────────

class TestCleanWhitespace:
    def test_multiple_spaces(self):
        assert clean_whitespace("hello   world") == "hello world"

    def test_tabs(self):
        assert clean_whitespace("hello\tworld") == "hello world"

    def test_multiple_newlines(self):
        assert clean_whitespace("a\n\n\n\nb") == "a\n\nb"

    def test_windows_line_endings(self):
        assert clean_whitespace("a\r\nb") == "a\nb"

    def test_leading_trailing(self):
        assert clean_whitespace("  hello  ") == "hello"

    def test_empty(self):
        assert clean_whitespace("") == ""
        assert clean_whitespace(None) is None


# ── sanitize_for_storage ─────────────────────────────────────────────

class TestSanitizeForStorage:
    def test_combines_both(self):
        result = sanitize_for_storage("Ã¼ber   die   Arbeit")
        assert result == "über die Arbeit"

    def test_empty(self):
        assert sanitize_for_storage("") == ""
        assert sanitize_for_storage(None) is None


# ── normalize_extraction ─────────────────────────────────────────────

class TestNormalizeExtraction:
    def test_underscores(self):
        assert normalize_extraction("budget_management") == "budget management"

    def test_newline_split(self):
        result = normalize_extraction("java\npython")
        assert result == "java, python"

    def test_sorts_alphabetically(self):
        result = normalize_extraction("python\njava")
        assert result == "java, python"

    def test_none_values(self):
        assert normalize_extraction("NONE") == "NONE"
        assert normalize_extraction("none") == "NONE"
        assert normalize_extraction("") == "NONE"
        assert normalize_extraction(None) == "NONE"

    def test_filters_none_items(self):
        result = normalize_extraction("team_player\nNONE")
        assert result == "team player"

    def test_mixed_separators(self):
        result = normalize_extraction("a,b\nc")
        assert result == "a, b, c"


# ── normalize_for_match ──────────────────────────────────────────────

class TestNormalizeForMatch:
    def test_lowercase_strip_punctuation(self):
        assert normalize_for_match("Hello, World!") == "hello world"

    def test_collapses_whitespace(self):
        assert normalize_for_match("Hello  World") == "hello world"

    def test_empty(self):
        assert normalize_for_match("") == ""
        assert normalize_for_match(None) == ""

    def test_unicode_punctuation(self):
        # Smart quotes should be stripped
        result = normalize_for_match("it\u2019s great")
        assert "great" in result


# ── detect_language ──────────────────────────────────────────────────

class TestDetectLanguage:
    def test_german_umlauts(self):
        assert detect_language("Das ist deutscher Text mit Ümlauten") == "de"

    def test_english_default(self):
        assert detect_language("") == "en"

    def test_plain_english(self):
        assert detect_language("This is a plain English text") == "en"

    def test_eszett(self):
        assert detect_language("Straße") == "de"


# ── verify_quote_in_source ──────────────────────────────────────────

class TestVerifyQuote:
    def test_exact_match(self):
        assert verify_quote_in_source("Hello World", "Say Hello World today") is True

    def test_no_match(self):
        assert verify_quote_in_source("Goodbye", "Hello World") is False

    def test_too_short(self):
        assert verify_quote_in_source("Hi", "Say Hi") is False

    def test_normalized_match(self):
        # Whitespace differences should still match after normalization
        assert verify_quote_in_source("Hello World!", "Say Hello World! today", min_length=5) is True


# ── verify_quotes_batch ──────────────────────────────────────────────

class TestVerifyQuotesBatch:
    def test_batch(self):
        source = "The quick brown fox jumps over the lazy dog"
        reqs = [
            {"quote": "quick brown fox"},
            {"quote": "purple elephant rides"},
        ]
        verified, unverified = verify_quotes_batch(reqs, source)
        assert len(verified) == 1
        assert len(unverified) == 1

    def test_empty(self):
        verified, unverified = verify_quotes_batch([], "some text")
        assert verified == []
        assert unverified == []


# ── clean_json_from_llm ─────────────────────────────────────────────

class TestCleanJsonFromLLM:
    def test_markdown_code_block(self):
        assert clean_json_from_llm("```json\n[1,2,3]\n```") == "[1,2,3]"

    def test_embedded_object(self):
        result = clean_json_from_llm('Here is the result: {"a": 1}')
        assert result == '{"a": 1}'

    def test_none_input(self):
        assert clean_json_from_llm(None) is None
        assert clean_json_from_llm("") is None

    def test_plain_json(self):
        assert clean_json_from_llm('{"key": "val"}') == '{"key": "val"}'

    def test_array(self):
        assert clean_json_from_llm("[1, 2, 3]") == "[1, 2, 3]"


# ── truncate_text ────────────────────────────────────────────────────

class TestTruncateText:
    def test_short_text(self):
        assert truncate_text("hello", 10) == "hello"

    def test_exact_length(self):
        assert truncate_text("hello", 5) == "hello"

    def test_truncated(self):
        result = truncate_text("hello world", 8)
        assert result.endswith("...")
        assert len(result) == 8

    def test_custom_suffix(self):
        result = truncate_text("hello world", 9, suffix="…")
        assert result.endswith("…")

    def test_empty(self):
        assert truncate_text("", 10) == ""
        assert truncate_text(None, 10) == ""
