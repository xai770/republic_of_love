"""
Tests for Tier 2 intent detection, search intent extraction,
and timeline formatting.
"""
import unittest
from core.mira_llm import (
    detect_tier2_intent,
    extract_search_intent,
    _format_event,
    _compose_search_reply,
)


class TestDetectTier2Intent(unittest.TestCase):
    """Test Tier 2 on-demand intent detection."""

    # ── Profile ──
    def test_profile_german_du(self):
        self.assertEqual(detect_tier2_intent("Zeig mir mein Profil"), 'profile_detail')

    def test_profile_german_was_steht(self):
        self.assertEqual(detect_tier2_intent("Was steht in meinem Profil?"), 'profile_detail')

    def test_profile_english(self):
        self.assertEqual(detect_tier2_intent("Show me my profile"), 'profile_detail')

    def test_profile_english_whats(self):
        self.assertEqual(detect_tier2_intent("What's in my profile?"), 'profile_detail')

    # ── Match detail ──
    def test_match_german(self):
        self.assertEqual(detect_tier2_intent("Was sind meine besten Matches?"), 'match_detail')

    def test_match_english(self):
        self.assertEqual(detect_tier2_intent("Tell me about my matches"), 'match_detail')

    def test_match_why(self):
        self.assertEqual(detect_tier2_intent("Why did I match with that job?"), 'match_detail')

    def test_match_top(self):
        self.assertEqual(detect_tier2_intent("My top match"), 'match_detail')

    # ── Doug messages ──
    def test_doug_german(self):
        self.assertEqual(detect_tier2_intent("Was hat Doug geschrieben?"), 'doug_messages')

    def test_doug_english(self):
        self.assertEqual(detect_tier2_intent("What did Doug find?"), 'doug_messages')

    def test_doug_report(self):
        self.assertEqual(detect_tier2_intent("Doug's report"), 'doug_messages')

    # ── My messages / inbox ──
    def test_inbox_german(self):
        self.assertEqual(detect_tier2_intent("Habe ich neue Nachrichten?"), 'my_messages')

    def test_inbox_english(self):
        self.assertEqual(detect_tier2_intent("Any new messages?"), 'my_messages')

    def test_inbox_check(self):
        self.assertEqual(detect_tier2_intent("Check my inbox"), 'my_messages')

    # ── No intent ──
    def test_greeting_no_intent(self):
        self.assertIsNone(detect_tier2_intent("Hallo!"))

    def test_casual_no_intent(self):
        self.assertIsNone(detect_tier2_intent("How are you?"))

    def test_job_search_no_tier2(self):
        self.assertIsNone(detect_tier2_intent("Ich suche Jobs in Berlin"))

    def test_empty(self):
        self.assertIsNone(detect_tier2_intent(""))


class TestExtractSearchIntent(unittest.TestCase):
    """Test search intent extraction (domain, city, QL)."""

    def test_pflege_muenchen(self):
        result = extract_search_intent("Pflegejobs in München")
        self.assertIsNotNone(result)
        self.assertIn('set_filters', result)
        filters = result['set_filters']
        self.assertIn('domains', filters)
        self.assertIn('city', filters)

    def test_it_berlin(self):
        result = extract_search_intent("IT Jobs in Berlin")
        self.assertIsNotNone(result)
        filters = result['set_filters']
        self.assertIn('domains', filters)

    def test_english_nursing(self):
        result = extract_search_intent("nursing jobs in Frankfurt")
        self.assertIsNotNone(result)

    def test_greeting_no_search(self):
        result = extract_search_intent("Hallo, wie geht's?")
        self.assertIsNone(result)

    def test_city_only(self):
        result = extract_search_intent("Jobs in Hamburg")
        self.assertIsNotNone(result)
        filters = result['set_filters']
        self.assertIn('city', filters)

    def test_ql_ausbildung(self):
        result = extract_search_intent("Ausbildungsstellen in der Pflege")
        self.assertIsNotNone(result)

    def test_domain_gesundheit(self):
        result = extract_search_intent("Gesundheit Jobs")
        self.assertIsNotNone(result)


class TestFormatEvent(unittest.TestCase):
    """Test behavioral event formatting."""

    def test_page_view(self):
        self.assertEqual(_format_event('page_view', {'page': '/search'}), "Visited /search")

    def test_search_filter(self):
        text = _format_event('search_filter', {'domains': ['81'], 'city': 'Berlin', 'results': 42})
        self.assertIn('Berlin', text)
        self.assertIn('42', text)

    def test_posting_view(self):
        text = _format_event('posting_view', {'title': 'Backend Developer'})
        self.assertIn('Backend Developer', text)

    def test_login(self):
        self.assertEqual(_format_event('login', {}), "Logged in")

    def test_match_action(self):
        text = _format_event('match_action', {'action': 'save'})
        self.assertIn('save', text)

    def test_unknown_event(self):
        self.assertIsNone(_format_event('unknown_thing', {}))


class TestComposeSearchReply(unittest.TestCase):
    """Test deterministic search reply composition."""

    def test_german_du(self):
        actions = {'set_filters': {'domains': ['81', '82'], 'city': 'München', 'lat': 48.14, 'lon': 11.58}}
        reply = _compose_search_reply(actions, 'de', True)
        self.assertIn('München', reply)
        self.assertNotIn('None', reply)

    def test_english(self):
        actions = {'set_filters': {'domains': ['43'], 'city': 'Berlin', 'lat': 52.52, 'lon': 13.41}}
        reply = _compose_search_reply(actions, 'en', False)
        self.assertIn('Berlin', reply)

    def test_domain_only_german(self):
        actions = {'set_filters': {'domains': ['62']}}
        reply = _compose_search_reply(actions, 'de', False)
        self.assertIsInstance(reply, str)
        self.assertTrue(len(reply) > 10)


if __name__ == '__main__':
    unittest.main()
