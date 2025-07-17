#!/usr/bin/env python3
"""
Quick Batch Test for Enhanced Prototype
=====================================

Quick test of the enhanced prototype across multiple job files.
"""

import json
import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_requirements_extraction import EnhancedRequirementsExtractor, EnhancedLocationValidator

def quick_batch_test():
    """Quick test of enhanced prototype on multiple jobs."""
    
    inbox_path = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/inbox')
    job_files = list(inbox_path.glob('job*.json'))[:5]  # Test first 5 jobs
    
    extractor = EnhancedRequirementsExtractor()
    validator = EnhancedLocationValidator()
    
    print("=== ENHANCED PROTOTYPE QUICK BATCH TEST ===\n")
    
    results_summary = {
        'total_jobs': 0,
        'location_valid': 0,
        'avg_tech_requirements': 0,
        'avg_soft_skills': 0,
        'jobs_with_experience': 0,
        'jobs_with_business_req': 0
    }
    
    for job_file in job_files:
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            job_id = job_data['job_metadata']['job_id']
            job_description = job_data['job_content']['description']
            metadata_location = job_data['job_content']['location']
            
            # Extract requirements
            requirements = extractor.extract_requirements(job_description)
            
            # Validate location
            is_valid, confidence, details = validator.validate_location(metadata_location, job_description)
            
            # Update summary stats
            results_summary['total_jobs'] += 1
            if is_valid:
                results_summary['location_valid'] += 1
            results_summary['avg_tech_requirements'] += len(requirements.technical)
            results_summary['avg_soft_skills'] += len(requirements.soft_skills)
            if requirements.experience:
                results_summary['jobs_with_experience'] += 1
            if requirements.business:
                results_summary['jobs_with_business_req'] += 1
            
            print(f"Job {job_id}:")
            print(f"  Tech Requirements: {len(requirements.technical)}")
            print(f"  Soft Skills: {len(requirements.soft_skills)} (deduplicated)")
            print(f"  Experience Requirements: {len(requirements.experience)}")
            print(f"  Business Requirements: {len(requirements.business)}")
            print(f"  Location Valid: {is_valid} (confidence: {confidence:.2f})")
            print()
            
        except Exception as e:
            print(f"Error processing {job_file.name}: {e}")
    
    # Calculate averages
    total = results_summary['total_jobs']
    if total > 0:
        results_summary['avg_tech_requirements'] /= total
        results_summary['avg_soft_skills'] /= total
        results_summary['location_success_rate'] = results_summary['location_valid'] / total
    
    print("=== ENHANCED PROTOTYPE PERFORMANCE SUMMARY ===")
    print(f"Location Validation Success Rate: {results_summary['location_success_rate']:.1%}")
    print(f"Average Technical Requirements per Job: {results_summary['avg_tech_requirements']:.1f}")
    print(f"Average Soft Skills per Job (deduplicated): {results_summary['avg_soft_skills']:.1f}")
    print(f"Jobs with Experience Requirements: {results_summary['jobs_with_experience']}/{total}")
    print(f"Jobs with Business Requirements: {results_summary['jobs_with_business_req']}/{total}")
    
    return results_summary

if __name__ == "__main__":
    quick_batch_test()
