"""
Tests for onboarding + CV anonymization + PII detection.

Covers:
- Yogi name validation (length, characters, reserved names)
- Yogi name extraction from conversational messages
- PII detector (emails, phones, company names, clean text)
- CV anonymizer output structure validation
- Onboarding state detection
- Notification email extraction
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mira_llm import (
    validate_yogi_name,
    extract_yogi_name_from_message,
    detect_notification_email_response,
)
from core.pii_detector import PIIDetector
from core.cv_anonymizer import _extract_json, _validate_and_normalize, _flatten_to_text


# ─────────────────────────────────────────────────────────
# Yogi Name Validation
# ─────────────────────────────────────────────────────────

class TestValidateYogiName(unittest.TestCase):
    """Test yogi name validation rules."""
    
    def test_valid_simple(self):
        ok, err = validate_yogi_name("xai")
        self.assertTrue(ok)
        self.assertIsNone(err)
    
    def test_valid_with_numbers(self):
        ok, err = validate_yogi_name("luna42")
        self.assertTrue(ok)
    
    def test_valid_with_umlauts(self):
        ok, err = validate_yogi_name("müller")
        self.assertTrue(ok)
    
    def test_valid_with_dots(self):
        ok, err = validate_yogi_name("j.smith")
        self.assertTrue(ok)

    def test_valid_with_spaces(self):
        ok, err = validate_yogi_name("Blue Moon")
        self.assertTrue(ok)
    
    def test_too_short(self):
        ok, err = validate_yogi_name("x")
        self.assertFalse(ok)
        self.assertIn("2 characters", err)
    
    def test_too_long(self):
        ok, err = validate_yogi_name("a" * 25)
        self.assertFalse(ok)
        self.assertIn("20 characters", err)
    
    def test_empty(self):
        ok, err = validate_yogi_name("")
        self.assertFalse(ok)
    
    def test_none(self):
        ok, err = validate_yogi_name(None)
        self.assertFalse(ok)
    
    def test_reserved_mira(self):
        ok, err = validate_yogi_name("Mira")
        self.assertFalse(ok)
        self.assertIn("reserved", err)
    
    def test_reserved_admin(self):
        ok, err = validate_yogi_name("admin")
        self.assertFalse(ok)
    
    def test_reserved_doug(self):
        ok, err = validate_yogi_name("Doug")
        self.assertFalse(ok)


# ─────────────────────────────────────────────────────────
# Yogi Name Extraction from Messages
# ─────────────────────────────────────────────────────────

class TestExtractYogiName(unittest.TestCase):
    """Test extracting yogi name from conversational messages."""
    
    def test_plain_name(self):
        self.assertEqual(extract_yogi_name_from_message("xai"), "xai")
    
    def test_nenn_mich(self):
        self.assertEqual(extract_yogi_name_from_message("Nenn mich Luna"), "Luna")
    
    def test_call_me(self):
        self.assertEqual(extract_yogi_name_from_message("Call me Stellar"), "Stellar")
    
    def test_ich_bin(self):
        self.assertEqual(extract_yogi_name_from_message("Ich bin Max"), "Max")
    
    def test_im(self):
        self.assertEqual(extract_yogi_name_from_message("I'm Phoenix"), "Phoenix")
    
    def test_ich_heisse(self):
        self.assertEqual(extract_yogi_name_from_message("Ich heiße Yogi Bear"), "Yogi Bear")
    
    def test_my_name_is(self):
        self.assertEqual(extract_yogi_name_from_message("My name is Neo"), "Neo")
    
    def test_plain_two_words(self):
        self.assertEqual(extract_yogi_name_from_message("Blue Moon"), "Blue Moon")
    
    def test_strips_punctuation(self):
        self.assertEqual(extract_yogi_name_from_message("Luna!"), "Luna")
    
    def test_too_long_returns_none(self):
        result = extract_yogi_name_from_message("This is a very long response that doesn't contain a name at all and should return None")
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────
# PII Detector
# ─────────────────────────────────────────────────────────

class TestPIIDetector(unittest.TestCase):
    """Test the PII safety net."""
    
    def setUp(self):
        # No DB connection — uses hardcoded entity list only
        self.detector = PIIDetector(conn=None)
    
    def test_clean_text(self):
        text = "Senior software engineer with 12 years of experience in Python, Java, and cloud technologies."
        violations = self.detector.check(text)
        self.assertEqual(violations, [])
    
    def test_detects_email(self):
        text = "Contact: john.doe@gmail.com for more info"
        violations = self.detector.check(text)
        self.assertTrue(any('[email]' in v for v in violations))
    
    def test_detects_german_phone(self):
        text = "Telefon: +49 69 12345678"
        violations = self.detector.check(text)
        self.assertTrue(any('[phone' in v for v in violations))
    
    def test_detects_company_deutsche_bank(self):
        text = "Worked at Deutsche Bank for 5 years"
        violations = self.detector.check(text)
        self.assertTrue(any('deutsche bank' in v.lower() for v in violations))
    
    def test_detects_company_novartis(self):
        text = "Previously at Novartis in Basel"
        violations = self.detector.check(text)
        self.assertTrue(any('novartis' in v.lower() for v in violations))
    
    def test_detects_company_sap(self):
        text = "Senior developer at SAP with cloud experience"
        violations = self.detector.check(text)
        self.assertTrue(any('sap' in v.lower() for v in violations))
    
    def test_detects_university(self):
        text = "Graduated from INSEAD with MBA"
        violations = self.detector.check(text)
        self.assertTrue(any('insead' in v.lower() for v in violations))
    
    def test_detects_linkedin(self):
        text = "See my profile at linkedin.com/in/johndoe"
        violations = self.detector.check(text)
        self.assertTrue(any('[linkedin]' in v for v in violations))
    
    def test_detects_real_name(self):
        text = "Profile of a senior engineer"
        violations = self.detector.check(text, extra_names=["Gershon Pollatschek"])
        # Should not trigger since name is not in the text
        self.assertFalse(any('[real_name]' in v for v in violations))
    
    def test_detects_real_name_present(self):
        text = "Gershon is a senior engineer"
        violations = self.detector.check(text, extra_names=["Gershon Pollatschek"])
        self.assertTrue(any('[real_name]' in v for v in violations))
    
    def test_corpus_size(self):
        # Should have at least the hardcoded entities
        self.assertGreater(self.detector.corpus_size, 50)
    
    def test_anonymized_text_passes(self):
        """Text that's properly anonymized should pass."""
        text = ("12 years experience in risk management. "
                "Worked at a large German bank (4 years), "
                "a top-tier consulting firm (3 years). "
                "Skills: Python, PostgreSQL, AWS, Docker.")
        violations = self.detector.check(text)
        self.assertEqual(violations, [])


