#!/usr/bin/env python3
"""
Main entry point for the requirements extraction system.

This module provides the main interface for testing and using the
5-dimensional requirements extraction system.

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

import json
import sys
from pathlib import Path
from dataclasses import asdict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from requirements_extraction_v2.models import FiveDimensionalRequirements
from requirements_extraction_v2.extractor import EnhancedRequirementsExtractor
from requirements_extraction_v2.location_validator import EnhancedLocationValidator


def test_enhanced_extraction():
    """Test the enhanced extraction system with a sample job."""
    
    # Load sample job
    job_file = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/inbox/job59428.json')
    
    if not job_file.exists():
        print(f"Error: Job file not found: {job_file}")
        return False
    
    try:
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
    except Exception as e:
        print(f"Error loading job file: {e}")
        return False
    
    job_description = job_data['job_content']['description']
    metadata_location = job_data['job_content']['location']
    
    print("=== ENHANCED 5-DIMENSIONAL REQUIREMENTS EXTRACTION v2.0 ===\n")
    
    # Test enhanced requirements extraction
    try:
        extractor = EnhancedRequirementsExtractor()
        requirements = extractor.extract_requirements(job_description)
        
        print("TECHNICAL REQUIREMENTS:")
        for req in requirements.technical:
            print(f"  - {req.skill} ({req.category}, {req.proficiency_level}, mandatory: {req.is_mandatory})")
        
        print(f"\nBUSINESS REQUIREMENTS (CONSOLIDATED):")
        for req in requirements.business:
            print(f"  - {req.domain} ({req.experience_type}): {req.years_required} years")
        
        print(f"\nSOFT SKILLS (DEDUPLICATED):")
        for req in requirements.soft_skills:
            print(f"  - {req.skill} ({req.importance})")
        
        print(f"\nEXPERIENCE REQUIREMENTS:")
        for req in requirements.experience:
            print(f"  - {req.type}: {req.description}")
        
        print(f"\nEDUCATION REQUIREMENTS (CONSOLIDATED):")
        for req in requirements.education:
            print(f"  - {req.level} in {req.field} (mandatory: {req.is_mandatory})")
        
        # Test enhanced location validation
        print("\n=== ENHANCED LOCATION VALIDATION ===\n")
        
        validator = EnhancedLocationValidator()
        is_valid, confidence, details = validator.validate_location(metadata_location, job_description)
        
        print(f"Metadata Location: {metadata_location}")
        print(f"Validation Result: {is_valid}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Details: {details}")
        
        # Export enhanced results
        results = {
            'job_id': job_data['job_metadata']['job_id'],
            'version': '2.0_modular',
            'requirements': asdict(requirements),
            'location_validation': {
                'is_valid': is_valid,
                'confidence': confidence,
                'details': details,
                'metadata_location': metadata_location
            },
            'improvements': {
                'modular_architecture': True,
                'german_patterns': True,
                'soft_skills_deduplication': True,
                'enhanced_experience_extraction': True,
                'business_domain_detection': True,
                'business_requirements_consolidation': True,
                'education_requirements_consolidation': True
            }
        }
        
        output_file = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/outbox/modular_extraction_results.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nModular extraction results exported to: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_from_job_data(job_data: dict) -> dict:
    """
    Extract requirements from job data dictionary.
    
    Args:
        job_data: Dictionary containing job information
        
    Returns:
        Dictionary containing extracted requirements and validation results
    """
    try:
        job_description = job_data['job_content']['description']
        metadata_location = job_data['job_content']['location']
        
        # Extract requirements
        extractor = EnhancedRequirementsExtractor()
        requirements = extractor.extract_requirements(job_description)
        
        # Validate location
        validator = EnhancedLocationValidator()
        is_valid, confidence, details = validator.validate_location(metadata_location, job_description)
        
        return {
            'job_id': job_data['job_metadata']['job_id'],
            'version': '2.0_modular',
            'requirements': asdict(requirements),
            'location_validation': {
                'is_valid': is_valid,
                'confidence': confidence,
                'details': details,
                'metadata_location': metadata_location
            },
            'success': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'job_id': job_data.get('job_metadata', {}).get('job_id', 'unknown'),
            'version': '2.0_modular',
            'success': False,
            'error': str(e)
        }


def extract_from_file(file_path: str) -> dict:
    """
    Extract requirements from a job file.
    
    Args:
        file_path: Path to the job JSON file
        
    Returns:
        Dictionary containing extracted requirements and validation results
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        return extract_from_job_data(job_data)
        
    except Exception as e:
        return {
            'job_id': 'unknown',
            'version': '2.0_modular',
            'success': False,
            'error': f"File loading error: {str(e)}"
        }


def main():
    """Main function for testing and demonstration."""
    if len(sys.argv) > 1:
        # If file path provided, process that file
        file_path = sys.argv[1]
        result = extract_from_file(file_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Run standard test
        success = test_enhanced_extraction()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
