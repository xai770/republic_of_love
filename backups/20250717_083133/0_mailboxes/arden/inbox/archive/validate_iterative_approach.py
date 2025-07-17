#!/usr/bin/env python3
"""
Validate the iterative prompt refinement approach on full golden test dataset
"""

import json
import requests
import time
from datetime import datetime

def load_test_cases():
    """Load golden test cases"""
    with open('golden_test_cases_content_extraction_v2.json', 'r') as f:
        return json.load(f)

def extract_skills_with_iterative_prompt(job_description):
    """Extract skills using the final optimized prompt from iterative refinement"""
    
    # This is the final prompt that achieved 100% on the test case
    optimized_prompt = """Extract specific skills, techniques, frameworks, tools, and methodologies from this job description with extreme precision. Focus on exact term matching:

FOR BUSINESS/FINANCIAL SKILLS:
- Look for exact domain terms like "FX Trading", "Derivatives", "Risk Management" 
- Don't generalize "FX Trading" to just "Trading"
- Capture financial methodologies like "Hedge Accounting", "Quantitative Analysis"

FOR TECHNICAL SKILLS:
- Extract exact tool names, programming languages, frameworks
- Preserve specific version numbers or variants when mentioned

FOR SOFT SKILLS:
- Identify relationship and management skills like "Client Relationship Management"
- Extract process skills like "Sales", "Project Management"

CRITICAL RULES:
1. Use EXACT terminology from the job description
2. Don't summarize or generalize specific terms
3. Extract both obvious and implied skills
4. Include domain-specific jargon and technical terms
5. Capture methodologies, frameworks, and approaches

Return ONLY a JSON list of extracted skills, nothing else.

Job Description:
{job_description}"""

    try:
        response = ollama.chat(
            model='llama3.1:8b',
            messages=[
                {
                    'role': 'user', 
                    'content': optimized_prompt.format(job_description=job_description)
                }
            ],
            stream=False
        )
        
        response_text = response['message']['content'].strip()
        
        # Try to parse JSON from response
        if response_text.startswith('[') and response_text.endswith(']'):
            return json.loads(response_text)
        else:
            # Try to find JSON in the response
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            if start != -1 and end != 0:
                return json.loads(response_text[start:end])
            else:
                print(f"⚠️ Could not parse JSON from response: {response_text}")
                return []
                
    except Exception as e:
        print(f"❌ Error extracting skills: {e}")
        return []

def calculate_accuracy(extracted_skills, expected_skills):
    """Calculate skill extraction accuracy"""
    if not expected_skills:
        return 0.0
    
    matched = 0
    for expected in expected_skills:
        if expected in extracted_skills:
            matched += 1
    
    return (matched / len(expected_skills)) * 100

def main():
    print("🌸 VALIDATING ITERATIVE APPROACH ON FULL DATASET")
    print("=" * 60)
    
    test_cases = load_test_cases()
    total_accuracy = 0
    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 Test {i+1}/{len(test_cases)}: {test_case['role']}")
        
        extracted_skills = extract_skills_with_iterative_prompt(test_case['job_description'])
        expected_skills = test_case['expected_skills']
        accuracy = calculate_accuracy(extracted_skills, expected_skills)
        
        print(f"📊 Accuracy: {accuracy:.1f}% ({len([s for s in expected_skills if s in extracted_skills])}/{len(expected_skills)})")
        print(f"✅ Matched: {[s for s in expected_skills if s in extracted_skills]}")
        print(f"❌ Missed: {[s for s in expected_skills if s not in extracted_skills]}")
        if extracted_skills:
            extra = [s for s in extracted_skills if s not in expected_skills]
            if extra:
                print(f"➕ Extra: {extra}")
        
        total_accuracy += accuracy
        
        results.append({
            'role': test_case['role'],
            'expected_skills': expected_skills,
            'extracted_skills': extracted_skills,
            'accuracy': accuracy,
            'matched': [s for s in expected_skills if s in extracted_skills],
            'missed': [s for s in expected_skills if s not in extracted_skills],
            'extra': [s for s in extracted_skills if s not in expected_skills]
        })
        
        time.sleep(1)  # Be nice to the API
    
    overall_accuracy = total_accuracy / len(test_cases)
    
    print(f"\n" + "=" * 60)
    print(f"📊 OVERALL RESULTS")
    print(f"🎯 Average Accuracy: {overall_accuracy:.1f}%")
    print(f"🏆 Target (90%): {'✅ ACHIEVED!' if overall_accuracy >= 90 else '❌ Not reached'}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"iterative_approach_validation_{timestamp}.json"
    
    final_results = {
        'approach': 'Iterative Prompt Refinement',
        'overall_accuracy': overall_accuracy,
        'target_achieved': overall_accuracy >= 90,
        'test_cases': results,
        'timestamp': timestamp
    }
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"💾 Results saved to: {results_file}")
    
    return overall_accuracy >= 90

if __name__ == "__main__":
    main()
