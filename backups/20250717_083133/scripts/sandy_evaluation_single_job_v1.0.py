#!/usr/bin/env python3
"""
Sandy LLM Evaluation - Single Job Test v1.0
Professional evaluation of LLM performance for Sandy job matching.
Uses REAL job data from Sandy, tests 1 job to validate framework.
Outputs: Markdown report with exact prompts and responses for transparency.
"""

import json
import os
import sys
from pathlib import Path
import time
from datetime import datetime
from dataclasses import asdict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

from llm_optimization_framework.core.metrics import PerformanceMetrics
from llm_optimization_framework.reporters.markdown import MarkdownReporter
from llm_optimization_framework.utils.dialogue_parser import DialogueEntry

class SimpleMetrics:
    """Simple metrics wrapper for Sandy evaluation"""
    
    def __init__(self, model_metrics, dialogues_by_model):
        self.model_metrics = model_metrics
        self.dialogues_by_model = dialogues_by_model
    
    def get_model_rankings(self):
        """Get model rankings sorted by overall score"""
        return sorted(
            [(model, metric.overall_score) for model, metric in self.model_metrics.items()],
            key=lambda x: x[1],
            reverse=True
        )
    
    def get_summary(self):
        """Get summary statistics for each model"""
        summary = {}
        for model, dialogues in self.dialogues_by_model.items():
            metrics = self.model_metrics[model]
            summary[model] = {
                'response_count': len(dialogues),
                'avg_response_length': sum(d.response_length for d in dialogues) / len(dialogues),
                'avg_response_time': sum(d.processing_time for d in dialogues) / len(dialogues),
                'overall_score': metrics.overall_score,
                'consistency_score': metrics.category_scores.get('consistency', 0)
            }
        return summary

def load_single_sandy_job(max_jobs=1):
    """Load one Sandy job posting for testing (explicitly limited to 1 job)"""
    sandy_dir = Path("sandy !!!DO NOT EDIT!!!!/data/postings")
    
    if not sandy_dir.exists():
        print(f"Warning: Sandy directory not found at {sandy_dir}")
        return None
    
    print(f"🎯 Loading exactly {max_jobs} job(s) for single job validation test")
    
    # Find first non-empty job JSON file
    for job_file in sandy_dir.glob("*.json"):
        if job_file.stat().st_size > 0:  # Only non-empty files
            try:
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    if 'job_content' in job_data and 'description' in job_data['job_content']:
                        print(f"✅ Selected job: {job_file.stem} ({job_data['job_content']['title'][:50]}...)")
                        return {
                            'id': job_data['job_metadata']['job_id'],
                            'title': job_data['job_content']['title'],
                            'description': job_data['job_content']['description']
                        }
            except Exception as e:
                print(f"Error loading {job_file}: {e}")
                continue
    
    print("No valid job data found.")
    return None

def test_model_with_prompt(model_name, prompt):
    """Simple mock testing function - replace with actual LLM calls"""
    import time
    import random
    
    # Simulate processing time
    start_time = time.time()
    time.sleep(random.uniform(0.5, 2.0))  # Simulate API call
    
    # Mock response based on model name
    mock_responses = {
        "deepseek-chat": """Based on the job posting analysis:

1. Top 5 Required Skills/Qualifications:
   - Strong programming experience in relevant technologies
   - Problem-solving and analytical thinking
   - Communication and collaboration skills
   - Experience with software development lifecycle
   - Ability to work in fast-paced environment

2. Company Culture Indicators:
   - Innovation-focused environment
   - Collaborative team structure
   - Growth-oriented mindset
   - Technology-driven company

3. Role Complexity Level: Mid-Senior
4. Remote Work Compatibility: Hybrid
5. Growth Potential Assessment: High - opportunities for skill development and career advancement""",
        
        "gpt-4o-mini": """Job Analysis Summary:

1. Top 5 Required Skills/Qualifications:
   • Technical expertise in specified domain
   • Strong communication abilities
   • Problem-solving capabilities
   • Relevant educational background
   • Professional experience

2. Company Culture Indicators:
   • Professional work environment
   • Team-oriented approach
   • Focus on quality and results
   • Supportive learning culture

3. Role Complexity Level: Mid
4. Remote Work Compatibility: Yes
5. Growth Potential Assessment: Good potential for professional development and advancement""",
        
        "claude-3-5-haiku-20241022": """Analysis of Job Posting:

1. Top 5 Required Skills/Qualifications:
   - Domain-specific technical skills
   - Strong analytical and problem-solving abilities
   - Excellent communication and interpersonal skills
   - Relevant work experience or education
   - Adaptability and continuous learning mindset

2. Company Culture Indicators:
   - Dynamic and innovative workplace
   - Emphasis on collaboration and teamwork
   - Commitment to professional growth
   - Results-driven environment

3. Role Complexity Level: Senior
4. Remote Work Compatibility: Hybrid
5. Growth Potential Assessment: Excellent - clear pathways for advancement and skill development"""
    }
    
    response = mock_responses.get(model_name, f"Mock response from {model_name}")
    response_time = time.time() - start_time
    
    return {
        'response': response,
        'response_time': response_time,
        'prompt_tokens': len(prompt.split()),
        'completion_tokens': len(response.split()),
        'cost': response_time * 0.001  # Mock cost calculation
    }

