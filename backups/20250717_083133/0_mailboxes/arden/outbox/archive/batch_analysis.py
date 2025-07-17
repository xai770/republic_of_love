#!/usr/bin/env python3
"""
Batch Analysis: 5D Requirements & Location Validation
===================================================

This script processes multiple job files to:
1. Test 5-dimensional requirements extraction across different jobs
2. Compare regex-based vs metadata location validation
3. Generate a comprehensive analysis report

Author: Investigation Team
Date: 2025-07-08
"""

import json
import glob
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from dataclasses import asdict

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from requirements_extraction_prototype import RequirementsExtractor, LocationValidator
except ImportError as e:
    print(f"Error importing prototype module: {e}")
    print("Make sure requirements_extraction_prototype.py is in the same directory")
    sys.exit(1)

def analyze_all_jobs():
    """Analyze all job files in the inbox."""
    
    inbox_path = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/inbox')
    job_files = list(inbox_path.glob('job*.json'))
    
    if not job_files:
        print("No job files found!")
        return
    
    print(f"Found {len(job_files)} job files to analyze...")
    
    extractor = RequirementsExtractor()
    validator = LocationValidator()
    
    results = []
    
    for job_file in job_files:
        print(f"Processing {job_file.name}...")
        
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            job_id = job_data['job_metadata']['job_id']
            job_description = job_data['job_content']['description']
            metadata_location = job_data['job_content']['location']
            job_title = job_data['job_content']['title']
            
            # Extract requirements
            requirements = extractor.extract_requirements(job_description)
            
            # Validate location
            is_valid, confidence, details = validator.validate_location(metadata_location, job_description)
            
            # Compile summary stats
            tech_count = len(requirements.technical)
            business_count = len(requirements.business)
            soft_skills_count = len(requirements.soft_skills)
            experience_count = len(requirements.experience)
            education_count = len(requirements.education)
            
            # Get unique technical categories
            tech_categories = list(set(req.category for req in requirements.technical))
            
            # Get programming languages
            programming_langs = [req.skill for req in requirements.technical if req.category == 'programming']
            
            result = {
                'job_id': job_id,
                'title': job_title[:100],  # Truncate for readability
                'location_city': metadata_location.get('city', ''),
                'location_valid': is_valid,
                'location_confidence': confidence,
                'location_details': details,
                'tech_requirements_count': tech_count,
                'business_requirements_count': business_count,
                'soft_skills_count': soft_skills_count,
                'experience_requirements_count': experience_count,
                'education_requirements_count': education_count,
                'tech_categories': ', '.join(tech_categories),
                'programming_languages': ', '.join(programming_langs),
                'full_requirements': asdict(requirements)
            }
            
            results.append(result)
            
        except Exception as e:
            print(f"Error processing {job_file.name}: {e}")
            continue
    
    return results

def generate_analysis_report(results: List[Dict]):
    """Generate comprehensive analysis report."""
    
    if not results:
        print("No results to analyze!")
        return
    
    print("\\n=== BATCH ANALYSIS RESULTS ===\\n")
    
    # Location validation analysis
    valid_locations = sum(1 for r in results if r['location_valid'])
    invalid_locations = len(results) - valid_locations
    avg_confidence = sum(r['location_confidence'] for r in results) / len(results)
    
    print("LOCATION VALIDATION ANALYSIS:")
    print(f"Total jobs analyzed: {len(results)}")
    print(f"Valid locations: {valid_locations}")
    print(f"Invalid locations: {invalid_locations}")
    print(f"Average location confidence: {avg_confidence:.2f}")
    
    # Group by location validation status
    print("\\nLocation issues by city:")
    city_issues = {}
    for r in results:
        if not r['location_valid']:
            city = r['location_city']
            city_issues[city] = city_issues.get(city, 0) + 1
    
    for city, count in sorted(city_issues.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {city}: {count} invalid")
    
    # Requirements extraction analysis
    avg_tech = sum(r['tech_requirements_count'] for r in results) / len(results)
    avg_business = sum(r['business_requirements_count'] for r in results) / len(results)
    avg_soft = sum(r['soft_skills_count'] for r in results) / len(results)
    avg_exp = sum(r['experience_requirements_count'] for r in results) / len(results)
    avg_edu = sum(r['education_requirements_count'] for r in results) / len(results)
    
    print("\\nREQUIREMENTS EXTRACTION ANALYSIS:")
    print(f"Average technical requirements per job: {avg_tech:.1f}")
    print(f"Average business requirements per job: {avg_business:.1f}")
    print(f"Average soft skills per job: {avg_soft:.1f}")
    print(f"Average experience requirements per job: {avg_exp:.1f}")
    print(f"Average education requirements per job: {avg_edu:.1f}")
    
    # Most common technical categories
    all_categories = []
    for r in results:
        if r['tech_categories']:
            all_categories.extend(r['tech_categories'].split(', '))
    
    category_counts = Counter(all_categories)
    print("\\nMost common technical categories:")
    for category, count in category_counts.most_common(5):
        print(f"  {category}: {count}")
    
    # Most common programming languages
    all_langs = []
    for r in results:
        if r['programming_languages']:
            all_langs.extend(r['programming_languages'].split(', '))
    
    lang_counts = Counter(all_langs)
    print("\\nMost common programming languages:")
    for lang, count in lang_counts.most_common(5):
        print(f"  {lang}: {count}")
    
    # Export results
    output_path = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/outbox')
    
    # Export summary as JSON (simplified without pandas)
    summary_results = []
    for r in results:
        summary = {k: v for k, v in r.items() if k != 'full_requirements'}
        summary_results.append(summary)
    
    with open(output_path / 'batch_analysis_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary_results, f, indent=2, ensure_ascii=False)
    
    # Export full results as JSON
    with open(output_path / 'batch_analysis_full.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\\nDetailed results exported to:")
    print(f"  - {output_path / 'batch_analysis_summary.json'}")
    print(f"  - {output_path / 'batch_analysis_full.json'}")
    
    return results

def identify_improvement_opportunities(results):
    """Identify specific improvement opportunities."""
    
    print("\\n=== IMPROVEMENT OPPORTUNITIES ===\\n")
    
    # Jobs with no requirements extracted
    no_tech = [r for r in results if r['tech_requirements_count'] == 0]
    if no_tech:
        print(f"Jobs with NO technical requirements extracted: {len(no_tech)}")
        for job in no_tech:
            print(f"  - {job['job_id']}: {job['title']}")
    
    # Jobs with location validation issues
    location_issues = [r for r in results if not r['location_valid']]
    if location_issues:
        print(f"\\nJobs with location validation issues: {len(location_issues)}")
        for job in location_issues[:5]:
            print(f"  - {job['job_id']} ({job['location_city']}): {job['location_details']}")
    
    # Jobs with very few requirements overall
    for r in results:
        r['total_requirements'] = (r['tech_requirements_count'] + 
                                  r['business_requirements_count'] + 
                                  r['experience_requirements_count'] + 
                                  r['education_requirements_count'])
    
    low_requirements = [r for r in results if r['total_requirements'] < 3]
    if low_requirements:
        print(f"\\nJobs with very few total requirements (<3): {len(low_requirements)}")
        for job in low_requirements:
            print(f"  - {job['job_id']}: {job['total_requirements']} total requirements")

if __name__ == "__main__":
    # Run batch analysis
    results = analyze_all_jobs()
    
    if results:
        generate_analysis_report(results)
        identify_improvement_opportunities(results)
    
    print("\\nBatch analysis complete!")