# ─────────────────────────────────────────────────────────
# CV Anonymizer Helpers
# ─────────────────────────────────────────────────────────

class TestExtractJson(unittest.TestCase):
    """Test JSON extraction from LLM responses."""
    
    def test_clean_json(self):
        result = _extract_json('{"skills": ["Python", "Java"]}')
        self.assertEqual(result['skills'], ["Python", "Java"])
    
    def test_json_with_markdown(self):
        result = _extract_json('```json\n{"skills": ["Python"]}\n```')
        self.assertIsNotNone(result)
        self.assertEqual(result['skills'], ["Python"])
    
    def test_json_with_preamble(self):
        result = _extract_json('Here is the result:\n{"skills": ["Go"]}')
        self.assertIsNotNone(result)
    
    def test_invalid_json(self):
        result = _extract_json('This is not JSON at all')
        self.assertIsNone(result)


class TestValidateAndNormalize(unittest.TestCase):
    """Test structure normalization of anonymized profiles."""
    
    def test_basic_structure(self):
        data = {
            'years_experience': 12,
            'career_level': 'senior',
            'skills': ['Python', 'PostgreSQL'],
            'work_history': [
                {'employer_description': 'a large German bank', 'role': 'Developer', 'duration_years': 4}
            ]
        }
        result = _validate_and_normalize(data, 'xai')
        self.assertEqual(result['yogi_name'], 'xai')
        self.assertEqual(result['years_experience'], 12)
        self.assertEqual(len(result['skills']), 2)
        self.assertEqual(len(result['work_history']), 1)
    
    def test_caps_skills_at_30(self):
        data = {'skills': [f'skill_{i}' for i in range(50)]}
        result = _validate_and_normalize(data, 'test')
        self.assertEqual(len(result['skills']), 30)
    
    def test_invalid_career_level_defaults_to_mid(self):
        data = {'career_level': 'wizard'}
        result = _validate_and_normalize(data, 'test')
        self.assertEqual(result['career_level'], 'mid')
    
    def test_insane_years_set_to_none(self):
        data = {'years_experience': 100}
        result = _validate_and_normalize(data, 'test')
        self.assertIsNone(result['years_experience'])
    
    def test_empty_input(self):
        result = _validate_and_normalize({}, 'test')
        self.assertEqual(result['yogi_name'], 'test')
        self.assertEqual(result['skills'], [])
        self.assertEqual(result['work_history'], [])


class TestFlattenToText(unittest.TestCase):
    """Test text flattening for PII checking."""
    
    def test_simple(self):
        data = {'name': 'xai', 'skills': ['Python', 'Java']}
        text = _flatten_to_text(data)
        self.assertIn('xai', text)
        self.assertIn('Python', text)
        self.assertIn('Java', text)
    
    def test_nested(self):
        data = {'work': [{'employer': 'a large bank', 'role': 'dev'}]}
        text = _flatten_to_text(data)
        self.assertIn('a large bank', text)


# ─────────────────────────────────────────────────────────
# Notification Email
# ─────────────────────────────────────────────────────────

class TestNotificationEmail(unittest.TestCase):
    """Test email extraction from yogi messages."""
    
    def test_email_provided(self):
        result = detect_notification_email_response("my.email@example.com")
        self.assertEqual(result, "my.email@example.com")
    
    def test_email_in_sentence(self):
        result = detect_notification_email_response("Sure, use test@yoga.de for notifications")
        self.assertEqual(result, "test@yoga.de")
    
    def test_decline_nein(self):
        result = detect_notification_email_response("Nein danke")
        self.assertEqual(result, 'decline')
    
    def test_decline_no(self):
        result = detect_notification_email_response("No thanks")
        self.assertEqual(result, 'decline')
    
    def test_decline_lieber_nicht(self):
        result = detect_notification_email_response("Lieber nicht")
        self.assertEqual(result, 'decline')
    
    def test_unrelated_message(self):
        result = detect_notification_email_response("Tell me about my matches")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