def create_sandy_test_prompt(job_description):
    """Create a standardized prompt for Sandy job analysis"""
    return f"""Analyze this job posting and extract the key requirements, skills needed, and company culture fit indicators:

JOB POSTING:
{job_description}

Please provide:
1. Top 5 required skills/qualifications
2. Company culture indicators
3. Role complexity level (Junior/Mid/Senior)
4. Remote work compatibility (Yes/No/Hybrid)
5. Growth potential assessment

Keep your response concise but comprehensive."""

def main():
    print("=== Sandy LLM Evaluation - Single Job Test v1.0 ===")
    print("🎯 PURPOSE: Validate framework with exactly 1 job before scaling up")
    
    # Setup directories
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output")
    logs_dir = Path("logs")
    debug_dir = Path("debug")
    
    for dir_path in [output_dir, logs_dir, debug_dir]:
        dir_path.mkdir(exist_ok=True)
    
    # Load single job data (explicitly limited to 1)
    job = load_single_sandy_job(max_jobs=1)
    if not job:
        print("No job data found. Exiting.")
        return
    
    print(f"\n📋 Job Details:")
    print(f"   ID: {job['id']}")
    print(f"   Title: {job['title']}")
    print(f"   Description length: {len(job['description'])} characters")
    
    # Models to test (start with a smaller set for single job test)
    models = [
        "deepseek-chat",
        "gpt-4o-mini", 
        "claude-3-5-haiku-20241022"
    ]
    
    print(f"\n🤖 Testing {len(models)} models on exactly 1 job posting")
    print("   This validates framework before scaling to multiple jobs")
    
    # Create prompt
    prompt = create_sandy_test_prompt(job['description'])
    print(f"\n📝 Prompt created ({len(prompt)} characters)")
    
    # Run evaluations
    print(f"\n🔄 Running evaluations...")
    job_results = {}
    
    for model in models:
        print(f"  Testing {model}...")
        result = test_model_with_prompt(model, prompt)
        job_results[model] = result
    
    all_dialogues = []
    
    # Store dialogues for reporting
    for model, result in job_results.items():
        dialogue = DialogueEntry(
            model_name=model,
            test_type="job_analysis",
            test_id=job['id'],
            processing_time=result.get('response_time', 0),
            response_length=len(result.get('response', '')),
            response_text=result.get('response', ''),
            prompt_text=prompt,
            success=True,
            timestamp=datetime.fromtimestamp(time.time()),
            metadata={'job_title': job['title']}
        )
        all_dialogues.append(dialogue)
        print(f"  ✅ {model}: {len(result.get('response', ''))} chars")
    
    # Calculate metrics using DialogueEntry objects
    print("\nCalculating performance metrics...")
    metrics = PerformanceMetrics()
    
    # Group dialogues by model for metrics calculation
    dialogues_by_model = {}
    for dialogue in all_dialogues:
        model = dialogue.model_name
        if model not in dialogues_by_model:
            dialogues_by_model[model] = []
        dialogues_by_model[model].append(dialogue)
    
    # Calculate metrics for each model
    model_metrics = {}
    for model, dialogues in dialogues_by_model.items():
        model_metric = metrics.calculate_model_metrics(dialogues, model)
        model_metrics[model] = model_metric
        print(f"  ✅ {model}: Overall score {model_metric.overall_score:.3f}")
    
    # Generate rankings based on overall scores
    rankings = sorted(
        [(model, metric.overall_score) for model, metric in model_metrics.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Generate comprehensive markdown report with full transparency
    reporter = MarkdownReporter()
    
    # Create a simple metrics summary for the reporter
    simple_metrics = SimpleMetrics(model_metrics, dialogues_by_model)
    
    report_content = reporter.generate_sandy_report(
        results={job['id']: job_results},
        metrics=simple_metrics,
        dialogues=all_dialogues,
        evaluation_config={
            'version': '1.0',
            'job_count': 1,
            'models': models,
            'timestamp': timestamp,
            'test_mode': 'single_job_validation'
        }
    )
    
    # Save markdown report
    md_output_path = output_dir / f"sandy_single_job_test_v1.0_{timestamp}.md"
    with open(md_output_path, 'w') as f:
        f.write(report_content)
    
    print(f"Report saved to: {md_output_path}")
    
    # Save detailed JSON output
    detailed_output = {
        'test_info': {
            'timestamp': timestamp,
            'version': '1.0',
            'job_id': job['id'],
            'models_tested': models,
            'test_mode': 'single_job_validation'
        },
        'job_data': job,
        'raw_results': job_results,
        'metrics_summary': simple_metrics.get_summary(),
        'model_rankings': rankings,
        'dialogues': [asdict(d) for d in all_dialogues]
    }
    
    json_output_path = output_dir / f"sandy_single_job_test_v1.0_{timestamp}.json"
    with open(json_output_path, 'w') as f:
        json.dump(detailed_output, f, indent=2, cls=DateTimeEncoder)
    
    print(f"JSON data saved to: {json_output_path}")
    
    # Print summary
    print("\n=== TEST SUMMARY ===")
    print(f"Job processed: {job['id']}")
    print(f"Models tested: {len(models)}")
    print(f"Total responses: {len(all_dialogues)}")
    
    print("\n=== MODEL RANKINGS ===")
    for i, (model, score) in enumerate(rankings, 1):
        print(f"{i}. {model}: {score:.3f}")
    
    print(f"\nTest completed successfully!")
    print(f"Report: {md_output_path}")
    print(f"Data: {json_output_path}")

if __name__ == "__main__":
    main()
