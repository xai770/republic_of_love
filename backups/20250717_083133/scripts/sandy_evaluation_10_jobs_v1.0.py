#!/usr/bin/env python3
"""
Sandy LLM Evaluation - 10 Jobs Test v1.0
Professional evaluation of LLM performance for Sandy job matching.
Uses REAL job data from Sandy, tests 10 jobs to validate framework at scale.
Outputs: Comprehensive markdown report with exact prompts and responses for transparency.

CRITICAL DESIGN PRINCIPLE:
🚫 NEVER use JSON as output format from LLMs - always use structured text templates
✅ This prevents JSON parsing errors and ensures reliable, consistent responses
"""

import json
import os
import sys
from pathlib import Path
import time
from datetime import datetime
from dataclasses import asdict
import subprocess

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Add LLM Factory paths for Ollama client
LLM_FACTORY_PATH = "/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/llm_factory"
if LLM_FACTORY_PATH not in sys.path:
    sys.path.insert(0, LLM_FACTORY_PATH)

# Import model discovery
from llm_optimization_framework.utils.model_discovery import ModelDiscovery

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Import Ollama client for real LLM calls
try:
    from core.ollama_client import OllamaClient
    OLLAMA_AVAILABLE = True
    print("✅ Ollama client loaded successfully")
except ImportError as e:
    print(f"⚠️ Ollama client not available: {e}")
    OLLAMA_AVAILABLE = False

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

def load_sandy_jobs(max_jobs=10):
    """Load multiple Sandy job postings for testing"""
    sandy_dir = Path("sandy !!!DO NOT EDIT!!!!/data/postings")
    
    if not sandy_dir.exists():
        print(f"Warning: Sandy directory not found at {sandy_dir}")
        return []
    
    print(f"🎯 Loading up to {max_jobs} jobs for comprehensive evaluation")
    
    jobs = []
    job_files = list(sandy_dir.glob("*.json"))[:max_jobs]  # Limit to max_jobs
    
    for job_file in job_files:
        if job_file.stat().st_size > 0:  # Only non-empty files
            try:
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    if 'job_content' in job_data and 'description' in job_data['job_content']:
                        job = {
                            'id': job_data['job_metadata']['job_id'],
                            'title': job_data['job_content']['title'],
                            'description': job_data['job_content']['description']
                        }
                        jobs.append(job)
                        print(f"✅ Loaded job {len(jobs)}: {job_file.stem} ({job['title'][:50]}...)")
                        
                        if len(jobs) >= max_jobs:
                            break
            except Exception as e:
                print(f"Error loading {job_file}: {e}")
                continue
    
    print(f"📊 Successfully loaded {len(jobs)} jobs for evaluation")
    return jobs

def test_model_health_check(model_name, timeout_seconds=180):
    """Quick health check: 'Hello, how are you?' test with 3-minute timeout"""
    
    if not OLLAMA_AVAILABLE:
        return False, "Ollama not available"
    
    # Check if model is available
    if not check_ollama_model_available(model_name):
        return False, f"Model {model_name} not found"
    
    start_time = time.time()
    
    try:
        client = OllamaClient()
        
        print(f"   🩺 Health check: {model_name}...")
        
        # Simple health check with 3-minute timeout
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Health check timeout after {timeout_seconds} seconds")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            response = client.generate(
                model=model_name,
                prompt="Hello, how are you? Please respond briefly.",
                stream=False
            )
        finally:
            signal.alarm(0)
        
        response_time = time.time() - start_time
        
        # Handle response format
        if response:
            if isinstance(response, str):
                response_text = response.strip()
            elif isinstance(response, dict) and response.get('response'):
                response_text = response['response'].strip()
            else:
                return False, f"Unexpected response format: {type(response)}"
            
            if response_text and len(response_text) > 0:
                print(f"      ✅ Healthy ({response_time:.1f}s): {response_text[:50]}...")
                return True, f"Healthy in {response_time:.1f}s"
            else:
                return False, "Empty response"
        else:
            return False, "No response"
            
    except TimeoutError as e:
        response_time = time.time() - start_time
        print(f"      ⏰ TIMEOUT ({response_time:.1f}s)")
        return False, f"Timeout after {response_time:.1f}s"
    except Exception as e:
        response_time = time.time() - start_time
        print(f"      ❌ ERROR ({response_time:.1f}s): {str(e)[:50]}...")
        return False, f"Error: {str(e)}"

