"""
Tests for lib/faq_candidate_detector.py — FAQ candidate detection signals.
"""
import pytest
from lib.faq_candidate_detector import (
    detect_positive_feedback,
    is_substantive_question,
    detect_interesting_exchange,
)


# ── detect_positive_feedback ─────────────────────────────────────────

class TestDetectPositiveFeedback:
    def test_danke(self):
        assert detect_positive_feedback("Danke, das hilft!") is True

    def test_thanks(self):
        assert detect_positive_feedback("Thanks, very helpful!") is True

    def test_super(self):
        assert detect_positive_feedback("Super, genau das brauchte ich") is True

    def test_emoji(self):
        assert detect_positive_feedback("👍") is True

    def test_neutral_message(self):
        assert detect_positive_feedback("Tell me about software jobs") is False

    def test_question(self):
        assert detect_positive_feedback("What jobs are in Berlin?") is False


# ── is_substantive_question ──────────────────────────────────────────

class TestIsSubstantiveQuestion:
    def test_long_question(self):
        assert is_substantive_question("Was für Qualifikationen brauche ich für eine Stelle als Entwickler?") is True

    def test_short_not_substantive(self):
        assert is_substantive_question("Hi?") is False

    def test_short_message(self):
        assert is_substantive_question("How?") is False

    def test_statement_not_question(self):
        assert is_substantive_question("I am looking for a job in Berlin as a developer") is False

    def test_english_question(self):
        assert is_substantive_question("How can I improve my chances at getting matched with a posting?") is True


# ── detect_interesting_exchange ──────────────────────────────────────

class TestDetectInterestingExchange:
    def test_positive_feedback_flags_previous(self):
        prev = ("Was brauche ich als Entwickler?", "Als Entwickler benötigst du in der Regel eine Ausbildung in Informatik oder verwandten Fächern.")
        is_interesting, reason = detect_interesting_exchange(
            "Danke, das ist super hilfreich!",
            "Gern geschehen!",
            previous_exchange=prev,
        )
        assert is_interesting is True
        assert reason == "positive_feedback"

    def test_fallback_flags_knowledge_gap(self):
        is_interesting, reason = detect_interesting_exchange(
            "Welche Zertifizierungen sind für Cloud-Architekten am wichtigsten?",
            "Das weiß ich leider nicht genau.",
            was_fallback=True,
        )
        assert is_interesting is True
        assert reason == "low_match"

    def test_greeting_not_interesting(self):
        is_interesting, reason = detect_interesting_exchange(
            "Hallo!",
            "Hallo! Wie kann ich helfen?",
        )
        assert is_interesting is False
        assert reason is None

    def test_short_message_not_interesting(self):
        is_interesting, reason = detect_interesting_exchange(
            "ok",
            "Alles klar!",
        )
        assert is_interesting is False
        assert reason is None

    def test_no_previous_exchange_no_positive_flag(self):
        is_interesting, reason = detect_interesting_exchange(
            "Danke dir!",
            "Gern geschehen!",
            previous_exchange=None,
        )
        # Without previous exchange context, positive feedback alone doesn't trigger
        assert is_interesting is False

    def test_normal_question_no_fallback(self):
        is_interesting, reason = detect_interesting_exchange(
            "Welche Jobs gibt es als Krankenpfleger in Hamburg?",
            "Hier sind einige aktuelle Stellen...",
            was_fallback=False,
        )
        assert is_interesting is False
