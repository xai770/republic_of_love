#!/usr/bin/env python3
"""
Unit tests for the requirements extraction system.

This module contains comprehensive unit tests for all components of the
5-dimensional requirements extraction system.

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from requirements_extraction_v2.models import (
    TechnicalRequirement, BusinessRequirement, SoftSkillRequirement,
    ExperienceRequirement, EducationRequirement, FiveDimensionalRequirements
)
from requirements_extraction_v2.extractor import EnhancedRequirementsExtractor
from requirements_extraction_v2.location_validator import EnhancedLocationValidator
from requirements_extraction_v2.utils import (
    normalize_text, get_context, determine_proficiency, is_mandatory,
    extract_years_from_context, consolidate_business_requirements,
    consolidate_education_requirements
)


class TestUtils(unittest.TestCase):
    """Test utility functions."""
    
    def test_normalize_text(self):
        """Test text normalization."""
        text = "  Multiple   spaces\n\nand\tlines  "
        normalized = normalize_text(text)
        self.assertEqual(normalized, "Multiple spaces and lines")
    
    def test_get_context(self):
        """Test context extraction."""
        text = "This is a test text for context extraction testing."
        context = get_context(text, 10, 14, window=5)
        self.assertIn("test", context)
        self.assertTrue(len(context) <= 15)  # 5 + 4 + 5 + margin
    
    def test_determine_proficiency(self):
        """Test proficiency determination."""
        self.assertEqual(determine_proficiency("expert level required"), "expert")
        self.assertEqual(determine_proficiency("good knowledge of"), "advanced")
        self.assertEqual(determine_proficiency("basic understanding"), "intermediate")
        self.assertEqual(determine_proficiency("some experience"), "intermediate")
    
    def test_is_mandatory(self):
        """Test mandatory requirement detection."""
        self.assertTrue(is_mandatory("this is required"))
        self.assertTrue(is_mandatory("muss haben"))
        self.assertFalse(is_mandatory("nice to have"))
        self.assertFalse(is_mandatory("wünschenswert"))
    
    def test_extract_years_from_context(self):
        """Test years extraction."""
        self.assertEqual(extract_years_from_context("5 Jahre Erfahrung"), 5)
        self.assertEqual(extract_years_from_context("3 years experience"), 3)
        self.assertEqual(extract_years_from_context("no years mentioned"), 0)
    
    def test_consolidate_business_requirements(self):
        """Test business requirements consolidation."""
        reqs = [
            {
                'domain': 'banking',
                'experience_type': 'industry',
                'years_required': 3,
                'is_mandatory': True,
                'confidence': 0.8,
                'context': 'First context'
            },
            {
                'domain': 'banking',
                'experience_type': 'industry',
                'years_required': 5,
                'is_mandatory': False,
                'confidence': 0.9,
                'context': 'Second context'
            }
        ]
        
        consolidated = consolidate_business_requirements(reqs)
        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated[0]['years_required'], 5)  # Max years
        self.assertEqual(consolidated[0]['confidence'], 0.9)  # Max confidence
        self.assertTrue(consolidated[0]['is_mandatory'])  # Any mandatory = True


class TestLocationValidator(unittest.TestCase):
    """Test location validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = EnhancedLocationValidator()
    
    def test_validate_location_with_city(self):
        """Test location validation with city match."""
        location = {'city': 'Frankfurt', 'state': 'Hessen', 'country': 'Deutschland'}
        text = "This position is located in Frankfurt am Main, Germany."
        
        is_valid, confidence, details = self.validator.validate_location(location, text)
        self.assertTrue(is_valid)
        self.assertGreater(confidence, 0.6)
        self.assertIn("Frankfurt", details)
    
    def test_validate_location_no_match(self):
        """Test location validation with no matches."""
        location = {'city': 'Munich', 'state': 'Bayern', 'country': 'Deutschland'}
        text = "This position is located in Berlin, Germany."
        
        is_valid, confidence, details = self.validator.validate_location(location, text)
        # Should be invalid since Munich is not in Berlin text
        self.assertFalse(is_valid)
    
    def test_validate_location_german_variants(self):
        """Test location validation with German variants."""
        location = {'city': 'München', 'state': 'Bayern', 'country': 'Deutschland'}
        text = "We are looking for candidates in Munich, Bavaria."
        
        is_valid, confidence, details = self.validator.validate_location(location, text)
        self.assertTrue(is_valid)
        self.assertIn("München", details)