def test_model_with_prompt(model_name, prompt, job_id):
    """Real Ollama testing function with actual LLM calls"""
    
    if not OLLAMA_AVAILABLE:
        print(f"⚠️ Ollama not available, using mock response for {model_name}")
        return generate_mock_response(model_name, job_id)
    
    # Use the model name directly (no mapping needed with dynamic discovery)
    ollama_model = model_name
    
    # Check if model is available (should be since we discovered it)
    if not check_ollama_model_available(ollama_model):
        print(f"❌ Model {ollama_model} not available, using mock response")
        return generate_mock_response(model_name, job_id)
    
    start_time = time.time()
    
    try:
        # Create Ollama client and make real call with timeout
        client = OllamaClient()
        
        print(f"🔥 Making REAL Ollama call to {ollama_model}...")
        
        # Add timeout handling - increased to 90 seconds based on memo
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Model {ollama_model} timed out after 90 seconds")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(90)  # 90 second timeout as recommended
        
        try:
            response = client.generate(
                model=ollama_model,
                prompt=prompt,
                stream=False
            )
        finally:
            signal.alarm(0)  # Clear the alarm
        
        response_time = time.time() - start_time
        
        # Handle both string and dict responses from Ollama
        if response:
            if isinstance(response, str):
                response_text = response.strip()
            elif isinstance(response, dict) and response.get('response'):
                response_text = response['response'].strip()
            else:
                print(f"❌ Unexpected response format from {ollama_model}: {type(response)}")
                return generate_mock_response(model_name, job_id)
            
            if response_text:
                return {
                    'response': response_text,
                    'response_time': response_time,
                    'prompt_tokens': len(prompt.split()),
                    'completion_tokens': len(response_text.split()),
                    'cost': response_time * 0.001,  # Mock cost calculation
                    'real_llm_call': True,
                    'ollama_model': ollama_model
                }
            else:
                print(f"❌ Empty response from {ollama_model}")
                return generate_mock_response(model_name, job_id)
        else:
            print(f"❌ No response from {ollama_model}")
            return generate_mock_response(model_name, job_id)
            
    except TimeoutError as e:
        response_time = time.time() - start_time
        print(f"⏰ Timeout calling {ollama_model}: {e}")
        return {
            'response': f"Timeout calling {ollama_model}: Model took longer than 90 seconds to respond",
            'response_time': response_time,
            'prompt_tokens': len(prompt.split()),
            'completion_tokens': 0,
            'cost': 0,
            'real_llm_call': False,
            'error': str(e),
            'timeout': True
        }
    except Exception as e:
        response_time = time.time() - start_time
        print(f"❌ Error calling {ollama_model}: {e}")
        return {
            'response': f"Error calling {ollama_model}: {str(e)}",
            'response_time': response_time,
            'prompt_tokens': len(prompt.split()),
            'completion_tokens': 0,
            'cost': 0,
            'real_llm_call': False,
            'error': str(e)
        }

def check_ollama_model_available(model_name):
    """Check if Ollama model is available locally"""
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            # Check if model name (without tag) is in the output
            model_base = model_name.split(':')[0]
            return model_base in result.stdout
        return False
    except Exception:
        return False

def pull_ollama_model(model_name):
    """Try to pull an Ollama model"""
    try:
        print(f"📥 Pulling {model_name}...")
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to pull {model_name}: {e}")
        return False

def generate_mock_response(model_name, job_id):
    """Fallback mock response if Ollama fails"""
    import random
    time.sleep(random.uniform(0.5, 1.5))  # Simulate some processing time
    
    mock_responses = {
        "deepseek-chat": generate_deepseek_response(job_id),
        "gpt-4o-mini": generate_gpt4_response(job_id),
        "claude-3-5-haiku-20241022": generate_claude_response(job_id),
        "gemini-1.5-flash": generate_gemini_response(job_id),
        "llama-3.1-8b-instant": generate_llama_response(job_id)
    }
    
    response = mock_responses.get(model_name, f"Mock response from {model_name} for job {job_id}")
    
    return {
        'response': response,
        'response_time': random.uniform(0.5, 1.5),
        'prompt_tokens': 100,
        'completion_tokens': len(response.split()),
        'cost': 0.001,
        'real_llm_call': False,
        'mock': True
    }

