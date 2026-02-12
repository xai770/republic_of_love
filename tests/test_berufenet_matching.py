"""
Unit tests for lib/berufenet_matching.py — pure functions, no DB needed.
"""
import pytest
from lib.berufenet_matching import (
    clean_job_title,
    get_qualification_level_name,
    classify_match_confidence,
)


class TestCleanJobTitle:
    """Test the title cleaning / normalization logic."""

    def test_strips_gender_suffix_mwd(self):
        assert clean_job_title("Koch (m/w/d)") == "Koch"

    def test_strips_gender_suffix_mfd(self):
        assert clean_job_title("Schlosser (m/f/d)") == "Schlosser"

    def test_strips_gender_suffix_with_spaces(self):
        assert clean_job_title("Elektriker  (m/w/d)") == "Elektriker"

    def test_strips_star_gender(self):
        assert clean_job_title("Mitarbeiter*in") == "Mitarbeiter"

    def test_strips_star_gender_with_continuation(self):
        assert clean_job_title("Ingenieur*in Maschinenbau") == "Ingenieur Maschinenbau"

    def test_strips_slash_in_suffix(self):
        assert clean_job_title("Staplerfahrer/in (m/w/d)") == "Staplerfahrer"

    def test_strips_dash_mwd_no_parens(self):
        assert clean_job_title("Elektroniker - m/w/d") == "Elektroniker"

    def test_strips_comma_separated_gender(self):
        assert clean_job_title("Elektroniker (m,w,d)") == "Elektroniker"

    def test_strips_pipe_separated_gender(self):
        assert clean_job_title("Elektroniker (m|w|d)") == "Elektroniker"

    def test_removes_empty_parens(self):
        assert clean_job_title("Elektrotechniker () Betriebstechnik") == "Elektrotechniker Betriebstechnik"

    def test_strips_euro_salary(self):
        assert clean_job_title("Elektroniker (m/w/d) 23,23€ Std. brutto") == "Elektroniker"

    def test_strips_price_range(self):
        assert clean_job_title("Elektroniker (m/w/d) 20,30 - 29,12€/h") == "Elektroniker"

    def test_strips_date_suffix(self):
        assert clean_job_title("Elektroniker (m/w/d) ab Januar 2026") == "Elektroniker"

    def test_strips_pipe_sections(self):
        result = clean_job_title("Elektroniker (m/w/d) Automatisierungstechnik | MSR - Technik | Gebäudeautomation")
        assert result == "Elektroniker Automatisierungstechnik"

    def test_preserves_slash_compound(self):
        result = clean_job_title("Elektroniker / Mechatroniker Sicherheitstechnik (w/m/d)")
        assert result == "Elektroniker / Mechatroniker Sicherheitstechnik"

    def test_preserves_meaningful_content(self):
        result = clean_job_title("Senior Software Engineer")
        assert result == "Senior Software Engineer"

    def test_strips_whitespace(self):
        result = clean_job_title("  Koch (m/w/d)  ")
        assert result == "Koch"

    def test_empty_string(self):
        result = clean_job_title("")
        assert result == ""

    def test_none_handling(self):
        """Should handle None gracefully or raise clear error."""
        with pytest.raises((TypeError, AttributeError)):
            clean_job_title(None)


class TestQualificationLevel:
    """Test KLDB qualification level mapping."""

    def test_level_1(self):
        assert "Helfer" in get_qualification_level_name(1)

    def test_level_2(self):
        result = get_qualification_level_name(2)
        assert "Fachkraft" in result or "fachlich" in result.lower()

    def test_level_3(self):
        result = get_qualification_level_name(3)
        assert "Spezialist" in result or "komplex" in result.lower()

    def test_level_4(self):
        result = get_qualification_level_name(4)
        assert "Experte" in result or "hoch" in result.lower()

    def test_unknown_level(self):
        result = get_qualification_level_name(99)
        assert result is not None  # Should return something, not crash


class TestClassifyMatchConfidence:
    """Test score → confidence bucket mapping."""

    def test_high_score(self):
        level, _ = classify_match_confidence(0.95)
        assert level == "high"

    def test_medium_score(self):
        level, _ = classify_match_confidence(0.75)
        assert level == "medium"

    def test_low_score(self):
        level, _ = classify_match_confidence(0.40)
        assert level == "low"

    def test_boundary_high(self):
        level, _ = classify_match_confidence(0.85)
        assert level == "high"

    def test_returns_description(self):
        _, desc = classify_match_confidence(0.90)
        assert isinstance(desc, str)
        assert len(desc) > 0
