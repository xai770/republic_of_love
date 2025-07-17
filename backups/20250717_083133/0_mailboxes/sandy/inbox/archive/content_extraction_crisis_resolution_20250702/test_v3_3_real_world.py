#!/usr/bin/env python3
"""
Content Extraction Specialist v3.3 - Real World Testing Script
===============================================================

Tests the production-ready v3.3 specialist on real Deutsche Bank job data
to validate performance with live pipeline data.
"""

import sys
import json
import time
from pathlib import Path

# Import the production specialist
sys.path.append('/home/xai/Documents/sandy/0_mailboxes/sandy@consciousness/inbox')
from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33

def load_job_data(job_file_path):
    """Load job data from our pipeline"""
    try:
        with open(job_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {job_file_path}: {e}")
        return None

def get_job_description(job_data):
    """Extract job description from our pipeline format"""
    # Try multiple possible locations for job description
    desc_sources = [
        job_data.get('web_details', {}).get('concise_description', ''),
        job_data.get('web_details', {}).get('full_description', ''),
        job_data.get('job_content', {}).get('description', ''),
        job_data.get('api_details', {}).get('PositionFormattedDescription', {}).get('Content', '')
    ]
    
    for desc in desc_sources:
        if desc and len(desc.strip()) > 100:  # Must be substantial content
            return desc.strip()
    
    return None

def test_specialist_on_real_jobs():
    """Test the specialist on real job data"""
    print("Content Extraction Specialist v3.3 - Real World Testing")
    print("=" * 60)
    
    # Initialize specialist
    specialist = ContentExtractionSpecialistV33()
    
    # Find job files
    job_data_dir = Path('/home/xai/Documents/sandy/data/postings')
    job_files = sorted(list(job_data_dir.glob('job*.json')))[:5]  # Test first 5 jobs
    
    print(f"Testing on {len(job_files)} real jobs from pipeline...")
    print()
    
    results = []
    
    for job_file in job_files:
        job_id = job_file.stem.replace('job', '')
        print(f"Testing Job {job_id}...")
        
        # Load job data
        job_data = load_job_data(job_file)
        if not job_data:
            print(f"  ❌ Failed to load job data")
            continue
            
        # Get job description
        job_description = get_job_description(job_data)
        if not job_description:
            print(f"  ❌ No job description found")
            continue
            
        # Get job title for context
        job_title = job_data.get('web_details', {}).get('position_title', 'Unknown Title')
        print(f"  📋 Title: {job_title}")
        print(f"  📝 Description: {len(job_description)} characters")
        
        # Test the specialist
        start_time = time.time()
        try:
            result = specialist.extract_skills(job_description)
            processing_time = time.time() - start_time
            
            # Extract skills from the result object
            skills = result.all_skills if hasattr(result, 'all_skills') else []
            technical_skills = result.technical_skills if hasattr(result, 'technical_skills') else []
            soft_skills = result.soft_skills if hasattr(result, 'soft_skills') else []
            
            print(f"  ⏱️  Processing: {processing_time:.1f}s")
            print(f"  🔧 Total skills: {len(skills)}")
            print(f"  � Technical skills: {len(technical_skills)}")
            print(f"  🤝 Soft skills: {len(soft_skills)}")
            
            # Show sample skills (first 3)
            if skills:
                sample_skills = skills[:3]
                print(f"  💡 Sample skills: {', '.join(sample_skills)}")
            
            # Validate format compliance
            format_clean = True
            format_issues = []
            
            for skill in skills:
                if any(char in skill for char in ['1.', '2.', '3.', '(', ')']):
                    format_clean = False
                    format_issues.append(skill)
            
            print(f"  ✅ Format clean: {'YES' if format_clean else 'NO'}")
            if format_issues:
                print(f"  ⚠️  Format issues in: {format_issues[:2]}")
            
            results.append({
                'job_id': job_id,
                'job_title': job_title,
                'processing_time': processing_time,
                'skills_count': len(skills),
                'technical_skills_count': len(technical_skills),
                'soft_skills_count': len(soft_skills),
                'format_clean': format_clean,
                'status': 'SUCCESS'
            })
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'job_id': job_id,
                'job_title': job_title,
                'status': 'ERROR',
                'error': str(e)
            })
        
        print()
    
    # Summary
    print("=" * 60)
    print("REAL WORLD TESTING SUMMARY")
    print("=" * 60)
    
    successful_tests = [r for r in results if r['status'] == 'SUCCESS']
    failed_tests = [r for r in results if r['status'] == 'ERROR']
    
    print(f"Total tests: {len(results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if successful_tests:
        avg_processing_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
        avg_skills = sum(r['skills_count'] for r in successful_tests) / len(successful_tests)
        format_compliant = sum(1 for r in successful_tests if r['format_clean'])
        
        print(f"Average processing time: {avg_processing_time:.1f}s")
        print(f"Average skills extracted: {avg_skills:.1f}")
        print(f"Format compliance: {format_compliant}/{len(successful_tests)} ({format_compliant/len(successful_tests)*100:.0f}%)")
        
        print()
        print("SUCCESS: v3.3 specialist working on real pipeline data! 🎉")
    else:
        print("No successful tests - specialist needs debugging")
    
    return results

if __name__ == "__main__":
    test_specialist_on_real_jobs()