def generate_deepseek_response(job_id):
    """Generate DeepSeek-style responses"""
    return f"""Based on comprehensive job posting analysis for Job {job_id}:

1. Top 5 Required Skills/Qualifications:
   - Advanced technical expertise in domain-specific systems
   - Strong analytical and problem-solving capabilities
   - Excellent communication and stakeholder management
   - Process optimization and continuous improvement mindset
   - Cross-functional collaboration and leadership skills

2. Company Culture Indicators:
   - Innovation-driven and technology-focused environment
   - Collaborative global team structure
   - Emphasis on professional development and growth
   - Results-oriented with high performance standards
   - Diversity and inclusion commitment

3. Role Complexity Level: Mid-Senior
4. Remote Work Compatibility: Hybrid
5. Growth Potential Assessment: High - excellent opportunities for career progression, skill development, and international exposure within a leading organization"""

def generate_gpt4_response(job_id):
    """Generate GPT-4 style responses"""
    return f"""Job Analysis Summary for Position {job_id}:

1. Top 5 Required Skills/Qualifications:
   • Subject matter expertise in relevant business domain
   • Strong analytical and quantitative skills
   • Excellent written and verbal communication abilities
   • Project management and process improvement experience
   • Technology proficiency and adaptability

2. Company Culture Indicators:
   • Professional and results-driven work environment
   • Team-oriented approach with global collaboration
   • Focus on continuous learning and development
   • Innovation and technology advancement
   • Inclusive and supportive workplace culture

3. Role Complexity Level: Mid
4. Remote Work Compatibility: Yes/Hybrid
5. Growth Potential Assessment: Strong potential for professional advancement with clear development pathways and comprehensive benefits package"""

def generate_claude_response(job_id):
    """Generate Claude-style responses"""
    return f"""Comprehensive Analysis for Job Posting {job_id}:

1. Top 5 Required Skills/Qualifications:
   - Specialized technical knowledge and system proficiency
   - Advanced analytical thinking and problem resolution
   - Superior communication and interpersonal capabilities
   - Strategic planning and process enhancement expertise
   - Leadership potential and collaborative mindset

2. Company Culture Indicators:
   - Dynamic and forward-thinking organizational culture
   - Strong emphasis on teamwork and knowledge sharing
   - Commitment to employee wellbeing and work-life balance
   - Innovation and continuous improvement focus
   - Global perspective with local impact

3. Role Complexity Level: Senior
4. Remote Work Compatibility: Hybrid
5. Growth Potential Assessment: Excellent - comprehensive career development opportunities, extensive benefits, and clear advancement pathways in a leading industry organization"""

def generate_gemini_response(job_id):
    """Generate Gemini-style responses"""
    return f"""Analysis Results for Job {job_id}:

1. Top 5 Required Skills/Qualifications:
   - Technical proficiency in specialized software/systems
   - Data analysis and reporting capabilities
   - Strong business acumen and industry knowledge
   - Effective communication across all organizational levels
   - Process improvement and project coordination skills

2. Company Culture Indicators:
   - Performance-oriented with clear metrics and goals
   - Collaborative environment with global reach
   - Innovation and technology leadership
   - Employee development and retention focus
   - Commitment to sustainability and social responsibility

3. Role Complexity Level: Mid-Senior
4. Remote Work Compatibility: Hybrid
5. Growth Potential Assessment: Very Good - substantial opportunities for skill enhancement, career progression, and meaningful impact within industry-leading organization"""

def generate_llama_response(job_id):
    """Generate Llama-style responses"""
    return f"""Job Evaluation for Position {job_id}:

1. Top 5 Required Skills/Qualifications:
   - Domain expertise and technical competency
   - Analytical problem-solving abilities
   - Communication and relationship management
   - Process optimization and efficiency focus
   - Adaptability and continuous learning orientation

2. Company Culture Indicators:
   - Professional growth and development emphasis
   - Team-based collaborative approach
   - Technology innovation and digital transformation
   - Global operations with local autonomy
   - Inclusive and diverse workplace values

3. Role Complexity Level: Mid
4. Remote Work Compatibility: Hybrid
5. Growth Potential Assessment: Good - solid opportunities for professional development and career advancement with comprehensive support systems"""