class TestRequirementsExtractor(unittest.TestCase):
    """Test requirements extraction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = EnhancedRequirementsExtractor()
    
    def test_extract_technical_requirements(self):
        """Test technical requirements extraction."""
        text = "We need someone with Python, SQL, and AWS experience."
        requirements = self.extractor._extract_technical_requirements(text)
        
        skills = [req.skill for req in requirements]
        self.assertIn("Python", skills)
        self.assertIn("SQL", skills)
        self.assertIn("AWS", skills)
    
    def test_extract_business_requirements(self):
        """Test business requirements extraction."""
        text = "Banking experience required with 5 Jahre Erfahrung in finance."
        requirements = self.extractor._extract_business_requirements(text)
        
        domains = [req.domain for req in requirements]
        self.assertIn("banking", domains)
    
    def test_extract_soft_skills_deduplicated(self):
        """Test soft skills extraction with deduplication."""
        text = "Strong communication skills and good communication abilities required."
        requirements = self.extractor._extract_soft_skills_deduplicated(text)
        
        # Should only have one communication skill due to deduplication
        skills = [req.skill for req in requirements]
        communication_count = sum(1 for skill in skills if 'communication' in skill.lower())
        self.assertEqual(communication_count, 1)
    
    def test_extract_experience_requirements(self):
        """Test experience requirements extraction."""
        text = "5 Jahre Erfahrung required with senior level expertise."
        requirements = self.extractor._extract_experience_requirements(text)
        
        # Should find both general experience and senior level
        types = [req.type for req in requirements]
        self.assertIn("general_experience", types)
        self.assertIn("senior_level", types)
    
    def test_extract_education_requirements(self):
        """Test education requirements extraction."""
        text = "Bachelor in Computer Science or Master in Informatik required."
        requirements = self.extractor._extract_education_requirements(text)
        
        levels = [req.level for req in requirements]
        self.assertIn("bachelor", levels)
        self.assertIn("master", levels)
    
    def test_full_extraction_workflow(self):
        """Test complete extraction workflow."""
        text = """
        We are looking for a Senior Python Developer with 5 Jahre Erfahrung in banking.
        Requirements:
        - Bachelor in Computer Science
        - Strong communication skills
        - AWS and SQL experience
        - Team leadership abilities
        """
        
        requirements = self.extractor.extract_requirements(text)
        
        # Check that all dimensions are populated
        self.assertIsInstance(requirements, FiveDimensionalRequirements)
        self.assertGreater(len(requirements.technical), 0)
        self.assertGreater(len(requirements.business), 0)
        self.assertGreater(len(requirements.soft_skills), 0)
        self.assertGreater(len(requirements.experience), 0)
        self.assertGreater(len(requirements.education), 0)


class TestDataModels(unittest.TestCase):
    """Test data model classes."""
    
    def test_technical_requirement_creation(self):
        """Test TechnicalRequirement creation."""
        req = TechnicalRequirement(
            skill="Python",
            proficiency_level="advanced",
            category="programming",
            is_mandatory=True,
            confidence=0.9,
            context="Strong Python skills required"
        )
        
        self.assertEqual(req.skill, "Python")
        self.assertEqual(req.proficiency_level, "advanced")
        self.assertTrue(req.is_mandatory)
    
    def test_five_dimensional_requirements_creation(self):
        """Test FiveDimensionalRequirements creation."""
        tech_req = TechnicalRequirement(
            skill="Python", proficiency_level="advanced", category="programming",
            is_mandatory=True, confidence=0.9, context="test"
        )
        
        requirements = FiveDimensionalRequirements(
            technical=[tech_req],
            business=[],
            soft_skills=[],
            experience=[],
            education=[]
        )
        
        self.assertEqual(len(requirements.technical), 1)
        self.assertEqual(requirements.technical[0].skill, "Python")


class TestConsolidation(unittest.TestCase):
    """Test consolidation functionality."""
    
    def test_business_requirements_consolidation(self):
        """Test business requirements consolidation removes duplicates."""
        extractor = EnhancedRequirementsExtractor()
        
        # Create test requirements
        from requirements_extraction_v2.models import BusinessRequirement
        
        reqs = [
            BusinessRequirement(
                domain="banking",
                experience_type="industry",
                years_required=3,
                is_mandatory=True,
                confidence=0.8,
                context="First mention"
            ),
            BusinessRequirement(
                domain="banking",
                experience_type="industry",
                years_required=5,
                is_mandatory=False,
                confidence=0.9,
                context="Second mention"
            )
        ]
        
        consolidated = extractor._consolidate_business_requirements(reqs)
        
        # Should consolidate to one requirement
        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated[0].years_required, 5)  # Take max years
        self.assertTrue(consolidated[0].is_mandatory)  # Any mandatory = True
    
    def test_education_requirements_consolidation(self):
        """Test education requirements consolidation removes duplicates."""
        extractor = EnhancedRequirementsExtractor()
        
        # Create test requirements
        from requirements_extraction_v2.models import EducationRequirement
        
        reqs = [
            EducationRequirement(
                level="bachelor",
                field="Computer Science",
                is_mandatory=True,
                alternatives=[],
                confidence=0.8
            ),
            EducationRequirement(
                level="bachelor",
                field="Computer Science",
                is_mandatory=False,
                alternatives=["Informatik"],
                confidence=0.9
            )
        ]
        
        consolidated = extractor._consolidate_education_requirements(reqs)
        
        # Should consolidate to one requirement
        self.assertEqual(len(consolidated), 1)
        self.assertTrue(consolidated[0].is_mandatory)  # Any mandatory = True
        self.assertIn("Informatik", consolidated[0].alternatives)  # Merge alternatives


def run_tests():
    """Run all tests."""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestUtils,
        TestLocationValidator,
        TestRequirementsExtractor,
        TestDataModels,
        TestConsolidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