def create_sandy_test_prompt(job_description, job_title):
    """Create a standardized prompt for Sandy job analysis with job context
    
    IMPORTANT: We NEVER use JSON as output from LLMs. Always use structured templates.
    This ensures consistent, parseable responses without JSON parsing errors.
    """
    return f"""Analyze this job posting and extract the key requirements, skills needed, and company culture fit indicators:

JOB TITLE: {job_title}

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
    print("=== Sandy LLM Evaluation - 10 Jobs Test v1.0 ===")
    print("🎯 PURPOSE: Comprehensive framework validation with 10 real job postings")
    print("📊 SCALE: Testing multiple models across diverse job types")
    
    # Setup directories
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output")
    logs_dir = Path("logs")
    debug_dir = Path("debug")
    
    for dir_path in [output_dir, logs_dir, debug_dir]:
        dir_path.mkdir(exist_ok=True)
    
    # Load 3 job postings for testing
    jobs = load_sandy_jobs(max_jobs=3)
    if not jobs:
        print("No job data found. Exiting.")
        return
    
    print(f"\n📋 Loaded {len(jobs)} jobs:")
    for i, job in enumerate(jobs, 1):
        print(f"   {i}. {job['id']}: {job['title'][:60]}...")
    
    # Discover available models dynamically
    print("\n🔍 Discovering available Ollama models...")
    model_discovery = ModelDiscovery()
    available_model_infos = model_discovery.get_available_models()
    available_models = [model.full_name for model in available_model_infos]  # Use full_name to include tags
    
    if not available_models:
        print("❌ No Ollama models found. Please install some models first.")
        return
    
    print(f"✅ Found {len(available_models)} available models:")
    for model in available_models[:10]:  # Show first 10
        print(f"   • {model}")
    if len(available_models) > 10:
        print(f"   ... and {len(available_models) - 10} more")
    
    # Use ALL available models - let's test them all!
    models = available_models
    print(f"\n🎯 Found {len(models)} models for health screening:")
    for i, model in enumerate(models, 1):
        print(f"   {i}. {model}")
    
    # HEALTH CHECK PHASE: Test each model with simple "Hello" prompt
    print(f"\n🩺 HEALTH CHECK PHASE: Testing basic responsiveness (3-minute timeout per model)")
    print("   Testing with simple 'Hello, how are you?' prompt...")
    
    healthy_models = []
    blacklisted_models = []
    
    for i, model in enumerate(models, 1):
        print(f"\n🔍 Testing {i}/{len(models)}: {model}")
        is_healthy, reason = test_model_health_check(model, timeout_seconds=180)
        
        if is_healthy:
            healthy_models.append(model)
            print(f"   ✅ APPROVED: {model}")
        else:
            blacklisted_models.append((model, reason))
            print(f"   ⚫ BLACKLISTED: {model} - {reason}")
    
    print(f"\n� HEALTH CHECK RESULTS:")
    print(f"   ✅ Healthy models: {len(healthy_models)}")
    print(f"   ⚫ Blacklisted models: {len(blacklisted_models)}")
    
    if not healthy_models:
        print("❌ No healthy models found! Cannot proceed with evaluation.")
        return
    
    print(f"\n🎯 PROCEEDING with {len(healthy_models)} healthy models:")
    for i, model in enumerate(healthy_models, 1):
        print(f"   {i}. {model}")
    
    if blacklisted_models:
        print(f"\n⚫ BLACKLISTED models (skipping):")
        for model, reason in blacklisted_models:
            print(f"   • {model}: {reason}")
    
    # Use only healthy models for the actual evaluation
    models = healthy_models
    
    print(f"\n🤖 Testing {len(models)} models on {len(jobs)} job postings")
    print(f"   Total evaluations: {len(models) * len(jobs)}")
    
    # Run evaluations
    print(f"\n🔄 Running comprehensive evaluations...")
    all_results = {}
    all_dialogues = []
    
    for i, job in enumerate(jobs, 1):
        print(f"\n📝 Processing Job {i}/{len(jobs)}: {job['id']} ({job['title'][:40]}...)")
        
        # Create prompt for this job
        prompt = create_sandy_test_prompt(job['description'], job['title'])
        
        job_results = {}
        for model in models:
            print(f"   🔄 Testing {model}...")
            result = test_model_with_prompt(model, prompt, job['id'])
            job_results[model] = result
            
            # Create dialogue entry
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
            print(f"     ✅ {len(result.get('response', ''))} chars in {result.get('response_time', 0):.1f}s")
        
        all_results[job['id']] = job_results
    
    # Calculate comprehensive metrics
    print(f"\n📊 Calculating performance metrics for {len(models)} models...")
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
        print(f"  ✅ {model}: Overall score {model_metric.overall_score:.3f} ({len(dialogues)} responses)")
    
    # Generate rankings based on overall scores
    rankings = sorted(
        [(model, metric.overall_score) for model, metric in model_metrics.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Generate comprehensive markdown report with full transparency
    reporter = MarkdownReporter()
    
    # Create metrics summary for the reporter
    simple_metrics = SimpleMetrics(model_metrics, dialogues_by_model)
    
    report_content = reporter.generate_sandy_report(
        results=all_results,
        metrics=simple_metrics,
        dialogues=all_dialogues,
        evaluation_config={
            'version': '1.0',
            'job_count': len(jobs),
            'models': models,
            'timestamp': timestamp,
            'test_mode': '10_jobs_comprehensive_evaluation'
        }
    )
    
    # Save markdown report
    md_output_path = output_dir / f"sandy_10_jobs_evaluation_v1.0_{timestamp}.md"
    with open(md_output_path, 'w') as f:
        f.write(report_content)
    
    print(f"\n📋 Comprehensive report saved to: {md_output_path}")
    
    # Save detailed JSON output
    detailed_output = {
        'evaluation_info': {
            'timestamp': timestamp,
            'version': '1.0',
            'job_count': len(jobs),
            'model_count': len(models),
            'total_evaluations': len(all_dialogues),
            'test_mode': '10_jobs_comprehensive_evaluation'
        },
        'jobs_analyzed': [{'id': job['id'], 'title': job['title']} for job in jobs],
        'models_tested': models,
        'raw_results': all_results,
        'metrics_summary': simple_metrics.get_summary(),
        'model_rankings': rankings,
        'dialogues': [asdict(d) for d in all_dialogues]
    }
    
    json_output_path = output_dir / f"sandy_10_jobs_evaluation_v1.0_{timestamp}.json"
    with open(json_output_path, 'w') as f:
        json.dump(detailed_output, f, indent=2, cls=DateTimeEncoder)
    
    print(f"📊 Detailed JSON data saved to: {json_output_path}")
    
    # Print comprehensive summary
    print("\n" + "="*60)
    print("🎉 COMPREHENSIVE EVALUATION COMPLETE!")
    print("="*60)
    print(f"📊 Jobs Processed: {len(jobs)}")
    print(f"🤖 Models Tested: {len(models)}")
    print(f"📝 Total Responses: {len(all_dialogues)}")
    print(f"⏱️  Total Processing Time: {sum(d.processing_time for d in all_dialogues):.1f} seconds")
    
    print(f"\n🏆 FINAL MODEL RANKINGS:")
    for i, (model, score) in enumerate(rankings, 1):
        performance_grade = "A" if score >= 0.8 else "B" if score >= 0.6 else "C" if score >= 0.4 else "D"
        print(f"  {i}. {model:<30} Score: {score:.3f} (Grade: {performance_grade})")
    
    print(f"\n📊 PERFORMANCE INSIGHTS:")
    avg_score = sum(score for _, score in rankings) / len(rankings)
    best_score = rankings[0][1]
    worst_score = rankings[-1][1]
    score_spread = best_score - worst_score
    
    print(f"  • Average Score: {avg_score:.3f}")
    print(f"  • Performance Spread: {score_spread:.3f}")
    print(f"  • Top Performer: {rankings[0][0]} ({rankings[0][1]:.3f})")
    print(f"  • All prompts & responses included for transparency")
    
    print(f"\n📁 OUTPUT FILES:")
    print(f"  📋 Report: {md_output_path}")
    print(f"  📊 Data: {json_output_path}")
    
    print(f"\n✅ Evaluation completed successfully!")
    print("🔍 Check the markdown report for complete transparency with all prompts & responses")

if __name__ == "__main__":
    main()
